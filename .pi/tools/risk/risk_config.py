"""Constants used by the risk scoring stage."""

SERVICE_NAMES = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    139: "NetBIOS",
    143: "IMAP",
    443: "HTTPS",
    445: "SMB",
    3000: "HTTP-dev",
    3306: "MySQL",
    5432: "PostgreSQL",
    6379: "Redis",
    8000: "HTTP-dev",
    8080: "HTTP-alt",
}

HTTP_PORTS = {80, 443, 3000, 8000, 8080}
SENSITIVE_PORTS = {21, 22, 23, 445, 3306, 5432, 6379}
HIGH_RISK_PORTS = {23, 445, 6379}
DATABASE_CACHE_PORTS = {3306, 5432, 6379}

FEATURE_NAMES = [
    "open_port_count",
    "sensitive_port_count",
    "high_risk_port_count",
    "database_cache_port_count",
    "http_port_count",
    "version_banner_count",
    "dns_record_count",
]

BANNER_VERSION_PATTERNS = [
    r"Server:\s*.+\d+\.\d+",
    r"OpenSSH[_/ -]?\d+\.\d+",
    r"Apache[/ -]?\d+\.\d+",
    r"nginx[/ -]?\d+\.\d+",
    r"MySQL[/ -]?\d+\.\d+",
    r"PostgreSQL[/ -]?\d+\.\d+",
    r"Redis[/ -]?\d+\.\d+",
    r"vsftpd[/ -]?\d+\.\d+",
    r"Demo.*\d+\.\d+",
]
