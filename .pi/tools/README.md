# Tool Map for Presentation

Use this file as a quick memory map when presenting the code.

## Main Entrypoint

- `main_pipeline.py`
  - Stage 1: runs recon tools in parallel.
  - Stage 2: scores risk with ML.
  - Stage 3: generates Markdown report.

- `pi_recon_agent.py`
  - Week 5 agentic extension.
  - Defines OpenAI tool schemas for the same project tools.
  - Runs the Observe-Think-Act loop with `tool_calls` and `tool` messages.
  - Requires `OPENAI_API_KEY`; the normal pipeline works offline.

## Common Helpers

- `common/tool_utils.py`
  - Project paths.
  - Target and port parsing.
  - Allowlist / `--authorized` safety gate.
  - JSON writing, logging, `.env` loading.

## Stage 1 - Recon

- `recon/port_scanner.py`
  - Checks TCP connectivity.
  - Returns open ports.
  - Uses per-port parallelism for faster scans.

- `recon/dns_enum.py`
  - Collects A, MX, NS, TXT records.
  - Skips localhost and IP targets.

- `recon/banner_grabber.py`
  - Reads service banners.
  - Sends HTTP HEAD request on common HTTP ports.

## Stage 2 - Risk Scoring

- `risk/risk_scorer.py`
  - Coordinates feature extraction, ML prediction, findings, and MITRE mapping.

- `risk/risk_features.py`
  - Converts recon results into simple numeric ML features.

- `risk/risk_model.py`
  - Small supervised KNN model.
  - Easy to explain: compare feature vector with training samples.

- `risk/risk_findings.py`
  - Converts risk signals into findings.
  - Maps findings to MITRE ATT&CK.
  - Creates defensive recommendations.

## Stage 3 - Reporting

- `reporting/ai_reporter.py`
  - Uses OpenAI/GPT report generation when API key exists.
  - Falls back to offline report template.

- `reporting/openai_report_client.py`
  - Contains only the API call.

- `reporting/report_templates.py`
  - Default prompt and offline report builder.

## Compatibility Wrappers

Files like `port_scanner.py`, `risk_scorer.py`, and `ai_reporter.py` directly inside `.pi/tools/` are wrappers. They keep old commands working while real code lives in the folders above.

## Quick Validation

```bash
python -m unittest discover -s tests
python -m compileall test_api.py .pi/tools
```
