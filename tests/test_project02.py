"""Small regression tests for Topic 02.

These tests focus on the scoped final project:
- parse target and ports correctly
- keep the allowlist safety gate working
- run the offline recon -> risk -> report pipeline
- keep the Week 5 agentic extension wired to the same core tools
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = PROJECT_ROOT / ".pi" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import pi_recon_agent  # noqa: E402
from common.tool_utils import (  # noqa: E402
    display_path,
    is_target_allowed,
    parse_ports,
    parse_target,
    resolve_target,
    validate_timeout,
)
from main_pipeline import run_pipeline  # noqa: E402
from recon.banner_grabber import grab_banners, identify_service, inspect_tls  # noqa: E402
from recon.dns_enum import enumerate_dns  # noqa: E402
from recon.port_scanner import scan_ports  # noqa: E402
from recon.udp_scanner import scan_udp_ports  # noqa: E402
from reporting.ai_reporter import generate_report  # noqa: E402
from reporting.report_templates import build_offline_report, load_prompt  # noqa: E402
from risk.risk_model import predict_with_isolation_forest  # noqa: E402
from risk.risk_scorer import classify_target_exposure, score_risk, score_risk_from_files  # noqa: E402


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
            "services": {"8000": "http", "3306": "mysql"},
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

    def test_isolation_forest_prediction_is_explainable(self) -> None:
        prediction = predict_with_isolation_forest(
            {
                "open_port_count": 3,
                "sensitive_port_count": 1,
                "high_risk_port_count": 1,
                "database_cache_port_count": 1,
                "http_port_count": 1,
                "version_banner_count": 1,
                "dns_record_count": 2,
            }
        )

        self.assertEqual(prediction["model_name"], "SimpleIsolationForestRiskModel")
        self.assertEqual(prediction["model_type"], "unsupervised Isolation Forest anomaly detection")
        self.assertEqual(prediction["n_trees"], 64)
        self.assertIn(prediction["predicted_label"], {"Low", "Medium", "High"})
        self.assertTrue(prediction["risk_drivers"])

    def test_agent_definitions_match_scoped_topic02_pipeline(self) -> None:
        agents_dir = PROJECT_ROOT / ".pi" / "agents"
        expected_agents = {
            "orchestrator_agent.md",
            "permission_gate_agent.md",
            "port_scan_agent.md",
            "dns_enum_agent.md",
            "banner_grab_agent.md",
            "risk_score_agent.md",
            "report_agent.md",
        }
        removed_optional_agents = {
            "log_monitor_agent.md",
            "threat_detection_agent.md",
            "alert_agent.md",
        }

        existing_agents = {path.name for path in agents_dir.glob("*.md")}
        self.assertTrue(expected_agents.issubset(existing_agents))
        self.assertTrue(removed_optional_agents.isdisjoint(existing_agents))

    def test_offline_pipeline_runs_end_to_end(self) -> None:
        result = run_pipeline("localhost", [9], False, 0.05, offline=True)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["offline_report"])
        self.assertIn("recon", result["stage_durations"])
        self.assertTrue(Path(result["risk_profile"]).exists())
        self.assertTrue(Path(result["report"]).exists())

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

    def test_offline_report_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as output_dir:
            profile = score_risk(
                {"target": "localhost", "open_ports": [8000]},
                {"target": "localhost", "message": "skipped", "records": {}},
                {"target": "localhost", "banners": {"8000": "No banner"}},
            )
            risk_path = Path(output_dir) / "risk.json"
            report_path = Path(output_dir) / "report.md"
            risk_path.write_text(json.dumps(profile), encoding="utf-8")
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
                path.write_text(json.dumps(payload), encoding="utf-8")
            output = base / "risk.json"
            profile = score_risk_from_files(*paths, output)
            self.assertTrue(output.exists())
            self.assertEqual(profile["target_exposure"], "local")

    def test_week5_agentic_extension_exposes_core_topic02_tools(self) -> None:
        tool_names = {tool["function"]["name"] for tool in pi_recon_agent.TOOLS}
        self.assertEqual(
            tool_names,
            {
                "scan_ports",
                "enumerate_dns",
                "grab_banners",
                "score_risk_from_triage",
                "generate_markdown_report",
            },
        )
        self.assertIn("Observe-Think-Act", pi_recon_agent.__doc__ or "")


if __name__ == "__main__":
    unittest.main()
