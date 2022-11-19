import asyncio
import uvloop

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


class DnsServerProtocol:
    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        message = data.decode()
        print('Received %r from %s' % (message, addr))
        print('Send %r to %s' % (message, addr))
        self.transport.sendto(data, addr)


def main():
    print("Starting UDP server")

    # Create an event loop
    loop = asyncio.new_event_loop()

    # One protocol instance will be created to serve all
    # client requests.
    t = loop.create_datagram_endpoint(
        lambda: DnsServerProtocol(),
        local_addr=('127.0.0.1', 9999))

    loop.run_until_complete(t)
    loop.run_forever()


if __name__ == "__main__":
    main()
