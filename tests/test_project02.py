"""Small regression tests for Topic 02.

These tests are intentionally simple so they are easy to explain in an oral exam:
- parse target and ports correctly
- convert recon data into a risk profile
- keep the allowlist safety gate working
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = PROJECT_ROOT / ".pi" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from common.tool_utils import is_target_allowed, parse_ports, parse_target  # noqa: E402
from risk.risk_scorer import score_risk  # noqa: E402


class Project02Tests(unittest.TestCase):
    def test_parse_ports_supports_lists_and_ranges(self) -> None:
        self.assertEqual(parse_ports("80,443,8000"), [80, 443, 8000])
        self.assertEqual(parse_ports("3-1,2"), [1, 2, 3])

    def test_parse_target_extracts_host_and_url_port(self) -> None:
        target, ports = parse_target("http://localhost:8080/api")
        self.assertEqual(target, "localhost")
        self.assertEqual(ports, [8080])

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
        self.assertIn("mitre_mapping", profile)
        self.assertIn("recommendations", profile)


if __name__ == "__main__":
    unittest.main()
