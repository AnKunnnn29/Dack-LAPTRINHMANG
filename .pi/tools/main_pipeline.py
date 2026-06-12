"""Main runner for Topic 02 - Network Recon + Risk Profiler.

File nay la entrypoint de thuyet trinh:
1. Stage 1: chay 3 recon tool song song.
2. Stage 2: gom ket qua va cham diem rui ro bang ML.
3. Stage 3: sinh bao cao Markdown co MITRE ATT&CK mapping.
"""

import argparse
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from common.tool_utils import (
    choose_ports,
    display_path,
    ensure_output_dirs,
    is_target_allowed,
    load_env,
    logs_dir,
    parse_target,
    prompts_dir,
    results_dir,
    setup_logging,
    triage_dir,
    write_json,
    resolve_target,
    validate_timeout,
)
from recon.banner_grabber import grab_banners
from recon.dns_enum import enumerate_dns
from recon.port_scanner import DEFAULT_PORTS, scan_ports
from reporting.ai_reporter import generate_report
from risk.risk_scorer import save_risk_profile, score_risk


def run_recon_stage(target: str, ports: list[int], timeout: float) -> tuple[dict, dict, dict]:
    """STAGE 1 - Parallel Recon.

    Ba tac vu ben duoi khong phu thuoc nhau, nen chay dong thoi de giam
    wall-clock time:
    - port scan: kiem tra cong TCP dang mo.
    - DNS enum: lay A/MX/NS/TXT record.
    - banner grab: thu doc banner dich vu.
    """
    port_path = triage_dir() / "port_scan_result.json"
    dns_path = triage_dir() / "dns_enum_result.json"
    banner_path = triage_dir() / "banner_result.json"

    # MARK: Stage 1 parallelism - 3 workers cho 3 recon agents.
    with ThreadPoolExecutor(max_workers=3) as executor:
        logging.info("Stage 1 started: port scan, DNS enum, and banner grab in parallel")
        futures = {
            executor.submit(scan_ports, target, ports, timeout): "port",
            executor.submit(enumerate_dns, target, timeout): "dns",
            executor.submit(grab_banners, target, ports, timeout): "banner",
        }

        port_result = {}
        dns_result = {}
        banner_result = {}

        # as_completed giup task nao xong truoc thi ghi output truoc.
        for future in as_completed(futures):
            task_name = futures[future]
            if task_name == "port":
                port_result = future.result()
                write_json(port_path, port_result)
                logging.info("Port scan completed: %s", port_result.get("open_ports", []))
            elif task_name == "dns":
                dns_result = future.result()
                write_json(dns_path, dns_result)
                logging.info("DNS enumeration completed")
            else:
                banner_result = future.result()
                write_json(banner_path, banner_result)
                logging.info("Banner grabbing completed")

    return port_result, dns_result, banner_result


def run_risk_stage(port_result: dict, dns_result: dict, banner_result: dict) -> dict:
    """STAGE 2 - ML Risk Scoring."""
    risk_path = triage_dir() / "risk_profile.json"

    logging.info("Stage 2 started: risk scoring")
    risk_profile = score_risk(port_result, dns_result, banner_result)
    save_risk_profile(risk_profile, risk_path)
    logging.info(
        "Risk scoring completed: score=%s level=%s",
        risk_profile["score"],
        risk_profile["risk_level"],
    )
    return risk_profile


def run_report_stage(offline: bool = False) -> None:
    """STAGE 3 - AI/Offline Report Generation."""
    risk_path = triage_dir() / "risk_profile.json"
    report_path = results_dir() / "ket_qua.md"
    prompt_path = prompts_dir() / "report_prompt.md"

    logging.info("Stage 3 started: report generation")
    generate_report(risk_path, report_path, prompt_path, offline=offline)
    logging.info("Report generated: %s", report_path)


def run_pipeline(
    target: str,
    ports: list[int],
    authorized: bool,
    timeout: float,
    offline: bool = False,
) -> dict:
    """Chay tron ven pipeline va tra ve duong dan cac file output."""
    ensure_output_dirs()
    setup_logging(logs_dir() / "pipeline_run.log")
    load_env()

    started = time.perf_counter()
    timeout = validate_timeout(timeout)
    logging.info("Pipeline started for target=%s", target)

    # MARK: Safety gate - chi scan target demo hoac target da xac nhan co quyen.
    if not is_target_allowed(target, authorized):
        message = (
            "Permission gate blocked this target. Use localhost, 127.0.0.1, "
            "scanme.nmap.org, or add --authorized only when you have permission."
        )
        logging.warning(message)
        raise PermissionError(message)

    resolved_addresses = resolve_target(target)
    stage_started = time.perf_counter()
    port_result, dns_result, banner_result = run_recon_stage(target, ports, timeout)
    recon_seconds = round(time.perf_counter() - stage_started, 4)
    stage_started = time.perf_counter()
    run_risk_stage(port_result, dns_result, banner_result)
    risk_seconds = round(time.perf_counter() - stage_started, 4)
    stage_started = time.perf_counter()
    run_report_stage(offline=offline)
    report_seconds = round(time.perf_counter() - stage_started, 4)

    return {
        "status": "completed",
        "target": target,
        "resolved_addresses": resolved_addresses,
        "offline_report": offline,
        "duration_seconds": round(time.perf_counter() - started, 4),
        "stage_durations": {
            "recon": recon_seconds,
            "risk": risk_seconds,
            "report": report_seconds,
        },
        "port_scan_result": str(triage_dir() / "port_scan_result.json"),
        "dns_enum_result": str(triage_dir() / "dns_enum_result.json"),
        "banner_result": str(triage_dir() / "banner_result.json"),
        "risk_profile": str(triage_dir() / "risk_profile.json"),
        "report": str(results_dir() / "ket_qua.md"),
        "log": str(logs_dir() / "pipeline_run.log"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Network Recon + Risk Profiler")
    parser.add_argument("--target", default="localhost", help="Target hostname, IP, or URL")
    parser.add_argument("--ports", default="", help="Ports, e.g. 80,443,3000 or 1-1000")
    parser.add_argument("--authorized", action="store_true", help="Confirm permission to scan target")
    parser.add_argument("--timeout", type=float, default=0.5, help="Socket timeout in seconds")
    parser.add_argument("--offline", action="store_true", help="Never call an AI report API")
    args = parser.parse_args()

    target, url_ports = parse_target(args.target)
    ports = choose_ports(args.ports, url_ports, DEFAULT_PORTS)

    try:
        outputs = run_pipeline(target, ports, args.authorized, args.timeout, offline=args.offline)
    except (PermissionError, ValueError) as exc:
        print(f"[BLOCKED] {exc}")
        return

    print("Pipeline completed.")
    path_keys = {
        "port_scan_result",
        "dns_enum_result",
        "banner_result",
        "risk_profile",
        "report",
        "log",
    }
    for name, value in outputs.items():
        rendered = display_path(value) if name in path_keys else json.dumps(value, ensure_ascii=False)
        print(f"- {name}: {rendered}")


if __name__ == "__main__":
    main()
