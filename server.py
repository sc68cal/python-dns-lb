import aiohttp
import asyncio
import os
import socket
import sys

from dns import message

try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

# Two of google.com's raw IPs
servers = ['http://142.251.40.110',
           'http://142.251.116.101'
           ]


class DnsServerProtocol:
    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):

        loop = asyncio.get_event_loop()

        loop.create_task(self.check_servers(data, addr))

    async def check_servers(self, data, addr):
        dq = message.from_wire(data)
        print('Received %r from %s' % (dq, addr))

        checks = []
        for server in servers:
            checks.append(self.check_server(server))

        results = await asyncio.gather(*checks)
        output = message.make_response(dq)
        for server, alive in results:
            # TODO add rrset objects to output
            pass

        print('Send %r to %s' % (output, addr))
        self.transport.sendto(output.to_wire(), addr)

    async def check_server(self, server):
        async with aiohttp.ClientSession() as session:
            async with session.get(server) as response:
                return (server, response.status == 200)


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
