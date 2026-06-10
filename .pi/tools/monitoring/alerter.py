"""Alert writing and optional Discord/email dispatch."""

from __future__ import annotations

import json
import os
import smtplib
import urllib.error
import urllib.request
from email.message import EmailMessage
from pathlib import Path
from typing import Any


def alerts_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "alerts"


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def render_alert_markdown(summary: dict[str, Any]) -> str:
    """Render alerts as a compact Markdown report."""
    lines = [
        "# Defensive Monitoring Alerts",
        "",
        f"- Generated at: `{summary.get('generated_at', '')}`",
        f"- Events analyzed: `{summary.get('event_count', 0)}`",
        f"- Alerts: `{summary.get('alert_count', 0)}`",
        "",
    ]

    alerts = summary.get("alerts", [])
    if not alerts:
        lines.append("No alerts detected in the monitored log window.")
    else:
        for alert in alerts:
            techniques = ", ".join(alert.get("mitre_technique_ids", [])) or "N/A"
            lines.extend(
                [
                    f"## [{alert.get('severity')}] {alert.get('title')}",
                    "",
                    f"- ID: `{alert.get('id')}`",
                    f"- Category: `{alert.get('category')}`",
                    f"- Evidence: {alert.get('evidence')}",
                    f"- MITRE: `{techniques}`",
                    f"- Recommendation: {alert.get('recommendation')}",
                    "",
                ]
            )

    lines.extend(
        [
            "## Notes",
            "",
            "- Defensive monitoring demo only.",
            "- Validate alerts before taking incident response action.",
        ]
    )
    return "\n".join(lines)


def write_alert_outputs(summary: dict[str, Any], output_dir: str | Path | None = None) -> dict[str, str]:
    """Write alert JSON and Markdown outputs."""
    current_dir = Path(output_dir) if output_dir else alerts_dir()
    current_dir.mkdir(parents=True, exist_ok=True)
    json_path = current_dir / "alerts.json"
    md_path = current_dir / "alert_report.md"

    write_json(json_path, summary)
    md_path.write_text(render_alert_markdown(summary), encoding="utf-8")
    return {"alerts_json": str(json_path), "alert_report": str(md_path)}


def send_discord_alert(summary: dict[str, Any]) -> dict[str, Any]:
    """Send a compact alert summary to Discord if DISCORD_WEBHOOK_URL exists."""
    webhook = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook:
        return {"enabled": False, "status": "missing DISCORD_WEBHOOK_URL"}

    top_alerts = summary.get("alerts", [])[:5]
    content_lines = [
        f"Network Recon Risk Profiler detected {summary.get('alert_count', 0)} alert(s).",
    ]
    for alert in top_alerts:
        content_lines.append(f"- [{alert.get('severity')}] {alert.get('title')} ({alert.get('id')})")

    payload = json.dumps({"content": "\n".join(content_lines)}).encode("utf-8")
    request = urllib.request.Request(
        webhook,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return {"enabled": True, "status": "sent", "http_status": response.status}
    except urllib.error.URLError as exc:
        return {"enabled": True, "status": "failed", "error": str(exc)}


def send_email_alert(summary: dict[str, Any]) -> dict[str, Any]:
    """Send alert email if SMTP environment variables are configured."""
    host = os.getenv("SMTP_HOST", "").strip()
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    sender = os.getenv("ALERT_EMAIL_FROM", "").strip()
    recipient = os.getenv("ALERT_EMAIL_TO", "").strip()
    if not all([host, username, password, sender, recipient]):
        return {"enabled": False, "status": "missing SMTP configuration"}

    port = int(os.getenv("SMTP_PORT", "587"))
    message = EmailMessage()
    message["Subject"] = f"Security monitoring alerts: {summary.get('alert_count', 0)}"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(render_alert_markdown(summary))

    try:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(username, password)
            smtp.send_message(message)
        return {"enabled": True, "status": "sent"}
    except Exception as exc:
        return {"enabled": True, "status": "failed", "error": str(exc)}


def dispatch_alerts(summary: dict[str, Any], output_dir: str | Path | None = None) -> dict[str, Any]:
    """Write local alerts and optionally send Discord/email notifications."""
    outputs = write_alert_outputs(summary, output_dir)
    return {
        "outputs": outputs,
        "discord": send_discord_alert(summary),
        "email": send_email_alert(summary),
    }
