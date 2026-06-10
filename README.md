# Network Recon + Risk Profiler

Final project **Topic 02** for Network Programming with AI/ML for Cybersecurity.

## Topic 02 Goal

Build a multi-agent pipeline that runs **port scanning**, **DNS enumeration**, and
**banner grabbing** in parallel, then combines the findings into an **ML-based
risk score** and a **MITRE-mapped Markdown report**.

## Pipeline To Remember

```text
Stage 0 - Safety Gate
  permission_gate_agent -> allow/block decision

Stage 1 - Parallel Recon
  port_scan_agent      -> .pi/triage/port_scan_result.json
  dns_enum_agent       -> .pi/triage/dns_enum_result.json
  banner_grab_agent    -> .pi/triage/banner_result.json

Stage 2 - ML Risk Scoring
  risk_score_agent     -> .pi/triage/risk_profile.json

Stage 3 - Report Generation
  report_agent         -> .pi/results/ket_qua.md

Stage 4 - Defensive Monitoring
  log_monitor_agent    -> read authorized logs
  threat_detection_agent -> rules + Isolation Forest log anomaly detection
  alert_agent          -> .pi/alerts/alerts.json and alert_report.md
```

The most important Topic 02 point is Stage 1 parallelism:

```text
/parallel
  scan_ports(target, ports)
  enumerate_dns(target)
  grab_banners(target, ports)
/join
```

In runnable Python, this is implemented with `ThreadPoolExecutor` in
`.pi/tools/main_pipeline.py`.

## Requirement Mapping

| Topic 02 requirement | Where it is implemented |
| --- | --- |
| 3+ sequential stages | `.pi/tools/main_pipeline.py` |
| Parallel stage | `run_recon_stage()` in `.pi/tools/main_pipeline.py` |
| Agent definitions | `.pi/agents/*.md` |
| Skills | `.pi/skills/recon`, `.pi/skills/risk_scoring`, `.pi/skills/reporting` |
| Python tools | `.pi/tools/recon`, `.pi/tools/risk`, `.pi/tools/reporting` |
| Chain/orchestration | `.pi/chains/recon_risk_pipeline.chain.md` |
| Prompt file | `.pi/prompts/report_prompt.md` |
| End-to-end demo target | localhost with Python's built-in `http.server` |
| GPT/agent loop extension | `.pi/tools/pi_recon_agent.py` |

## Code Design

The code is intentionally simple for oral defense:

- Recon tools use normal Python sockets and short timeouts.
- Stage 1 runs three independent tools at the same time.
- Risk scoring uses a small Isolation Forest anomaly model with explainable numeric features.
- Monitoring trains a separate Isolation Forest directly on each selected Loghub file.
- Report generation uses GPT when an API key exists and an offline template when it does not.
- Safety gate blocks non-allowlisted targets unless `--authorized` is explicitly provided.

## Agent Design

The `.pi/agents` folder defines ten agents:

- `orchestrator_agent`: coordinates the full pipeline and handoffs.
- `permission_gate_agent`: blocks unauthorized targets before network activity.
- `port_scan_agent`: checks candidate TCP ports.
- `dns_enum_agent`: collects A/MX/NS/TXT DNS records when applicable.
- `banner_grab_agent`: collects lightweight service banners.
- `risk_score_agent`: runs Isolation Forest risk scoring and MITRE mapping.
- `report_agent`: creates the final defensive Markdown report.
- `log_monitor_agent`: monitors authorized log files.
- `threat_detection_agent`: detects malware-like, brute-force, exploit, and traffic anomaly signals.
- `alert_agent`: writes alerts and optionally sends Discord/email notifications.

## Install

```bash
cd Network-Recon-Risk-Profiler
pip install -r requirements.txt
```

Create `.env` only if you want GPT report or agentic mode:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=
OPENAI_MODEL=gpt-4o
```

The normal pipeline still works without an API key.

## Run The Offline-Stable Pipeline

Terminal 1:

```bash
python -m http.server 8000 --bind 127.0.0.1
```

Terminal 2:

```bash
python .pi/tools/main_pipeline.py --target localhost --ports "8000,8080,3306,5432,6379" --offline
```

Outputs:

- `.pi/triage/port_scan_result.json`
- `.pi/triage/dns_enum_result.json`
- `.pi/triage/banner_result.json`
- `.pi/triage/risk_profile.json`
- `.pi/results/ket_qua.md`
- `.pi/logs/pipeline_run.log`

## Run The Week 5 Agentic Mode

This optional mode uses the OpenAI API.

Create `.env`:

```env
OPENAI_API_KEY=replace_with_your_openai_api_key
OPENAI_MODEL=gpt-4o
OPENAI_BASE_URL=https://api.openai.com/v1
```

Then run:

```bash
python .pi/tools/pi_recon_agent.py --target localhost --ports "8000,8080,3306,5432,6379"
```

Why this file exists:

- It defines OpenAI tool schemas.
- It implements the Observe-Think-Act agent loop.
- It preserves assistant `tool_calls` and appends `tool` results.
- It executes a batch of requested tool calls before the next model call.
- It can parse JSON tool plans if an API response returns tool calls as text.
- It reuses the same simple Topic 02 tools, so the core project remains easy to explain.

## Run Tests

```bash
python -m unittest discover -s tests
python -m compileall .pi/tools
```

## Run Defensive Monitoring Demo

This extension detects risk signals from an authorized sample log. It does not
execute malware, brute force, exploits, or harmful traffic.

```bash
python .pi/tools/threat_monitor.py --log-file .pi/data/sample_security_events.log
```

Public Loghub OpenSSH demo:

```bash
python .pi/tools/threat_monitor.py --log-file .pi/data/loghub_openssh_2k.log --output-dir .pi/alerts/loghub_openssh
```

Standalone ML training and anomaly ranking:

```bash
python .pi/tools/log_anomaly.py --log-file .pi/data/loghub_openssh_2k.log --top 20 --output .pi/alerts/loghub_openssh/ml_anomalies.json
python .pi/tools/log_anomaly.py --log-file .pi/data/loghub_apache_2k.log --top 20 --output .pi/alerts/loghub_apache/ml_anomalies.json
```

The public OpenSSH log is from LogPAI/loghub, a public system log dataset for
AI-driven log analytics. The OpenSSH README says the log was collected from an
OpenSSH server in their lab over 28+ days.

The monitoring ML flow:

1. Parse all 2,000 raw log lines into events.
2. Extract 12 explainable features per line, including message length, token
   count, IP count, error/security keyword counts, and template rarity.
3. Standardize the feature vectors.
4. Fit an unsupervised `IsolationForest` on the selected 2,000-line file.
5. Rank anomaly candidates and combine them with rule-based alerts.
6. Combine rule severity and the strongest ML anomaly into a separate
   `monitoring_risk_profile` score from 0 to 10.

This is separate from the network exposure risk model because log-line features
and scan-result features describe different security problems.

Outputs:

- `.pi/alerts/alerts.json`
- `.pi/alerts/alert_report.md`
- Optional standalone `.pi/alerts/.../ml_anomalies.json`

Live polling demo:

```bash
python .pi/tools/threat_monitor.py --live --duration 20 --poll-interval 2
```

Use `--no-ml` to run only the original rules, or change the expected anomaly
fraction with `--ml-contamination 0.03`.

Optional Discord/email alerting is controlled by `.env` variables shown in
`.env.example`.

Live mode stores delivered alert IDs in `monitor_state.json`, so repeated polls
do not resend the same alert.

## Run The API And Dashboard

```bash
uvicorn api_server:app --app-dir .pi/tools --host 127.0.0.1 --port 8000
```

Open:

- Dashboard: `http://127.0.0.1:8000`
- OpenAPI documentation: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

Optional API protection:

```env
API_KEY=replace_with_a_long_random_value
ALLOW_NON_ALLOWLISTED_TARGETS=false
```

Limited UDP reachability check for an authorized lab target:

```bash
python .pi/tools/udp_scanner.py --target localhost --ports "53,123,161"
```

UDP timeouts are reported as `open_or_filtered`; they are not treated as proof
that a UDP service is open.

Compare the Isolation Forest score with a supervised Random Forest on the
included classroom scenarios:

```bash
python .pi/tools/evaluate_models.py
```

The output includes precision, recall, false-positive rate, and a warning that
the small classroom dataset is not sufficient for production decisions.

Public log files included:

- `.pi/data/loghub_openssh_2k.log`
- `.pi/data/loghub_apache_2k.log`

Source:

- https://github.com/logpai/loghub/tree/master/OpenSSH
- https://github.com/logpai/loghub/tree/master/Apache

## Oral Defense Notes

Short answer for "What does your project do?":

> My project is Topic 02: Network Recon + Risk Profiler. It runs port scanning,
> DNS enumeration, and banner grabbing in parallel, then extracts simple features,
> predicts Low/Medium/High risk with an Isolation Forest model, maps findings to
> MITRE ATT&CK, and writes a defensive Markdown report.

Short answer for "Where is parallelism?":

> In Stage 1. `main_pipeline.py` submits port scan, DNS enum, and banner grab to
> `ThreadPoolExecutor(max_workers=3)` because they have no data dependency.

Short answer for "Where is ML?":

> `risk_features.py` converts recon output into numeric features, and
> `risk_model.py` uses a small Isolation Forest baseline to detect unusual
> exposure. The anomaly score is calibrated into a 0-10 Low/Medium/High risk
> result for the classroom report. Separately, `monitoring/anomaly_detector.py`
> trains Isolation Forest directly on all 2,000 Loghub lines to rank unusual
> security log events without requiring labels.

Short answer for "Where is the AI agent?":

> The stable pipeline is deterministic. The Week 5 agentic extension is
> `pi_recon_agent.py`, which exposes the same tools through OpenAI function
> calling and runs the Observe-Think-Act loop.

## Safety

This project is defensive and read-only:

- Scan only localhost, lab machines, or authorized targets.
- Do not exploit.
- Do not brute force.
- Do not bypass controls.
- Do not attack real systems.
