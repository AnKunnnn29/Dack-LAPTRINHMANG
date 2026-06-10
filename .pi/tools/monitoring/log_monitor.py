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


def _notification_summary(summary: dict, seen_alert_ids: set[str]) -> dict:
    """Return only alerts that have not previously been delivered."""
    new_alerts = [
        alert for alert in summary.get("alerts", [])
        if alert.get("id") not in seen_alert_ids
    ]
    return {
        **summary,
        "alert_count": len(new_alerts),
        "alerts": new_alerts,
    }


def _state_path(output_dir: str | Path | None) -> Path:
    base = Path(output_dir) if output_dir else Path(__file__).resolve().parents[2] / "alerts"
    return base / "monitor_state.json"


def load_seen_alert_ids(output_dir: str | Path | None = None) -> set[str]:
    path = _state_path(output_dir)
    if not path.exists():
        return set()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return set(payload.get("seen_alert_ids", []))
    except (json.JSONDecodeError, OSError):
        return set()


def save_seen_alert_ids(seen_alert_ids: set[str], output_dir: str | Path | None = None) -> None:
    path = _state_path(output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"seen_alert_ids": sorted(seen_alert_ids)}, indent=2),
        encoding="utf-8",
    )


def run_monitor_once(
    log_file: str | Path,
    output_dir: str | Path | None = None,
    seen_alert_ids: set[str] | None = None,
    include_ml: bool = True,
    ml_contamination: float = 0.03,
) -> dict:
    """Analyze a log file once and write alert outputs."""
    events = load_events(log_file)
    summary = detect_threats(events, include_ml=include_ml, ml_contamination=ml_contamination)
    notification_summary = None
    if seen_alert_ids is not None:
        notification_summary = _notification_summary(summary, seen_alert_ids)
        seen_alert_ids.update(
            alert["id"] for alert in notification_summary.get("alerts", [])
        )
    dispatch = dispatch_alerts(summary, output_dir, notification_summary)
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
    include_ml: bool = True,
    ml_contamination: float = 0.03,
) -> dict:
    """Poll a log file for a limited duration and update alert outputs."""
    deadline = time.time() + max(0, duration)
    last_result: dict | None = None
    seen_alert_ids = load_seen_alert_ids(output_dir)
    notification_alert_count_total = 0
    while time.time() <= deadline:
        last_result = run_monitor_once(
            log_file,
            output_dir,
            seen_alert_ids,
            include_ml,
            ml_contamination,
        )
        notification_alert_count_total += last_result["dispatch"].get("notification_alert_count", 0)
        save_seen_alert_ids(seen_alert_ids, output_dir)
        time.sleep(max(0.2, poll_interval))

    if last_result is None:
        last_result = run_monitor_once(
            log_file,
            output_dir,
            seen_alert_ids,
            include_ml,
            ml_contamination,
        )
        notification_alert_count_total += last_result["dispatch"].get("notification_alert_count", 0)
        save_seen_alert_ids(seen_alert_ids, output_dir)
    last_result["mode"] = "live"
    last_result["duration"] = duration
    last_result["notification_alert_count_total"] = notification_alert_count_total
    return last_result


def main() -> None:
    parser = argparse.ArgumentParser(description="Defensive realtime log monitor")
    parser.add_argument("--log-file", default=str(default_sample_log()))
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--duration", type=float, default=20)
    parser.add_argument("--poll-interval", type=float, default=2)
    parser.add_argument("--no-ml", action="store_true", help="Disable Isolation Forest log anomaly detection")
    parser.add_argument("--ml-contamination", type=float, default=0.03)
    args = parser.parse_args()

    load_env()
    output_dir = args.output_dir or None
    try:
        if args.live:
            result = run_monitor_live(
                args.log_file,
                output_dir,
                args.duration,
                args.poll_interval,
                not args.no_ml,
                args.ml_contamination,
            )
        else:
            result = run_monitor_once(
                args.log_file,
                output_dir,
                include_ml=not args.no_ml,
                ml_contamination=args.ml_contamination,
            )
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(f"[ERROR] {exc}") from exc

    compact = {
        "mode": result["mode"],
        "log_file": result["log_file"],
        "alert_count": result["summary"]["alert_count"],
        "ml_anomaly_count": result["summary"]["ml_anomaly_analysis"].get("anomaly_count", 0),
        "ml_trained_on_events": result["summary"]["ml_anomaly_analysis"].get("trained_on_event_count", 0),
        "monitoring_risk_profile": result["summary"]["monitoring_risk_profile"],
        "outputs": result["dispatch"]["outputs"],
        "discord": result["dispatch"]["discord"],
        "email": result["dispatch"]["email"],
        "notification_alert_count": result["dispatch"].get("notification_alert_count", 0),
        "notification_alert_count_total": result.get(
            "notification_alert_count_total",
            result["dispatch"].get("notification_alert_count", 0),
        ),
    }
    print(json.dumps(compact, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
