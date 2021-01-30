"""
Single-connection web server
"""
import socket
import sys
from typing import ByteString
from pathlib import Path
from typing import Union

from header import Header

BUF_SIZE = 16384
HOST = "127.0.0.1"
BACKLOG = 1

HTTP_MSG = {
    200: 'OK',
    301: 'Moved Permanently',
    302: 'Found',
    400: 'Bad Request',
    401: 'Unauthorized',
    402: 'Payment Required',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    500: 'Internal Server Error',
}

RESP_HEADER_TMPL = """HTTP/1.0 {code} {msg}
Content-Length: {length}
Content-Type: {content_type}

""".replace("\n", "\r\n")

HTTP_ERROR_TMPL = """
<p>File not found.</p>
""".encode()

filepath = Path(".")


def run_server(host, port):

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as accept_socket:
        # tell the kernel to reuse sockets that are in "TIME_WAIT" state
        accept_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        accept_socket.bind((host, port))
        accept_socket.listen(BACKLOG)
        print(f"Listening on http://{host}:{port}")

        # Listen on the socket forever
        while True:
            # Get client socket and address
            client_sock, client_addr = accept_socket.accept()
            print(f"Accepted connection from {client_addr}...")

            try:
                handle_client(client_sock)
            except Exception as e:
                print("Oops, error occurred...")
                print(e)


def handle_client(client_sock: socket.socket):
    # Read header
    header_buf = b""
    payload_buf = b""

    with client_sock:
        while True:
            tmp = client_sock.recv(BUF_SIZE)

            if not tmp:
                break
            i = tmp.find(b"\r\n\r\n")

            if i != -1:
                header_buf += tmp[:i]
                payload_buf += tmp[i:]
                break

            header_buf += tmp

        header = Header.from_raw(header_buf, request=False)

        if header.http_path.endswith(".htm") or header.http_path.endswith(".html"):
            # Check if path exists
            path = filepath / Path(header.http_path[1:])
            print(path)
            if path.exists():
                print("File exists, trying to send file")
                # file exists, send file
                client_sock.sendall(RESP_HEADER_TMPL.format(code=200,
                                                            msg=HTTP_MSG[200],
                                                            length=path.stat().st_size,
                                                            content_type="text/html").encode())
                send_file_to_sock(client_sock, path)
            else:
                # file doesn't exist
                print("File doesnt exist, sending error msg")
                client_sock.sendall(RESP_HEADER_TMPL.format(code=403,
                                                            msg=HTTP_MSG[403],
                                                            length=len(
                                                                HTTP_ERROR_TMPL),
                                                            content_type="text/html").encode())
                client_sock.sendall(HTTP_ERROR_TMPL)

        else:
            # Not asking for a HTML file, we don't know how to handle that
            print("Not asking for html, abort")
            client_sock.sendall(RESP_HEADER_TMPL.format(code=404,
                                                        msg=HTTP_MSG[404],
                                                        length=len(
                                                            HTTP_ERROR_TMPL),
                                                        content_type="text/html").encode())
            client_sock.sendall(HTTP_ERROR_TMPL)


def send_file_to_sock(sock: socket.socket, path: Path):
    with path.open("rb") as fptr:
        sock.sendfile(fptr)


if __name__ == "__main__":

    # Handle CLI arguments
    if len(sys.argv) <= 1:
        print(f"Usage: python3 {sys.argv[0]} <port>")
        sys.exit(1)

    port: int = int(sys.argv[1])
    if port < 1024:
        sys.stderr.write("Please use a port number > 1024")
        sys.exit(1)

    try:
        run_server(HOST, port)
    except KeyboardInterrupt:
        sys.stderr.write("Exiting . . .")
        sys.exit(1)
