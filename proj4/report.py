from typing import List, NamedTuple
from collections import Counter
import json
import sys

from texttable import Texttable


def format_data(data: dict) -> str:
    builder = []
    for url, entry in data.items():
        builder.append(url + "\n")
        table = Texttable()
        for k, v in entry.items():
            if isinstance(v, list):
                table.add_row((k, "\n".join(str(i) for i in v)))
            else:
                table.add_row((k, v))
        builder.append(table.draw())
        builder.append("\n")

    out = "\n".join(builder)
    return out


def rtt_range(data: dict) -> str:
    class RTTEntry(NamedTuple):
        min: int
        max: int
        url: str

    lst: List[RTTEntry] = []  #
    timeout_url: List[str] = []

    for url, entry in data.items():
        if "rtt_range" not in entry:
            continue

        if not entry["rtt_range"][0]:
            timeout_url.append(url)
            continue

        lst.append(RTTEntry(*entry["rtt_range"], url))

    lst.sort()

    table = Texttable()
    table.set_deco(Texttable.HEADER)
    table.add_row(("url", "rtt_min", "rtt_max"))

    for rttentry in lst:
        table.add_row((rttentry.url, rttentry.min, rttentry.max))

    for url in timeout_url:
        table.add_row((url, "Timeout", "Timeout"))

    return table.draw()


def web_server_table(data: dict) -> str:
    counter = Counter()
    for entry in data.values():
        if "http_server" not in entry or not entry["http_server"]:
            continue

        counter[entry["http_server"]] += 1

    table = Texttable()
    table.set_deco(Texttable.HEADER)
    table.add_row(("web server", "number of occurences"))

    for server, count in counter.most_common():  # List[value, count]
        if "SSL" in server:
            breakpoint()
        table.add_row((server, str(count)))

    return table.draw()


def root_cert_table(data: dict) -> str:
    counter = Counter()
    for entry in data.values():
        if "root_ca" not in entry or not entry["root_ca"]:
            continue
        counter[entry["root_ca"]] += 1

    table = Texttable()
    table.set_deco(Texttable.HEADER)
    table.add_row(("root certificate authority", "number of occurences"))

    for root_ca, count in counter.most_common():  # List[value, count]
        table.add_row((root_ca, count))

    return table.draw()


def percentage_table(data: dict) -> str:
    table = Texttable()
    table.set_deco(Texttable.HEADER)
    table.add_row(("feature", "percentage supported"))

    tlsv = {
        "TLSv1.0": 0,
        "TLSv1.1": 0,
        "TLSv1.2": 0,
        "TLSv1.3": 0,
        "SSLv2": 0,
        "SSLv3": 0,
    }

    d = {
        "plain http": 0,
        "https redirect": 0,
        "hsts": 0,
        "ipv6": 0,
    }

    for entry in data.values():
        for k in tlsv.keys():
            if k in entry["tls_versions"]:
                tlsv[k] += 1

        if entry.get("insecure_http"):
            d["plain http"] += 1

        if entry.get("redirect_to_https"):
            d["https redirect"] += 1

        if entry.get("hsts"):
            d["hsts"] += 1

        if entry.get("ipv6_addresses"):
            d["ipv6"] += 1

    l = len(data)
    for k, v in tlsv.items():
        table.add_row((k, f"{round(v/l * 100, 2)}%"))

    for k, v in d.items():
        table.add_row((k, f"{round(v/l * 100, 2)}%"))

    return table.draw()


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: python3 scan.py [input_file.json] [output_file.txt]",
            file=sys.stderr,
        )
        sys.exit(1)

    input_fname = sys.argv[1]
    output_fname = sys.argv[2]

    with open(input_fname, "r") as fp:
        data = json.load(fp)

    fmt = format_data(data)
    rtt = rtt_range(data)
    rca = root_cert_table(data)
    wst = web_server_table(data)
    pt = percentage_table(data)

    out_s = "\n\n".join(
        (
            fmt,
            "\nRTT Range",
            rtt,
            "\nRoot Certificate Authority",
            rca,
            "\nWeb Server",
            wst,
            "\nFeature Support",
            pt,
        )
    )

    with open(output_fname, "w") as fp:
        fp.write(out_s)


if __name__ == "__main__":
    main()