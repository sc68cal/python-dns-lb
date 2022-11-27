import aiohttp
import asyncio
import os
import socket
import sys

import dns
from dns import message
from dns.rdtypes.IN.A import A as A_RECORD

try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

server_query = """
SELECT host FROM dns_zone_member
JOIN dns_zone ON dns_zone_member.dns_zone = dns_zone.id
WHERE dns_zone.name=?
"""


class DnsServerProtocol:
    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):

        loop = asyncio.get_event_loop()

        loop.create_task(self.check_servers(data, addr))

    async def check_servers(self, data, addr):
        dq = message.from_wire(data)
        print('Received %r from %s' % (dq, addr))

        domain = dq.question[0].name.to_text()
        servers = await self.get_servers_for_domain(domain)
        checks = []
        for server in servers:
            checks.append(self.check_server(server))

        results = await asyncio.gather(*checks)
        output = message.make_response(dq)
        rdclass = dns.rdataclass.from_text('IN')
        rdtype = dns.rdatatype.A
        dnsname = dns.name.from_text(domain)

        records = []

        # TODO - implement round-robin instead of returning all
        for server, alive in results:
            if alive:
                records.append(A_RECORD(rdclass, rdtype, server))

        rrset = dns.rrset.from_rdata(dnsname, 9600,*records)
        output.answer.append(rrset)

        print('Send %r to %s' % (output, addr))
        self.transport.sendto(output.to_wire(), addr)

    async def check_server(self, server):
        async with aiohttp.ClientSession() as session:
            async with session.get("http://"+server) as response:
                return (server, response.status == 200)

    async def get_servers_for_domain(self, domain):
        query = [[server_query, domain]]
        async with aiohttp.ClientSession() as session:
            async with session.post("http://127.0.0.1:4001/db/query?associative",
                                    json=query) as resp:
                data = await resp.json()
                return [x['host'] for x in data['results'][0]['rows']]


def main():
    print("Starting UDP server")

    # Create an event loop
    loop = asyncio.new_event_loop()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if os.name == 'posix' and sys.platform != 'cygwin':
        if os.uname().sysname == 'FreeBSD':
            opt = 0x10000  # SO_REUSEPORT_LB on FreeBSD
        else:
            opt = socket.SO_REUSEPORT
        sock.setsockopt(socket.SOL_SOCKET, opt, 1)

    sock.bind(("127.0.0.1", 9999))

    # One protocol instance will be created to serve all
    # client requests.
    t = loop.create_datagram_endpoint(
        lambda: DnsServerProtocol(),
        sock=sock
    )

    loop.run_until_complete(t)
    loop.run_forever()


if __name__ == "__main__":
    main()
