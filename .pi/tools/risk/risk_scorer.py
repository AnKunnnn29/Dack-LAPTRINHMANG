"""STAGE 2 - Risk Scorer Coordinator.

File nay noi 3 phan:
1. Lay feature tu recon output.
2. Goi KNN model de cham diem.
3. Tao findings, MITRE mapping va recommendations.
"""

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from risk.risk_features import extract_features
from risk.risk_findings import build_findings, build_mitre_mapping, build_recommendations
from risk.risk_model import predict_with_knn


def score_risk(port_result: dict, dns_result: dict, banner_result: dict) -> dict:
    """Gom ket qua recon va tra ve risk_profile.json."""
    target = port_result.get("target") or dns_result.get("target") or banner_result.get("target")
    open_ports = [int(port) for port in port_result.get("open_ports", [])]
    banners = banner_result.get("banners", {})

    # MARK: ML input/output - feature_map vao model, prediction ra score/label.
    feature_map, version_leaks = extract_features(open_ports, banners, dns_result)
    prediction = predict_with_knn(feature_map)

    # MARK: Final risk profile - day la file trung tam cho bao cao.
    return {
        "target": target,
        "score": prediction["predicted_score"],
        "risk_level": prediction["predicted_label"],
        "ml_model": {
            "name": prediction["model_name"],
            "type": prediction["model_type"],
            "k": prediction["k"],
            "features": feature_map,
            "feature_names": prediction["feature_names"],
            "feature_vector": prediction["feature_vector"],
            "nearest_samples": prediction["nearest_samples"],
        },
        "mitre_mapping": build_mitre_mapping(open_ports, version_leaks, dns_result),
        "findings": build_findings(open_ports, version_leaks, dns_result),
        "recommendations": build_recommendations(open_ports, version_leaks),
        "recon_summary": {
            "open_ports": open_ports,
            "dns_records": dns_result.get("records", {}),
            "dns_message": dns_result.get("message", ""),
            "banners": banners,
        },
        "notes": [
            "Risk is predicted by a small supervised KNN model for classroom demonstration.",
            "MITRE mapping is defensive context, not exploitation guidance.",
            "No exploit, brute force, bypass, or real attack step is performed.",
        ],
    }


def save_risk_profile(profile: dict, output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")


def score_risk_from_files(
    port_file: str | Path,
    dns_file: str | Path,
    banner_file: str | Path,
    output_file: str | Path,
) -> dict:
    port_result = json.loads(Path(port_file).read_text(encoding="utf-8"))
    dns_result = json.loads(Path(dns_file).read_text(encoding="utf-8"))
    banner_result = json.loads(Path(banner_file).read_text(encoding="utf-8"))

    profile = score_risk(port_result, dns_result, banner_result)
    save_risk_profile(profile, output_file)
    return profile


def main() -> None:
    parser = argparse.ArgumentParser(description="ML-based recon risk scorer")
    parser.add_argument("--port-file", required=True)
    parser.add_argument("--dns-file", required=True)
    parser.add_argument("--banner-file", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = score_risk_from_files(args.port_file, args.dns_file, args.banner_file, args.output)
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
