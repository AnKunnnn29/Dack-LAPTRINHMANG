# Network Recon + Risk Profiler

Final project **Topic 02** for Network Programming with AI/ML for Cybersecurity.

## Topic 02 Goal

Build a multi-agent pipeline that runs **port scanning**, **DNS enumeration**, and
**banner grabbing** in parallel, then combines the findings into an **ML-based
risk score** and a **MITRE-mapped Markdown report**.

This repository is intentionally scoped to the core Topic 02 requirements. The
stable demo path is deterministic and offline-friendly. The OpenAI agent loop is
kept only as a **Week 5 optional extension**.

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
| End-to-end demo target | `localhost` with Python's built-in `http.server` |
| Week 5 agent loop extension | `.pi/tools/pi_recon_agent.py` |

## Code Design

The code is intentionally simple for oral defense:

- Recon tools use normal Python sockets and short timeouts.
- Stage 1 runs three independent tools at the same time.
- Risk scoring uses a small, explainable Isolation Forest-style anomaly model.
- Report generation uses GPT when an API key exists and an offline template when it does not.
- Safety gate blocks non-allowlisted targets unless `--authorized` is explicitly provided.

## Agent Design

The `.pi/agents` folder defines seven core agents:

- `orchestrator_agent`: coordinates the full pipeline and handoffs.
- `permission_gate_agent`: blocks unauthorized targets before network activity.
- `port_scan_agent`: checks candidate TCP ports.
- `dns_enum_agent`: collects A/CNAME/MX/NS/SOA/TXT DNS records when applicable.
- `banner_grab_agent`: collects lightweight service banners and TLS metadata.
- `risk_score_agent`: runs Isolation Forest risk scoring and MITRE mapping.
- `report_agent`: creates the final defensive Markdown report.

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

This optional mode uses the OpenAI API and is kept to show the Week 5
Observe-Think-Act/tool-calling pattern.

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
- It executes requested tool calls before the next model call.
- It can parse JSON tool plans if an API response returns tool calls as text.
- It reuses the same simple Topic 02 tools, so the core project remains easy to explain.

## Run Tests

```bash
python -m unittest discover -s tests
python -m compileall .pi/tools
```

## Optional UDP Check

The main project is TCP recon. A small UDP reachability helper is kept as a
minor network-programming utility:

```bash
python .pi/tools/udp_scanner.py --target localhost --ports "53,123,161"
```

UDP timeouts are reported as `open_or_filtered`; they are not treated as proof
that a UDP service is open.

## Oral Defense Notes

Short answer for "What does your project do?":

> My project is Topic 02: Network Recon + Risk Profiler. It runs port scanning,
> DNS enumeration, and banner grabbing in parallel, then extracts simple features,
> predicts Low/Medium/High risk with an Isolation Forest-style model, maps findings
> to MITRE ATT&CK, and writes a defensive Markdown report.

Short answer for "Where is parallelism?":

> In Stage 1. `main_pipeline.py` submits port scan, DNS enum, and banner grab to
> `ThreadPoolExecutor(max_workers=3)` because they have no data dependency.

Short answer for "Where is ML?":

> `risk_features.py` converts recon output into numeric features, and
> `risk_model.py` uses a small Isolation Forest baseline to detect unusual
> network exposure. The anomaly score is calibrated into a 0-10 Low/Medium/High
> risk result for the classroom report.

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
