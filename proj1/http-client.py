import sys
import socket
from typing import Dict, Generator
from urllib.parse import urlparse

BUF_SIZE = 16384


def exit_err(msg: str, code=1):
    """Print error msg to stderr and exit"""
    sys.stderr.write(msg)
    sys.exit(code)
    

def parse_dict(raw: str, delimiter: str, newline: str = "\r\n") -> Dict[str, str]:
    res: Dict[str, str] = {}
    for line in raw.split(newline):
        key, val = line.split(delimiter, 1)
        res[key] = val
    return res



class Header:
    """Wrapper around a HTTP Header. Acts like a dict"""

    def __init__(self, header_str: str):
        self.header_str: str = header_str

        http_line, header_str = header_str.split("\r\n", 1)
        http_lst = http_line.split(" ")

        self.http_version = http_lst[0]
        self.http_code = int(http_lst[1])
        self.http_msg = " ".join(http_lst[2:])

        self._header: Dict[str, str] = parse_dict(header_str, ": ", "\r\n")
    
    @classmethod
    def from_raw(cls, header_bytes: bytes) -> "Header":
        return Header(header_bytes.decode())

    def to_string(self) -> str:
        raise NotImplementedError

    def __getitem__(self, key: str) -> str:
        return self._header[key]

    def __setitem__(self, key: str, val: str):
        self._header[key] = val

    def __delitem(self, key: str):
        del self._header[key]

    def __iter__(self):
        return self._header.__iter__()
    

class Response:
    def __init__(self, header: Header, payload: str):
        self.header = header
        self.payload = payload
        self.http_code = header.http_code
        self.http_msg = header.http_msg
    
    def __repr__(self):
        return f"<Response {self.http_code}>"


def do_http_request(url, n_redirs=0):
    if n_redirs >= 10:
        # too many redirects, give up with nonzero exit code
        exit_err("Error: Too many redirects.\n")

    ### Parse destination URL
    o = urlparse(url)
    if not o.scheme:
        exit_err(
            f"Error: {sys.argv[0]} can only handle http. Must prepend url with 'http://'.\n"
        )
    if o.scheme.lower() != "http":
        exit_err(
            f"Error: {sys.argv[0]} can only handle http, not {o.scheme}.\n"
        )

    path = o.path if o.path else "/"
    port = o.port if o.port else 80
    hostname = o.hostname
    host = o.hostname if port == 80 else f"{o.hostname}:{port}"

    ### Build HTTP request
    request_str = f"""GET {path} HTTP/1.0
User-Agent: http-client.py/0.1
Host: {host}

""".replace("\n", "\r\n")

    ### Do request
    buf = b""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((hostname, port))
        sock.sendall(request_str.encode())

        # Read all response regardless of content length
        while True:
            tmp = sock.recv(BUF_SIZE)
            if not tmp:
                break
            buf += tmp

    ### Parse results
    header_bytes, payload_bytes = buf.split(b"\r\n\r\n", 1)

    header = Header.from_raw(header_bytes)
    if "Content-Type" not in header:
        exit_err("Error: Content-Type not specified in response header.")
    
    if not header["Content-Type"].startswith("text/html"):
        exit_err("Error: Content-Type is not text/html.")

    payload = payload_bytes.decode()

    ### Handle responses

    # Follow redirects
    if header.http_code == 301 or header.http_code == 302:
        redir_url = header["Location"]
        sys.stderr.write(f"Redirected to {redir_url}\n")
        return do_http_request(redir_url, n_redirs=n_redirs + 1)

    # Handle http errors
    if header.http_code >= 400:
        sys.stdout.write(payload)
        sys.stdout.write("\n")
        sys.exit(1)
        
    return Response(header, payload)


if __name__ == "__main__":

    # Handle CLI arguments
    if len(sys.argv) <= 1:
        print(f"Usage: python3 {sys.argv[0]} <url>")
        sys.exit(1)

    url = sys.argv[1]

    resp = do_http_request(url)
    sys.stdout.write(resp.payload)
    sys.exit(0)