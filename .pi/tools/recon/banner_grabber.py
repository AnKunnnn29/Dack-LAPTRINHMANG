"""STAGE 1C - Banner Grabber.

Muc dich:
- Ket noi TCP den cac port ung vien.
- Neu la HTTP port thi gui HEAD request de lay header.
- Luu banner de ML scorer phat hien version leak.
"""

import socket
import ssl
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from common.tool_utils import parse_ports, validate_port, validate_timeout


HTTP_PORTS = {80, 3000, 8000, 8080}
TLS_PORTS = {443, 465, 636, 993, 995, 8443}
SERVICE_BY_PORT = {
    21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "dns",
    80: "http", 110: "pop3", 143: "imap", 443: "https", 445: "smb",
    3306: "mysql", 5432: "postgresql", 6379: "redis", 8000: "http",
    8080: "http", 8443: "https",
}


def _clean_banner(raw_data: bytes) -> str:
    """Chuyen bytes thanh text ngan gon, tranh report qua dai."""
    text = raw_data.decode("utf-8", errors="replace").strip()
    if not text:
        return "No banner"
    return text[:500]


def grab_banner(target: str, port: int, timeout: float = 1.0) -> str:
    """Thu doc banner tren mot port."""
    try:
        with socket.create_connection((target, port), timeout=timeout) as sock:
            sock.settimeout(timeout)

            # MARK: HTTP helper - server HTTP thuong chi tra header sau khi co request.
            if port in HTTP_PORTS:
                request = f"HEAD / HTTP/1.1\r\nHost: {target}\r\nConnection: close\r\n\r\n"
                sock.sendall(request.encode("utf-8"))

            try:
                data = sock.recv(1024)
                return _clean_banner(data)
            except socket.timeout:
                return "No banner"
    except OSError:
        return "No banner"


def inspect_tls(target: str, port: int, timeout: float = 2.0) -> dict:
    """Collect public certificate metadata without validating trust."""
    if port not in TLS_PORTS:
        return {}
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    try:
        with socket.create_connection((target, port), timeout=timeout) as raw_socket:
            with context.wrap_socket(raw_socket, server_hostname=target) as tls_socket:
                certificate = tls_socket.getpeercert()
                return {
                    "protocol": tls_socket.version(),
                    "cipher": tls_socket.cipher()[0] if tls_socket.cipher() else "",
                    "subject": certificate.get("subject", []),
                    "issuer": certificate.get("issuer", []),
                    "not_after": certificate.get("notAfter", ""),
                }
    except (OSError, ssl.SSLError):
        return {}


def identify_service(port: int, banner: str) -> str:
    """Use port and banner hints for a lightweight service guess."""
    lowered = banner.lower()
    for marker, service in [
        ("ssh-", "ssh"), ("smtp", "smtp"), ("mysql", "mysql"),
        ("postgresql", "postgresql"), ("redis", "redis"), ("http/", "http"),
    ]:
        if marker in lowered:
            return service
    return SERVICE_BY_PORT.get(port, "unknown")


def grab_banners(target: str, candidate_ports: Iterable[int], timeout: float = 1.0) -> dict:
    """Lay banner tren danh sach port ung vien.

    Tool nay khong dung ket qua port scan de giu dung yeu cau Stage 1:
    port scan, DNS enum, banner grab khong co data dependency va chay song song.
    """
    banners = {}
    services = {}
    tls = {}
    attempted_ports = [validate_port(int(port)) for port in candidate_ports]
    timeout = validate_timeout(timeout)
    max_workers = min(50, max(1, len(attempted_ports)))

    # MARK: Per-port parallelism - moi worker thu lay banner tren mot port.
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(grab_banner, target, port, timeout): port
            for port in attempted_ports
        }

        for future in as_completed(futures):
            port = futures[future]
            banners[str(port)] = future.result()
            services[str(port)] = identify_service(port, banners[str(port)])
            tls_result = inspect_tls(target, port, timeout)
            if tls_result:
                tls[str(port)] = tls_result

    return {
        "target": target,
        "attempted_ports": attempted_ports,
        "banners": dict(sorted(banners.items(), key=lambda item: int(item[0]))),
        "services": dict(sorted(services.items(), key=lambda item: int(item[0]))),
        "tls": dict(sorted(tls.items(), key=lambda item: int(item[0]))),
    }


def main() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Simple banner grabber")
    parser.add_argument("--target", default="localhost")
    parser.add_argument("--ports", default="")
    args = parser.parse_args()

    ports = parse_ports(args.ports)
    result = grab_banners(args.target, ports)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
