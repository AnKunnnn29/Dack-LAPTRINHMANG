# Project 02 Alignment Checklist

This file is written for graders and for oral defense preparation.

## Topic

**Topic 02 - Network Recon + Risk Profiler**

One-line description from the topic list:

> A recon pipeline that runs port scanning, DNS enumeration, and banner grabbing
> simultaneously, then feeds the combined findings into an ML-based risk scorer
> and a GPT-4o MITRE-mapped risk report.

## What This Repository Implements

| Requirement | Evidence in repo |
| --- | --- |
| Multi-agent pipeline | `.pi/agents/*.md` plus `.pi/chains/recon_risk_pipeline.chain.md` |
| At least 3 sequential stages | Stage 1 recon, Stage 2 risk scoring, Stage 3 report |
| Parallel agent execution | `.pi/tools/main_pipeline.py`, function `run_recon_stage()` |
| Python tools | `.pi/tools/recon`, `.pi/tools/risk`, `.pi/tools/reporting` |
| Skills | `.pi/skills/recon/SKILL.md`, `.pi/skills/risk_scoring/SKILL.md`, `.pi/skills/reporting/SKILL.md` |
| Prompt or chain | `.pi/prompts/report_prompt.md`, `.pi/chains/recon_risk_pipeline.chain.md` |
| End-to-end demo target | localhost with Python's built-in `http.server` |
| AI/GPT report | `.pi/tools/reporting/openai_report_client.py` with offline fallback |
| Week 5 agent loop | `.pi/tools/pi_recon_agent.py` |
| Safety boundary | allowlist and `--authorized` gate in `.pi/tools/common/tool_utils.py` |
| Tests | `tests/test_project02.py` |

## Stage Details

### Stage 1 - Parallel Recon

Agents:

- `port_scan_agent`
- `dns_enum_agent`
- `banner_grab_agent`

Tools:

- `.pi/tools/recon/port_scanner.py`
- `.pi/tools/recon/dns_enum.py`
- `.pi/tools/recon/banner_grabber.py`

Reason for parallelism:

- The port scanner, DNS resolver, and banner grabber do not depend on each other.
- They are I/O-bound tasks, so parallel execution reduces waiting time.

### Stage 2 - ML Risk Scoring

Agent:

- `risk_score_agent`

Tools:

- `.pi/tools/risk/risk_features.py`
- `.pi/tools/risk/risk_model.py`
- `.pi/tools/risk/risk_findings.py`
- `.pi/tools/risk/risk_scorer.py`

ML explanation:

- The project extracts seven simple features from recon output.
- A small KNN model compares the feature vector with labelled classroom samples.
- The output is a Low/Medium/High risk level plus a 0-10 score.
- The model is intentionally small so each student can explain and rewrite it.

### Stage 3 - MITRE-Mapped Report

Agent:

- `report_agent`

Tools:

- `.pi/tools/reporting/ai_reporter.py`
- `.pi/tools/reporting/openai_report_client.py`
- `.pi/tools/reporting/report_templates.py`

Report output:

- `.pi/results/ket_qua.md`

## How To Run

Offline-stable demo:

```bash
python -m http.server 8000 --bind 127.0.0.1
python .pi/tools/main_pipeline.py --target localhost --ports "8000,8080,3306,5432,6379"
```

Agentic Week 5 demo, requires `OPENAI_API_KEY`:

```bash
python .pi/tools/pi_recon_agent.py --target localhost --ports "8000,8080,3306,5432,6379"
```

Validation:

```bash
python -m unittest discover -s tests
python -m compileall test_api.py .pi/tools
```

## Short Oral Defense Answers

**Why is this Topic 02?**

Because it runs port scan, DNS enum, and banner grabbing in parallel, then uses
ML risk scoring and a MITRE-mapped report.

**Why use sockets?**

Port scanning and banner grabbing need TCP connections. The code uses
`socket.create_connection`, short timeouts, and `sendall` for HTTP banner requests.

**Why is Stage 1 parallel?**

The three recon tasks are independent and mostly wait for network I/O, so
`ThreadPoolExecutor` reduces total waiting time.

**Why KNN?**

KNN is easy to explain: convert recon output to a feature vector, compare it with
labelled examples, and use the nearest examples to predict risk.

**Where is MITRE ATT&CK?**

`risk_findings.py` maps open ports, active scanning, DNS collection, and version
banner exposure to MITRE techniques.

**Where is the Week 5 agent loop?**

`pi_recon_agent.py` defines tool schemas and implements the OpenAI function-calling
loop with message history and `tool_call_id` matching.

## Scope And Safety

This project is read-only and defensive:

- No exploit code.
- No brute force.
- No payloads.
- No bypass.
- Targets must be localhost, lab systems, or explicitly authorized systems.
