import asyncio
import webbrowser
from urllib.parse import parse_qs
import socket


class WebServer:
    @staticmethod
    async def start_server_and_open_browser(url, port: int = 12345):
        response_queue = asyncio.Queue(1)

        # start callback webserver
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("localhost", port))
        server.listen()
        # this is set, so we can restart the server quickly without getting
        # OSError: [Errno 48] Address already in use errors
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.setblocking(False)

        server_task = asyncio.create_task(WebServer.run_http_server(server, response_queue))

        webbrowser.open(url)

        val = await response_queue.get()
        server.close()
        server_task.cancel()

        return val

    # this is a tiny webserver to be able to receive the callback from oauth
    # heavily inspired by https://github.com/jangia/http_server/blob/master/server.py

    CHUNK_LIMIT = 50
    DEFAULT_RESPONSE = "HTTP/1.1 {status} {status_msg}\r\nContent-Type: text/html; charset=UTF-8\r\nContent-Encoding: UTF-8\r\nAccept-Ranges: bytes\r\nConnection: closed\r\n\r\n{html}"

    @staticmethod
    def parse_request(request_str):
        part_one, part_two = request_str.split("\r\n\r\n")
        http_lines = part_one.split("\r\n")
        method, url, _ = http_lines[0].split(" ")
        if method != "GET":
            status, status_msg = 405, "Not allowed"
        else:
            status, status_msg = 200, "OK"

        return status, status_msg, url

    @staticmethod
    async def build_response(request, response_queue):
        status, status_msg, url = WebServer.parse_request(request)
        html = ""
        # if there is code in the response it is the one we want
        if "code" in url:
            query = parse_qs(url.split("?", 1)[1])
            await response_queue.put(query)
            html = "Thank you, auth is handed back to the cli."
        else:
            status = 404
            status_msg = "Not Found"
        response = WebServer.DEFAULT_RESPONSE.format(
            status=status, status_msg=status_msg, html=html
        ).encode("utf-8")

        return response

    @staticmethod
    async def read_request(client):
        request = ""
        while True:
            chunk = (await asyncio.get_event_loop().sock_recv(client, WebServer.CHUNK_LIMIT)).decode(
                "utf8"
            )
            request += chunk
            if len(chunk) < WebServer.CHUNK_LIMIT:
                break

        return request

    @staticmethod
    async def handle_client(client, response_queue):
        request = await WebServer.read_request(client)
        response = await WebServer.build_response(request, response_queue)
        await asyncio.get_event_loop().sock_sendall(client, response)
        client.close()

    @staticmethod
    async def run_http_server(selected_server, response_queue):
        while True:
            client, _ = await asyncio.get_event_loop().sock_accept(selected_server)
            asyncio.create_task(WebServer.handle_client(client, response_queue))
