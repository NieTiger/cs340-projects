from typing import Dict, Generator, Optional

class Header:
    """Wrapper around a HTTP Header. Acts like a dict"""

    def __init__(self, header_str: str, request=True):
        self.header_str: str = header_str


        http_line, header_str = header_str.split("\r\n", 1)
        http_lst = http_line.split(" ")

        if request:
            self.http_version = http_lst[0]
            self.http_code = int(http_lst[1])
            self.http_msg = " ".join(http_lst[2:])
        else:
            self.http_method = http_lst[0]
            self.http_path = http_lst[1]
            self.http_version = http_lst[2]

        self._header: Dict[str, str] = parse_dict(header_str, ": ", "\r\n")
    
    @classmethod
    def from_raw(cls, header_bytes: bytes, request=True) -> "Header":
        return Header(header_bytes.decode(), request=request)

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

    def get(self, key: str) -> Optional[str]:
        return self._header.get(key)




def parse_dict(raw: str, delimiter: str, newline: str = "\r\n") -> Dict[str, str]:
    res: Dict[str, str] = {}
    for line in raw.split(newline):
        key, val = line.split(delimiter, 1)
        res[key] = val
    return res