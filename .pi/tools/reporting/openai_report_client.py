"""OpenAI API client for report generation."""

import json
import os


def generate_ai_report(profile: dict, prompt: str, model: str) -> str:
    """Call OpenAI API to create the Markdown report."""
    from openai import OpenAI

    base_url = os.getenv("OPENAI_BASE_URL", "").strip()
    if base_url:
        client = OpenAI(base_url=base_url)
    else:
        client = OpenAI()

    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": "You write concise defensive cybersecurity reports in Markdown.",
            },
            {
                "role": "user",
                "content": (
                    f"{prompt}\n\n"
                    "Risk profile JSON:\n"
                    f"```json\n{json.dumps(profile, indent=2, ensure_ascii=False)}\n```"
                ),
            },
        ],
    )
    return response.choices[0].message.content.strip()
