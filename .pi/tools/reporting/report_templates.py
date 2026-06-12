"""Prompt loading and offline Markdown report templates."""

from pathlib import Path


DEFAULT_PROMPT = """
Write a short, clear Markdown report for Network Recon + Risk Profiler.
Do not include exploit steps, payloads, brute-force guidance, bypass steps, or attack instructions.
Only provide defensive observations and recommendations.

Required sections:
1. Target
2. Recon Summary
3. Risk Level
4. ML Risk Model
5. Findings
6. MITRE ATT&CK Mapping
7. Recommendations
8. Conclusion
"""


def load_prompt(prompt_path: str | Path | None = None) -> str:
    """Load custom report prompt, or use DEFAULT_PROMPT."""
    if not prompt_path:
        return DEFAULT_PROMPT.strip()

    path = Path(prompt_path)
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return DEFAULT_PROMPT.strip()


def build_offline_report(profile: dict, reason: str = "No API key found") -> str:
    """Fallback report used when OpenAI API is unavailable."""
    summary = profile.get("recon_summary", {})
    open_ports = summary.get("open_ports", [])
    dns_message = summary.get("dns_message", "")
    banners = summary.get("banners", {})
    services = summary.get("services", {})
    tls = summary.get("tls", {})
    findings = profile.get("findings", [])
    mitre_mapping = profile.get("mitre_mapping", [])
    ml_model = profile.get("ml_model", {})
    recommendations = profile.get("recommendations", [])

    lines = [
        "# Network Recon + Risk Profiler Report",
        "",
        "## Target",
        f"- Target: `{profile.get('target', 'unknown')}`",
        "",
        "## Recon Summary",
        f"- Open ports: `{open_ports}`",
        f"- DNS status: {dns_message or 'N/A'}",
        f"- Banner results: `{banners}`",
        f"- Service guesses: `{services}`",
        f"- TLS metadata: `{tls}`",
        "",
        "## Risk Level",
        f"- Score: `{profile.get('score', 0)}`",
        f"- Level: **{profile.get('risk_level', 'Low')}**",
        "",
        "## ML Risk Model",
        f"- Model: {ml_model.get('name', 'N/A')}",
        f"- Type: {ml_model.get('type', 'N/A')}",
        f"- Anomaly score: `{ml_model.get('anomaly_score', 'N/A')}`",
        f"- Calibrated anomaly: `{ml_model.get('calibrated_anomaly', 'N/A')}`",
        f"- Exposure severity: `{ml_model.get('exposure_severity', 'N/A')}`",
        f"- Features: `{ml_model.get('features', {})}`",
        f"- Risk drivers: `{ml_model.get('risk_drivers', [])}`",
        "",
        "## Findings",
    ]

    if findings:
        for finding in findings:
            techniques = ", ".join(finding.get("mitre_technique_ids", [])) or "N/A"
            lines.append(f"- {finding.get('description')} MITRE: `{techniques}`")
    else:
        lines.append("- No notable findings from the selected safe checks.")

    lines.extend(["", "## MITRE ATT&CK Mapping"])

    if mitre_mapping:
        for item in mitre_mapping:
            lines.append(
                f"- `{item.get('technique_id')}` {item.get('technique')} "
                f"({item.get('tactic')}): {item.get('defensive_note')}"
            )
    else:
        lines.append("- No MITRE mapping was generated for this run.")

    lines.extend(["", "## Recommendations"])

    for item in recommendations:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Conclusion",
            "This report is for defensive assessment on authorized systems only. "
            "Prioritize closing unnecessary services, limiting access scope, "
            "reducing banner exposure, and reviewing scan findings with a human analyst.",
            "",
            f"> Offline fallback used: {reason}",
        ]
    )

    return "\n".join(lines)
