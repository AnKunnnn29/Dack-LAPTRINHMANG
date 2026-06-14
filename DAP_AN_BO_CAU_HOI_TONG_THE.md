# ĐÁP ÁN BỘ CÂU HỎI TỔNG THỂ TOÀN PROJECT
## Network Recon + Risk Profiler – Topic 02

---

## 🅰️ PHẦN TỔNG QUAN KIẾN TRÚC

**Câu 1.** Pipeline 4 stage:
- Stage 0 (Safety Gate): Kiểm tra target trong allowlist hoặc có `--authorized`. Nếu không → `PermissionError`.
- Stage 1 (Parallel Recon): Chạy song song port_scan, dns_enum, banner_grab bằng `ThreadPoolExecutor(max_workers=3)`.
- Stage 2 (ML Risk Scoring): Đọc 3 JSON recon, trích feature, Isolation Forest → risk_score 0-10.
- Stage 3 (Report Generation): Đọc risk_profile.json → sinh Markdown report (OpenAI API hoặc offline template).

**Câu 2.** Vì Stage 1 là **I/O-bound tasks** (network socket, chờ timeout). ThreadPoolExecutor nhẹ hơn multiprocessing (không tốn bộ nhớ copy process), đủ dùng cho 3 worker.

**Câu 3.** Sửa `ThreadPoolExecutor(max_workers=5)` trong `run_recon_stage()`. Hậu quả: socket connection quá nhiều cùng lúc có thể gây **rate-limit** từ target hoặc treo do giới hạn file descriptor của OS.

**Câu 4.** Dict gồm: `status`, `target`, `resolved_addresses`, `offline_report`, `duration_seconds`, `stage_durations` (recon/risk/report), 5 đường dẫn output (port_scan_result, dns_enum_result, banner_result, risk_profile, report) + `log`.

**Câu 5.** `stage_durations` cho thấy thời gian từng stage → chứng minh Stage 1 song song nhanh hơn tuần tự, Stage 2/3 tuần tự nhanh vì chỉ đọc file JSON.

**Câu 6.** `parse_target()` dùng `urlparse()` → scheme=http, hostname=localhost, port=8080. Trả về `("localhost", [8080])`.

**Câu 7.** `generate_report()`:
1. Nếu `offline=True` → `build_offline_report()`
2. Nếu không có API key hoặc key là placeholder → `build_offline_report()`
3. Nếu có API key → `generate_ai_report()`. Nếu API lỗi → fallback `build_offline_report()`

**Câu 8.** `udp_scanner.py` dùng `socket.SOCK_DGRAM` gửi probe bytes mẫu cho DNS (53), NTP (123), SNMP (161). Không trong pipeline vì project chính là **TCP recon**, UDP scan chỉ là utility phụ.

**Câu 9.** `manage_targets.py` dùng `load_config()` đọc `allowed_targets.json`. `list` in danh sách, `add` thêm target, `remove` xóa target.

**Câu 10.** `chain.md` là **markdown design document** mô tả multi-agent orchestration. `main_pipeline.py` là **code chạy thật**.

---

## 🅱️ PHẦN HIỂU CODE

### tool_utils.py

**Câu 11.** `Path(__file__).resolve().parents[3]`: file ở `.pi/tools/common/tool_utils.py`, lên 3 cấp: common → tools → .pi → project_root.

**Câu 12.** File `.pi/data/allowed_targets.json`. Nếu không tồn tại hoặc lỗi → return `DEFAULT_ALLOWED_TARGETS`.

**Câu 13.** `socket.getaddrinfo()`. Ném `ValueError("Target could not be resolved")`.

**Câu 14.** Tách `-`, swap nếu start > end, validate từng port, thêm range vào set, giới hạn `MAX_PORT_COUNT=4096`.

**Câu 15.** Kiểm tra: empty, khoảng trắng, có path (`/` hoặc `\`), độ dài > 253.

**Câu 16.** `--ports` > URL port > `DEFAULT_PORTS`.

### main_pipeline.py

**Câu 17.** Để task nào xong trước xử lý trước, không bị task chậm chặn.

**Câu 18.** Safety Gate chạy trước **mọi network activity**. `resolve_target()` đã là DNS lookup.

**Câu 19.** `--target`, `--ports`, `--authorized`, `--timeout`, `--offline`. Nếu không `--ports` → dùng `DEFAULT_PORTS`.

**Câu 20.** Thêm hàm `run_stage4()` trong `main_pipeline.py`, gọi trong `run_pipeline()`, thêm output path vào return dict.

### port_scanner.py

**Câu 21.**
```python
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(timeout)
    return sock.connect_ex((target, port)) == 0
```
`connect_ex()` trả 0 nếu thành công.

**Câu 22.** Vì port **filtered** (firewall drop) cũng được tính là closed. Scanner đơn giản không phân biệt được timeout (filtered) vs connection refused (closed).

**Câu 23.** Tránh tạo quá nhiều socket connection cùng lúc, giới hạn file descriptor.

### dns_enum.py

**Câu 24.** `localhost`, `127.0.0.1`, `::1`.

**Câu 25.** `ipaddress.ip_address()`. IPv6 `::1` → True (loopback).

**Câu 26.** MX: `f"{preference} {exchange}"`. TXT: decode bytes từng phần rồi join.

**Câu 27.** Không. Mỗi record có try/except riêng. Lỗi ghi vào `errors`, record = `[]`.

### banner_grabber.py

**Câu 28.** Decode bytes → string, strip, cắt 500 ký tự. Để report không quá dài.

**Câu 29.** `HEAD / HTTP/1.1\r\nHost: {target}\r\nConnection: close\r\n\r\n`. `Connection: close` báo server đóng kết nối sau response.

**Câu 30.** Chỉ đọc metadata công khai (protocol, cipher), không cần validate trust. Self-signed cert trong lab sẽ không gây lỗi.

**Câu 31.** `80: http, 443: https, 22: ssh, 21: ftp,...`. Port 3000: `HTTP-dev`.

**Câu 32.** Banner thật chính xác hơn port mặc định (server có thể chạy service khác port tiêu chuẩn).

### risk_config.py

**Câu 33.** 7 feature: open_port_count(0.8), sensitive_port_count(1.2), high_risk_port_count(**2.0**), database_cache_port_count(1.4), http_port_count(0.7), version_banner_count(1.1), dns_record_count(0.25).

**Câu 34.** `Server:\s*.+\d+\.\d+`, `Apache[/ -]?\d+\.\d+`, `nginx[/ -]?\d+\.\d+`, `OpenSSH[_/ -]?\d+\.\d+`,...

### risk_features.py

**Câu 35.** Input: `open_ports(list[int])`, `banners(dict)`, `dns_result(dict)`. Output: `feature_map(dict)`, `version_leaks(list[int])`.

**Câu 36.** Regex trong `BANNER_VERSION_PATTERNS`. Nếu banner là `"No banner"` → False.

### risk_model.py

**Câu 37.** `fit(samples)`: train trên baseline. `path_length(vector, node)`: tính độ dài đường đi trong isolation tree. `anomaly_score(vector)`: tính anomaly score.

**Câu 38.** `c(n) = 2*ln(n-1) + 0.5772 - 2*(n-1)/n`.

**Câu 39.** Để thêm **domain knowledge**: port 23 Telnet nguy hiểm hơn port 80 HTTP. Giúp score giải thích được.

**Câu 40.** `combined = (calibrated_anomaly * 0.55) + (exposure * 0.45)`. Score = `round(combined * 10)`.

### risk_scorer.py

**Câu 41.** localhost/local IP → "local". Private IP → "private". Còn lại → "public".

**Câu 42.** `exposure_adjustment = 1` nếu public và có open_ports.

**Câu 43.** Đọc 3 JSON từ `.pi/triage`, gọi `score_risk()`, gọi `save_risk_profile()`.

### risk_findings.py

**Câu 44.** 3 loại: `open_port`, `banner_version`, `dns_records`.

**Câu 45.** T1046 (Network Service Discovery), T1595 (Active Scanning), T1590 (Gather Network Info), T1592.002 (Software Info).

### report_templates.py & ai_reporter.py

**Câu 46.** 9 sections: Target, Scope & Authorization, Recon Summary, Risk Level, ML Risk Model, Findings, MITRE ATT&CK Mapping, Recommendations, Conclusion.

**Câu 47.** Để thầy biết report không dùng AI, tránh hiểu lầm.

**Câu 48.** System: "You write concise defensive cybersecurity reports in Markdown." User: prompt + risk profile JSON.

**Câu 49.** Đầu ra ổn định, ít sáng tạo, giữ đúng cấu trúc report.

### pi_recon_agent.py

**Câu 50.** `_check_target()`, `_check_rate_limit()`, `_select_ports()`.

**Câu 51.** `max_iterations = 8`.

**Câu 52.** `_extract_text_tool_plan()` parse JSON từ content, `_execute_text_tool_plan()` chạy các tool.

**Câu 53.** Rút gọn tool result: cắt scanned_ports dài, giữ field chính của ml_model.

---

## 🅲 PHẦN CÂU HỎI CODE TAY

**Câu 54.** Không nên. Port không open thì không biết service gì. Chỉ nên ghi `"unknown"` khi port open nhưng banner không xác định được.

**Câu 55.** Đã có. `FEATURE_WEIGHTS` có `high_risk_port_count: 2.0`, cao nhất.

**Câu 56.** `risk_config.py`: thêm `"total_banner_length"` vào FEATURE_NAMES + FEATURE_WEIGHTS. `risk_features.py`: thêm logic tính. `risk_scorer.py`: truyền banners vào.

**Câu 57.** Thêm vào `port_scanner.py`:
```python
def ping_target(target, timeout=1.0):
    try:
        socket.create_connection((target, 80), timeout=timeout).close()
        return True
    except OSError:
        return False
```

**Câu 58.** `report_templates.py`:
```python
"## Evidence Files",
"- `.pi/triage/port_scan_result.json`",
"- `.pi/triage/dns_enum_result.json`",
"- `.pi/triage/banner_result.json`",
"- `.pi/triage/risk_profile.json`",
```

**Câu 59.** `main_pipeline.py`:
```python
parser.add_argument("--verbose", action="store_true")
if args.verbose:
    logging.getLogger().addHandler(logging.StreamHandler())
```

**Câu 60.** Bắt exception từ OpenAI API trong `generate_report()`, nếu lỗi → fallback `build_offline_report()`. Code đã có sẵn `except Exception as exc: build_offline_report(reason=f"OpenAI API error: {exc}")`.

---

## 🅳 PHẦN DEBUG & TÌNH HUỐNG

**Câu 61.** `[BLOCKED] Permission gate blocked this target. Use a local/classroom-lab allowlisted target, or add --authorized only when you have permission.`

**Câu 62.** HTTP server bind `--bind 127.0.0.1` nhưng target không phải localhost.

**Câu 63.** Chưa `pip install dnspython`. Hoặc network không có DNS. Hoặc domain thật không tồn tại.

**Câu 64.** Service không gửi banner tự động, hoặc cần gửi request đặc thù (SMTP, FTP thì cần lệnh). Tool không retry.

**Câu 65.** Kiểm tra `open_ports` rỗng? `dns_record_count == 0`? `version_leaks` rỗng? → `build_mitre_mapping()` không có gì để append.

**Câu 66.** `calibrate_anomaly_score()` trả 0 nếu score ≤ baseline mean + std. Target exposure thấp → không bất thường.

---

## 🅴 PHẦN CÂU HỎI RIÊNG CHO VŨ VĂN THÔNG

### Pipeline & Safety Gate

**Câu T1.** `ensure_output_dirs()` → `setup_logging()` → `load_env()` → `validate_timeout()` → `is_target_allowed()` → `resolve_target()` → `run_recon_stage()` → `run_risk_stage()` → `run_report_stage()` → return dict.

**Câu T2.** `as_completed()` trả future theo thứ tự hoàn thành → task nhanh không bị task chậm chặn.

**Câu T3.** Chỉ để thông tin, không dùng ở stage sau.

**Câu T4.** Không. `write_json()` gọi `path.parent.mkdir(parents=True, exist_ok=True)`.

**Câu T5.** `return authorized or target.lower() in load_allowed_targets()`. authorized bypass, nếu không → kiểm tra lowercase trong allowlist.

**Câu T6.** `except Exception: return DEFAULT_ALLOWED_TARGETS`.

**Câu T7.** File JSON có thể bị xóa/lỗi, DEFAULT_ALLOWED_TARGETS là fallback.

**Câu T8.** JSON: thêm vào `"allowed_targets"`. `tool_utils.py`: thêm vào `DEFAULT_ALLOWED_TARGETS`.

### Port Scanner

**Câu T9.** `with` = context manager, tự động close socket. `create_connection` trả socket object.

**Câu T10.** Dùng `socket.socket(socket.AF_INET, socket.SOCK_DGRAM)`, gửi probe bytes, không `connect()`. Xem `recon/udp_scanner.py`.

**Câu T11.** Cả 2 đều dùng `as_completed()`. Ở `scan_ports()` để xử lý từng port, ở `main_pipeline.py` để xử lý từng tool.

**Câu T12.** Port 9200 vẫn được scan. Banner grabber ghi `"unknown"`. Không lỗi.

**Câu T13.** Khó. Scanner đơn giản chỉ bắt `OSError`. Cần phân biệt: timeout vs connection refused vs host unreachable.

### DNS Enumeration

**Câu T14.** `is_ip_address("example.com")` → ValueError → False.

**Câu T15.** Nếu chưa cài `dnspython`, tool vẫn chạy, trả `skipped=True`.

**Câu T16.** `dns_enum.py`: thêm `"SRV"` vào `DNS_RECORD_TYPES`.

**Câu T17.** Đổi `DNS_RECORD_TYPES = ["A"]`.

**Câu T18.** Dùng cho IP address, thực hiện reverse DNS lookup (PTR).

### Banner Grabber

**Câu T19.** `socket.create_connection()` → `sock.sendall(HEAD request)` → `sock.recv(1024)` → `_clean_banner()`.

**Câu T20.** Đổi `HEAD` thành `GET`. Rủi ro: server trả body lớn, `recv(1024)` không đủ.

**Câu T21.** `{443, 465, 636, 993, 995, 8443}`. 8443 là HTTPS alt port.

**Câu T22.** Không, vì `verify_mode = ssl.CERT_NONE`.

**Câu T23.** `return text[:200]`.

**Câu T24.** Banner bị cắt. Demo chỉ cần banner ngắn nên chấp nhận.

### Tool Utils

**Câu T25.** Target là hostname/IP, không phải URL path. Tránh misinterpretation.

**Câu T26.** Ném `ValueError: "Timeout must be between 0.01 and 30 seconds."`.

**Câu T27.** `urlparse` → scheme=http, hostname=localhost, port=8000. Trả `("localhost", [8000])`.

**Câu T28.** Để so sánh case-insensitive với allowlist.

**Câu T29.** `custom_ports(CLI)` > `url_ports` > `DEFAULT_PORTS`.

### Cross-check

**Câu T30.** Không bắt buộc. Nhưng nếu port là sensitive/high-risk, bạn An nên thêm vào `risk_config.py`.

**Câu T31.** Không. `banner_has_version("No banner")` → False.

**Câu T32.** Nếu An không đọc field mới thì không cần. Nếu feature extraction cần field mới, An phải sửa.

**Câu T33.** Không. An chỉ đọc `open_ports` từ kết quả.

### Bài code tay nâng cao

**Bài T34.**
```python
def scan_port(target, port, timeout=0.5):
    timeout = min(timeout, 5.0)
    try:
        with socket.create_connection((target, port), timeout=timeout):
            return True
    except OSError:
        return False
```

**Bài T35.**
```python
def safe_scan(target, ports, authorized):
    if not is_target_allowed(target, authorized):
        raise PermissionError(f"Blocked: {target}")
    return scan_ports(target, ports)
```

**Bài T36.**
```python
parser.add_argument("--format", choices=["text", "json"], default="text")
if args.format == "json":
    print(json.dumps(outputs, indent=2))
```

**Bài T37.**
```python
def test_parse_ports():
    assert parse_ports("80,443") == [80, 443]
    assert parse_ports("1-5") == [1, 2, 3, 4, 5]
```

**Bài T38.**
```python
def is_safe_target(target):
    try:
        addr = ipaddress.ip_address(target)
        return addr.is_loopback or addr.is_private
    except ValueError:
        return False
```

**Bài T39.**
```python
def grab_banner(target, port, timeout=1.0):
    for attempt in range(2):
        try:
            with socket.create_connection((target, port), timeout=timeout) as sock:
                ...
                return _clean_banner(data)
        except socket.timeout:
            continue
    return "No banner"
```

**Bài T40.**
```python
def validate_ports(ports, max_count=100):
    if len(ports) > max_count:
        print(f"Warning: scanning {len(ports)} ports may be slow")
```

### Tình huống vấn đáp

**T41.** Project là lập trình mạng, cần tự implement socket để hiểu cơ chế TCP connect scan. Nmap là công cụ có sẵn, không chứng minh được kiến thức lập trình mạng.

**T42.** 1. `socket.getaddrinfo()` đã hỗ trợ IPv6. 2. `create_connection()` dùng dual-stack. 3. `parse_target()` xử lý `[::1]`. 4. Allowlist đã có `::1`.

**T43.** Mỗi port tạo **1 kết nối TCP**. N port scan với timeout T → tối đa N*T giây, song song với 50 worker → giảm xuống còn T*(N/50) giây.

**T44.** `MAX_PORT_COUNT = 4096`. Quét 65535 port sẽ rất chậm, cần tối ưu batch processing, không phù hợp demo.
