import socket
from contextlib import closing

from aiohttp import web

unix_socket_path = "/var/run/portd/portd.sock"


async def handle(request):  # noqa:
    blacklist = set([int(v) for v in request.query.getall("blacklist", [])])

    port = -1
    blacklist.add(port)
    while port in blacklist:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(("", 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            port = int(s.getsockname()[1])
    return web.Response(text=str(port))


def main():  # noqa:
    app = web.Application()
    app.router.add_get("/", handle)

    web.run_app(app, path=unix_socket_path)


if __name__ == "__main__":
    main()
