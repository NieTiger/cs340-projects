from typing import NamedTuple, Optional


class URL(NamedTuple):
    scheme: str  # "http"
    hostname: str  # "www.python.org"
    port: Optional[int]  # 80
    path: str  # "/3/library"
    # params: str
    # query: str
    # fragment: str


def urlparse(raw: str) -> URL:
    """A very limited url parser

    scheme must equal http
    port can be empty, default 80
    """
    # scheme
    i = raw.find("://")
    if i == -1:  # no scheme
        scheme = ""
    else:
        scheme = raw[:i]
        raw = raw[i + 3 :]

    # hostname and port
    i = raw.find(":")
    if i != -1:  # port present
        hostname = raw[:i]
        raw = raw[i + 1 :]

        i = raw.find("/")
        if i == -1:
            port = int(raw)
            path = "/"
        else:
            port = int(raw[:i])
            path = raw[i:]
    else:
        port = 80

        i = raw.find("/")
        if i == -1:
            hostname = raw
            path = "/"
        else:
            hostname = raw[:i]
            path = raw[i:]

    # ignoring query and fragment for now

    return URL(
        scheme=scheme,
        hostname=hostname,
        port=port,
        path=path,
    )


if __name__ == "__main__":
    import unittest

    class TestUrlParse(unittest.TestCase):
        def test_parse_1(self):
            raw = "http://www.cwi.nl:80/%7Eguido/Python.html"
            url = urlparse(raw)
            self.assertEqual(url.scheme, "http", "Incorrect scheme")
            self.assertEqual(url.hostname, "www.cwi.nl", "Incorrect hostname")
            self.assertEqual(url.port, 80, "Incorrect port")
            self.assertEqual(url.path, "/%7Eguido/Python.html", "Incorrect path")

        def test_parse_2(self):
            raw = "insecure.stevetarzia.com"
            url = urlparse(raw)
            self.assertEqual(url.scheme, "", "Incorrect scheme")
            self.assertEqual(url.hostname, "insecure.stevetarzia.com", "Incorrect hostname")
            self.assertEqual(url.port, 80, "Incorrect port")
            self.assertEqual(url.path, "/", "Incorrect path")

        def test_parse_3(self):
            raw = "http://somewebsite.com/path/page.htm"
            url = urlparse(raw)
            self.assertEqual(url.scheme, "http", "Incorrect scheme")
            self.assertEqual(url.hostname, "somewebsite.com", "Incorrect hostname")
            self.assertEqual(url.port, 80, "Incorrect port")
            self.assertEqual(url.path, "/path/page.htm", "Incorrect path")

        def test_parse_4(self):
            raw = "https://www.google.com:443/maps"
            url = urlparse(raw)
            self.assertEqual(url.scheme, "https", "Incorrect scheme")
            self.assertEqual(url.hostname, "www.google.com", "Incorrect hostname")
            self.assertEqual(url.port, 443, "Incorrect port")
            self.assertEqual(url.path, "/maps", "Incorrect path")

    unittest.main()
