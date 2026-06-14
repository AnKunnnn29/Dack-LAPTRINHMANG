# Vũ Văn Thông — Giải thích code chi tiết từng dòng

> MSSV: 23162098  
> Phạm vi: Pipeline chính, Safety Gate, Port Scanner, DNS Enum, Banner Grabber

---

# 📌 PHẦN 1 — PIPELINE CHÍNH (`main_pipeline.py`)

**File:** `.pi/tools/main_pipeline.py`

## 1.1. Hàm `main()` — Entrypoint

```python
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
        "port_scan_result", "dns_enum_result", "banner_result",
        "risk_profile", "report", "log",
    }
    for name, value in outputs.items():
        rendered = display_path(value) if name in path_keys else json.dumps(value, ensure_ascii=False)
        print(f"- {name}: {rendered}")
```

### Giải thích từng dòng:

| Dòng code | Giải thích |
|---|---|
| `argparse` | Parse CLI arguments. `--target` mặc định là `localhost`, `--timeout` mặc định 0.5s |
| `parse_target(args.target)` | Xử lý target: nếu là URL (có `://`) thì extract host+port; nếu là `host:port` thì tách ra; nếu là hostname/IP thường thì dùng luôn |
| `choose_ports(args.ports, url_ports, DEFAULT_PORTS)` | Ưu tiên: `--ports` > port trong URL > `DEFAULT_PORTS` |
| `run_pipeline(...)` | Gọi pipeline chính. Bắt `PermissionError` (Safety Gate block) và `ValueError` (input sai) |
| `display_path(value)` | In đường dẫn tương đối cho các file output |

---

## 1.2. Hàm `run_pipeline()` — Trái tim của project

```python
def run_pipeline(
    target: str,
    ports: list[int],
    authorized: bool,
    timeout: float,
    offline: bool = False,
) -> dict:
```

### Luồng chạy đầy đủ:

```
run_pipeline()
  │
  ├── 1. ensure_output_dirs()           → Tạo .pi/triage/, .pi/logs/, .pi/results/
  ├── 2. setup_logging()                → Ghi log vào .pi/logs/pipeline_run.log
  ├── 3. load_env()                     → Load OPENAI_API_KEY từ .env (nếu có)
  ├── 4. timeout = validate_timeout()   → Kiểm tra timeout (0.01 - 30s)
  │
  ├── [STAGE 0] Safety Gate
  │     └── is_target_allowed(target, authorized)
  │           ├── authorized=True? → OK
  │           ├── target in allowlist? → OK
  │           └── Cả hai đều False → raise PermissionError → DỪNG NGAY
  │
  ├── resolve_target(target)            → DNS lookup, kiểm tra hostname
  │
  ├── [STAGE 1] run_recon_stage()
  │     ├── scan_ports(target, ports, timeout)     → port_scan_result.json
  │     ├── enumerate_dns(target, timeout)          → dns_enum_result.json
  │     └── grab_banners(target, ports, timeout)     → banner_result.json
  │     ← 3 task này chạy SONG SONG
  │
  ├── [STAGE 2] run_risk_stage()         → risk_profile.json  (bạn An)
  │
  ├── [STAGE 3] run_report_stage()       → ket_qua.md         (bạn An)
  │
  └── Return dict kết quả
```

### Chi tiết code:

```python
def run_pipeline(target, ports, authorized, timeout, offline=False):
    # ─── Khởi tạo ───
    ensure_output_dirs()
    setup_logging(logs_dir() / "pipeline_run.log")
    load_env()
    started = time.perf_counter()
    timeout = validate_timeout(timeout)
    logging.info("Pipeline started for target=%s", target)

    # ─── STAGE 0: Safety Gate ───
    if not is_target_allowed(target, authorized):
        message = (
            "Permission gate blocked this target. Use a local/classroom-lab "
            "allowlisted target, or add --authorized only when you have permission."
        )
        logging.warning(message)
        raise PermissionError(message)

    # Resolve target (chỉ chạy sau khi Safety Gate pass)
    resolved_addresses = resolve_target(target)

    # ─── STAGE 1: Parallel Recon ───
    stage_started = time.perf_counter()
    port_result, dns_result, banner_result = run_recon_stage(target, ports, timeout)
    recon_seconds = round(time.perf_counter() - stage_started, 4)

    # ─── STAGE 2: ML Risk Scoring ───
    stage_started = time.perf_counter()
    run_risk_stage(port_result, dns_result, banner_result)
    risk_seconds = round(time.perf_counter() - stage_started, 4)

    # ─── STAGE 3: Report Generation ───
    stage_started = time.perf_counter()
    run_report_stage(offline=offline)
    report_seconds = round(time.perf_counter() - stage_started, 4)

    # ─── Return kết quả ───
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
```

---

## 1.3. Hàm `run_recon_stage()` — Parallelism cốt lõi

```python
def run_recon_stage(target: str, ports: list[int], timeout: float) -> tuple[dict, dict, dict]:
    port_path = triage_dir() / "port_scan_result.json"
    dns_path = triage_dir() / "dns_enum_result.json"
    banner_path = triage_dir() / "banner_result.json"

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
```

### Giải thích:

| Chi tiết | Giải thích |
|---|---|
| `ThreadPoolExecutor(max_workers=3)` | Tạo pool 3 threads, mỗi thread chạy một tác vụ recon |
| `executor.submit(scan_ports, ...)` | Gửi hàm `scan_ports` chạy trên thread, trả về future |
| `as_completed(futures)` | Iterator trả future theo thứ tự **hoàn thành**, không theo thứ tự submit |
| `futures[future]` | Dict map future → tên task ("port"/"dns"/"banner") vì `as_completed()` không giữ thứ tự |
| `write_json(path, data)` | Ghi dict ra JSON đẹp (indent=2, ensure_ascii=False) |

### 🔴 Câu hỏi thầy hay hỏi:

**Q: Vì sao dùng dict `{future: "port"}`?**

A: Vì `as_completed()` trả future theo thứ tự hoàn thành, không theo thứ tự submit. Nếu chỉ dùng list, không biết future nào là task nào. Dict map giúp xác định task name:

```python
futures = {
    executor.submit(scan_ports, ...): "port",      # future_A → "port"
    executor.submit(enumerate_dns, ...): "dns",     # future_B → "dns"
    executor.submit(grab_banners, ...): "banner",   # future_C → "banner"
}
for future in as_completed(futures):
    task_name = futures[future]   # future_B → "dns"
```

**Q: `as_completed()` khác gì vòng lặp bình thường?**

A: Với vòng lặp thường:
```python
port = scan_ports(...)      # Chờ port scan xong (có thể 5s)
dns = enumerate_dns(...)    # Rồi mới chạy DNS (thêm 2s)
banner = grab_banners(...)  # Rồi mới chạy banner (thêm 3s)
# Tổng: ~10s
```

Với `as_completed()`:
```python
# Cả 3 chạy đồng thời
# Task nào xong trước xử lý trước
# Tổng: ~5s (thời gian task lâu nhất)
```

---

## 1.4. Stage 2 và Stage 3 (gọi sang phần bạn An)

```python
def run_risk_stage(port_result, dns_result, banner_result):
    risk_path = triage_dir() / "risk_profile.json"
    risk_profile = score_risk(port_result, dns_result, banner_result)
    save_risk_profile(risk_profile, risk_path)
    return risk_profile

def run_report_stage(offline=False):
    risk_path = triage_dir() / "risk_profile.json"
    report_path = results_dir() / "ket_qua.md"
    prompt_path = prompts_dir() / "report_prompt.md"
    generate_report(risk_path, report_path, prompt_path, offline=offline)
```

---

# 📌 PHẦN 2 — SAFETY GATE (`tool_utils.py`)

**File:** `.pi/tools/common/tool_utils.py`

## 2.1. Hàm `is_target_allowed()` — Lõi của Safety Gate

```python
def is_target_allowed(target: str, authorized: bool) -> bool:
    """Safety gate: allowlist hoặc user truyền --authorized."""
    return authorized or target.lower() in load_allowed_targets()
```

**Logic:**
- `authorized = True` (user truyền `--authorized`) → **cho phép**
- `target` nằm trong allowlist → **cho phép**
- Cả hai đều False → **chặn**

## 2.2. Hàm `load_allowed_targets()` — Đọc allowlist

```python
DEFAULT_ALLOWED_TARGETS = {"localhost", "127.0.0.1", "::1", "scanme.nmap.org"}

def load_allowed_targets() -> set[str]:
    config_path = data_dir() / "allowed_targets.json"
    if not config_path.exists():
        return DEFAULT_ALLOWED_TARGETS

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        targets = set(config.get("allowed_targets", []))
        return targets if targets else DEFAULT_ALLOWED_TARGETS
    except Exception:
        return DEFAULT_ALLOWED_TARGETS
```

## 2.3. File allowlist — `.pi/data/allowed_targets.json`

```json
{
  "allowed_targets": [
    "localhost", "127.0.0.1", "::1",
    "scanme.nmap.org", "pentest-ground.com",
    "demo.testfire.net", "testfire.net",
    "testphp.vulnweb.com", "testhtml5.vulnweb.com",
    "testasp.vulnweb.com", "vulnweb.com"
  ],
  "scope_groups": {
    "local_loopback_demo": ["localhost", "127.0.0.1", "::1"],
    "public_classroom_lab_demo": [
      "scanme.nmap.org", "pentest-ground.com",
      "demo.testfire.net", "testfire.net",
      "testphp.vulnweb.com", "testhtml5.vulnweb.com",
      "testasp.vulnweb.com", "vulnweb.com"
    ]
  }
}
```

**Hai nhóm target được phép:**
1. **Local loopback:** localhost, 127.0.0.1, ::1 — demo offline
2. **Public classroom/lab:** scanme.nmap.org, vulnweb.com... — target có chủ đích cho lab

## 2.4. Các hàm helper khác

### `parse_target()`

```python
def parse_target(raw_target: str) -> tuple[str, list[int]]:
    """Parse target URL hoặc hostname, extract host + optional port."""
    # Dạng URL: "http://localhost:8000"
    if "://" in raw_target:
        parsed = urlparse(raw_target)
        host = parsed.hostname or parsed.netloc.split(":")[0]
        port = parsed.port
        return validate_target(host), [validate_port(port)] if port else []

    # Dạng "host:port"
    if raw_target.count(":") == 1 and not raw_target.startswith("["):
        host_text, port_text = raw_target.split(":", 1)
        return validate_target(host_text), [validate_port(int(port_text))]

    # Dạng hostname/IP thường
    return validate_target(raw_target), []
```

**Ví dụ xử lý:**
```
Input                   → Output
"localhost"             → ("localhost", [])
"http://localhost:8000"  → ("localhost", [8000])
"192.168.1.1:8080"      → ("192.168.1.1", [8080])
```

### `parse_ports()`

```python
def parse_ports(raw_ports: str) -> list[int]:
    """Parse comma-separated ports and simple ranges like 1-1000."""
    ports: set[int] = set()
    for part in raw_ports.split(","):
        item = part.strip()
        if "-" in item:
            start_text, end_text = item.split("-", 1)
            start_port = int(start_text.strip())
            end_port = int(end_text.strip())
            ports.update(range(start_port, end_port + 1))
        else:
            ports.add(validate_port(int(item)))
    return sorted(ports)
```

**Ví dụ xử lý:**
```
Input              → Output
"80,443,8000"      → [80, 443, 8000]
"1-5"             → [1, 2, 3, 4, 5]
"80,443,3000-3005" → [80, 443, 3000, 3001, 3002, 3003, 3004, 3005]
```

### `validate_timeout()`

```python
def validate_timeout(timeout: float) -> float:
    if not 0.01 <= timeout <= 30:
        raise ValueError("Timeout must be between 0.01 and 30 seconds.")
    return timeout
```

### `resolve_target()`

```python
def resolve_target(target: str) -> list[str]:
    normalized = validate_target(target)
    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(normalized, None, type=socket.SOCK_STREAM)
        }
    except socket.gaierror as exc:
        raise ValueError(f"Target could not be resolved: {normalized}.") from exc
    return sorted(addresses)
```

---

# 📌 PHẦN 3 — PORT SCANNER (`port_scanner.py`)

**File:** `.pi/tools/recon/port_scanner.py`

## 3.1. DEFAULT_PORTS

```python
DEFAULT_PORTS = [
    21,    # FTP
    22,    # SSH
    23,    # Telnet
    25,    # SMTP
    53,    # DNS
    80,    # HTTP
    110,   # POP3
    139,   # NetBIOS
    143,   # IMAP
    443,   # HTTPS
    445,   # SMB
    3306,  # MySQL
    5432,  # PostgreSQL
    6379,  # Redis
    8000,  # HTTP-dev
    8080,  # HTTP-alt
]
```

## 3.2. Hàm `scan_port()` — TCP Connect Scan cốt lõi

```python
def scan_port(target: str, port: int, timeout: float = 0.5) -> bool:
    """Kiểm tra một port TCP. True = port đang mở."""
    try:
        with socket.create_connection((target, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False
```

### 🔴 Cơ chế TCP Connect Scan:

```
Client (bạn)                    Server (target)
    |                               |
    |────── SYN ──────────────────→|  (1) Gửi SYN
    |←───── SYN-ACK ─────────────|  (2) Port mở → SYN-ACK
    |────── ACK ──────────────────→|  (3) ACK → Kết nối thành công
    |                               |      → return True
    |                               |
    |────── SYN ──────────────────→|  (1) Gửi SYN
    |←───── RST ─────────────────|  (2) Port đóng → RST
    |                               |      → OSError → return False
    |                               |
    |────── SYN ──────────────────→|  (1) Gửi SYN
    |            ... timeout ...    |  (2) Không response
    |                               |      → socket.timeout → return False
```

**Tại sao gọi là "TCP connect scan"?**
- Vì nó thực hiện **đầy đủ TCP 3-way handshake** (SYN → SYN-ACK → ACK)
- Không phải SYN scan (chỉ gửi SYN, không hoàn tất handshake)
- Không phải UDP scan (dùng UDP socket)

## 3.3. Hàm `scan_ports()` — Quét nhiều port với per-port parallelism

```python
def scan_ports(target, ports=None, timeout=0.5):
    selected_ports = [validate_port(int(port)) for port in (ports or DEFAULT_PORTS)]
    timeout = validate_timeout(timeout)
    open_ports = []

    max_workers = min(50, max(1, len(selected_ports)))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(scan_port, target, port, timeout): port
            for port in selected_ports
        }

        for future in as_completed(futures):
            port = futures[future]
            if future.result():
                open_ports.append(port)

    return {
        "target": target,
        "scanned_ports": selected_ports,
        "open_ports": sorted(open_ports),
        "open_count": len(open_ports),
    }
```

### 🔴 Hai lớp song song:

```
LỚP 1 (Stage 1 — giữa các tool):
  ThreadPoolExecutor(max_workers=3)
    ├── scan_ports(...)       ← Thread này chạy port scanner
    ├── enumerate_dns(...)    ← Thread này chạy DNS enum
    └── grab_banners(...)     ← Thread này chạy banner grab

LỚP 2 (bên trong port scanner — giữa các port):
  ThreadPoolExecutor(max_workers=min(50, số_port))
    ├── scan_port(target, 8000, 0.5)    ← Thread con
    ├── scan_port(target, 8080, 0.5)    ← Thread con
    ├── scan_port(target, 3306, 0.5)    ← Thread con
    └── ...                              ← Mỗi port một thread
```

### 🔴 `max_workers = min(50, max(1, len(selected_ports)))`:

| Số port scan | `max_workers` |
|---|---|
| 1 port | 1 |
| 16 ports (DEFAULT_PORTS) | 16 |
| 1000 ports | 50 (vì min(50, 1000) = 50) |
| 5000 ports | 50 |

**Lý do giới hạn 50:** Tránh tạo quá nhiều thread làm quá tải socket/CPU.

**Lý do tối thiểu 1:** Đảm bảo luôn có thread chạy.

### 🔴 Output example:

Với `localhost` + HTTP server port 8000:
```json
{
    "target": "localhost",
    "scanned_ports": [8000, 8080, 3306, 5432, 6379],
    "open_ports": [8000],
    "open_count": 1
}
```

Vì chỉ port 8000 có HTTP server đang chạy.

---

# 📌 PHẦN 4 — DNS ENUMERATION (`dns_enum.py`)

**File:** `.pi/tools/recon/dns_enum.py`

## 4.1. Hằng số

```python
DNS_RECORD_TYPES = ["A", "CNAME", "MX", "NS", "SOA", "TXT"]
```

## 4.2. Hàm `enumerate_dns()` — Xử lý 3 trường hợp

```python
def enumerate_dns(domain: str, timeout: float = 2.0) -> dict:
```

### Sơ đồ xử lý:

```
enumerate_dns(target)
    │
    ├── localhost? ──→ return skipped=True (không query)
    │
    ├── IP address? ──→ query PTR reverse DNS
    │
    └── Domain name? ──→ query A, CNAME, MX, NS, SOA, TXT
```

### Trường hợp 1: localhost

```python
def is_localhost(target: str) -> bool:
    return target.lower() in {"localhost", "127.0.0.1", "::1"}

# Trong enumerate_dns():
if is_localhost(domain):
    return {
        "target": domain,
        "skipped": True,
        "message": "DNS enumeration skipped for localhost target",
        "records": {},
        "errors": {},
    }
```

**Output:**
```json
{
    "target": "localhost",
    "skipped": true,
    "message": "DNS enumeration skipped for localhost target",
    "records": {},
    "errors": {}
}
```

### Trường hợp 2: IP address

```python
def is_ip_address(target: str) -> bool:
    try:
        ipaddress.ip_address(target)
        return True
    except ValueError:
        return False

# Trong enumerate_dns():
if is_ip_address(domain):
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
```

**Ví dụ với 8.8.8.8:**
- Query PTR: `8.8.8.8` → `dns.google`
- Output: `records["PTR"] = ["dns.google"]`

### Trường hợp 3: Domain name

```python
for record_type in DNS_RECORD_TYPES:   # A, CNAME, MX, NS, SOA, TXT
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
```

### 🔴 try/except riêng cho mỗi record type

Ví dụ với domain `example.com`:
```
A:     có     → records["A"] = ["93.184.216.34"]
CNAME: không → records["CNAME"] = [], errors["CNAME"] = "NXDOMAIN"
MX:    có     → records["MX"] = ["10 mail.example.com"]
NS:    có     → records["NS"] = ["a.iana-servers.net"]
SOA:   có     → records["SOA"] = ["ns.icann.org..."]
TXT:   có     → records["TXT"] = ["v=spf1 ..."]
```

★ MX lỗi nhưng A, NS, TXT vẫn chạy bình thường!

## 4.3. Hàm `_format_answer()` — Format đặc biệt cho MX và TXT

```python
def _format_answer(record_type, answer):
    if record_type == "MX":
        # MX có preference + exchange
        # Ví dụ: preference=10, exchange=mail.example.com
        # → "10 mail.example.com"
        return f"{answer.preference} {answer.exchange}".rstrip(".")
    
    if record_type == "TXT":
        # TXT là bytes string, cần decode từng phần
        # Ví dụ: [b"v=spf1", b"include:_spf.example.com"]
        # → "v=spf1 include:_spf.example.com"
        return " ".join(part.decode("utf-8", errors="replace") for part in answer.strings)
    
    # A, CNAME, NS, SOA: str(answer).rstrip(".")
    return str(answer).rstrip(".")
```

---

# 📌 PHẦN 5 — BANNER GRABBER (`banner_grabber.py`)

**File:** `.pi/tools/recon/banner_grabber.py`

## 5.1. Hằng số

```python
HTTP_PORTS = {80, 3000, 8000, 8080}
TLS_PORTS = {443, 465, 636, 993, 995, 8443}
SERVICE_BY_PORT = {
    21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "dns",
    80: "http", 110: "pop3", 143: "imap", 443: "https", 445: "smb",
    3306: "mysql", 5432: "postgresql", 6379: "redis", 8000: "http",
    8080: "http", 8443: "https",
}
```

## 5.2. Hàm `grab_banner()` — Cốt lõi của banner grabbing

```python
def grab_banner(target: str, port: int, timeout: float = 1.0) -> str:
    try:
        with socket.create_connection((target, port), timeout=timeout) as sock:
            sock.settimeout(timeout)

            # HTTP port: gửi HEAD request
            if port in HTTP_PORTS:
                request = f"HEAD / HTTP/1.1\r\nHost: {target}\r\nConnection: close\r\n\r\n"
                sock.sendall(request.encode("utf-8"))

            try:
                data = sock.recv(1024)
                return _clean_banner(data)
            except socket.timeout:
                return "No banner"
    except OSError:
        return "No banner"
```

### 🔴 Giải thích chi tiết:

**Tại sao HTTP port phải gửi HEAD request?**

```
HTTP server không tự gửi banner khi client mới connect.
Client phải gửi request trước.

Không gửi gì:
  Client ──connect──→ Server
  Client ←─(im lặng)─ Server     ← Server chờ request

Gửi HEAD request:
  Client ──connect──→ Server
  Client ──HEAD / ──→ Server     ← Gửi request
  Client ←─HTTP/1.1 200 OK── Server
           Server: SimpleHTTP/0.6 Python/3.x
           ...                     ← Nhận được banner
```

**Tại sao dùng HEAD thay vì GET?**
- HEAD chỉ lấy **header** (nhẹ)
- GET lấy cả header + **body** (nặng hơn)
- Mục tiêu chỉ là lấy banner (Server header, version) → HEAD đủ

**`Connection: close` có ý nghĩa gì?**
```
HEAD / HTTP/1.1
Host: localhost
Connection: close    ← Yêu cầu server đóng kết nối sau response
                     ← Tránh giữ kết nối lâu không cần thiết
```

**`_clean_banner()` — làm sạch dữ liệu:**
```python
def _clean_banner(raw_data: bytes) -> str:
    text = raw_data.decode("utf-8", errors="replace").strip()
    if not text:
        return "No banner"
    return text[:500]    # Giới hạn 500 ký tự
```

## 5.3. Hàm `inspect_tls()` — TLS metadata

```python
def inspect_tls(target, port, timeout=2.0):
    if port not in TLS_PORTS:   # {443, 465, 636, 993, 995, 8443}
        return {}               # Không phải TLS port → skip

    context = ssl.create_default_context()
    context.check_hostname = False       # Không verify hostname
    context.verify_mode = ssl.CERT_NONE  # Không verify cert (chấp nhận self-signed)

    try:
        with socket.create_connection((target, port), timeout=timeout) as raw_socket:
            with context.wrap_socket(raw_socket, server_hostname=target) as tls_socket:
                certificate = tls_socket.getpeercert()
                return {
                    "protocol": tls_socket.version(),          # TLSv1.2, TLSv1.3
                    "cipher": tls_socket.cipher()[0],          # Cipher suite name
                    "subject": certificate.get("subject", []), # CN, O, etc.
                    "issuer": certificate.get("issuer", []),   # Certificate issuer
                    "not_after": certificate.get("notAfter"),  # Expiry date
                }
    except (OSError, ssl.SSLError):
        return {}
```

**🔴 Tại sao `verify_mode = ssl.CERT_NONE`?**

Vì mục tiêu chỉ là **đọc metadata công khai** (protocol, cipher, subject), không xác thực trust. Lab/local có thể dùng self-signed certificate → nếu verify sẽ fail.

## 5.4. Hàm `identify_service()` — Đoán service

```python
def identify_service(port: int, banner: str) -> str:
    lowered = banner.lower()
    # Ưu tiên marker trong banner
    for marker, service in [
        ("ssh-", "ssh"), ("smtp", "smtp"), ("mysql", "mysql"),
        ("postgresql", "postgresql"), ("redis", "redis"), ("http/", "http"),
    ]:
        if marker in lowered:
            return service
    # Fallback: map từ port
    return SERVICE_BY_PORT.get(port, "unknown")
```

**Ví dụ:**
```
Banner: "HTTP/1.0 200 OK Server: SimpleHTTP/0.6"
→ marker "http/" trong banner → service = "http"

Banner: "SSH-2.0-OpenSSH_8.9"
→ marker "ssh-" trong banner → service = "ssh"

Banner: "No banner", port 3306
→ không có marker → fallback SERVICE_BY_PORT[3306] = "mysql"
```

## 5.5. Hàm `grab_banners()` — Orchestrate

```python
def grab_banners(target, candidate_ports, timeout=1.0):
    banners = {}
    services = {}
    tls = {}
    attempted_ports = [validate_port(int(port)) for port in candidate_ports]
    timeout = validate_timeout(timeout)
    max_workers = min(50, max(1, len(attempted_ports)))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(grab_banner, target, port, timeout): port
            for port in attempted_ports
        }

        for future in as_completed(futures):
            port = futures[future]
            banners[str(port)] = future.result()
            services[str(port)] = identify_service(port, banners[str(port)])
            tls_result = inspect_tls(target, port, timeout)
            if tls_result:
                tls[str(port)] = tls_result

    return {
        "target": target,
        "attempted_ports": attempted_ports,
        "banners": dict(sorted(banners.items(), key=lambda item: int(item[0]))),
        "services": dict(sorted(services.items(), key=lambda item: int(item[0]))),
        "tls": dict(sorted(tls.items(), key=lambda item: int(item[0]))),
    }
```

### Cũng có per-port parallelism như port scanner!

## 5.6. Output example với localhost + HTTP server port 8000

```json
{
    "target": "localhost",
    "attempted_ports": [8000, 8080, 3306, 5432, 6379],
    "banners": {
        "8000": "HTTP/1.0 200 OK Server: SimpleHTTP/0.6 Python/3.12.3 Date: ...",
        "8080": "No banner",
        "3306": "No banner",
        "5432": "No banner",
        "6379": "No banner"
    },
    "services": {
        "8000": "http",
        "8080": "unknown",
        "3306": "mysql",
        "5432": "postgresql",
        "6379": "redis"
    },
    "tls": {}
}
```

Port 8000 có banner HTTP vì có gửi HEAD request. Các port khác không có service → "No banner".

---

# 📌 PHẦN 6 — KIỂM THỬ RECON

## 6.1. Chạy pipeline local

**Terminal 1** — HTTP server:
```powershell
python -m http.server 8000 --bind 127.0.0.1
```

**Terminal 2** — Pipeline:
```powershell
python .pi\tools\main_pipeline.py --target localhost --ports "8000,8080,3306,5432,6379" --offline
```

## 6.2. Chạy riêng từng tool

```powershell
# Port scanner
python .pi\tools\recon\port_scanner.py --target localhost --ports "8000,8080"

# DNS enum (dùng target domain thật)
python .pi\tools\recon\dns_enum.py --target scanme.nmap.org

# Banner grabber
python .pi\tools\recon\banner_grabber.py --target localhost --ports "8000,8080"
```

## 6.3. Kiểm tra output

```powershell
# Xem 3 file JSON
notepad .pi\triage\port_scan_result.json
notepad .pi\triage\dns_enum_result.json
notepad .pi\triage\banner_result.json
```

---

# 📌 PHẦN 7 — TỔNG KẾT LUỒNG CHẠY ĐẦY ĐỦ

```
LỆNH: python .pi/tools/main_pipeline.py --target localhost --ports "8000,8080,3306,5432,6379" --offline
  │
  ├── main()
  │     ├── parse_target("localhost")          → ("localhost", [])
  │     ├── choose_ports("8000,...", [], DEFAULT_PORTS) → [8000, 8080, 3306, 5432, 6379]
  │     └── run_pipeline(localhost, [8000,...], authorized=False, timeout=0.5, offline=True)
  │           │
  │           ├── ensure_output_dirs()          → Tạo .pi/triage/, .pi/logs/, .pi/results/
  │           ├── setup_logging()               → Ghi log vào .pi/logs/pipeline_run.log
  │           ├── load_env()                    → Load .env (nếu có)
  │           ├── validate_timeout(0.5)         → OK
  │           │
  │           ├── [STAGE 0] is_target_allowed("localhost", False)
  │           │     ├── "localhost" in allowlist? → True
  │           │     └── → PASS
  │           │
  │           ├── resolve_target("localhost")    → ["127.0.0.1", "::1"]
  │           │
  │           ├── [STAGE 1] run_recon_stage("localhost", [8000,...], 0.5)
  │           │     │
  │           │     ├── ThreadPoolExecutor(max_workers=3)
  │           │     │     │
  │           │     │     ├── scan_ports(...) → [8000]
  │           │     │     │     ├── scan_port(8000)  → True  (HTTP server)
  │           │     │     │     ├── scan_port(8080)  → False
  │           │     │     │     ├── scan_port(3306)  → False
  │           │     │     │     ├── scan_port(5432)  → False
  │           │     │     │     └── scan_port(6379)  → False
  │           │     │     │     → Ghi port_scan_result.json
  │           │     │     │
  │           │     │     ├── enumerate_dns("localhost")
  │           │     │     │     → skipped (localhost)
  │           │     │     │     → Ghi dns_enum_result.json
  │           │     │     │
  │           │     │     └── grab_banners(...)
  │           │     │           ├── grab_banner(8000)  → "HTTP/1.0 200 OK..."
  │           │     │           ├── grab_banner(8080)  → "No banner"
  │           │     │           ├── grab_banner(3306)  → "No banner"
  │           │     │           ├── grab_banner(5432)  → "No banner"
  │           │     │           └── grab_banner(6379)  → "No banner"
  │           │     │         → Ghi banner_result.json
  │           │     │
  │           │     └── Trả về 3 dict
  │           │
  │           ├── [STAGE 2] run_risk_stage(...)  → risk_profile.json (bạn An)
  │           │
  │           ├── [STAGE 3] run_report_stage(offline=True) → ket_qua.md (bạn An)
  │           │
  │           └── Return dict kết quả
  │
  └── In output paths
```

---

# 📌 PHẦN 8 — CÂU HỎI VẤN ĐÁP THƯỜNG GẶP

## 8.1. Về Pipeline

| Câu hỏi | Trả lời |
|---|---|
| Pipeline có mấy stage? | 4: Stage 0 (Safety Gate), Stage 1 (Parallel Recon), Stage 2 (ML Risk), Stage 3 (Report) |
| Stage nào song song? | Stage 1 |
| Dùng class gì? | `ThreadPoolExecutor(max_workers=3)` |
| Hàm xử lý kết quả song song? | `as_completed()` |
| Vì sao dùng dict `{future: "port"}`? | Vì `as_completed()` trả future theo thứ tự hoàn thành, không theo thứ tự submit |

## 8.2. Về Safety Gate

| Câu hỏi | Trả lời |
|---|---|
| Safety Gate nằm ở đâu? | `is_target_allowed()` trong `tool_utils.py` |
| Chạy trước hay sau resolve_target? | **Trước** |
| Target nào được phép? | Target trong allowlist (local + lab) hoặc có `--authorized` |
| Mặc định allow hay deny? | **Deny** |

## 8.3. Về Port Scanner

| Câu hỏi | Trả lời |
|---|---|
| Kỹ thuật scan gì? | TCP connect scan (`socket.create_connection`) |
| Có mấy lớp song song? | 2 lớp: Stage 1 (giữa 3 tool) + per-port (giữa các port) |
| `max_workers` tối đa bao nhiêu? | 50 |
| Vì sao sort open_ports? | Vì future hoàn thành không theo thứ tự port |

## 8.4. Về DNS Enum

| Câu hỏi | Trả lời |
|---|---|
| localhost xử lý thế nào? | Skip, trả `skipped=True` |
| IP address xử lý thế nào? | Query PTR reverse DNS |
| Domain xử lý thế nào? | Query A, CNAME, MX, NS, SOA, TXT |
| Một record lỗi có fail toàn bộ? | Không, mỗi record có try/except riêng |

## 8.5. Về Banner Grabber

| Câu hỏi | Trả lời |
|---|---|
| HTTP port gửi request gì? | `HEAD / HTTP/1.1` |
| Vì sao không dùng GET? | HEAD nhẹ hơn, chỉ lấy header |
| `Connection: close` để làm gì? | Yêu cầu server đóng kết nối |
| TLS lấy thông tin gì? | protocol, cipher, subject, issuer, not_after |
| Vì sao `verify_mode = ssl.CERT_NONE`? | Chấp nhận self-signed cert, chỉ đọc metadata |

---

# 📌 PHẦN 9 — BÀI CODE TAY THẦY DỄ HỎI

## Bài 1: Thêm `closed_count` vào port scan result

**File sửa:** `.pi/tools/recon/port_scanner.py`

```python
return {
    "target": target,
    "scanned_ports": selected_ports,
    "open_ports": sorted(open_ports),
    "open_count": len(open_ports),
    "closed_count": len(selected_ports) - len(open_ports),  # THÊM DÒNG NÀY
}
```

**Giải thích:** `closed_count = tổng số port scan - số port open`. Đơn giản, dễ tính.

## Bài 2: Thêm MongoDB port 27017 vào DEFAULT_PORTS

**File sửa:** `.pi/tools/recon/port_scanner.py`

```python
DEFAULT_PORTS = [
    21, 22, 23, 25, 53, 80, 110, 139, 143, 443, 445,
    3306, 5432, 6379, 8000, 8080, 27017,    # THÊM 27017
]
```

## Bài 3: Thêm CAA record vào DNS enum

**File sửa:** `.pi/tools/recon/dns_enum.py`

```python
DNS_RECORD_TYPES = ["A", "CNAME", "MX", "NS", "SOA", "TXT", "CAA"]  # THÊM "CAA"
```

## Bài 4: Thêm `--timeout` cho banner grabber CLI

**File sửa:** `.pi/tools/recon/banner_grabber.py`

```python
parser.add_argument("--timeout", type=float, default=1.0)    # THÊM
result = grab_banners(args.target, ports, args.timeout)       # SỬA
```

## Bài 5: Fallback DEFAULT_PORTS khi banner grabber không có --ports

**File sửa:** `.pi/tools/recon/banner_grabber.py`

```python
from recon.port_scanner import DEFAULT_PORTS    # THÊM IMPORT

# Trong main():
ports = parse_ports(args.ports) if args.ports else DEFAULT_PORTS    # SỬA
```

## Bài 6: Thêm field `"stage": "recon"` vào output

**File sửa:** Cả 3 file:
- `.pi/tools/recon/port_scanner.py`
- `.pi/tools/recon/dns_enum.py`
- `.pi/tools/recon/banner_grabber.py`

Thêm vào dict return:
```python
"stage": "recon",
```

## Bài 7: Log rõ target bị block

**File sửa:** `.pi/tools/main_pipeline.py`

```python
logging.warning("Permission gate blocked target=%s: %s", target, message)
```

---

# 📋 CHECKLIST TRƯỚC KHI VẤN ĐÁP

| STT | Kỹ năng | File cần mở | ✅ |
|:---:|---|---|:---:|
| 1 | Chỉ đúng `run_recon_stage()` | `main_pipeline.py` | ☐ |
| 2 | Giải thích `ThreadPoolExecutor` + `as_completed` | `main_pipeline.py` | ☐ |
| 3 | Giải thích dict `{future: "port"}` | `main_pipeline.py` | ☐ |
| 4 | Giải thích `is_target_allowed()` | `tool_utils.py` | ☐ |
| 5 | Giải thích `parse_target()`, `parse_ports()` | `tool_utils.py` | ☐ |
| 6 | Giải thích TCP connect scan | `port_scanner.py` | ☐ |
| 7 | Giải thích per-port parallelism | `port_scanner.py` | ☐ |
| 8 | Giải thích 3 trường hợp DNS | `dns_enum.py` | ☐ |
| 9 | Giải thích try/except từng record | `dns_enum.py` | ☐ |
| 10 | Giải thích HEAD request | `banner_grabber.py` | ☐ |
| 11 | Giải thích TLS metadata | `banner_grabber.py` | ☐ |
| 12 | Giải thích `identify_service()` | `banner_grabber.py` | ☐ |
| 13 | Chạy được pipeline local | Terminal | ☐ |
| 14 | Sửa được 3 bài code tay | Các file tương ứng | ☐ |
