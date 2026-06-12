"""Compatibility wrapper for `recon.udp_scanner`."""

import argparse
import json

from common.tool_utils import parse_ports
from recon.udp_scanner import DEFAULT_UDP_PORTS, scan_udp_ports


def main() -> None:
    parser = argparse.ArgumentParser(description="Limited authorized UDP scanner")
    parser.add_argument("--target", default="localhost")
    parser.add_argument("--ports", default="")
    parser.add_argument("--timeout", type=float, default=1.0)
    args = parser.parse_args()
    ports = parse_ports(args.ports) if args.ports else DEFAULT_UDP_PORTS
    print(json.dumps(scan_udp_ports(args.target, ports, args.timeout), indent=2))


if __name__ == "__main__":
    main()
