# recon_risk_pipeline

Topic 02: Network Recon + Risk Profiler.

## Goal

Run safe reconnaissance on an authorized target, score the risk with a simple ML
model, map findings to MITRE ATT&CK, and generate a defensive Markdown report.

## Agent Roles

- `orchestrator_agent`: validates order, coordinates stages, and returns output paths.
- `permission_gate_agent`: blocks unauthorized targets before network activity.
- `port_scan_agent`: checks candidate TCP ports.
- `dns_enum_agent`: collects allowed DNS records.
- `banner_grab_agent`: collects lightweight service banners.
- `risk_score_agent`: extracts ML features and runs Isolation Forest scoring.
- `report_agent`: writes the final defensive Markdown report.
- `log_monitor_agent`: reads authorized logs once or in live polling mode.
- `threat_detection_agent`: detects malware-like, brute-force, exploit, and traffic anomaly signals.
- `alert_agent`: writes local alerts and optionally sends Discord/email notifications.

## Stage 0: Permission Gate

Before any network tool runs:

```text
permission_gate_agent(target, authorized)
```

Decision:

- allowed -> continue to Stage 1
- blocked -> stop pipeline and write reason to log

## Stage 1: Parallel Recon Collection

These three agents have no data dependency, so they run at the same time:

```text
/parallel
  port_scan_agent(target, ports)
  dns_enum_agent(target)
  banner_grab_agent(target, ports)
/join
```

Outputs:

- `.pi/triage/port_scan_result.json`
- `.pi/triage/dns_enum_result.json`
- `.pi/triage/banner_result.json`

Python implementation:

- `.pi/tools/main_pipeline.py` uses `ThreadPoolExecutor(max_workers=3)`.
- `.pi/tools/recon/port_scanner.py` also uses per-port parallelism for faster scans.

Why this matches Topic 02:

- Port scanning can be slow because each port may wait for a timeout.
- DNS enumeration is independent of TCP scanning.
- Banner grabbing can try the same candidate ports without waiting for scan output.
- Running them in parallel reduces wall-clock time compared with serial execution.

## Stage 2: ML Risk Scoring

Agent:

- `risk_score_agent`

Tools:

- `.pi/tools/risk/risk_features.py`
- `.pi/tools/risk/risk_model.py`
- `.pi/tools/risk/risk_findings.py`
- `.pi/tools/risk/risk_scorer.py`

Process:

1. Confirm the three Stage 1 JSON files exist.
2. Read the three Stage 1 JSON files.
3. Extract simple explainable features:
   - open port count
   - sensitive port count
   - high-risk port count
   - database/cache port count
   - HTTP port count
   - version banner count
   - DNS record count
4. Predict Low/Medium/High risk with a small Isolation Forest anomaly model.
5. Build findings, MITRE mapping, and recommendations.

Output:

- `.pi/triage/risk_profile.json`

## Stage 3: Report Generation

Agent:

- `report_agent`

Tools:

- `.pi/tools/reporting/ai_reporter.py`
- `.pi/tools/reporting/openai_report_client.py`
- `.pi/tools/reporting/report_templates.py`

Process:

1. Read `.pi/triage/risk_profile.json`.
2. Read `.pi/prompts/report_prompt.md`.
3. Use GPT if `OPENAI_API_KEY` exists.
4. Otherwise use the offline report template.
5. Write the final Markdown report.

Output:

- `.pi/results/ket_qua.md`

## Stage 4: Defensive Monitoring And Alerting

Agents:

- `log_monitor_agent`
- `threat_detection_agent`
- `alert_agent`

Tools:

- `.pi/tools/monitoring/log_monitor.py`
- `.pi/tools/monitoring/detectors.py`
- `.pi/tools/monitoring/alerter.py`

Process:

1. Read authorized log events from `.pi/data/sample_security_events.log` or another log file.
2. Extract per-line features and train Isolation Forest on the selected log.
3. Detect malware-like indicators, brute force, web exploit probes, traffic anomalies, and ML anomaly candidates.
4. Map alerts to defensive MITRE context.
5. Write alert JSON and Markdown.
6. Send Discord/email only when environment variables are configured.

Outputs:

- `.pi/alerts/alerts.json`
- `.pi/alerts/alert_report.md`

## Week 5 Agentic Extension

The deterministic pipeline above is the stable demo path.
The Week 5 Observe-Think-Act version is implemented in:

- `.pi/tools/pi_recon_agent.py`

It defines OpenAI tool schemas for:

- `scan_ports`
- `enumerate_dns`
- `grab_banners`
- `score_risk_from_triage`
- `generate_markdown_report`

The agent loop:

1. Sends full message history to the model.
2. Lets the model choose tools with `tool_choice="auto"`.
3. Preserves the assistant message and its `tool_calls`.
4. Executes every requested tool call.
5. Appends all `role="tool"` results with matching `tool_call_id`.
6. Repeats until `finish_reason == "stop"` or the iteration limit is reached.

## Safety Boundary

- Read-only recon only.
- No exploit, no brute force, no bypass.
- Allowlist gate in `.pi/tools/common/tool_utils.py`.
- `--authorized` is required for targets outside the demo allowlist.
- The agentic runner also has simple per-tool rate limiting.

## Handoff Summary

```text
orchestrator_agent
  -> permission_gate_agent
  -> /parallel
       port_scan_agent
       dns_enum_agent
       banner_grab_agent
     /join
  -> risk_score_agent
  -> report_agent
  -> log_monitor_agent
  -> threat_detection_agent
  -> alert_agent
```
