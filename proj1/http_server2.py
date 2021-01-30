"""
Multi-connection web server
"""
import select
import socket
import sys
from pathlib import Path
from typing import ByteString, Dict, Union

from header import Header

BUF_SIZE = 16384
HOST = "127.0.0.1"
BACKLOG = 8

HTTP_MSG = {
    200: "OK",
    301: "Moved Permanently",
    302: "Found",
    400: "Bad Request",
    401: "Unauthorized",
    402: "Payment Required",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    500: "Internal Server Error",
}

RESP_HEADER_TMPL = """HTTP/1.0 {code} {msg}
Content-Length: {length}
Content-Type: {content_type}

""".replace(
    "\n", "\r\n"
)

HTTP_ERROR_TMPL = """
<p>File not found.</p>
""".strip().encode()

filepath = Path(".")


def run_server(host, port):

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as accept_socket:
        # tell the kernel to reuse sockets that are in "TIME_WAIT" state
        accept_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        accept_socket.bind((host, port))
        accept_socket.listen(BACKLOG)
        print(f"Listening on http://{host}:{port}")

        # Sockets from which we expect to read
        inputs = [accept_socket]
        # Sockets from which we expect to write
        outputs = []
        # Outgoing message queues (byte buffer)
        message_queues: Dict[socket.socket, bytearray] = {}

        def release_resources(s: socket.socket):
            inputs.remove(s)
            if s in outputs:
                outputs.remove(s)
            s.close()
            del message_queues[s]


        while inputs:
            print("Waiting for the next event", file=sys.stderr)
            readable, writable, exceptional = select.select(inputs, outputs, inputs)
        
            for s in readable:

                if s is accept_socket:
                    ### Case if 
                    # Get client socket and address
                    client_sock, client_addr = accept_socket.accept()
                    print(f"Accepted connection from {client_addr}...")
                    client_sock.setblocking(0)
                    inputs.append(client_sock)

                    # read/write queues
                    message_queues[client_sock] = b""

                else:
                    # s is a client_sock
                    data = s.recv(1024)

                    if data:
                        # Client sock has data!
                        # handle that here

                        # If the message_queue for this client forms
                        # a valid HTTP request, handle that
                        message_queues[s] += data
                        if b"\r\n\r\n" in message_queues[s]:
                            # Receive a full HTTP header
                            outputs.append(s)
                            try:
                                message_queues[s] = handle_http_header(message_queues[s])
                            except Exception as e:
                                print(f"Oops - error on {s.getpeername()}: {e}", file=sys.stderr)
                                release_resources(s)

                    else:
                        # Empty - connection must be closed
                        print("closing", client_addr, file=sys.stderr)
                        release_resources(s)
            
            for s in writable:
                msg: bytearray = message_queues[s]
                if not msg:
                    print(s.getpeername(), 'queue empty', file=sys.stderr)
                    release_resources(s)
                else:
                    # There is a message available to write to the given socket
                    print(f"sending to {s.getpeername()}", file=sys.stderr)
                    i = s.send(msg)
                    message_queues[s] = msg[i:]
            
            for s in exceptional:
                print('Oops - ', s.getpeername(), file=sys.stderr)
                release_resources(s)


def handle_http_header(header_buf: bytearray) -> bytearray:
    header = Header.from_raw(header_buf)
    output_buf = b""

    if header.http_path.endswith(".htm") or header.http_path.endswith(".html"):
        # Check if path exists
        path = filepath / Path(header.http_path[1:])
        print(path)
        if path.exists():
            print("File exists, trying to send file")

            # file exists, send file
            output_buf += RESP_HEADER_TMPL.format(
                code=200,
                msg=HTTP_MSG[200],
                length=path.stat().st_size,
                content_type="text/html",
            ).encode()

            with path.open("rb") as fptr:
                output_buf += fptr.read()

        else:
            # file doesn't exist
            print("File doesnt exist, sending error msg")
            output_buf += RESP_HEADER_TMPL.format(
                code=403,
                msg=HTTP_MSG[403],
                length=len(HTTP_ERROR_TMPL),
                content_type="text/html",
            ).encode()
            output_buf += HTTP_ERROR_TMPL

    else:
        # Not asking for a HTML file, we don't know how to handle that
        print("Not asking for html, abort")
        output_buf += RESP_HEADER_TMPL.format(
            code=404,
            msg=HTTP_MSG[404],
            length=len(HTTP_ERROR_TMPL),
            content_type="text/html",
        ).encode()
        output_buf += HTTP_ERROR_TMPL
    
    return output_buf


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
