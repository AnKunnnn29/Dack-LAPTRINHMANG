"""Rule-based defensive detections for lab/demo log monitoring.

The goal is to detect risk signals from authorized logs, not to exploit systems.
Input events are JSON lines with fields such as timestamp, event_type, src_ip,
username, process, path, message, and bytes_out.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BRUTE_FORCE_THRESHOLD = 5
TRAFFIC_EVENT_THRESHOLD = 20
TRAFFIC_BYTES_THRESHOLD = 50_000_000

MALWARE_PATTERNS = [
    r"\bmimikatz\b",
    r"\bpowershell(\.exe)?\b.*(-enc|-encodedcommand)\b",
    r"\bcertutil\b.*\b-urlcache\b",
    r"\brundll32\b.*\bhttp",
    r"\bmshta\b.*\bhttp",
    r"\\temp\\[^\\]+\.exe\b",
]

EXPLOIT_PATTERNS = [
    r"\.\./",
    r"/etc/passwd",
    r"\bunion\b.+\bselect\b",
    r"\bselect\b.+\bfrom\b",
    r"\bcmd=",
    r"\$\{jndi:",
    r"/wp-admin",
    r"/phpmyadmin",
]


def parse_raw_log_event(text: str) -> dict[str, Any]:
    """Best-effort parser for public raw logs such as Loghub OpenSSH/Apache."""
    event: dict[str, Any] = {"message": text}
    lowered = text.lower()

    failed_invalid = re.search(
        r"failed password for invalid user (?P<user>\S+) from (?P<src_ip>[0-9a-fA-F:.]+)",
        text,
        re.IGNORECASE,
    )
    failed_user = re.search(
        r"failed password for (?P<user>\S+) from (?P<src_ip>[0-9a-fA-F:.]+)",
        text,
        re.IGNORECASE,
    )
    invalid_user = re.search(
        r"invalid user (?P<user>\S+) from (?P<src_ip>[0-9a-fA-F:.]+)",
        text,
        re.IGNORECASE,
    )
    auth_failure = re.search(r"rhost=(?P<src_ip>\S+)(?:\s+user=(?P<user>\S+))?", text, re.IGNORECASE)

    match = failed_invalid or failed_user or invalid_user or auth_failure
    if match and any(term in lowered for term in ["failed password", "invalid user", "authentication failure"]):
        event["event_type"] = "failed_login"
        event["src_ip"] = match.groupdict().get("src_ip") or "unknown"
        event["username"] = match.groupdict().get("user") or "unknown"
        return event

    if "possible break-in attempt" in lowered:
        event["event_type"] = "ssh_break_in_probe"
        src_match = re.search(r"\[(?P<src_ip>[0-9a-fA-F:.]+)\]", text)
        if src_match:
            event["src_ip"] = src_match.group("src_ip")
        return event

    if "[error]" in lowered and "apache" not in lowered:
        event["event_type"] = "application_error"
    elif "http" in lowered or "[error]" in lowered or "[notice]" in lowered:
        event["event_type"] = "web_log"

    return event


def load_events(path: str | Path) -> list[dict[str, Any]]:
    """Load JSONL events. Invalid lines are preserved as raw log events."""
    events: list[dict[str, Any]] = []
    log_path = Path(path)
    if not log_path.exists():
        return events

    for line_number, line in enumerate(log_path.read_text(encoding="utf-8").splitlines(), 1):
        text = line.strip()
        if not text:
            continue
        try:
            event = json.loads(text)
            if not isinstance(event, dict):
                event = {"message": text}
        except json.JSONDecodeError:
            event = parse_raw_log_event(text)
        event.setdefault("line_number", line_number)
        events.append(event)

    return events


def alert_id(category: str, evidence: str) -> str:
    """Stable short alert id for deduplication and reporting."""
    digest = hashlib.sha1(f"{category}:{evidence}".encode("utf-8")).hexdigest()
    return f"{category.upper()}-{digest[:10]}"


def normalize_text(event: dict[str, Any]) -> str:
    """Combine text-like fields for simple pattern matching."""
    parts = [
        str(event.get("process", "")),
        str(event.get("command_line", "")),
        str(event.get("path", "")),
        str(event.get("message", "")),
    ]
    return " ".join(parts)


def build_alert(
    category: str,
    severity: str,
    title: str,
    evidence: str,
    recommendation: str,
    mitre: list[str],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create one alert object with defensive context."""
    return {
        "id": alert_id(category, evidence),
        "category": category,
        "severity": severity,
        "title": title,
        "evidence": evidence,
        "recommendation": recommendation,
        "mitre_technique_ids": mitre,
        "event_count": len(events),
        "first_seen": events[0].get("timestamp", ""),
        "last_seen": events[-1].get("timestamp", ""),
        "sample_events": events[:5],
    }


def detect_malware_indicators(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Detect malware-like command/process indicators in logs."""
    alerts = []
    for event in events:
        text = normalize_text(event)
        for pattern in MALWARE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                evidence = f"Pattern `{pattern}` matched event line {event.get('line_number')}: {text[:160]}"
                alerts.append(
                    build_alert(
                        "malware_indicator",
                        "High",
                        "Malware-like process or command indicator",
                        evidence,
                        "Isolate the host if confirmed, collect process/file evidence, and run trusted endpoint scanning.",
                        ["T1059", "T1105"],
                        [event],
                    )
                )
                break
    return alerts


def detect_brute_force(events: list[dict[str, Any]], threshold: int = BRUTE_FORCE_THRESHOLD) -> list[dict[str, Any]]:
    """Detect repeated failed logins by source IP and username."""
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        event_type = str(event.get("event_type", "")).lower()
        message = str(event.get("message", "")).lower()
        if (
            event_type == "failed_login"
            or "failed login" in message
            or "failed password" in message
            or "authentication failure" in message
            or "authentication failed" in message
        ):
            src_ip = str(event.get("src_ip", "unknown"))
            username = str(event.get("username", "unknown"))
            groups[(src_ip, username)].append(event)

    alerts = []
    for (src_ip, username), items in groups.items():
        if len(items) >= threshold:
            evidence = f"{len(items)} failed logins from {src_ip} for user {username}"
            alerts.append(
                build_alert(
                    "brute_force",
                    "High" if len(items) >= threshold * 2 else "Medium",
                    "Possible brute-force login activity",
                    evidence,
                    "Review authentication logs, block or rate-limit the source, and enforce MFA/account lockout policy.",
                    ["T1110"],
                    items,
                )
            )
    return alerts


def detect_exploit_attempts(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Detect common web exploit probes from HTTP log-like events."""
    alerts = []
    for event in events:
        event_type = str(event.get("event_type", "")).lower()
        text = normalize_text(event)
        if event_type not in {"http_request", "web_request", ""} and "http" not in text.lower():
            continue
        for pattern in EXPLOIT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                src_ip = str(event.get("src_ip", "unknown"))
                evidence = f"Web exploit probe from {src_ip}; pattern `{pattern}` matched: {text[:160]}"
                alerts.append(
                    build_alert(
                        "exploit_attempt",
                        "High",
                        "Possible web exploit attempt",
                        evidence,
                        "Review web access logs, patch exposed apps, add WAF rules, and verify no compromise occurred.",
                        ["T1190"],
                        [event],
                    )
                )
                break
    return alerts


def detect_traffic_anomalies(
    events: list[dict[str, Any]],
    count_threshold: int = TRAFFIC_EVENT_THRESHOLD,
    bytes_threshold: int = TRAFFIC_BYTES_THRESHOLD,
) -> list[dict[str, Any]]:
    """Detect unusual network bursts or large outbound transfer indicators."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    bytes_by_src: dict[str, int] = defaultdict(int)

    for event in events:
        event_type = str(event.get("event_type", "")).lower()
        if event_type not in {"network_connection", "traffic"}:
            continue
        src_ip = str(event.get("src_ip", "unknown"))
        groups[src_ip].append(event)
        try:
            bytes_by_src[src_ip] += int(event.get("bytes_out", 0))
        except (TypeError, ValueError):
            pass

    alerts = []
    for src_ip, items in groups.items():
        total_bytes = bytes_by_src[src_ip]
        if len(items) >= count_threshold or total_bytes >= bytes_threshold:
            evidence = f"{len(items)} network events from {src_ip}, outbound bytes={total_bytes}"
            alerts.append(
                build_alert(
                    "traffic_anomaly",
                    "High" if total_bytes >= bytes_threshold else "Medium",
                    "Unusual network traffic pattern",
                    evidence,
                    "Check the source host, destination list, expected workload, and firewall/proxy logs.",
                    ["T1041", "T1046"],
                    items,
                )
            )
    return alerts


def detect_threats(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Run all defensive detectors and return one summary."""
    alerts = []
    alerts.extend(detect_malware_indicators(events))
    alerts.extend(detect_brute_force(events))
    alerts.extend(detect_exploit_attempts(events))
    alerts.extend(detect_traffic_anomalies(events))

    unique: dict[str, dict[str, Any]] = {}
    for alert in alerts:
        unique[alert["id"]] = alert

    sorted_alerts = sorted(
        unique.values(),
        key=lambda item: {"High": 0, "Medium": 1, "Low": 2}.get(item["severity"], 3),
    )
    generated_at = datetime.now(timezone.utc).isoformat()
    return {
        "generated_at": generated_at,
        "event_count": len(events),
        "alert_count": len(sorted_alerts),
        "alerts": sorted_alerts,
        "notes": [
            "Detections are rule-based for defensive classroom demonstration.",
            "Alerts require human validation before incident response action.",
            "No exploit, malware execution, brute force, or offensive action is performed.",
        ],
    }
