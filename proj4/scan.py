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
from typing import Dict, List, NamedTuple, Optional, Set, Tuple
import asyncio
import concurrent.futures
import json
import re
import socket
import subprocess
import sys
import time
import logging

import maxminddb
import requests

logging.basicConfig(
    format="%(asctime)s %(levelname)s:%(name)s: %(message)s", level=logging.DEBUG
)
logger = logging.getLogger(__name__)

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
            cmd, timeout=5, stderr=subprocess.STDOUT
        ).decode("utf-8")
    except subprocess.TimeoutExpired:
        return None
    else:
        return result


def _reverse_nslookup(ipv4: str, dns_server) -> List[str]:
    proc = subprocess.run(
        ["nslookup", "-type=PTR", ipv4, dns_server], capture_output=True, timeout=5
    )
    result = proc.stdout.decode()
    if not result:  # failed
        return []

    addrs = re.findall(r"name\s=\s[\w\.]+", result)
    return [l.split("=")[1].strip() for l in addrs]


def reverse_nslookup(ipv4_addrs: List[str]) -> List[str]:
    logger.debug("reverse_nslookup: %s", ipv4_addrs)
    addrs = []
    for ipv4 in ipv4_addrs:
        res = _reverse_nslookup(ipv4, "8.8.8.8")
        addrs.extend(res)

    return list(set(addrs))


def _nslookup(url: str, dns_server: str) -> Tuple[List[str], List[str]]:
    ipv4_addrs, ipv6_addrs = [], []
    result = run_cmd(["nslookup", url, dns_server])

    if not result:  # failed
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
    logger.debug("nslookup: %s", url)
    ipv4_addrs, ipv6_addrs = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for dns_server in DNS_SERVERS:
            futures.append(executor.submit(_nslookup, url, dns_server))

        for future in futures:
            ipv4, ipv6 = future.result()
            ipv4_addrs.extend(ipv4)
            ipv6_addrs.extend(ipv6)

    ipv4_addrs = list(set(ipv4_addrs))
    ipv6_addrs = list(set(ipv6_addrs))
    return ipv4_addrs, ipv6_addrs


class ServerInfo(NamedTuple):
    server: Optional[str] = None
    hsts: Optional[bool] = None
    redirect_to_https: Optional[bool] = None
    insecure: Optional[bool] = None


USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0"


def get_server_info(url: str, n_redir=10) -> ServerInfo:
    logger.debug("get_server_info: %s", url)
    redirect_to_https = False
    insecure_http = False
    
    with requests.Session() as session:
        session.max_redirects = n_redir
        session.headers = {"User-Agent", USER_AGENT}
        
        # Try insecure HTTP
        try:
            resp = session.get(
                "http://" + url, timeout=4, allow_redirects=True
            )
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            # Try HTTPS
            try:
                resp = session.get(
                    "https://" + url, timeout=4, allow_redirects=True
                )
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                return ServerInfo()
        else:
            insecure_http = True
    
    if len(resp.history) > 1 and resp.history[0].is_redirect and resp.history[1].url.startswith("https"):
        redirect_to_https = True

    server = resp.headers.get("server")
    hsts = "Strict-Transport-Security" in resp.headers

    return ServerInfo(
        server=server,
        hsts=hsts,
        insecure=insecure_http,
        redirect_to_https=redirect_to_https,
    )


def get_ssl_tls_version(url: str) -> List[str]:
    logger.debug("get_ssl_tls_version: %s", url)
    versions = []

    # Scan for protocols with nmap
    proc = subprocess.run(
        ["nmap", "--script", "ssl-enum-ciphers", "-p", "443", url], capture_output=True
    )
    nmap_output = proc.stdout.decode()
    vers = re.findall(r"\|\s\s\s[\w.]+", nmap_output)
    versions.extend(v.split()[1] for v in vers)

    # Check TLSv1.3 with openssl
    proc = subprocess.run(
        ["openssl", "s_client", "-tls1_3", "-connect", url + ":443"],
        input=b"",
        capture_output=True,
    )
    if re.search(r"TLSv1.3", proc.stdout.decode()):
        versions.append("TLSv1.3")

    return versions


def get_root_ca(url: str) -> str:
    logger.debug("get_root_ca: %s", url)
    proc = subprocess.run(
        ["openssl", "s_client", "-connect", url + ":443"],
        input=b"",
        capture_output=True,
    )
    s = proc.stdout.decode()
    i1 = s.find("Certificate chain")
    i2 = s[i1:].find("--")
    cchain = s[i1 : i1 + i2]
    if not cchain:
        return ""
    ca = re.findall(r"O\s=\s[^,]+,", cchain)[-1]
    return ca[:-1].split(" = ")[1].strip()


def _rtt(ip: str, port: int = 443):

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        start = time.time()
        sock.connect((ip, port))
        elapsed = time.time() - start

    return round(elapsed * 1000)


def get_rtt(ip_list: List[str]) -> Tuple[float, float]:
    logger.debug("get_rtt: %s", ip_list)
    _min = float("inf")
    _max = float("-inf")

    for ip in ip_list:
        t = _rtt(ip)
        _min = min(_min, t)
        _max = max(_max, t)

    return _min, _max


def get_geo_locations(ip_list: List[str]) -> List[str]:
    logger.debug("get_geo_locations: %s", ip_list)
    reader = maxminddb.open_database("GeoLite2-City.mmdb")
    locations = []
    for ip in ip_list:
        temp = reader.get(ip)
        builder = []
        if "city" in temp:
            city = temp["city"]["names"]["en"]
            builder.append(city)
        if "subdivisions" in temp:
            subdivision = temp["subdivisions"][0]["names"]["en"]
            builder.append(subdivision)
        if "country" in temp:
            country = temp["country"]["names"]["en"]
            builder.append(country)

        s = ", ".join(builder)
        locations.append(s)

    reader.close()
    return list(set(locations))


def scan_url(url: str) -> Dict:
    ""
    logger.info(f"Scanning {url}")
    start = time.time()
    ipv4, ipv6 = nslookup(url)

    server = None
    insecure = None
    redirect = None
    hsts = None
    try:
        server, hsts, redirect, insecure = get_server_info(url)
    except Exception as e:
        # wtf
        logger.exception(e)

    tls_versions = get_ssl_tls_version(url)
    root_ca = get_root_ca(url)
    rdns_names = reverse_nslookup(ipv4)
    rtt_range = get_rtt(ipv4)
    geo_locations = get_geo_locations(ipv4)

    d = {
        "scan_time": time.time() - start,
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
    return url, d


def scan_urls(input_file: str, output_file: str) -> Dict:
    data = {}

    with open(input_file, "r") as fp:
        urls = fp.read().strip().split("\n")

    ## concurrent version
    # with concurrent.futures.ThreadPoolExecutor() as executor:
    #     futures = []

    #     for url in urls:
    #         executor.submit(scan_url, url)

    #     for future in futures:
    #         url, d = future.result()
    #         data[url] = d
    
    ## sequential version
    for url in urls:
        data[url] = scan_url(url)[1]

    with open(output_file, "w") as fp:
        json.dump(data, fp, sort_keys=True, indent=4)

    return data


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: python3 scan.py [input_file.txt] [output_file.json]",
            file=sys.stderr,
        )
        sys.exit(1)

    input_fname = sys.argv[1]
    output_fname = sys.argv[2]

    scan_urls(input_fname, output_fname)


if __name__ == "__main__":
    main()