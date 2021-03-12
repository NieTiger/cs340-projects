"""
Usage: python3 scan.py [input_file.txt] [output_file.json]

Sample output JSON:

{
  "northwestern.edu": {
    "scan_time": 1605038710.32,
    "ipv4_addresses": ["129.105.136.48"],
    "ipv6_addresses": [],
    "http_server": "Apache",
    ...
  }
  "google.com": {
    "scan_time": 1605038714.20,
    "ipv4_addresses": ["172.217.6.110", "216.58.192.206", "172.217.1.46"],
    "ipv6_addresses": ["2607:f8b0:4009:800::200e"],
    "http_server": "gws",
    ...
  }
}

"""
from typing import Dict, List, Tuple, Set
import asyncio
import sys
import json
import subprocess
from time import time

# import texttable

DNS_SERVERS = (
    "208.67.222.222",
    "1.1.1.1",
    "8.8.8.8",
    "8.26.56.26",
    "9.9.9.9",
    "64.6.65.6",
    "91.239.100.100",
    "185.228.168.168",
    "77.88.8.7",
    "156.154.70.1",
    "198.101.242.72",
    "176.103.130.130",
)


def run_cmd(cmd: List):
    try:
        result = subprocess.check_output(
            cmd, timeout=2, stderr=subprocess.STDOUT
        ).decode("utf-8")
    except FileNotFoundError as e:
        # Handle command not found gracefully
        print(e)
        pass
    except subprocess.TimeoutExpired as e:
        # duh
        print(e)
        pass
    else:
        return result


# ["nslookup", "northwestern.edu", "8.8.8.8"]


def _nslookup(url: str, dns_server: str) -> Tuple[List[str], List[str]]:
    ipv4_addrs, ipv6_addrs = [], []
    result = run_cmd(["nslookup", url, dns_server])
    if not result:
        print(
            f"NSLookup failed for url: {url}, dns_server: {dns_server}", file=sys.stderr
        )
        return ipv4_addrs, ipv6_addrs
    answers = result.strip().split("\n\n")[1]
    for line in answers.split("\n"):
        if not line.startswith("Address:"):
            continue
        _, addr = line.split()
        if ":" in addr:  # ipv6
            ipv6_addrs.append(addr)
        else:
            ipv4_addrs.append(addr)
    return ipv4_addrs, ipv6_addrs


def nslookup(url: str) -> Tuple[List[str], List[str]]:
    ipv4_addrs, ipv6_addrs = [], []
    for dns_server in DNS_SERVERS:
        ipv4, ipv6 = _nslookup(url, dns_server)
        ipv4_addrs.extend(ipv4)
        ipv6_addrs.extend(ipv6)

    ipv4_addrs = list(set(ipv4_addrs))
    ipv6_addrs = list(set(ipv6_addrs))
    return ipv4_addrs, ipv6_addrs


def scan_url(url: str) -> Dict:
    ""
    t = time()
    ipv4, ipv6 = nslookup(url)
    server = None
    insecure = None
    redirect = None
    hsts = None
    tls_versions = None
    root_ca = None
    rdns_names = None
    rtt_range = None
    geo_locations = None

    return {
        "scan_time": t,
        "ipv4_addresses": ipv4,
        "ipv6_addresses": ipv6,
        "http_server": server,
        "insecure_http": insecure,
        "redirect_to_https": redirect,
        "hsts": hsts,
        "tls_versions": tls_versions,
        "root_ca": root_ca,
        "rdns_names": rdns_names,
        "rtt_range": rtt_range,
        "geo_locations": geo_locations,
    }


def scan_urls(input_file: str, output_file: str) -> Dict:
    data = {}

    with open(input_file, "r") as fp:
        urls = fp.read().strip().split("\n")
        for url in urls:
            data[url] = scan_url(url)
    data = json.dumps(data)

    f = open(output_file, "w")
    json.dump(data, f, sort_keys=True, indent=4)
    f.close()


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: python3 scan.py [input_file.txt] [output_file.json]",
            file=sys.stderr,
        )
        sys.exit(1)

    input_fname = sys.argv[1]
    output_fname = sys.argv[2]

    with open(input_fname, "r") as fp:
        urls = fp.read().strip().split("\n")

    print(urls)
    breakpoint()


if __name__ == "__main__":
    main()