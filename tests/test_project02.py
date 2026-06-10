"""Small regression tests for Topic 02.

These tests are intentionally simple so they are easy to explain in an oral exam:
- parse target and ports correctly
- convert recon data into a risk profile
- keep the allowlist safety gate working
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = PROJECT_ROOT / ".pi" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from api_server import ScanRequest, create_scan, dashboard, health, latest_alerts, latest_risk  # noqa: E402
from common.tool_utils import (  # noqa: E402
    display_path,
    is_target_allowed,
    parse_ports,
    parse_target,
    resolve_target,
    validate_timeout,
)
from main_pipeline import run_pipeline  # noqa: E402
from monitoring.anomaly_detector import analyze_log_anomalies, extract_log_features  # noqa: E402
from monitoring.log_monitor import run_monitor_live, run_monitor_once  # noqa: E402
from monitoring.detectors import detect_threats, load_events  # noqa: E402
from recon.banner_grabber import grab_banners, identify_service, inspect_tls  # noqa: E402
from recon.dns_enum import enumerate_dns  # noqa: E402
from recon.port_scanner import scan_ports  # noqa: E402
from recon.udp_scanner import scan_udp_ports  # noqa: E402
from reporting.ai_reporter import generate_report  # noqa: E402
from reporting.report_templates import build_offline_report, load_prompt  # noqa: E402
from risk.risk_scorer import classify_target_exposure, score_risk, score_risk_from_files  # noqa: E402
from risk.evaluate_models import evaluate_models  # noqa: E402


class Project02Tests(unittest.TestCase):
    def test_parse_ports_supports_lists_and_ranges(self) -> None:
        self.assertEqual(parse_ports("80,443,8000"), [80, 443, 8000])
        self.assertEqual(parse_ports("3-1,2"), [1, 2, 3])

    def test_parse_target_extracts_host_and_url_port(self) -> None:
        target, ports = parse_target("http://localhost:8080/api")
        self.assertEqual(target, "localhost")
        self.assertEqual(ports, [8080])

    def test_invalid_ports_are_rejected(self) -> None:
        for invalid in ["0", "65536", "-1", "1-5000"]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                parse_ports(invalid)

    def test_invalid_target_port_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_target("localhost:99999")

    def test_common_validation_and_resolution_helpers(self) -> None:
        self.assertEqual(validate_timeout(0.5), 0.5)
        with self.assertRaises(ValueError):
            validate_timeout(0)
        self.assertIn("127.0.0.1", resolve_target("localhost"))
        self.assertTrue(str(display_path(PROJECT_ROOT / "README.md")).endswith("README.md"))

    def test_allowlist_blocks_unknown_without_authorization(self) -> None:
        self.assertTrue(is_target_allowed("localhost", authorized=False))
        self.assertFalse(is_target_allowed("example.invalid", authorized=False))
        self.assertTrue(is_target_allowed("example.invalid", authorized=True))

    def test_risk_profile_contains_required_sections(self) -> None:
        port_result = {"target": "localhost", "open_ports": [8000, 3306]}
        dns_result = {
            "target": "localhost",
            "message": "DNS enumeration skipped for localhost/IP target",
            "records": {},
        }
        banner_result = {
            "target": "localhost",
            "banners": {
                "8000": "HTTP/1.1 200 OK\r\nServer: SimpleHTTP/0.6 Python/3.12",
                "3306": "MySQL 8.0.36",
            },
        }

        profile = score_risk(port_result, dns_result, banner_result)

        self.assertEqual(profile["target"], "localhost")
        self.assertIn(profile["risk_level"], {"Low", "Medium", "High"})
        self.assertIn("ml_model", profile)
        self.assertEqual(profile["ml_model"]["name"], "SimpleIsolationForestRiskModel")
        self.assertIn("anomaly_score", profile["ml_model"])
        self.assertIn("calibrated_anomaly", profile["ml_model"])
        self.assertIn("mitre_mapping", profile)
        self.assertIn("recommendations", profile)
        self.assertTrue(profile["ml_model"]["risk_drivers"])
        self.assertIn("services", profile["recon_summary"])

    def test_agent_definitions_include_orchestration_and_safety(self) -> None:
        agents_dir = PROJECT_ROOT / ".pi" / "agents"
        expected_agents = {
            "orchestrator_agent.md",
            "permission_gate_agent.md",
            "port_scan_agent.md",
            "dns_enum_agent.md",
            "banner_grab_agent.md",
            "risk_score_agent.md",
            "report_agent.md",
            "log_monitor_agent.md",
            "threat_detection_agent.md",
            "alert_agent.md",
        }

        existing_agents = {path.name for path in agents_dir.glob("*.md")}
        self.assertTrue(expected_agents.issubset(existing_agents))

    def test_monitoring_detects_sample_threat_categories(self) -> None:
        sample_log = PROJECT_ROOT / ".pi" / "data" / "sample_security_events.log"
        events = load_events(sample_log)
        summary = detect_threats(events)
        categories = {alert["category"] for alert in summary["alerts"]}

        self.assertGreaterEqual(summary["alert_count"], 4)
        self.assertIn("malware_indicator", categories)
        self.assertIn("brute_force", categories)
        self.assertIn("exploit_attempt", categories)
        self.assertIn("traffic_anomaly", categories)

    def test_monitoring_detects_public_loghub_openssh_brute_force(self) -> None:
        public_log = PROJECT_ROOT / ".pi" / "data" / "loghub_openssh_2k.log"
        events = load_events(public_log)
        summary = detect_threats(events)
        categories = {alert["category"] for alert in summary["alerts"]}

        self.assertEqual(len(events), 2000)
        self.assertIn("brute_force", categories)
        self.assertGreaterEqual(summary["alert_count"], 1)

    def test_loghub_2k_is_used_to_train_ml_anomaly_model(self) -> None:
        public_log = PROJECT_ROOT / ".pi" / "data" / "loghub_openssh_2k.log"
        events = load_events(public_log)
        vectors, feature_maps = extract_log_features(events)
        analysis = analyze_log_anomalies(events, contamination=0.03, top_limit=10)

        self.assertEqual(len(vectors), 2000)
        self.assertEqual(len(feature_maps), 2000)
        self.assertEqual(analysis["status"], "completed")
        self.assertEqual(analysis["trained_on_event_count"], 2000)
        self.assertGreater(analysis["anomaly_count"], 0)
        self.assertTrue(analysis["top_anomalies"])
        self.assertTrue(
            any(
                "break-in attempt" in item["message"].lower()
                for item in analysis["top_anomalies"]
            )
        )

    def test_monitoring_summary_includes_ml_anomaly_analysis(self) -> None:
        public_log = PROJECT_ROOT / ".pi" / "data" / "loghub_apache_2k.log"
        summary = detect_threats(load_events(public_log))
        categories = {alert["category"] for alert in summary["alerts"]}

        self.assertEqual(summary["ml_anomaly_analysis"]["trained_on_event_count"], 2000)
        self.assertGreater(summary["ml_anomaly_analysis"]["anomaly_count"], 0)
        self.assertIn("ml_log_anomaly", categories)
        self.assertGreater(summary["monitoring_risk_profile"]["ml_anomaly_points"], 0)
        self.assertIn(summary["monitoring_risk_profile"]["risk_level"], {"Low", "Medium", "High"})

    def test_missing_monitor_log_fails_clearly(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_events(PROJECT_ROOT / ".pi" / "data" / "missing.log")

    def test_monitor_deduplicates_notifications(self) -> None:
        sample_log = PROJECT_ROOT / ".pi" / "data" / "sample_security_events.log"
        with tempfile.TemporaryDirectory() as output_dir:
            seen: set[str] = set()
            first = run_monitor_once(sample_log, output_dir, seen)
            second = run_monitor_once(sample_log, output_dir, seen)
            self.assertGreater(first["dispatch"]["notification_alert_count"], 0)
            self.assertEqual(second["dispatch"]["notification_alert_count"], 0)

    def test_offline_pipeline_runs_end_to_end(self) -> None:
        result = run_pipeline("localhost", [9], False, 0.05, offline=True)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["offline_report"])
        self.assertIn("recon", result["stage_durations"])

    def test_udp_scanner_rejects_invalid_port(self) -> None:
        with self.assertRaises(ValueError):
            scan_udp_ports("localhost", [0], 0.05)

    def test_local_recon_tools_return_structured_results(self) -> None:
        port_result = scan_ports("localhost", [9], 0.05)
        banner_result = grab_banners("localhost", [9], 0.05)
        dns_result = enumerate_dns("localhost")
        udp_result = scan_udp_ports("localhost", [53], 0.05)

        self.assertEqual(port_result["target"], "localhost")
        self.assertEqual(banner_result["services"]["9"], "unknown")
        self.assertTrue(dns_result["skipped"])
        self.assertIn(udp_result["results"]["53"], {"responsive", "closed", "open_or_filtered", "unreachable"})
        self.assertEqual(identify_service(22, "SSH-2.0-OpenSSH_9.0"), "ssh")
        self.assertEqual(inspect_tls("localhost", 9, 0.05), {})

    def test_api_health_dashboard_and_safe_scan(self) -> None:
        self.assertEqual(health()["status"], "ok")
        self.assertIn("Run safe scan", dashboard())
        result = create_scan(ScanRequest(target="localhost", ports="9", timeout=0.05))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(latest_risk()["target"], "localhost")
        self.assertIn("alert_count", latest_alerts())
        with self.assertRaises(HTTPException):
            create_scan(ScanRequest(target="example.invalid", ports="9", timeout=0.05))

    def test_model_evaluation_reports_quality_metrics(self) -> None:
        evaluation = evaluate_models()
        self.assertEqual(evaluation["sample_count"], 12)
        for model in ["isolation_forest", "random_forest"]:
            self.assertIn("precision", evaluation[model])
            self.assertIn("recall", evaluation[model])
            self.assertIn("false_positive_rate", evaluation[model])

    def test_live_monitor_and_offline_report_helpers(self) -> None:
        sample_log = PROJECT_ROOT / ".pi" / "data" / "sample_security_events.log"
        with tempfile.TemporaryDirectory() as output_dir:
            result = run_monitor_live(sample_log, output_dir, duration=0, poll_interval=0.2)
            self.assertEqual(result["mode"], "live")
            self.assertGreater(result["notification_alert_count_total"], 0)

            profile = score_risk(
                {"target": "localhost", "open_ports": [8000]},
                {"target": "localhost", "message": "skipped", "records": {}},
                {"target": "localhost", "banners": {"8000": "No banner"}},
            )
            risk_path = Path(output_dir) / "risk.json"
            report_path = Path(output_dir) / "report.md"
            risk_path.write_text(__import__("json").dumps(profile), encoding="utf-8")
            report = generate_report(risk_path, report_path, offline=True)
            self.assertIn("Offline fallback used: Offline mode requested", report)
            self.assertEqual(load_prompt(Path(output_dir) / "missing.md"), load_prompt())
            self.assertIn("Risk Level", build_offline_report(profile))

    def test_file_risk_scoring_and_target_exposure(self) -> None:
        self.assertEqual(classify_target_exposure("localhost"), "local")
        self.assertEqual(classify_target_exposure("10.0.0.1"), "private")
        self.assertEqual(classify_target_exposure("example.com"), "public")
        with tempfile.TemporaryDirectory() as output_dir:
            base = Path(output_dir)
            payloads = [
                {"target": "localhost", "open_ports": []},
                {"target": "localhost", "message": "skipped", "records": {}},
                {"target": "localhost", "banners": {}},
            ]
            paths = [base / f"{index}.json" for index in range(3)]
            for path, payload in zip(paths, payloads):
                path.write_text(__import__("json").dumps(payload), encoding="utf-8")
            output = base / "risk.json"
            profile = score_risk_from_files(*paths, output)
            self.assertTrue(output.exists())
            self.assertEqual(profile["target_exposure"], "local")


if __name__ == "__main__":
    unittest.main()
