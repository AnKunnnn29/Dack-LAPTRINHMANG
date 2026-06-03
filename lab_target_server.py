"""Safe local lab target server for recon demo.

Run this file in one terminal, then run main_pipeline.py in another terminal.
It opens harmless fake services on localhost so the scanner can collect
open ports and banners for the final report.
"""

import argparse
import socket
import threading
import time


DEFAULT_LAB_PORTS = [3000, 8000, 8080, 3306, 5432, 6379]

SERVICE_BANNERS = {
    3306: "MySQL 8.0.36 Demo Lab - no real database here\r\n",
    5432: "PostgreSQL 16.2 Demo Lab - no real database here\r\n",
    6379: "Redis 7.2.0 Demo Lab - no real cache here\r\n",
}

HTTP_PORTS = {3000, 8000, 8080}


class LabService:
    """One small TCP listener for a fake lab service."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self) -> bool:
        """Bind port and start one background serving thread."""
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.host, self.port))
            self.sock.listen(10)
        except OSError as exc:
            print(f"[SKIP] {self.host}:{self.port} is unavailable: {exc}")
            return False

        thread = threading.Thread(target=self._serve_forever, daemon=True)
        thread.start()
        print(f"[OK] Fake service listening on {self.host}:{self.port}")
        return True

    def _serve_forever(self) -> None:
        """Accept clients forever until socket is closed."""
        while True:
            try:
                client, _ = self.sock.accept()
                thread = threading.Thread(target=self._handle_client, args=(client,), daemon=True)
                thread.start()
            except OSError:
                break

    def _handle_client(self, client: socket.socket) -> None:
        """Return HTTP response or plain service banner."""
        with client:
            client.settimeout(2)
            try:
                if self.port in HTTP_PORTS:
                    self._handle_http(client)
                else:
                    banner = SERVICE_BANNERS.get(self.port, "Demo Lab Service 1.0\r\n")
                    client.sendall(banner.encode("utf-8"))
            except OSError:
                return

    def _handle_http(self, client: socket.socket) -> None:
        """Return a tiny HTTP page plus a version-like Server header."""
        try:
            client.recv(1024)
        except socket.timeout:
            pass

        body = (
            "<html><body>"
            "<h1>Lab Target Server</h1>"
            "<p>Safe localhost target for Network Recon + Risk Profiler.</p>"
            "</body></html>"
        )
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Server: LabTargetHTTP/1.0\r\n"
            "Content-Type: text/html; charset=utf-8\r\n"
            f"Content-Length: {len(body.encode('utf-8'))}\r\n"
            "Connection: close\r\n"
            "\r\n"
            f"{body}"
        )
        client.sendall(response.encode("utf-8"))


def parse_ports(raw_ports: str) -> list[int]:
    """Parse comma-separated lab ports, or use DEFAULT_LAB_PORTS."""
    if not raw_ports:
        return DEFAULT_LAB_PORTS
    return [int(port.strip()) for port in raw_ports.split(",") if port.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Safe local lab target server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--ports", default="", help="Comma-separated lab ports")
    args = parser.parse_args()

    # MARK: Safety - lab server only binds to local machine.
    if args.host not in {"127.0.0.1", "localhost"}:
        print("[BLOCKED] Lab server only binds to localhost for safety.")
        return

    # MARK: Start fake services - each port becomes one small listener.
    services = []
    for port in parse_ports(args.ports):
        service = LabService(args.host, port)
        if service.start():
            services.append(service)

    if not services:
        print("No lab service started. Check whether ports are already in use.")
        return

    print("\nLab target server is running.")
    print("Open another terminal and scan it with:")
    print("python .pi/tools/main_pipeline.py --target localhost --ports 3000,8000,8080,3306,5432,6379")
    print("\nPress Ctrl+C to stop the lab server.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping lab target server.")


if __name__ == "__main__":
    main()
