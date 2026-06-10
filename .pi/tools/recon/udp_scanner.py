"""Limited UDP reachability scanner for authorized lab targets."""

from __future__ import annotations

import socket
from typing import Iterable

from common.tool_utils import validate_port, validate_timeout


DEFAULT_UDP_PORTS = [53, 123, 161]
UDP_PROBES = {
    53: b"\x00\x00\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00",
    123: b"\x1b" + (b"\0" * 47),
    161: b"\x30\x26\x02\x01\x01\x04\x06public\xa0\x19\x02\x04\x00\x00\x00\x01\x02\x01\x00\x02\x01\x00\x30\x0b\x30\x09\x06\x05\x2b\x06\x01\x02\x01\x05\x00",
}


def scan_udp_port(target: str, port: int, timeout: float = 1.0) -> str:
    """Return responsive, closed, or open_or_filtered for one UDP port."""
    validate_port(port)
    validate_timeout(timeout)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        try:
            sock.connect((target, port))
            sock.send(UDP_PROBES.get(port, b""))
            sock.recv(1024)
            return "responsive"
        except ConnectionRefusedError:
            return "closed"
        except socket.timeout:
            return "open_or_filtered"
        except OSError:
            return "unreachable"


def scan_udp_ports(target: str, ports: Iterable[int] | None = None, timeout: float = 1.0) -> dict:
    selected = [validate_port(int(port)) for port in (ports or DEFAULT_UDP_PORTS)]
    return {
        "target": target,
        "protocol": "udp",
        "results": {str(port): scan_udp_port(target, port, timeout) for port in selected},
        "note": "UDP timeout means open_or_filtered; it does not prove the port is open.",
    }
