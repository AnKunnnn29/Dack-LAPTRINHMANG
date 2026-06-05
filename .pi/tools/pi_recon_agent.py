"""Topic 02 agentic runner using OpenAI tool calling.

This file is the Week 5 Observe-Think-Act layer for the project.
It reuses the simple Python tools from the normal pipeline:

1. scan_ports
2. enumerate_dns
3. grab_banners
4. score_risk_from_triage
5. generate_markdown_report

The deterministic runner in main_pipeline.py is still useful for offline demos.
This agentic runner shows that the same tools can be controlled by an LLM agent.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parent))

from common.tool_utils import (  # noqa: E402
    choose_ports,
    display_path,
    ensure_output_dirs,
    is_target_allowed,
    load_env,
    logs_dir,
    parse_ports,
    parse_target,
    prompts_dir,
    results_dir,
    setup_logging,
    triage_dir,
    write_json,
)
from recon.banner_grabber import grab_banners  # noqa: E402
from recon.dns_enum import enumerate_dns  # noqa: E402
from recon.port_scanner import DEFAULT_PORTS, scan_ports  # noqa: E402
from reporting.ai_reporter import generate_report  # noqa: E402
from risk.risk_scorer import save_risk_profile, score_risk  # noqa: E402


RECON_AGENT_SYSTEM = """You are the Topic 02 Network Recon + Risk Profiler agent.

Goal: run an authorized, read-only reconnaissance workflow and produce a defensive report.

Required protocol:
1. In the first tool turn, call these independent tools: scan_ports, enumerate_dns, grab_banners.
2. After all three recon results are available, call score_risk_from_triage.
3. After risk scoring is complete, call generate_markdown_report.
4. Then stop and summarize the output paths.

Safety rules:
- Work only on authorized targets.
- Do not exploit, brute force, bypass controls, or provide payloads.
- Keep the analysis defensive and MITRE-mapped.
"""


TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "scan_ports",
            "description": (
                "Check a small TCP port list on an authorized target. "
                "Call this in the first recon step. Returns open ports and writes "
                ".pi/triage/port_scan_result.json."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Hostname or IP, for example localhost."},
                    "ports": {
                        "type": "string",
                        "description": "Comma list or range, for example 80,443,8000 or 1-1000.",
                    },
                    "timeout": {"type": "number", "description": "Socket timeout in seconds.", "default": 0.5},
                },
                "required": ["target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "enumerate_dns",
            "description": (
                "Collect A, MX, NS, and TXT records for a domain. "
                "Call this in the first recon step. It safely skips localhost/IP targets."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Domain, hostname, or IP target."}
                },
                "required": ["target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grab_banners",
            "description": (
                "Read service banners from a small TCP port list. "
                "Call this in the first recon step together with scan_ports and enumerate_dns."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Hostname or IP target."},
                    "ports": {
                        "type": "string",
                        "description": "Comma list or range. Use the same ports as scan_ports.",
                    },
                    "timeout": {"type": "number", "description": "Socket timeout in seconds.", "default": 1.0},
                },
                "required": ["target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "score_risk_from_triage",
            "description": (
                "Read the three recon JSON files, extract ML features, run the simple KNN risk model, "
                "write .pi/triage/risk_profile.json, and return score, level, findings, and MITRE mapping. "
                "Call only after scan_ports, enumerate_dns, and grab_banners have finished."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_markdown_report",
            "description": (
                "Generate .pi/results/ket_qua.md from risk_profile.json. "
                "Call this last after risk scoring."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


class ToolRuntime:
    """Small safety wrapper around the project tools.

    The LLM can choose tool arguments, but this runtime decides whether a call is safe.
    That is the key Week 5 rule: the model decides what to request; code enforces scope.
    """

    def __init__(self, authorized: bool, default_ports: list[int], timeout: float):
        self.authorized = authorized
        self.default_ports = default_ports
        self.timeout = timeout
        self.call_times: dict[str, list[float]] = {}

    def _check_rate_limit(self, tool_name: str, max_calls: int = 6, window_seconds: int = 60) -> dict | None:
        """Sliding-window limiter so a confused agent cannot loop forever on one tool."""
        now = time.time()
        recent = [item for item in self.call_times.get(tool_name, []) if now - item < window_seconds]
        if len(recent) >= max_calls:
            return {"error": f"rate limit exceeded for {tool_name}"}
        recent.append(now)
        self.call_times[tool_name] = recent
        return None

    def _check_target(self, target: str) -> dict | None:
        """Hard safety gate: only allow demo/allowlisted targets unless --authorized is used."""
        if is_target_allowed(target, self.authorized):
            return None
        return {
            "error": (
                f"target {target} is outside the allowlist. "
                "Use localhost or pass --authorized only when you have permission."
            )
        }

    def _select_ports(self, raw_ports: str | None) -> list[int]:
        """Use model-provided ports when valid, otherwise fall back to CLI/default ports."""
        if raw_ports:
            return parse_ports(raw_ports)
        return self.default_ports

    def scan_ports(self, target: str, ports: str = "", timeout: float | None = None) -> dict:
        blocked = self._check_target(target) or self._check_rate_limit("scan_ports")
        if blocked:
            return blocked

        selected_ports = self._select_ports(ports)
        result = scan_ports(target, selected_ports, timeout or self.timeout)
        write_json(triage_dir() / "port_scan_result.json", result)
        return result

    def enumerate_dns(self, target: str) -> dict:
        blocked = self._check_target(target) or self._check_rate_limit("enumerate_dns")
        if blocked:
            return blocked

        result = enumerate_dns(target)
        write_json(triage_dir() / "dns_enum_result.json", result)
        return result

    def grab_banners(self, target: str, ports: str = "", timeout: float | None = None) -> dict:
        blocked = self._check_target(target) or self._check_rate_limit("grab_banners")
        if blocked:
            return blocked

        selected_ports = self._select_ports(ports)
        result = grab_banners(target, selected_ports, timeout or self.timeout)
        write_json(triage_dir() / "banner_result.json", result)
        return result

    def score_risk_from_triage(self) -> dict:
        blocked = self._check_rate_limit("score_risk_from_triage")
        if blocked:
            return blocked

        try:
            port_result = _read_json(triage_dir() / "port_scan_result.json")
            dns_result = _read_json(triage_dir() / "dns_enum_result.json")
            banner_result = _read_json(triage_dir() / "banner_result.json")
        except FileNotFoundError as exc:
            return {"error": f"missing recon file: {exc.filename}"}

        profile = score_risk(port_result, dns_result, banner_result)
        save_risk_profile(profile, triage_dir() / "risk_profile.json")
        return profile

    def generate_markdown_report(self) -> dict:
        blocked = self._check_rate_limit("generate_markdown_report")
        if blocked:
            return blocked

        risk_path = triage_dir() / "risk_profile.json"
        report_path = results_dir() / "ket_qua.md"
        prompt_path = prompts_dir() / "report_prompt.md"

        if not risk_path.exists():
            return {"error": "risk_profile.json does not exist. Run score_risk_from_triage first."}

        report = generate_report(risk_path, report_path, prompt_path)
        return {
            "report_path": str(report_path),
            "preview": report[:800],
        }


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _compact_for_llm(result: Any) -> Any:
    """Keep tool messages small while full data remains saved in .pi/triage."""
    if not isinstance(result, dict):
        return result

    compact = dict(result)
    if "scanned_ports" in compact and len(compact["scanned_ports"]) > 40:
        compact["scanned_ports"] = compact["scanned_ports"][:40] + ["..."]
    if "attempted_ports" in compact and len(compact["attempted_ports"]) > 40:
        compact["attempted_ports"] = compact["attempted_ports"][:40] + ["..."]
    if "nearest_samples" in compact:
        compact["nearest_samples"] = compact["nearest_samples"][:3]
    return compact


def _assistant_message(message: Any) -> dict:
    """OpenAI requires the assistant tool_calls turn to be preserved in history."""
    return {
        "role": "assistant",
        "content": message.content,
        "tool_calls": [item.model_dump() for item in (message.tool_calls or [])],
    }


def _execute_tool_batch(tool_calls: list[Any], tool_map: dict[str, Callable[..., dict]]) -> list[dict]:
    """Execute one assistant batch of tool calls and return all tool messages.

    If the model requests three independent recon tools in one turn, this function
    runs them concurrently and appends every result before the next model call.
    """
    results: list[dict] = []

    def run_one(tool_call: Any) -> dict:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments or "{}")
        func = tool_map.get(name)
        if not func:
            payload = {"error": f"unknown tool: {name}"}
        else:
            try:
                payload = func(**args)
            except Exception as exc:  # Tools should not crash the agent loop.
                payload = {"error": str(exc)}

        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(_compact_for_llm(payload), ensure_ascii=False),
        }

    with ThreadPoolExecutor(max_workers=max(1, len(tool_calls))) as executor:
        futures = [executor.submit(run_one, item) for item in tool_calls]
        for future in as_completed(futures):
            results.append(future.result())

    return results


def run_agent(
    system_prompt: str,
    user_request: str,
    tools: list[dict[str, Any]],
    tool_map: dict[str, Callable[..., dict]],
    model: str,
    max_iterations: int = 8,
) -> dict:
    """Generic Week 5 agent loop: observe, think, act, repeat."""
    from openai import OpenAI

    base_url = os.getenv("OPENAI_BASE_URL", "").strip()
    client = OpenAI(base_url=base_url) if base_url else OpenAI()

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_request},
    ]

    for iteration in range(1, max_iterations + 1):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.0,
            max_tokens=900,
        )

        message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason
        messages.append(_assistant_message(message))

        if finish_reason == "tool_calls":
            tool_messages = _execute_tool_batch(message.tool_calls or [], tool_map)
            messages.extend(tool_messages)
            continue

        if finish_reason == "stop":
            return {
                "status": "completed",
                "iterations": iteration,
                "final_response": message.content,
                "messages_used": len(messages),
            }

        return {
            "status": "stopped",
            "reason": finish_reason,
            "iterations": iteration,
            "final_response": message.content,
        }

    return {
        "status": "max_iterations_reached",
        "iterations": max_iterations,
        "final_response": "Agent stopped before completion.",
    }


def run_topic02_agent(target: str, ports: list[int], authorized: bool, timeout: float, model: str) -> dict:
    """Build runtime and run the Topic 02 agent."""
    ensure_output_dirs()
    setup_logging(logs_dir() / "agent_run.log")
    load_env()

    runtime = ToolRuntime(authorized=authorized, default_ports=ports, timeout=timeout)
    tool_map = {
        "scan_ports": runtime.scan_ports,
        "enumerate_dns": runtime.enumerate_dns,
        "grab_banners": runtime.grab_banners,
        "score_risk_from_triage": runtime.score_risk_from_triage,
        "generate_markdown_report": runtime.generate_markdown_report,
    }

    port_text = ",".join(str(port) for port in ports)
    user_request = (
        f"Investigate target {target} for Topic 02. "
        f"Use this safe port list: {port_text}. "
        "Create the final Markdown report."
    )
    return run_agent(RECON_AGENT_SYSTEM, user_request, TOOLS, tool_map, model=model)


def main() -> None:
    parser = argparse.ArgumentParser(description="Agentic Topic 02 Recon + Risk Profiler")
    parser.add_argument("--target", default="localhost")
    parser.add_argument("--ports", default="")
    parser.add_argument("--authorized", action="store_true")
    parser.add_argument("--timeout", type=float, default=0.5)
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-4o"))
    args = parser.parse_args()

    load_env()
    target, url_ports = parse_target(args.target)
    ports = choose_ports(args.ports, url_ports, DEFAULT_PORTS)

    if not os.getenv("OPENAI_API_KEY"):
        print("[INFO] OPENAI_API_KEY is missing, so agentic mode cannot call the model.")
        print("       Run the offline pipeline instead:")
        print(f"       python .pi/tools/main_pipeline.py --target {target} --ports \"{','.join(map(str, ports))}\"")
        return

    try:
        result = run_topic02_agent(target, ports, args.authorized, args.timeout, args.model)
    except Exception as exc:
        print("[ERROR] Agentic OpenAI call failed.")
        print(f"        {exc}")
        print("\nUse the offline-stable pipeline for submission/demo:")
        print(f"python .pi/tools/main_pipeline.py --target {target} --ports \"{','.join(map(str, ports))}\"")
        return

    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("\nImportant outputs:")
    print(f"- risk_profile: {display_path(triage_dir() / 'risk_profile.json')}")
    print(f"- report: {display_path(results_dir() / 'ket_qua.md')}")
    print(f"- agent_log: {display_path(logs_dir() / 'agent_run.log')}")


if __name__ == "__main__":
    main()
