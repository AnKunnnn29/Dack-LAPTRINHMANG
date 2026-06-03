"""Utility script to manage the authorized target allowlist.

Use this only for targets you own or have permission to test.
"""

import argparse
import json
import sys
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def get_config_path() -> Path:
    """Return path to .pi/data/allowed_targets.json."""
    project_root = Path(__file__).resolve().parents[2]
    return project_root / ".pi" / "data" / "allowed_targets.json"


def load_config() -> dict:
    """Load allowlist config, or create a safe default in memory."""
    config_path = get_config_path()
    if not config_path.exists():
        return {
            "allowed_targets": ["localhost", "127.0.0.1", "::1", "scanme.nmap.org"],
            "notes": [
                "Only add targets you are authorized to scan.",
                "Unauthorized scanning may be illegal.",
            ],
        }
    return json.loads(config_path.read_text(encoding="utf-8"))


def save_config(config: dict) -> None:
    """Save allowlist config to disk."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def list_targets() -> None:
    """Print all allowed targets."""
    config = load_config()
    targets = config.get("allowed_targets", [])

    print("Allowed Targets:")
    if not targets:
        print("   (empty)")
    else:
        for index, target in enumerate(targets, 1):
            print(f"   {index}. {target}")

    print(f"\nConfig file: {get_config_path()}")


def add_target(target: str) -> None:
    """Add a target to the allowlist."""
    config = load_config()
    targets = config.get("allowed_targets", [])

    if target in targets:
        print(f"[WARN] Target '{target}' already exists in allowed list.")
        return

    targets.append(target)
    config["allowed_targets"] = targets
    save_config(config)
    print(f"[OK] Added '{target}' to allowed targets.")


def remove_target(target: str) -> None:
    """Remove a target from the allowlist."""
    config = load_config()
    targets = config.get("allowed_targets", [])

    if target not in targets:
        print(f"[WARN] Target '{target}' not found in allowed list.")
        return

    targets.remove(target)
    config["allowed_targets"] = targets
    save_config(config)
    print(f"[OK] Removed '{target}' from allowed targets.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage allowed scan targets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python .pi/tools/manage_targets.py list
  python .pi/tools/manage_targets.py add 192.168.1.100
  python .pi/tools/manage_targets.py remove 192.168.1.100

WARNING: Only add targets you have permission to scan.
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    subparsers.add_parser("list", help="List all allowed targets")

    add_parser = subparsers.add_parser("add", help="Add a new target")
    add_parser.add_argument("target", help="Target hostname or IP to add")

    remove_parser = subparsers.add_parser("remove", help="Remove a target")
    remove_parser.add_argument("target", help="Target hostname or IP to remove")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "list":
        list_targets()
    elif args.command == "add":
        add_target(args.target)
    elif args.command == "remove":
        remove_target(args.target)


if __name__ == "__main__":
    main()
