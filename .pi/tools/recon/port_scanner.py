"""STAGE 1A - TCP Port Scanner.

Muc dich:
- Thu ket noi TCP den tung port.
- Port nao connect duoc thi xem la "open".
- Chi dung cho localhost/lab/target da duoc uy quyen.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import socket
import sys
from pathlib import Path
from typing import Iterable

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from common.tool_utils import parse_ports, validate_port, validate_timeout


DEFAULT_PORTS = [
    21,
    22,
    23,
    25,
    53,
    80,
    110,
    139,
    143,
    443,
    445,
    3306,
    5432,
    6379,
    8000,
    8080,
]


def scan_port(target: str, port: int, timeout: float = 0.5) -> bool:
    """Kiem tra mot port TCP. True = port dang mo."""
    try:
        with socket.create_connection((target, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


def scan_ports(
    target: str,
    ports: Iterable[int] | None = None,
    timeout: float = 0.5,
) -> dict:
    """Quet danh sach port va tra ve JSON-friendly dict.

    Ghi chu thuyet trinh:
    - Pipeline da chay song song 3 recon agent o main_pipeline.py.
    - Ben trong port scanner, tung port cung duoc quet song song nhe de demo
      nhanh hon khi dung range lon nhu 1-1000.
    """
    selected_ports = [validate_port(int(port)) for port in (ports or DEFAULT_PORTS)]
    timeout = validate_timeout(timeout)
    open_ports = []

    max_workers = min(100, max(1, len(selected_ports)))

    # MARK: Per-port parallelism - moi worker thu ket noi mot port.
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(scan_port, target, port, timeout): port
            for port in selected_ports
        }

        for future in as_completed(futures):
            port = futures[future]
            if future.result():
                open_ports.append(port)

    return {
        "target": target,
        "scanned_ports": selected_ports,
        "open_ports": sorted(open_ports),
        "open_count": len(open_ports),
    }


def main() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Simple TCP port scanner")
    parser.add_argument("--target", default="localhost")
    parser.add_argument("--ports", default="")
    args = parser.parse_args()

    custom_ports = None
    if args.ports:
        custom_ports = parse_ports(args.ports)

    result = scan_ports(args.target, custom_ports)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
