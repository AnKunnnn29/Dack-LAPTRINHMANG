"""STAGE 1C - Banner Grabber.

Muc dich:
- Ket noi TCP den cac port ung vien.
- Neu la HTTP port thi gui HEAD request de lay header.
- Luu banner de ML scorer phat hien version leak.
"""

import socket
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from common.tool_utils import parse_ports


HTTP_PORTS = {80, 3000, 8000, 8080}


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


def grab_banners(target: str, candidate_ports: Iterable[int], timeout: float = 1.0) -> dict:
    """Lay banner tren danh sach port ung vien.

    Tool nay khong dung ket qua port scan de giu dung yeu cau Stage 1:
    port scan, DNS enum, banner grab khong co data dependency va chay song song.
    """
    banners = {}
    attempted_ports = [int(port) for port in candidate_ports]
    max_workers = min(100, max(1, len(attempted_ports)))

    # MARK: Per-port parallelism - moi worker thu lay banner tren mot port.
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(grab_banner, target, port, timeout): port
            for port in attempted_ports
        }

        for future in as_completed(futures):
            port = futures[future]
            banners[str(port)] = future.result()

    return {
        "target": target,
        "attempted_ports": attempted_ports,
        "banners": dict(sorted(banners.items(), key=lambda item: int(item[0]))),
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
