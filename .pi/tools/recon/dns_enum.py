"""STAGE 1B - DNS Enumeration.

Muc dich:
- Lay cac DNS record co ban: A, MX, NS, TXT.
- Bo qua IP/localhost vi chung khong can DNS lookup trong demo local.
"""

import ipaddress


DNS_RECORD_TYPES = ["A", "CNAME", "MX", "NS", "SOA", "TXT"]


def is_ip_or_localhost(target: str) -> bool:
    """True neu target khong phu hop de query DNS record."""
    if target.lower() in {"localhost", "127.0.0.1", "::1"}:
        return True

    try:
        ipaddress.ip_address(target)
        return True
    except ValueError:
        return False


def _format_answer(record_type: str, answer) -> str:
    if record_type == "MX":
        return f"{answer.preference} {answer.exchange}".rstrip(".")
    if record_type == "TXT":
        return " ".join(part.decode("utf-8", errors="replace") for part in answer.strings)
    return str(answer).rstrip(".")


def enumerate_dns(domain: str, timeout: float = 2.0) -> dict:
    """Query DNS record va tra ve JSON-friendly dict."""
    if domain.lower() in {"localhost", "127.0.0.1", "::1"}:
        return {
            "target": domain,
            "skipped": True,
            "message": "DNS enumeration skipped for localhost/IP target",
            "records": {},
        }

    try:
        import dns.resolver
    except ImportError:
        return {
            "target": domain,
            "skipped": True,
            "message": "dnspython is not installed",
            "records": {},
        }

    resolver = dns.resolver.Resolver()
    resolver.lifetime = timeout
    resolver.timeout = timeout

    records = {}
    errors = {}

    try:
        ipaddress.ip_address(domain)
        try:
            records["PTR"] = [str(item).rstrip(".") for item in resolver.resolve_address(domain)]
            message = "Reverse DNS enumeration completed"
        except Exception as exc:
            records["PTR"] = []
            errors["PTR"] = str(exc)
            message = "Reverse DNS enumeration completed with no PTR result"
        return {
            "target": domain,
            "skipped": False,
            "message": message,
            "records": records,
            "errors": errors,
        }
    except ValueError:
        pass

    # MARK: DNS record loop - moi loai record duoc thu rieng de khong lam fail ca tool.
    for record_type in DNS_RECORD_TYPES:
        try:
            answers = resolver.resolve(domain, record_type)
            records[record_type] = [_format_answer(record_type, answer) for answer in answers]
        except Exception as exc:
            records[record_type] = []
            errors[record_type] = str(exc)

    return {
        "target": domain,
        "skipped": False,
        "message": "DNS enumeration completed",
        "records": records,
        "errors": errors,
    }


def main() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Simple DNS enumeration")
    parser.add_argument("--target", default="localhost")
    args = parser.parse_args()

    result = enumerate_dns(args.target)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
