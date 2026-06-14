# Vũ Văn Thông - Bộ câu hỏi mở rộng kèm đáp án

> MSSV: 23162098  
> Phạm vi: `main_pipeline.py`, `tool_utils.py`, port scanner, DNS enum, banner grabber, handoff sang risk/report.  
> Ghi chú: Bộ này cố tình khác các file cũ. Câu hỏi tập trung vào hành vi thật của code, tình huống debug, câu hỏi bẫy và bài code tay.

---

## A. Nắm phạm vi và cách trả lời nhanh

### Câu 1. Nếu thầy hỏi "em phụ trách phần nào", trả lời ngắn nhất thế nào?

**Đáp án:**  
Em phụ trách Stage 0 và Stage 1 của pipeline: Safety Gate, điều phối recon song song, port scanner, DNS enum và banner grabber. Output của em là 3 file JSON trong `.pi/triage`, làm input cho risk scoring.

### Câu 2. Phần nào chứng minh project có parallelism?

**Đáp án:**  
Trong `.pi/tools/main_pipeline.py`, hàm `run_recon_stage()` dùng `ThreadPoolExecutor(max_workers=3)` để chạy song song 3 tool: `scan_ports`, `enumerate_dns`, `grab_banners`.

### Câu 3. Có mấy lớp song song trong phần em?

**Đáp án:**  
Có 2 lớp chính:

- Lớp 1: Stage 1 chạy song song 3 tool recon.
- Lớp 2: bên trong `port_scanner.py` và `banner_grabber.py`, mỗi port được xử lý bằng future riêng.

### Câu 4. Output nào của em được bạn An dùng trực tiếp?

**Đáp án:**  
Ba file:

- `.pi/triage/port_scan_result.json`
- `.pi/triage/dns_enum_result.json`
- `.pi/triage/banner_result.json`

### Câu 5. Nếu thầy hỏi "pipeline có exploit không", trả lời sao?

**Đáp án:**  
Không. Pipeline chỉ làm read-only recon: thử connect TCP, query DNS record cơ bản, đọc banner nhẹ và sinh báo cáo phòng thủ. Không brute force, không bypass, không khai thác lỗ hổng.

### Câu 6. Vì sao phải có Safety Gate?

**Đáp án:**  
Vì port scan và banner grab là hoạt động network chủ động. Safety Gate đảm bảo chỉ chạy trên localhost, target lab trong allowlist hoặc target có `--authorized`.

### Câu 7. Stage 1 có phụ thuộc kết quả port scan để banner grab không?

**Đáp án:**  
Không. `grab_banners(target, ports, timeout)` nhận cùng danh sách candidate ports với port scanner. Nó không đợi `open_ports`, để giữ đúng thiết kế chạy song song.

### Câu 8. Nếu banner grab thử cả port đóng thì có sai không?

**Đáp án:**  
Không sai. Port đóng sẽ timeout hoặc lỗi connect và trả `"No banner"`. Đổi lại, Stage 1 không bị phụ thuộc dữ liệu giữa các tool.

---

## B. Pipeline chính và CLI

### Câu 9. `main()` làm những bước gì trước khi gọi pipeline?

**Đáp án:**  
`main()` parse CLI bằng `argparse`, gọi `parse_target(args.target)` để lấy target và port trong URL nếu có, gọi `choose_ports()` để chọn danh sách port, rồi gọi `run_pipeline()`.

### Câu 10. `main()` bắt những exception nào?

**Đáp án:**  
`main()` chỉ bắt `PermissionError` và `ValueError`. Các lỗi khác như lỗi API hoặc lỗi code không được bắt ở đây, nên có thể làm chương trình traceback.

### Câu 11. Nếu bị Safety Gate chặn, terminal in gì?

**Đáp án:**  
Terminal in dạng:

```text
[BLOCKED] Permission gate blocked this target...
```

Vì `main()` bắt `PermissionError` và print với prefix `[BLOCKED]`.

### Câu 12. `run_pipeline()` có trả trực tiếp risk profile không?

**Đáp án:**  
Không. Nó gọi `run_risk_stage()` để ghi `.pi/triage/risk_profile.json`, nhưng dict trả về của `run_pipeline()` chủ yếu là status, target, stage durations và đường dẫn các file output.

### Câu 13. `run_report_stage()` trả về gì?

**Đáp án:**  
Hàm này trả về `None`. Nó chỉ gọi `generate_report(...)` để ghi file `.pi/results/ket_qua.md`.

### Câu 14. Vì sao `run_pipeline()` gọi `validate_timeout()` sớm?

**Đáp án:**  
Để timeout được kiểm tra trước khi truyền vào các tool network. Nếu timeout quá nhỏ hoặc quá lớn thì dừng sớm bằng `ValueError`.

### Câu 15. `ensure_output_dirs()` tạo những thư mục nào?

**Đáp án:**  
Tạo 3 thư mục output:

- `.pi/triage`
- `.pi/logs`
- `.pi/results`

Nó không tạo `.pi/prompts` hay `.pi/data`.

### Câu 16. Vì sao Safety Gate phải chạy trước `resolve_target()`?

**Đáp án:**  
Vì `resolve_target()` dùng DNS/socket lookup, cũng là hoạt động network. Target chưa được phép thì pipeline phải dừng trước mọi hoạt động network.

### Câu 17. `resolved_addresses` trong output lấy từ đâu?

**Đáp án:**  
Từ `resolve_target(target)`, dùng `socket.getaddrinfo()` để lấy các IP có thể kết nối TCP.

### Câu 18. Stage durations gồm những key nào?

**Đáp án:**  
Gồm:

- `recon`
- `risk`
- `report`

Các giá trị được tính bằng `time.perf_counter()` và làm tròn 4 chữ số.

### Câu 19. Nếu Stage 1 lỗi thì Stage 2 có chạy không?

**Đáp án:**  
Không. `run_recon_stage()` phải trả đủ `port_result`, `dns_result`, `banner_result` thì code mới gọi `run_risk_stage()`.

### Câu 20. Nếu Stage 2 lỗi thì report có được tạo không?

**Đáp án:**  
Không. `run_report_stage()` nằm sau `run_risk_stage()`. Nếu risk scoring raise exception thì pipeline dừng trước report.

### Câu 21. Vì sao `path_keys` trong `main()` cần thiết?

**Đáp án:**  
Để các giá trị là đường dẫn được in bằng `display_path()`, nhìn gọn hơn. Các giá trị khác được in bằng `json.dumps()`.

### Câu 22. `--offline` ảnh hưởng stage nào?

**Đáp án:**  
Ảnh hưởng Stage 3 report generation. Khi `offline=True`, report dùng template offline, không gọi AI API.

### Câu 23. Nếu target là `http://localhost:8000`, port nào được chọn khi không truyền `--ports`?

**Đáp án:**  
`parse_target()` lấy port 8000 từ URL. `choose_ports()` ưu tiên URL port sau CLI ports, nên danh sách port là `[8000]`.

### Câu 24. Nếu vừa truyền URL port vừa truyền `--ports`, cái nào thắng?

**Đáp án:**  
`--ports` thắng. Thứ tự ưu tiên trong `choose_ports()` là CLI ports, URL ports, rồi `DEFAULT_PORTS`.

### Câu 25. Lệnh demo local ổn định nhất là gì?

**Đáp án:**  
Terminal 1:

```powershell
python -m http.server 8000 --bind 127.0.0.1
```

Terminal 2:

```powershell
python .pi\tools\main_pipeline.py --target localhost --ports "8000,8080,3306,5432,6379" --offline
```

---

## C. Safety Gate và input validation

### Câu 26. `is_target_allowed()` logic chính là gì?

**Đáp án:**  
Logic là:

```python
return authorized or target.lower() in load_allowed_targets()
```

Nếu có `--authorized` thì cho phép. Nếu không, target phải nằm trong allowlist.

### Câu 27. Nếu `allowed_targets.json` bị lỗi JSON thì sao?

**Đáp án:**  
`load_allowed_targets()` bắt exception và trả `DEFAULT_ALLOWED_TARGETS`, gồm `localhost`, `127.0.0.1`, `::1`, `scanme.nmap.org`.

### Câu 28. Nếu file allowlist tồn tại nhưng `allowed_targets` rỗng thì sao?

**Đáp án:**  
Hàm trả `DEFAULT_ALLOWED_TARGETS` vì `targets` rỗng sẽ bị xem là false.

### Câu 29. Allowlist có tự lowercase target trong file JSON không?

**Đáp án:**  
Không. Code chỉ lowercase `target` đầu vào. `load_allowed_targets()` lấy set từ JSON y nguyên. Vì vậy nên lưu allowlist bằng chữ thường để match ổn định.

### Câu 30. `validate_target()` kiểm tra những gì?

**Đáp án:**  
Nó strip và lowercase target, rồi kiểm tra:

- không rỗng
- không có whitespace
- không chứa `/` hoặc `\`
- độ dài không quá 253 ký tự

### Câu 31. `validate_target()` có kiểm tra domain thật sự tồn tại không?

**Đáp án:**  
Không. Nó chỉ kiểm tra format cơ bản. Việc tồn tại hay không được kiểm tra sau bằng `resolve_target()`.

### Câu 32. `parse_target("localhost:8000")` trả gì?

**Đáp án:**  
Trả `("localhost", [8000])`.

### Câu 33. `parse_target("localhost:")` lỗi gì?

**Đáp án:**  
Raise `ValueError("Target port is missing.")`.

### Câu 34. `parse_target("localhost:abc")` lỗi ở đâu?

**Đáp án:**  
Lỗi khi gọi `int(port_text)`, vì `"abc"` không phải số nguyên.

### Câu 35. `parse_target("http://localhost:8000/path")` có reject path không?

**Đáp án:**  
Không. Với URL có scheme, code dùng `urlparse()` lấy `hostname` và `port`, còn path bị bỏ qua. `validate_target()` chỉ nhận `"localhost"`, nên không thấy path.

### Câu 36. `validate_target("abc/def")` có pass không?

**Đáp án:**  
Không. Vì chuỗi có `/`, hàm raise `ValueError("Target must not contain a path.")`.

### Câu 37. `parse_ports("80,443,3000-3002")` trả gì?

**Đáp án:**  
Trả `[80, 443, 3000, 3001, 3002]`.

### Câu 38. `parse_ports("5-3")` trả gì?

**Đáp án:**  
Trả `[3, 4, 5]`. Code tự hoán đổi nếu `start_port > end_port`.

### Câu 39. `parse_ports("80,80,443")` trả gì?

**Đáp án:**  
Trả `[80, 443]` vì dùng `set` để loại trùng.

### Câu 40. `parse_ports("")` trả gì?

**Đáp án:**  
Trả list rỗng `[]`.

### Câu 41. Vì sao có `MAX_PORT_COUNT = 4096`?

**Đáp án:**  
Để giới hạn số port được parse, tránh tạo quá nhiều socket/thread khi demo và tránh scan quá rộng.

### Câu 42. `validate_port(0)` có pass không?

**Đáp án:**  
Không. Port hợp lệ từ 1 đến 65535.

### Câu 43. `validate_timeout(0)` có pass không?

**Đáp án:**  
Không. Timeout phải từ 0.01 đến 30 giây.

### Câu 44. `write_json()` có tạo thư mục cha không?

**Đáp án:**  
Có. Dòng `path.parent.mkdir(parents=True, exist_ok=True)` tạo thư mục cha trước khi ghi.

### Câu 45. `setup_logging(force=True)` có tác dụng gì?

**Đáp án:**  
`force=True` cấu hình lại logging kể cả khi trước đó đã có handler. Điều này giúp mỗi lần chạy pipeline ghi đúng file log mong muốn.

---

## D. Parallelism và lỗi bất đồng bộ

### Câu 46. Vì sao `futures` trong `run_recon_stage()` là dict?

**Đáp án:**  
Vì `as_completed()` chỉ trả future, không trả tên task. Dict giúp map future về `"port"`, `"dns"` hoặc `"banner"`.

### Câu 47. Nếu dùng list futures thì có vấn đề gì?

**Đáp án:**  
Khi future hoàn thành, khó biết kết quả thuộc tool nào để ghi vào file JSON tương ứng, trừ khi tự lưu metadata khác.

### Câu 48. `as_completed()` giúp gì khi DNS xong trước port scan?

**Đáp án:**  
DNS result được xử lý và ghi file ngay khi xong, không phải chờ port scan hoàn thành.

### Câu 49. Nếu `scan_ports()` raise exception trong worker thì exception xuất hiện ở đâu?

**Đáp án:**  
Exception xuất hiện khi gọi `future.result()` trong vòng `for future in as_completed(futures)`.

### Câu 50. Hiện tại `run_recon_stage()` có fallback nếu một tool lỗi không?

**Đáp án:**  
Không. Nếu một `future.result()` raise exception, pipeline sẽ dừng. Đây là điểm có thể cải tiến bằng try/except từng future.

### Câu 51. Khi một future lỗi, các future khác có bị hủy ngay không?

**Đáp án:**  
Không tự động hủy theo logic hiện tại. Khi thoát khỏi `with ThreadPoolExecutor`, executor sẽ shutdown và đợi các task đang chạy kết thúc trước khi exception lan ra.

### Câu 52. Vì sao port scanner cũng dùng `ThreadPoolExecutor` riêng?

**Đáp án:**  
Vì từng port có thể timeout. Chạy song song nhiều port giúp giảm thời gian chờ tổng.

### Câu 53. `max_workers` trong port scanner tính thế nào?

**Đáp án:**  
`max_workers = min(50, max(1, len(selected_ports)))`. Tối đa 50 worker, tối thiểu 1.

### Câu 54. Banner grabber có per-port parallelism giống port scanner không?

**Đáp án:**  
Có. `grab_banners()` submit `grab_banner()` cho từng port bằng `ThreadPoolExecutor`.

### Câu 55. Phần TLS trong `grab_banners()` có chạy trong cùng worker với `grab_banner()` không?

**Đáp án:**  
Không hoàn toàn. `grab_banner()` chạy trong worker, nhưng `inspect_tls()` được gọi sau khi `future.result()` trả về, trong vòng lặp xử lý kết quả. Vì vậy TLS check có thể làm thêm thời gian ở main thread.

### Câu 56. Nếu muốn TLS cũng song song đúng nghĩa, sửa hướng nào?

**Đáp án:**  
Có thể tạo hàm worker xử lý cả banner, service và TLS cho một port, rồi submit hàm đó cho từng port. Khi future xong thì lấy đầy đủ kết quả.

### Câu 57. Có cần lock khi thêm vào `open_ports` không?

**Đáp án:**  
Không cần trong code hiện tại, vì `open_ports.append(port)` diễn ra ở thread chính khi đọc `future.result()`, không phải trong worker.

### Câu 58. Vì sao output cần sort?

**Đáp án:**  
Do future hoàn thành không theo thứ tự port. Sort giúp JSON ổn định và dễ đọc.

---

## E. TCP Port Scanner

### Câu 59. `scan_port()` dùng kỹ thuật gì?

**Đáp án:**  
Dùng TCP connect scan qua `socket.create_connection((target, port), timeout=timeout)`.

### Câu 60. TCP connect scan khác SYN scan thế nào?

**Đáp án:**  
TCP connect scan hoàn tất kết nối TCP thông thường qua API socket. SYN scan chỉ gửi SYN và thường cần raw socket/quyền cao hơn. Code này không dùng SYN scan.

### Câu 61. `scan_port()` trả `True` khi nào?

**Đáp án:**  
Khi `socket.create_connection()` kết nối thành công đến target và port.

### Câu 62. Port đóng thường làm `scan_port()` trả gì?

**Đáp án:**  
Trả `False`, vì connect sẽ raise `OSError`, `ConnectionRefusedError` hoặc timeout.

### Câu 63. `scan_port()` có biết service phía sau là gì không?

**Đáp án:**  
Không. Nó chỉ biết port connect được hay không. Service được đoán ở `banner_grabber.py`.

### Câu 64. `scan_ports()` có dedupe input programmatic không?

**Đáp án:**  
Không. Nếu caller truyền trực tiếp `[80, 80]`, `selected_ports` vẫn là `[80, 80]`. Việc dedupe chỉ có trong `parse_ports()` khi parse chuỗi CLI.

### Câu 65. Nếu `scan_ports(target, [])` thì scan gì?

**Đáp án:**  
Vì code dùng `(ports or DEFAULT_PORTS)`, list rỗng bị xem là false, nên sẽ scan `DEFAULT_PORTS`.

### Câu 66. `DEFAULT_PORTS` có port 3000 không?

**Đáp án:**  
Không. `DEFAULT_PORTS` hiện có 16 port, gồm 21, 22, 23, 25, 53, 80, 110, 139, 143, 443, 445, 3306, 5432, 6379, 8000, 8080.

### Câu 67. Vì sao port 6379 được xem đáng chú ý?

**Đáp án:**  
6379 thường là Redis. Trong risk config, nó nằm trong `SENSITIVE_PORTS`, `HIGH_RISK_PORTS` và `DATABASE_CACHE_PORTS`, nên nếu mở sẽ làm risk tăng.

### Câu 68. Scanner có gửi payload vào service không?

**Đáp án:**  
Không. Port scanner chỉ connect TCP rồi đóng, không gửi payload.

### Câu 69. Scanner có phân biệt `closed` và `filtered` không?

**Đáp án:**  
Không. Với code hiện tại, mọi lỗi hoặc timeout đều được xem là không open, trả `False`.

### Câu 70. CLI của `port_scanner.py` có tham số `--timeout` không?

**Đáp án:**  
Không. CLI riêng của port scanner chỉ có `--target` và `--ports`. Timeout dùng default trong `scan_ports()` là 0.5 giây.

### Câu 71. Nếu muốn CLI port scanner có `--timeout`, thêm ở đâu?

**Đáp án:**  
Thêm trong `main()` của `.pi/tools/recon/port_scanner.py`:

```python
parser.add_argument("--timeout", type=float, default=0.5)
result = scan_ports(args.target, custom_ports, args.timeout)
```

### Câu 72. `scan_ports()` trả những field nào?

**Đáp án:**  
Trả:

- `target`
- `scanned_ports`
- `open_ports`
- `open_count`

### Câu 73. Nếu muốn thêm `closed_count`, công thức là gì?

**Đáp án:**  
`closed_count = len(selected_ports) - len(open_ports)`.

### Câu 74. Port scanner có tự ghi JSON không?

**Đáp án:**  
Hàm `scan_ports()` không tự ghi JSON. Trong pipeline, `run_recon_stage()` mới gọi `write_json(port_path, port_result)`. CLI riêng chỉ print JSON ra màn hình.

---

## F. DNS Enumeration

### Câu 75. `enumerate_dns()` xử lý localhost thế nào?

**Đáp án:**  
Nếu target là `localhost`, `127.0.0.1` hoặc `::1`, hàm trả `skipped=True`, message `"DNS enumeration skipped for localhost target"` và không import `dnspython`.

### Câu 76. Vì sao localhost được skip trước khi import `dns.resolver`?

**Đáp án:**  
Vì localhost không cần DNS public. Skip sớm giúp demo local vẫn chạy ngay cả khi chưa cài `dnspython`.

### Câu 77. Nếu `dnspython` chưa cài và target không phải localhost thì sao?

**Đáp án:**  
Hàm trả:

```json
{
  "skipped": true,
  "message": "dnspython is not installed",
  "records": {},
  "errors": {}
}
```

### Câu 78. IP address được xử lý khác domain thế nào?

**Đáp án:**  
IP address chỉ query reverse DNS PTR bằng `resolver.resolve_address(domain)`. Domain thì query các record trong `DNS_RECORD_TYPES`.

### Câu 79. `is_ip_address()` có hỗ trợ IPv6 không?

**Đáp án:**  
Có. Nó dùng `ipaddress.ip_address(target)`, hỗ trợ cả IPv4 và IPv6.

### Câu 80. `DNS_RECORD_TYPES` hiện gồm những gì?

**Đáp án:**  
`["A", "CNAME", "MX", "NS", "SOA", "TXT"]`.

### Câu 81. Nếu domain không có MX record thì tool có fail không?

**Đáp án:**  
Không. MX được set thành list rỗng và lỗi được ghi vào `errors["MX"]`. Các record khác vẫn chạy.

### Câu 82. Vì sao mỗi record type có try/except riêng?

**Đáp án:**  
Để lỗi ở một loại record không làm hỏng toàn bộ DNS enum.

### Câu 83. `_format_answer()` xử lý MX thế nào?

**Đáp án:**  
MX được format thành `"preference exchange"`, ví dụ `"10 mail.example.com"`.

### Câu 84. `_format_answer()` xử lý TXT thế nào?

**Đáp án:**  
TXT gồm các bytes string, nên code decode từng phần bằng UTF-8 với `errors="replace"` rồi join bằng khoảng trắng.

### Câu 85. SOA và CAA nếu thêm vào thì format theo nhánh nào?

**Đáp án:**  
Nếu không viết nhánh riêng, chúng đi vào fallback `str(answer).rstrip(".")`.

### Câu 86. `enumerate_dns()` có gọi `validate_timeout()` không?

**Đáp án:**  
Không. Trong pipeline, timeout đã được validate ở `run_pipeline()`. Nếu gọi `enumerate_dns()` trực tiếp, timeout không được validate bởi hàm này.

### Câu 87. Resolver dùng DNS server nào?

**Đáp án:**  
Code dùng `dns.resolver.Resolver()` mặc định, tức là theo cấu hình DNS của hệ thống.

### Câu 88. Nếu mọi record của domain đều lỗi, `skipped` là gì?

**Đáp án:**  
Vẫn là `False`, vì tool đã thực sự thử query DNS. Lỗi nằm trong dict `errors`.

### Câu 89. DNS enum có brute force subdomain không?

**Đáp án:**  
Không. Nó chỉ query các record cố định của target.

### Câu 90. DNS output nào được risk stage dùng?

**Đáp án:**  
Risk stage dùng `dns_result["records"]` để đếm `dns_record_count`, dùng DNS record để tạo MITRE mapping nếu có evidence.

---

## G. Banner Grabber và TLS

### Câu 91. HTTP port trong `banner_grabber.py` gồm những port nào?

**Đáp án:**  
`HTTP_PORTS = {80, 3000, 8000, 8080}`.

### Câu 92. TLS port trong `banner_grabber.py` gồm những port nào?

**Đáp án:**  
`TLS_PORTS = {443, 465, 636, 993, 995, 8443}`.

### Câu 93. HTTP port được gửi request gì?

**Đáp án:**  
Gửi:

```http
HEAD / HTTP/1.1
Host: {target}
Connection: close
```

### Câu 94. Vì sao HTTP cần gửi HEAD?

**Đáp án:**  
HTTP server thường chờ client gửi request trước. Nếu chỉ connect rồi recv, có thể không nhận được gì.

### Câu 95. Vì sao dùng HEAD thay vì GET?

**Đáp án:**  
HEAD chỉ lấy header, nhẹ hơn GET vì không cần body. Mục tiêu là đọc banner/header.

### Câu 96. `_clean_banner()` làm gì?

**Đáp án:**  
Decode bytes bằng UTF-8, thay ký tự lỗi bằng replacement, `strip()`, nếu rỗng trả `"No banner"`, nếu có thì cắt tối đa 500 ký tự.

### Câu 97. Nếu port không mở thì `grab_banner()` trả gì?

**Đáp án:**  
Trả `"No banner"` vì outer `except OSError` bắt lỗi connect.

### Câu 98. Nếu service mở nhưng không tự gửi banner thì sao?

**Đáp án:**  
Nếu không phải HTTP port và service không gửi banner trước, `recv()` có thể timeout và trả `"No banner"`.

### Câu 99. Port 443 có được gửi HEAD thường không?

**Đáp án:**  
Không. 443 nằm trong `TLS_PORTS`, nhưng không nằm trong `HTTP_PORTS`. `grab_banner()` không gửi HTTPS request qua TLS, mà `inspect_tls()` chỉ lấy metadata TLS riêng.

### Câu 100. `inspect_tls()` lấy những field nào?

**Đáp án:**  
Lấy `protocol`, `cipher`, `subject`, `issuer`, `not_after`.

### Câu 101. Vì sao `context.verify_mode = ssl.CERT_NONE`?

**Đáp án:**  
Vì mục tiêu là đọc metadata công khai trong lab/demo, không xác thực trust chain. Self-signed certificate vẫn có thể được inspect.

### Câu 102. `inspect_tls()` có chạy với port 9443 không?

**Đáp án:**  
Không, vì 9443 không nằm trong `TLS_PORTS`.

### Câu 103. `identify_service()` ưu tiên gì trước?

**Đáp án:**  
Ưu tiên marker trong banner như `ssh-`, `smtp`, `mysql`, `postgresql`, `redis`, `http/`. Nếu không thấy marker thì fallback theo `SERVICE_BY_PORT`.

### Câu 104. Câu bẫy: port 3000 nếu không có banner thì service là gì?

**Đáp án:**  
Là `"unknown"`. Port 3000 nằm trong `HTTP_PORTS` nên được gửi HEAD, nhưng không có trong `SERVICE_BY_PORT` của `banner_grabber.py`.

### Câu 105. `SERVICE_BY_PORT` trong banner grabber có giống `risk_config.SERVICE_NAMES` không?

**Đáp án:**  
Không hoàn toàn. Ví dụ `risk_config.SERVICE_NAMES` có port 3000 là `"HTTP-dev"`, còn `banner_grabber.SERVICE_BY_PORT` không có 3000.

### Câu 106. `grab_banners()` trả key port dạng số hay chuỗi?

**Đáp án:**  
Trong `banners`, `services`, `tls`, key port là chuỗi như `"8000"`. `attempted_ports` vẫn là list số nguyên.

### Câu 107. `grab_banners(target, [])` trả gì?

**Đáp án:**  
Trả output hợp lệ với `attempted_ports=[]`, `banners={}`, `services={}`, `tls={}`. Executor có `max_workers=1` nhưng không có future nào.

### Câu 108. CLI riêng của `banner_grabber.py` nếu không truyền `--ports` thì sao?

**Đáp án:**  
`parse_ports("")` trả `[]`, nên `grab_banners()` không thử port nào. Đây là điểm có thể cải tiến bằng fallback `DEFAULT_PORTS`.

### Câu 109. Banner grabber CLI hiện có `--timeout` không?

**Đáp án:**  
Không. CLI chỉ có `--target` và `--ports`; timeout dùng default 1.0 trong `grab_banners()`.

### Câu 110. Banner dài có làm report quá dài không?

**Đáp án:**  
Được hạn chế. `_clean_banner()` cắt banner còn tối đa 500 ký tự.

---

## H. Handoff sang risk scoring và report

### Câu 111. Stage 2 dùng 3 dict recon hay đọc lại JSON?

**Đáp án:**  
Trong `main_pipeline.py`, `run_risk_stage()` nhận trực tiếp 3 dict từ Stage 1. Còn hàm `score_risk_from_files()` trong `risk_scorer.py` là đường chạy riêng để đọc lại JSON từ file.

### Câu 112. `score_risk()` chọn target từ đâu?

**Đáp án:**  
Chọn theo thứ tự:

```python
port_result.get("target") or dns_result.get("target") or banner_result.get("target")
```

### Câu 113. `open_ports` được ép kiểu gì trong risk scorer?

**Đáp án:**  
Được ép sang int:

```python
open_ports = [int(port) for port in port_result.get("open_ports", [])]
```

### Câu 114. `extract_features()` tạo những feature nào?

**Đáp án:**  
Tạo:

- `open_port_count`
- `sensitive_port_count`
- `high_risk_port_count`
- `database_cache_port_count`
- `http_port_count`
- `version_banner_count`
- `dns_record_count`

### Câu 115. Banner `"No banner"` có tính là version leak không?

**Đáp án:**  
Không. `banner_has_version()` trả `False` nếu banner rỗng hoặc bằng `"No banner"`.

### Câu 116. Nếu banner có `OpenSSH_8.9` thì feature nào tăng?

**Đáp án:**  
`version_banner_count` tăng vì regex trong `BANNER_VERSION_PATTERNS` match OpenSSH version.

### Câu 117. Risk stage có dùng `closed_count` không?

**Đáp án:**  
Không. Hiện tại feature chỉ dùng open ports, DNS record count và version banners.

### Câu 118. `classify_target_exposure("localhost")` trả gì?

**Đáp án:**  
Trả `"local"`.

### Câu 119. `classify_target_exposure("192.168.1.10")` trả gì?

**Đáp án:**  
Trả `"private"` vì là private IP.

### Câu 120. Hostname public như `scanme.nmap.org` được classify thế nào?

**Đáp án:**  
Trả `"public"` vì không parse được thành IP và không phải `localhost`.

### Câu 121. Khi nào `exposure_adjustment` cộng 1 điểm?

**Đáp án:**  
Khi target exposure là `"public"` và có ít nhất một open port.

### Câu 122. `label_from_score()` chia mức risk thế nào?

**Đáp án:**  
Score <= 3 là `Low`, <= 6 là `Medium`, còn lại là `High`.

### Câu 123. Nếu muốn thêm port MongoDB 27017 vào risk đúng nghĩa, sửa mấy nơi?

**Đáp án:**  
Ít nhất sửa:

- `DEFAULT_PORTS` trong `port_scanner.py` nếu muốn scan mặc định.
- `SERVICE_NAMES` trong `risk_config.py` để report gọi tên MongoDB.
- `DATABASE_CACHE_PORTS` hoặc `SENSITIVE_PORTS` nếu muốn ảnh hưởng risk score.
- `SERVICE_BY_PORT` trong `banner_grabber.py` nếu muốn đoán service.

### Câu 124. Report offline được dùng khi nào?

**Đáp án:**  
Khi `offline=True`, hoặc không có `OPENAI_API_KEY`, hoặc key bằng placeholder `"your_api_key_here"`, hoặc API lỗi.

### Câu 125. Report có được phép chứa exploit step không?

**Đáp án:**  
Không. Prompt và template đều nhấn mạnh chỉ đưa quan sát và khuyến nghị phòng thủ, không exploit, không brute force, không bypass.

---

## I. Agent, chain, UDP scanner và debug

### Câu 126. File `.pi/agents/*.md` có chạy code không?

**Đáp án:**  
Không. Chúng là tài liệu mô tả vai trò agent, input, action, output, handoff và safety rule.

### Câu 127. `orchestrator_agent.md` có handoff contract gì quan trọng?

**Đáp án:**  
Không gọi Stage 1 nếu permission gate chặn, không gọi risk scoring nếu thiếu 1 trong 3 JSON recon, không gọi report nếu thiếu `risk_profile.json`.

### Câu 128. `recon_risk_pipeline.chain.md` mô tả parallelism bằng ký hiệu gì?

**Đáp án:**  
Dùng block:

```text
/parallel
  port_scan_agent(...)
  dns_enum_agent(...)
  banner_grab_agent(...)
/join
```

### Câu 129. `pi_recon_agent.py` khác `main_pipeline.py` thế nào?

**Đáp án:**  
`main_pipeline.py` là pipeline deterministic, chạy offline ổn định. `pi_recon_agent.py` là Week 5 agentic runner, để LLM chọn tool qua OpenAI tool calling nhưng vẫn dùng safety wrapper trong code.

### Câu 130. Agentic runner có rate limit tool không?

**Đáp án:**  
Có. `ToolRuntime._check_rate_limit()` giới hạn mặc định 6 lần gọi mỗi tool trong 60 giây.

### Câu 131. Agentic runner có Safety Gate trong runtime không?

**Đáp án:**  
Có. Mỗi tool runtime gọi `_check_target()`, dùng `is_target_allowed(target, self.authorized)` để chặn target ngoài scope.

### Câu 132. `_execute_tool_batch()` trong agentic runner chạy tool calls thế nào?

**Đáp án:**  
Nó dùng `ThreadPoolExecutor(max_workers=max(1, len(tool_calls)))` để chạy các tool call cùng batch song song.

### Câu 133. UDP scanner có nằm trong pipeline chính không?

**Đáp án:**  
Không. UDP scanner là utility phụ trong `.pi/tools/recon/udp_scanner.py` và wrapper `.pi/tools/udp_scanner.py`.

### Câu 134. UDP scanner trả `"open_or_filtered"` nghĩa là gì?

**Đáp án:**  
UDP timeout không chứng minh port open hay bị firewall lọc. Vì vậy code ghi `"open_or_filtered"`.

### Câu 135. UDP scanner dùng socket type gì?

**Đáp án:**  
Dùng `socket.SOCK_DGRAM`, khác TCP scanner dùng kết nối TCP stream.

### Câu 136. `manage_targets.py` dùng để làm gì?

**Đáp án:**  
Dùng để list, add, remove target trong `.pi/data/allowed_targets.json`. Chỉ nên thêm target mình có quyền scan.

### Câu 137. Nếu port 8000 không open khi demo, kiểm tra gì trước?

**Đáp án:**  
Kiểm tra đã chạy HTTP server chưa:

```powershell
python -m http.server 8000 --bind 127.0.0.1
```

### Câu 138. Nếu DNS enum báo lỗi nhiều record thì có phải pipeline hỏng không?

**Đáp án:**  
Không nhất thiết. Domain có thể không có một số record. Tool ghi lỗi theo từng record trong `errors`.

### Câu 139. Nếu report vẫn tạo khi không có API key, vì sao?

**Đáp án:**  
Vì `generate_report()` có offline fallback bằng `build_offline_report()`.

### Câu 140. Nếu `.pi/triage` chưa tồn tại thì JSON có ghi được không?

**Đáp án:**  
Có trong pipeline, vì `ensure_output_dirs()` tạo `.pi/triage`. Ngoài ra `write_json()` cũng tự tạo thư mục cha của path cần ghi.

---

## J. Bài code tay kèm đáp án mẫu

### Câu 141. Thêm `closed_count` vào port scan result.

**Đáp án mẫu:**  
Trong `.pi/tools/recon/port_scanner.py`, sửa dict return:

```python
return {
    "target": target,
    "scanned_ports": selected_ports,
    "open_ports": sorted(open_ports),
    "open_count": len(open_ports),
    "closed_count": len(selected_ports) - len(open_ports),
}
```

### Câu 142. Dedupe ports nếu caller truyền list trực tiếp cho `scan_ports()`.

**Đáp án mẫu:**  
Sửa dòng chọn port:

```python
selected_ports = sorted({validate_port(int(port)) for port in (ports or DEFAULT_PORTS)})
```

Giải thích: tránh scan trùng khi caller không đi qua `parse_ports()`.

### Câu 143. Thêm `--timeout` cho CLI port scanner.

**Đáp án mẫu:**  
Trong `main()` của `port_scanner.py`:

```python
parser.add_argument("--timeout", type=float, default=0.5)
result = scan_ports(args.target, custom_ports, args.timeout)
```

### Câu 144. Thêm fallback default ports cho CLI banner grabber.

**Đáp án mẫu:**  
Trong `banner_grabber.py`, import:

```python
from recon.port_scanner import DEFAULT_PORTS
```

Trong `main()`:

```python
ports = parse_ports(args.ports) if args.ports else DEFAULT_PORTS
```

### Câu 145. Thêm `--timeout` cho CLI banner grabber.

**Đáp án mẫu:**  
Trong `main()`:

```python
parser.add_argument("--timeout", type=float, default=1.0)
result = grab_banners(args.target, ports, args.timeout)
```

### Câu 146. Sửa port 3000 để fallback service không còn `"unknown"`.

**Đáp án mẫu:**  
Thêm vào `SERVICE_BY_PORT` trong `banner_grabber.py`:

```python
3000: "http",
```

### Câu 147. Thêm CAA record vào DNS enum.

**Đáp án mẫu:**  
Trong `dns_enum.py`:

```python
DNS_RECORD_TYPES = ["A", "CNAME", "MX", "NS", "SOA", "TXT", "CAA"]
```

### Câu 148. Thêm validate timeout khi gọi DNS enum trực tiếp.

**Đáp án mẫu:**  
Import:

```python
from common.tool_utils import validate_timeout
```

Trong `enumerate_dns()`:

```python
timeout = validate_timeout(timeout)
```

Nếu chạy file trực tiếp, cần thêm `sys.path` giống các recon tool khác để import được `common`.

### Câu 149. Log rõ target bị block trong `main_pipeline.py`.

**Đáp án mẫu:**  
Sửa dòng logging:

```python
logging.warning("Permission gate blocked target=%s: %s", target, message)
```

### Câu 150. Normalize allowlist thành lowercase khi load.

**Đáp án mẫu:**  
Trong `load_allowed_targets()`:

```python
targets = {str(item).lower() for item in config.get("allowed_targets", [])}
```

Giải thích: tránh lỗi khi JSON có target viết hoa.

### Câu 151. Thêm field `stage` vào output port scanner.

**Đáp án mẫu:**  
Trong dict return của `scan_ports()`:

```python
"stage": "recon",
"tool": "port_scanner",
```

### Câu 152. Thêm field `stage` vào DNS enum output.

**Đáp án mẫu:**  
Thêm vào mọi nhánh return của `enumerate_dns()`:

```python
"stage": "recon",
"tool": "dns_enum",
```

### Câu 153. Thêm field `stage` vào banner grabber output.

**Đáp án mẫu:**  
Trong dict return của `grab_banners()`:

```python
"stage": "recon",
"tool": "banner_grabber",
```

### Câu 154. Bắt lỗi từng future trong `run_recon_stage()` để ghi lỗi rõ hơn.

**Đáp án mẫu:**  
Ý tưởng:

```python
try:
    result = future.result()
except Exception as exc:
    logging.exception("Recon task failed: %s", task_name)
    result = {"target": target, "error": str(exc)}
```

Sau đó gán `result` vào đúng `port_result`, `dns_result` hoặc `banner_result`.

### Câu 155. Thêm elapsed time cho port scanner.

**Đáp án mẫu:**  
Import `time`, đo trước và sau:

```python
started = time.perf_counter()
...
"duration_seconds": round(time.perf_counter() - started, 4),
```

### Câu 156. Thêm MongoDB 27017 vào scan và risk.

**Đáp án mẫu:**  
Sửa nhiều nơi:

```python
# port_scanner.py
DEFAULT_PORTS = [..., 27017]

# risk_config.py
SERVICE_NAMES[27017] = "MongoDB"
DATABASE_CACHE_PORTS.add(27017)
SENSITIVE_PORTS.add(27017)

# banner_grabber.py
SERVICE_BY_PORT[27017] = "mongodb"
```

### Câu 157. Nếu không muốn `parse_ports("5-3")` tự đảo chiều, sửa thế nào?

**Đáp án mẫu:**  
Thay đoạn swap bằng raise:

```python
if start_port > end_port:
    raise ValueError("Port range start must be <= end.")
```

### Câu 158. Thêm giới hạn số candidate ports trong `grab_banners()` khi gọi programmatic.

**Đáp án mẫu:**  
Import `MAX_PORT_COUNT` rồi kiểm tra:

```python
if len(attempted_ports) > MAX_PORT_COUNT:
    raise ValueError(f"Port list cannot contain more than {MAX_PORT_COUNT} ports.")
```

### Câu 159. Thêm support port HTTPS dev 9443 vào TLS inspect.

**Đáp án mẫu:**  
Trong `banner_grabber.py`:

```python
TLS_PORTS = {443, 465, 636, 993, 995, 8443, 9443}
SERVICE_BY_PORT[9443] = "https"
```

### Câu 160. Nếu muốn thêm UDP scanner vào pipeline chính, cần lưu ý gì?

**Đáp án mẫu:**  
Không chỉ gọi thêm `scan_udp_ports()`. Cần cập nhật:

- Safety Gate vẫn phải chạy trước.
- Stage 1 có thể thêm future UDP nếu scope cho phép.
- Ghi thêm JSON riêng, ví dụ `.pi/triage/udp_scan_result.json`.
- Risk feature và report phải biết đọc UDP result.
- Cần giải thích rõ UDP timeout chỉ là `open_or_filtered`, không khẳng định open.

---

## K. 20 câu trả lời chớp nhoáng

1. Safety Gate nằm ở đâu?  
   **Đáp án:** `is_target_allowed()` trong `tool_utils.py`.

2. Stage 1 nằm ở hàm nào?  
   **Đáp án:** `run_recon_stage()` trong `main_pipeline.py`.

3. Stage 1 ghi mấy file JSON?  
   **Đáp án:** 3 file.

4. DNS localhost có query không?  
   **Đáp án:** Không, trả `skipped=True`.

5. IP target DNS enum query gì?  
   **Đáp án:** PTR reverse DNS.

6. HTTP banner dùng method gì?  
   **Đáp án:** HEAD.

7. Banner rỗng trả gì?  
   **Đáp án:** `"No banner"`.

8. Port scanner có exploit không?  
   **Đáp án:** Không.

9. `MAX_PORT_COUNT` là bao nhiêu?  
   **Đáp án:** 4096.

10. Timeout hợp lệ từ bao nhiêu đến bao nhiêu?  
    **Đáp án:** 0.01 đến 30 giây.

11. Port hợp lệ từ bao nhiêu đến bao nhiêu?  
    **Đáp án:** 1 đến 65535.

12. Report offline nằm ở đâu?  
    **Đáp án:** `.pi/results/ket_qua.md`.

13. Risk profile nằm ở đâu?  
    **Đáp án:** `.pi/triage/risk_profile.json`.

14. `scan_ports()` tự ghi JSON không?  
    **Đáp án:** Không.

15. `run_recon_stage()` dùng bao nhiêu worker?  
    **Đáp án:** 3 worker.

16. Port scanner worker tối đa bao nhiêu?  
    **Đáp án:** 50 worker.

17. Banner grabber worker tối đa bao nhiêu?  
    **Đáp án:** 50 worker.

18. `--authorized` có tác dụng gì?  
    **Đáp án:** Bypass allowlist khi người dùng xác nhận có quyền.

19. Target public bất kỳ có được scan mặc định không?  
    **Đáp án:** Không, chỉ public target trong allowlist lab hoặc có `--authorized`.

20. Stage 2/3 có phải phần chính của Thông không?  
    **Đáp án:** Không, nhưng cần hiểu handoff vì chúng dùng output của Stage 1.
