# Network Recon + Risk Profiler

Topic 02 final project for Network Programming with AI/ML for Cybersecurity.

## One-line Idea

The pipeline runs port scanning, DNS enumeration, and banner grabbing in parallel, then combines the findings into an ML-based risk score and a MITRE-mapped Markdown report.

## Easy-to-Remember Pipeline

1. **Stage 1 - Parallel Recon**
   - `recon/port_scanner.py`: finds open TCP ports.
   - `recon/dns_enum.py`: collects A, MX, NS, TXT records.
   - `recon/banner_grabber.py`: collects service banners.

2. **Stage 2 - ML Risk Scoring**
   - `risk/risk_features.py`: turns recon output into features.
   - `risk/risk_model.py`: predicts Low/Medium/High risk with a small KNN model.
   - `risk/risk_findings.py`: creates findings, MITRE mapping, and recommendations.

3. **Stage 3 - Report Generation**
   - `reporting/ai_reporter.py`: writes `.pi/results/ket_qua.md`.
   - Uses GPT-4o when API key is available.
   - Falls back to an offline Markdown template when API is unavailable.

## Key Features

- Socket-based TCP port scanning.
- DNS enumeration with `dnspython`.
- Socket-based banner grabbing.
- Stage 1 parallelism with `ThreadPoolExecutor`.
- Per-port parallelism inside the port scanner for faster large ranges.
- Explainable supervised KNN risk scoring.
- MITRE ATT&CK mapping for recon findings.
- Permission gate for safer authorized scanning.

## Install

```bash
cd security-agents
pip install -r requirements.txt
```

## OpenAI Config

Create or edit `.env`:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=
OPENAI_MODEL=gpt-4o
```

OpenRouter example:

```env
OPENAI_API_KEY=your_openrouter_key_here
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=openai/gpt-4o
```

If no API key is available, the project still runs and generates an offline report.

## Run

```bash
python .pi/tools/main_pipeline.py --target localhost
```

With custom ports:

```bash
python .pi/tools/main_pipeline.py --target localhost --ports "3000,8000,8080"
python .pi/tools/main_pipeline.py --target localhost --ports "1-1000"
```

For a target outside the allowlist, only run when you have permission:

```bash
python .pi/tools/main_pipeline.py --target example.com --authorized
```

## Local Lab Demo

Terminal 1:

```bash
python lab_target_server.py
```

Terminal 2:

```bash
python .pi/tools/main_pipeline.py --target localhost --ports "3000,8000,8080,3306,5432,6379"
```

The lab server opens safe fake services on:

- `3000`, `8000`, `8080`: HTTP demo services.
- `3306`: fake MySQL banner.
- `5432`: fake PostgreSQL banner.
- `6379`: fake Redis banner.

## Outputs

- `.pi/triage/port_scan_result.json`
- `.pi/triage/dns_enum_result.json`
- `.pi/triage/banner_result.json`
- `.pi/triage/risk_profile.json`
- `.pi/results/ket_qua.md`
- `.pi/logs/pipeline_run.log`

## Safety

This project is for learning and defensive assessment only:

- Scan only localhost, lab machines, or authorized targets.
- Do not exploit.
- Do not brute force.
- Do not bypass controls.
- Do not attack real systems.
