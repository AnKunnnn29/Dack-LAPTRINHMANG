"""STAGE 2C - Findings, MITRE Mapping, Recommendations."""

from risk.risk_config import DATABASE_CACHE_PORTS, HTTP_PORTS, SERVICE_NAMES
from risk.risk_features import count_dns_records


def build_findings(open_ports: list[int], version_leaks: list[int], dns_result: dict) -> list[dict]:
    """Tao danh sach finding ngan gon tu ket qua recon."""
    findings = []

    # MARK: Open port findings
    for port in open_ports:
        service = SERVICE_NAMES.get(port, "Unknown")
        findings.append(
            {
                "type": "open_port",
                "port": port,
                "service": service,
                "description": f"Port {port}/{service} is open.",
                "mitre_technique_ids": ["T1046", "T1595"],
            }
        )

    # MARK: Banner version findings
    for port in version_leaks:
        findings.append(
            {
                "type": "banner_version",
                "port": port,
                "description": "Banner appears to reveal service version information.",
                "mitre_technique_ids": ["T1592.002"],
            }
        )

    # MARK: DNS findings
    if count_dns_records(dns_result) > 0:
        findings.append(
            {
                "type": "dns_records",
                "description": "DNS records were collected for the target domain.",
                "mitre_technique_ids": ["T1590"],
            }
        )

    return findings


def build_mitre_mapping(open_ports: list[int], version_leaks: list[int], dns_result: dict) -> list[dict]:
    """Map findings sang MITRE ATT&CK de bao cao co ngu canh phong thu."""
    mappings = []

    if open_ports:
        mappings.append(
            {
                "technique_id": "T1046",
                "technique": "Network Service Discovery",
                "tactic": "Discovery",
                "evidence": f"Open ports discovered: {open_ports}",
                "defensive_note": "Monitor unusual internal scanning and restrict unnecessary exposed services.",
            }
        )
        mappings.append(
            {
                "technique_id": "T1595",
                "technique": "Active Scanning",
                "tactic": "Reconnaissance",
                "evidence": "Pipeline performed authorized active checks against the target.",
                "defensive_note": "Keep scanning limited to authorized ranges and log scan activity.",
            }
        )

    if count_dns_records(dns_result) > 0:
        mappings.append(
            {
                "technique_id": "T1590",
                "technique": "Gather Victim Network Information",
                "tactic": "Reconnaissance",
                "evidence": "DNS A/MX/NS/TXT records were collected.",
                "defensive_note": "Review public DNS exposure and remove unnecessary TXT details.",
            }
        )

    if version_leaks:
        mappings.append(
            {
                "technique_id": "T1592.002",
                "technique": "Gather Victim Host Information: Software",
                "tactic": "Reconnaissance",
                "evidence": f"Version-like banners found on ports: {version_leaks}",
                "defensive_note": "Reduce version disclosure in banners and server headers where practical.",
            }
        )

    return mappings


def build_recommendations(open_ports: list[int], version_leaks: list[int]) -> list[str]:
    """Tao khuyen nghi phong thu theo cac rui ro tim thay."""
    recommendations = [
        "Chi quet va danh gia tren target duoc uy quyen.",
        "Dong cac port khong can thiet bang firewall hoac security group.",
        "Cap nhat he dieu hanh va dich vu mang len phien ban on dinh moi.",
        "Theo doi log de phat hien hoat dong network discovery bat thuong.",
    ]

    if 21 in open_ports:
        recommendations.append("Han che FTP; uu tien SFTP/SSH hoac FTPS neu bat buoc can truyen file.")
    if 22 in open_ports:
        recommendations.append("Bao ve SSH bang key-based auth, allowlist IP va tat dang nhap root.")
    if 23 in open_ports:
        recommendations.append("Tat Telnet vi giao thuc nay khong ma hoa du lieu.")
    if any(port in open_ports for port in DATABASE_CACHE_PORTS):
        recommendations.append("Khong public database/cache ra Internet; chi bind noi bo hoac qua VPN.")
    if any(port in open_ports for port in HTTP_PORTS):
        recommendations.append("Kiem tra cau hinh web server, TLS, security headers va trang mac dinh.")
    if version_leaks:
        recommendations.append("An hoac giam thong tin version trong banner/server header neu khong can thiet.")

    return recommendations
