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
SELECT dns_zone_member.id, host FROM dns_zone_member
JOIN dns_zone ON dns_zone_member.dns_zone = dns_zone.id
WHERE dns_zone.name=?
"""

db_host = '127.0.0.1'


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

        domain_id = await self.get_domain_id(domain)

        servers = await self.get_servers_for_domain(domain)

        exclude = await self.get_last_server_round_robin(domain_id)

        to_check = list(filter(lambda x: x['id'] != exclude, servers))

        checks = []
        for server in to_check:
            checks.append(self.check_server(server['host']))

        results = await asyncio.gather(*checks)

        output = message.make_response(dq)
        rdclass = dns.rdataclass.from_text('IN')
        rdtype = dns.rdatatype.A
        dnsname = dns.name.from_text(domain)

        records = []

        for server, alive in results:
            if alive:
                records.append(A_RECORD(rdclass, rdtype, server))
                server_id = list(filter(lambda x: x['host'] == server, servers))[0]['id']
                await self.update_server_round_robin(server_id, domain_id)
                break

        rrset = dns.rrset.from_rdata(dnsname, 9600, *records)
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
            async with session.post(f"http://{db_host}:4001/db/query?associative",
                                    json=query) as resp:
                data = await resp.json()
                return data['results'][0]['rows']

    async def get_domain_id(self, domain):
        query = [["SELECT id FROM dns_zone WHERE name=?", domain]]
        async with aiohttp.ClientSession() as session:
            async with session.post(f"http://{db_host}:4001/db/query",
                                    json=query) as resp:
                data = await resp.json()
                return data['results'][0]['values'][0][0]

    async def get_last_server_round_robin(self, domain_id):
        query = [["SELECT dns_zone_member FROM \
                  rr_state JOIN dns_zone ON \
                  rr_state.dns_zone = dns_zone.id WHERE dns_zone.id=?",
                  domain_id]]
        async with aiohttp.ClientSession() as session:
            async with session.post(f"http://{db_host}:4001/db/query",
                                    json=query) as resp:
                data = await resp.json()
                return data['results'][0]["values"][0][0]

    async def update_server_round_robin(self, member_id, domain_id):
        query = [['UPDATE rr_state SET dns_zone_member=? WHERE dns_zone=?',
                 member_id, domain_id]]
        async with aiohttp.ClientSession() as session:
            async with session.post(f"http://{db_host}:4001/db/execute",
                                    json=query) as resp:
                await resp.json()


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
