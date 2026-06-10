"""CLI for training and running ML anomaly detection on a log file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parent))

from monitoring.anomaly_detector import analyze_log_anomalies  # noqa: E402
from monitoring.detectors import load_events  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Isolation Forest on a security log")
    parser.add_argument("--log-file", required=True)
    parser.add_argument("--contamination", type=float, default=0.03)
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    try:
        result = analyze_log_anomalies(
            load_events(args.log_file),
            contamination=args.contamination,
            top_limit=args.top,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(f"[ERROR] {exc}") from exc

    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
