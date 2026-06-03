"""Common utilities shared by all pipeline tools.

Nhom ham trong file:
- Path helpers: lay duong dan .pi/triage, .pi/logs, .pi/results.
- Input helpers: parse target, parse ports, chon port list.
- Safety helpers: allowlist va --authorized gate.
- Output helpers: logging, JSON, .env.
"""

import json
import logging
from pathlib import Path
from urllib.parse import urlparse


DEFAULT_ALLOWED_TARGETS = {"localhost", "127.0.0.1", "::1", "scanme.nmap.org"}


def project_root() -> Path:
    """Thu muc goc project security-agents."""
    return Path(__file__).resolve().parents[3]


def pi_dir() -> Path:
    return project_root() / ".pi"


def triage_dir() -> Path:
    return pi_dir() / "triage"


def logs_dir() -> Path:
    return pi_dir() / "logs"


def results_dir() -> Path:
    return pi_dir() / "results"


def prompts_dir() -> Path:
    return pi_dir() / "prompts"


def data_dir() -> Path:
    return pi_dir() / "data"


def ensure_output_dirs() -> None:
    """Dam bao cac thu muc output ton tai truoc khi chay pipeline."""
    for directory in [triage_dir(), logs_dir(), results_dir()]:
        directory.mkdir(parents=True, exist_ok=True)


def load_allowed_targets() -> set[str]:
    """Doc danh sach target duoc phep scan tu .pi/data/allowed_targets.json."""
    config_path = data_dir() / "allowed_targets.json"
    if not config_path.exists():
        return DEFAULT_ALLOWED_TARGETS

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        targets = set(config.get("allowed_targets", []))
        return targets if targets else DEFAULT_ALLOWED_TARGETS
    except Exception:
        return DEFAULT_ALLOWED_TARGETS


def is_target_allowed(target: str, authorized: bool) -> bool:
    """Safety gate: allowlist hoac user truyen --authorized."""
    return authorized or target.lower() in load_allowed_targets()


def parse_ports(raw_ports: str) -> list[int]:
    """Parse comma-separated ports and simple ranges like 1-1000."""
    if not raw_ports:
        return []

    ports = []
    for part in raw_ports.split(","):
        item = part.strip()
        if not item:
            continue

        if "-" in item:
            start_text, end_text = item.split("-", 1)
            start_port = int(start_text.strip())
            end_port = int(end_text.strip())
            if start_port > end_port:
                start_port, end_port = end_port, start_port
            ports.extend(range(start_port, end_port + 1))
        else:
            ports.append(int(item))

    return sorted(set(ports))


def parse_target(raw_target: str) -> tuple[str, list[int]]:
    """Parse target URL or hostname and extract host plus optional port."""
    if "://" in raw_target:
        parsed = urlparse(raw_target)
        host = parsed.hostname or parsed.netloc.split(":")[0]
        port = parsed.port
        return host, [port] if port else []

    if ":" in raw_target and not raw_target.startswith("["):
        parts = raw_target.split(":")
        try:
            return parts[0], [int(parts[1])]
        except (ValueError, IndexError):
            pass

    return raw_target, []


def choose_ports(raw_ports: str, url_ports: list[int], default_ports: list[int]) -> list[int]:
    """Uu tien --ports, sau do port trong URL, cuoi cung la DEFAULT_PORTS."""
    custom_ports = parse_ports(raw_ports)
    if custom_ports:
        return custom_ports
    if url_ports:
        return url_ports
    return default_ports


def write_json(path: Path, data: dict) -> None:
    """Ghi dict thanh JSON dep de xem trong bao cao."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def setup_logging(log_path: Path) -> None:
    """Cau hinh log chay pipeline."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        force=True,
    )


def load_env() -> None:
    """Load OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL tu .env neu co."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    load_dotenv(project_root() / ".env")


def display_path(path: str | Path, base: Path | None = None) -> Path | str:
    """In duong dan ngan gon tren terminal."""
    current_base = base or Path.cwd()
    resolved_path = Path(path).resolve()
    try:
        return resolved_path.relative_to(current_base.resolve())
    except ValueError:
        return resolved_path.name
