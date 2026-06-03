"""STAGE 2A - Feature Extraction for ML Risk Model.

Input: ket qua recon gom open ports, DNS records, banners.
Output: feature_map de dua vao KNN model.
"""

import re

from risk.risk_config import (
    BANNER_VERSION_PATTERNS,
    DATABASE_CACHE_PORTS,
    HIGH_RISK_PORTS,
    HTTP_PORTS,
    SENSITIVE_PORTS,
)


def banner_has_version(banner: str) -> bool:
    """True neu banner co dau hieu lo phien ban dich vu."""
    if not banner or banner == "No banner":
        return False

    return any(re.search(pattern, banner, re.IGNORECASE) for pattern in BANNER_VERSION_PATTERNS)


def count_dns_records(dns_result: dict) -> int:
    """Dem tong so DNS record thu duoc."""
    records = dns_result.get("records", {})
    return sum(len(values) for values in records.values() if isinstance(values, list))


def extract_features(open_ports: list[int], banners: dict, dns_result: dict) -> tuple[dict, list[int]]:
    """Bien recon result thanh feature vector de giai thich khi thuyet trinh."""
    # MARK: Version leak feature - banner co version thuong lam tang rui ro.
    version_leaks = [
        int(port)
        for port, banner in banners.items()
        if banner_has_version(str(banner))
    ]

    # MARK: ML features - cac dac trung don gian, de nho, de giai thich.
    feature_map = {
        "open_port_count": len(open_ports),
        "sensitive_port_count": len([port for port in open_ports if port in SENSITIVE_PORTS]),
        "high_risk_port_count": len([port for port in open_ports if port in HIGH_RISK_PORTS]),
        "database_cache_port_count": len([port for port in open_ports if port in DATABASE_CACHE_PORTS]),
        "http_port_count": len([port for port in open_ports if port in HTTP_PORTS]),
        "version_banner_count": len(version_leaks),
        "dns_record_count": count_dns_records(dns_result),
    }

    return feature_map, version_leaks
