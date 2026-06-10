"""STAGE 3 - Markdown Report Coordinator.

File nay co 2 che do:
- Co OPENAI_API_KEY: goi GPT model, mac dinh gpt-4o.
- Khong co key/API loi: dung offline template de demo van chay duoc.
"""

import argparse
import json
import os
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from reporting.openai_report_client import generate_ai_report
from reporting.report_templates import build_offline_report, load_prompt


def generate_report(
    risk_profile_path: str | Path,
    output_path: str | Path,
    prompt_path: str | Path | None = None,
    model: str | None = None,
    offline: bool = False,
) -> str:
    """Doc risk_profile.json va ghi report Markdown ra ket_qua.md."""
    risk_path = Path(risk_profile_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    profile = json.loads(risk_path.read_text(encoding="utf-8"))
    prompt = load_prompt(prompt_path)
    selected_model = model or os.getenv("OPENAI_MODEL", "gpt-4o")

    api_key = os.getenv("OPENAI_API_KEY")

    # MARK: Report generation mode - API truoc, fallback offline sau.
    if offline or not api_key or api_key == "your_api_key_here":
        reason = "Offline mode requested" if offline else "No API key found"
        report = build_offline_report(profile, reason=reason)
    else:
        try:
            report = generate_ai_report(profile, prompt, selected_model)
        except Exception as exc:
            report = build_offline_report(profile, reason=f"OpenAI API error: {exc}")

    output.write_text(report, encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Markdown report")
    parser.add_argument("--risk-profile", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--prompt", default="")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()

    generate_report(args.risk_profile, args.output, args.prompt or None, offline=args.offline)
    print(f"Report written to {args.output}")


if __name__ == "__main__":
    main()
