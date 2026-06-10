"""Realtime/file-based defensive log monitor for classroom demo."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from common.tool_utils import load_env  # noqa: E402
from monitoring.alerter import dispatch_alerts  # noqa: E402
from monitoring.detectors import detect_threats, load_events  # noqa: E402


def default_sample_log() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "sample_security_events.log"


def run_monitor_once(log_file: str | Path, output_dir: str | Path | None = None) -> dict:
    """Analyze a log file once and write alert outputs."""
    events = load_events(log_file)
    summary = detect_threats(events)
    dispatch = dispatch_alerts(summary, output_dir)
    return {
        "mode": "once",
        "log_file": str(log_file),
        "summary": summary,
        "dispatch": dispatch,
    }


def run_monitor_live(
    log_file: str | Path,
    output_dir: str | Path | None = None,
    duration: float = 30,
    poll_interval: float = 2,
) -> dict:
    """Poll a log file for a limited duration and update alert outputs."""
    deadline = time.time() + max(0, duration)
    last_result: dict | None = None
    while time.time() <= deadline:
        last_result = run_monitor_once(log_file, output_dir)
        time.sleep(max(0.2, poll_interval))

    if last_result is None:
        last_result = run_monitor_once(log_file, output_dir)
    last_result["mode"] = "live"
    last_result["duration"] = duration
    return last_result


def main() -> None:
    parser = argparse.ArgumentParser(description="Defensive realtime log monitor")
    parser.add_argument("--log-file", default=str(default_sample_log()))
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--duration", type=float, default=20)
    parser.add_argument("--poll-interval", type=float, default=2)
    args = parser.parse_args()

    load_env()
    output_dir = args.output_dir or None
    if args.live:
        result = run_monitor_live(args.log_file, output_dir, args.duration, args.poll_interval)
    else:
        result = run_monitor_once(args.log_file, output_dir)

    compact = {
        "mode": result["mode"],
        "log_file": result["log_file"],
        "alert_count": result["summary"]["alert_count"],
        "outputs": result["dispatch"]["outputs"],
        "discord": result["dispatch"]["discord"],
        "email": result["dispatch"]["email"],
    }
    print(json.dumps(compact, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
