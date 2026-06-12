# Vũ Văn Thông - Bộ ôn vấn đáp, code tay và debug

> File này dành riêng cho **Vũ Văn Thông - MSSV 23162098**.  
> Phạm vi chính: thiết kế pipeline, Safety Gate, port scanner, DNS enum, banner grabber và kiểm thử phase recon.

## 1. Phần em phụ trách

| Nhóm việc | Nội dung em cần nắm |
|---|---|
| Pipeline chính | Luồng Stage 0 -> Stage 1 -> Stage 2 -> Stage 3 trong `main_pipeline.py` |
| Safety Gate | Kiểm tra target bằng allowlist hoặc `--authorized` |
| Port scanner | TCP connect scan bằng socket, per-port parallelism |
| DNS enum | Query A, CNAME, MX, NS, SOA, TXT; skip localhost; IP thì PTR |
| Banner grabber | Kết nối TCP, gửi HEAD request cho HTTP, đọc banner, đoán service, đọc TLS metadata |
| Kiểm thử recon | Chạy pipeline local, kiểm tra JSON trong `.pi/triage` |

## 2. File em phải mở được khi thầy hỏi

- `.pi/tools/main_pipeline.py`
- `.pi/tools/common/tool_utils.py`
- `.pi/tools/recon/port_scanner.py`
- `.pi/tools/recon/dns_enum.py`
- `.pi/tools/recon/banner_grabber.py`
- `.pi/data/allowed_targets.json`
- `.pi/agents/orchestrator_agent.md`
- `.pi/agents/permission_gate_agent.md`
- `.pi/agents/port_scan_agent.md`
- `.pi/agents/dns_enum_agent.md`
- `.pi/agents/banner_grab_agent.md`
- `.pi/chains/recon_risk_pipeline.chain.md`
- `.pi/skills/recon/SKILL.md`

## 3. Tóm tắt 60 giây khi thầy hỏi em làm gì

Em phụ trách phần đầu của pipeline. Cụ thể, em thiết kế luồng chạy chính trong
`main_pipeline.py`, xây dựng Safety Gate để chặn target không nằm trong allowlist
hoặc không có `--authorized`, sau đó cài đặt 3 tool recon gồm port scanner, DNS
enumeration và banner grabber. Stage 1 chạy song song 3 tool này bằng
`ThreadPoolExecutor(max_workers=3)`. Mỗi tool ghi kết quả JSON riêng vào
`.pi/triage`, sau đó kết quả được chuyển sang phần risk scoring và report.

## 4. Câu hỏi vấn đáp tổng quan dành cho em

### Câu 1. Pipeline của project chạy như thế nào?

**Trả lời:**  
Pipeline có 4 stage. Stage 0 là Safety Gate. Stage 1 là Parallel Recon gồm port
scan, DNS enum, banner grab. Stage 2 là ML Risk Scoring. Stage 3 là Report
Generation. Stage 1 chạy song song, các stage còn lại chạy tuần tự.

**File cần mở:** `.pi/tools/main_pipeline.py`

### Câu 2. Stage nào là phần em thiết kế quan trọng nhất?

**Trả lời:**  
Stage 1 là phần quan trọng nhất của em vì đây là nơi thể hiện yêu cầu parallelism
của đề tài. Trong `run_recon_stage()`, em dùng `ThreadPoolExecutor(max_workers=3)`
để chạy đồng thời `scan_ports`, `enumerate_dns` và `grab_banners`.

**File cần mở:** `.pi/tools/main_pipeline.py`

### Câu 3. Vì sao Stage 1 chạy song song được?

**Trả lời:**  
Vì 3 tác vụ không phụ thuộc dữ liệu lẫn nhau. DNS enum không cần biết port nào
mở. Banner grab có thể thử trên danh sách candidate ports mà không cần chờ port
scanner. Do đó chạy song song giúp giảm thời gian chạy.

### Câu 4. Vì sao Stage 2 và Stage 3 không chạy song song?

**Trả lời:**  
Stage 2 cần output của Stage 1, gồm 3 file JSON recon. Stage 3 cần
`risk_profile.json` của Stage 2. Vì có dependency nên phải chạy tuần tự.

### Câu 5. Output chính của phần em là gì?

**Trả lời:**  
Phần em tạo ra 3 file:

- `.pi/triage/port_scan_result.json`
- `.pi/triage/dns_enum_result.json`
- `.pi/triage/banner_result.json`

Các file này là input cho risk scoring.

## 5. Câu hỏi về `main_pipeline.py`

### Câu 6. `run_recon_stage()` làm gì?

**Trả lời:**  
Hàm này chạy song song 3 tool recon. Nó tạo 3 future cho port scan, DNS enum và
banner grab. Khi future nào xong trước thì dùng `as_completed()` để lấy kết quả,
ghi đúng file JSON tương ứng rồi trả về 3 dict kết quả.

### Câu 7. Vì sao dùng dict `futures = {future: "port"}`?

**Trả lời:**  
Vì `as_completed()` trả future theo thứ tự hoàn thành, không theo thứ tự submit.
Dict này giúp biết future nào thuộc task nào để ghi đúng file output.

### Câu 8. `as_completed()` khác gì vòng lặp bình thường?

**Trả lời:**  
Nếu lặp theo thứ tự submit, task chậm có thể làm task nhanh phải chờ. `as_completed()`
cho phép task nào hoàn thành trước thì xử lý trước.

### Câu 9. Safety Gate nằm ở đâu trong `run_pipeline()`?

**Trả lời:**  
Sau khi setup output/log/env và validate timeout, code gọi:

```python
if not is_target_allowed(target, authorized):
    raise PermissionError(message)
```

Nó chạy trước `resolve_target()` và trước mọi network recon.

### Câu 10. Vì sao Safety Gate phải chạy trước `resolve_target()`?

**Trả lời:**  
Vì `resolve_target()` đã là hoạt động mạng/DNS lookup. Nếu target chưa được phép,
pipeline phải dừng trước để đảm bảo an toàn.

## 6. Câu hỏi về `tool_utils.py`

### Câu 11. `is_target_allowed()` hoạt động thế nào?

**Trả lời:**  
Hàm trả `True` nếu user truyền `--authorized` hoặc target nằm trong
`allowed_targets.json`. Nếu không thì trả `False`.

```python
def is_target_allowed(target: str, authorized: bool) -> bool:
    return authorized or target.lower() in load_allowed_targets()
```

### Câu 12. Vì sao allowlist có target public?

**Trả lời:**  
Allowlist có 2 nhóm: local loopback để demo offline và public classroom/lab
target như `scanme.nmap.org`, `pentest-ground.com`, `vulnweb.com`. Đây là target
được dùng cho lab/demo, không phải mọi website public đều được phép scan.

### Câu 13. `parse_target()` xử lý những dạng target nào?

**Trả lời:**  
Hàm xử lý URL có scheme như `http://example.com:8080`, xử lý dạng `host:port`,
hoặc hostname/IP thường. Sau đó validate host và port.

### Câu 14. `parse_ports()` xử lý `"80,443,8000"` và `"1-1000"` thế nào?

**Trả lời:**  
Nếu là danh sách, hàm tách bằng dấu phẩy. Nếu có dấu `-`, hàm hiểu là range,
validate start/end rồi thêm toàn bộ range vào set để tránh trùng.

### Câu 15. Vì sao có `MAX_PORT_COUNT = 4096`?

**Trả lời:**  
Để tránh user nhập range quá lớn làm chương trình tạo quá nhiều socket/thread,
không phù hợp demo và có thể gây tải không cần thiết.

### Câu 16. `validate_timeout()` để làm gì?

**Trả lời:**  
Để timeout nằm trong khoảng 0.01 đến 30 giây. Nếu timeout quá lớn, pipeline dễ
treo lâu. Nếu quá nhỏ, kết quả có thể không ổn định.

## 7. Câu hỏi về `port_scanner.py`

### Câu 17. `scan_port()` dùng kỹ thuật scan gì?

**Trả lời:**  
Dùng TCP connect scan. Code thử mở kết nối TCP đến target và port bằng
`socket.create_connection()`. Nếu connect được thì port open.

### Câu 18. Vì sao bắt `OSError` và `socket.timeout`?

**Trả lời:**  
Khi port đóng, host unreachable hoặc timeout, socket sẽ ném lỗi. Với scanner đơn
giản, các trường hợp đó được xem là port không open.

### Câu 19. `scan_ports()` song song ở đâu?

**Trả lời:**  
Trong `scan_ports()`, mỗi port được submit vào `ThreadPoolExecutor`. Đây là
per-port parallelism, khác với inter-agent parallelism trong `main_pipeline.py`.

### Câu 20. Có cần lock khi append `open_ports` không?

**Trả lời:**  
Không cần, vì append vào `open_ports` xảy ra trong main thread khi lấy
`future.result()`, không append trực tiếp từ worker thread.

### Câu 21. Vì sao kết quả `open_ports` được sort?

**Trả lời:**  
Vì các future hoàn thành không theo thứ tự port. Sort giúp output dễ đọc và ổn
định khi report.

## 8. Câu hỏi về `dns_enum.py`

### Câu 22. Vì sao localhost thì skip DNS enum?

**Trả lời:**  
Localhost là target demo local, không cần query DNS record công khai. Vì vậy code
trả `skipped=True` để pipeline vẫn chạy bình thường.

### Câu 23. Vì sao IP thì query PTR?

**Trả lời:**  
IP không có A/MX/NS/TXT như domain. Với IP, DNS enum phù hợp nhất là reverse DNS
PTR để xem IP có hostname ngược hay không.

### Câu 24. Domain thì query record nào?

**Trả lời:**  
Code query A, CNAME, MX, NS, SOA, TXT.

### Câu 25. Vì sao mỗi record có try/except riêng?

**Trả lời:**  
Để một record lỗi không làm hỏng toàn bộ DNS enum. Ví dụ domain không có MX thì
MX ghi `[]` và lỗi vào `errors`, các record khác vẫn chạy.

### Câu 26. `_format_answer()` xử lý MX và TXT khác gì?

**Trả lời:**  
MX có `preference` và `exchange`, nên format thành `"priority mailserver"`.
TXT là bytes string nên phải decode từng phần rồi join lại.

## 9. Câu hỏi về `banner_grabber.py`

### Câu 27. Vì sao HTTP port phải gửi HEAD request?

**Trả lời:**  
HTTP server thường không tự gửi banner. Client phải gửi request. HEAD lấy header
nhẹ hơn GET vì không lấy body.

### Câu 28. `Connection: close` có ý nghĩa gì?

**Trả lời:**  
Báo server đóng kết nối sau khi trả response, tránh giữ connection không cần
thiết.

### Câu 29. Nếu không nhận được banner thì sao?

**Trả lời:**  
Nếu socket timeout hoặc lỗi, hàm trả `"No banner"`. Tool không retry mạnh để giữ
demo an toàn và nhẹ.

### Câu 30. `inspect_tls()` làm gì?

**Trả lời:**  
Nếu port thuộc TLS ports, hàm thử bắt tay TLS và đọc metadata công khai của
certificate như protocol, cipher, subject, issuer, not_after.

### Câu 31. Vì sao `verify_mode = ssl.CERT_NONE`?

**Trả lời:**  
Vì mục tiêu chỉ là đọc metadata công khai, không xác thực trust. Lab/local có thể
dùng self-signed certificate nên verify có thể fail.

### Câu 32. `identify_service()` đoán service thế nào?

**Trả lời:**  
Nó ưu tiên marker trong banner như `ssh-`, `mysql`, `http/`. Nếu không có marker,
nó fallback theo `SERVICE_BY_PORT`.

## 10. Câu hỏi thầy bắt hiểu chéo phần bạn An

### Câu 33. Sau khi phần em tạo 3 JSON thì phần An làm gì?

**Trả lời:**  
Risk stage đọc 3 JSON đó, trích xuất feature như số port mở, port nhạy cảm, DNS
record count, version leak. Sau đó model Simple Isolation Forest chấm điểm risk,
tạo findings, MITRE mapping và recommendations.

### Câu 34. `risk_profile.json` có liên quan gì đến phần em?

**Trả lời:**  
Nó dùng trực tiếp output của phần em. Nếu port scan, DNS enum hoặc banner result
sai thì feature và risk score phía sau cũng sai.

### Câu 35. Report cuối cùng lấy dữ liệu từ đâu?

**Trả lời:**  
Report không đọc trực tiếp 3 file recon, mà đọc `risk_profile.json`. Nhưng
`risk_profile.json` có `recon_summary`, trong đó chứa output từ 3 tool recon của em.

## 11. Bài code tay thầy dễ bắt phần em

### Bài 1. Thêm `closed_count` vào port scan result

**Yêu cầu:**  
Trong `port_scan_result.json`, thêm số port đóng.

**File sửa:** `.pi/tools/recon/port_scanner.py`

**Code mẫu:**

```python
return {
    "target": target,
    "scanned_ports": selected_ports,
    "open_ports": sorted(open_ports),
    "open_count": len(open_ports),
    "closed_count": len(selected_ports) - len(open_ports),
}
```

**Cách giải thích:**  
`closed_count` bằng tổng số port đã scan trừ số port open.

### Bài 2. Thêm port MongoDB 27017 vào default scan

**File sửa:** `.pi/tools/recon/port_scanner.py`

**Code mẫu:**

```python
DEFAULT_PORTS = [
    21, 22, 23, 25, 53, 80, 110, 139, 143, 443, 445,
    3306, 5432, 6379, 8000, 8080, 27017,
]
```

**Cách giải thích:**  
Khi user không truyền `--ports`, `choose_ports()` sẽ dùng `DEFAULT_PORTS`.

### Bài 3. Thêm record CAA cho DNS enum

**File sửa:** `.pi/tools/recon/dns_enum.py`

**Code mẫu:**

```python
DNS_RECORD_TYPES = ["A", "CNAME", "MX", "NS", "SOA", "TXT", "CAA"]
```

**Cách giải thích:**  
Vòng lặp DNS tự query thêm CAA. Nếu domain không có CAA, lỗi được ghi vào
`errors["CAA"]`, pipeline không fail.

### Bài 4. Thêm `--timeout` cho banner grabber CLI

**File sửa:** `.pi/tools/recon/banner_grabber.py`

**Code mẫu:**

```python
parser.add_argument("--timeout", type=float, default=1.0)
result = grab_banners(args.target, ports, args.timeout)
```

**Cách giải thích:**  
Hàm `grab_banners()` đã có tham số timeout và validate timeout, nên CLI chỉ cần
truyền thêm giá trị này vào.

### Bài 5. Nếu không truyền `--ports` cho banner grabber thì dùng default ports

**File sửa:** `.pi/tools/recon/banner_grabber.py`

**Code mẫu:**

```python
from recon.port_scanner import DEFAULT_PORTS

ports = parse_ports(args.ports) if args.ports else DEFAULT_PORTS
result = grab_banners(args.target, ports)
```

**Cách giải thích:**  
Hiện tại chạy riêng `banner_grabber.py` không truyền ports thì `parse_ports("")`
trả list rỗng. Thêm fallback giúp tool độc lập dễ demo hơn.

### Bài 6. Thêm field `"stage": "recon"` vào output 3 tool

**File sửa:**

- `.pi/tools/recon/port_scanner.py`
- `.pi/tools/recon/dns_enum.py`
- `.pi/tools/recon/banner_grabber.py`

**Code mẫu:**

```python
"stage": "recon",
```

**Cách giải thích:**  
Thêm field này để report/debug biết JSON thuộc stage nào.

### Bài 7. Log rõ target bị block

**File sửa:** `.pi/tools/main_pipeline.py`

**Code mẫu:**

```python
logging.warning("Permission gate blocked target=%s: %s", target, message)
```

**Cách giải thích:**  
Log rõ target giúp debug khi người dùng nhập sai hoặc scan target ngoài allowlist.

### Bài 8. Thêm target lab mới vào allowlist

**File sửa:** `.pi/data/allowed_targets.json`

**Ví dụ thêm:**

```json
"example-lab.local"
```

**Cách giải thích:**  
Chỉ thêm target lab hoặc target có quyền. Không được sửa logic thành cho phép mọi
target public.

## 12. Lệnh chạy demo em phải thuộc

### Chạy demo local ổn định

Terminal 1:

```powershell
python -m http.server 8000 --bind 127.0.0.1
```

Terminal 2:

```powershell
python .pi\tools\main_pipeline.py --target localhost --ports "8000,8080,3306,5432,6379" --offline
```

Mở report:

```powershell
notepad .pi\results\ket_qua.md
```

### Chạy riêng port scanner

```powershell
python .pi\tools\recon\port_scanner.py --target localhost --ports "8000,8080"
```

### Chạy riêng DNS enum

```powershell
python .pi\tools\recon\dns_enum.py --target scanme.nmap.org
```

### Chạy riêng banner grabber

```powershell
python .pi\tools\recon\banner_grabber.py --target localhost --ports "8000,8080"
```

### Kiểm tra compile

```powershell
python -m compileall .pi\tools
```

## 13. Cách debug khi thầy bắt chạy lỗi

### Lỗi 1. `[BLOCKED] Permission gate blocked this target`

**Nguyên nhân:**  
Target không nằm trong allowlist và không có `--authorized`.

**Cách xử lý:**  
Dùng `localhost`, target lab trong allowlist, hoặc chỉ thêm `--authorized` khi có quyền.

**File mở để giải thích:** `.pi/tools/common/tool_utils.py`

### Lỗi 2. Port 8000 không open

**Nguyên nhân:**  
Chưa chạy HTTP server local.

**Cách xử lý:**

```powershell
python -m http.server 8000 --bind 127.0.0.1
```

### Lỗi 3. DNS enum báo nhiều errors

**Nguyên nhân:**  
Domain không có record đó hoặc DNS timeout. Đây không phải lỗi pipeline.

**Cách giải thích:**  
Mỗi record type fail riêng, tool vẫn trả JSON có `records` và `errors`.

### Lỗi 4. Banner toàn `No banner`

**Nguyên nhân:**  
Port đóng, service không gửi banner, hoặc timeout.

**Cách giải thích:**  
`No banner` là kết quả hợp lệ. Banner grabber không retry mạnh để giữ an toàn.

### Lỗi 5. Nhập `--ports "1-10000"` bị lỗi

**Nguyên nhân:**  
Vượt `MAX_PORT_COUNT = 4096`.

**Cách giải thích:**  
Giới hạn này tránh scan quá rộng trong demo.

### Lỗi 6. Target dạng URL không đúng

**Ví dụ đúng:**

```powershell
python .pi\tools\main_pipeline.py --target http://localhost:8000 --offline
```

**Cách giải thích:**  
`parse_target()` sẽ lấy host là `localhost` và port là `8000`.

## 14. Các câu thầy rất dễ hỏi nhanh

1. Stage 1 song song nằm ở hàm nào?  
   `run_recon_stage()` trong `main_pipeline.py`.

2. Safety Gate nằm ở hàm nào?  
   `is_target_allowed()` trong `tool_utils.py`.

3. Port scanner dùng thư viện gì?  
   Python `socket`.

4. DNS enum dùng thư viện gì?  
   `dnspython`, import là `dns.resolver`.

5. HTTP banner grab gửi request gì?  
   `HEAD / HTTP/1.1`.

6. Output recon nằm ở đâu?  
   `.pi/triage`.

7. Nếu không có API key thì report có chạy không?  
   Có, dùng offline template. Dù không phải phần chính của em, em vẫn cần biết.

8. Vì sao không scan mọi website public?  
   Vì có Safety Gate và allowlist. Target ngoài phạm vi cần `--authorized`.

## 15. Checklist trước khi vào vấn đáp

- Em mở được `main_pipeline.py` và chỉ đúng `run_recon_stage()`.
- Em giải thích được `ThreadPoolExecutor` và `as_completed`.
- Em mở được `tool_utils.py` và giải thích `is_target_allowed`, `parse_target`, `parse_ports`.
- Em mở được `port_scanner.py` và giải thích TCP connect scan.
- Em mở được `dns_enum.py` và giải thích localhost/IP/domain.
- Em mở được `banner_grabber.py` và giải thích HEAD request, TLS metadata.
- Em chạy được pipeline local.
- Em sửa được ít nhất 3 bài code tay: `closed_count`, thêm DNS CAA, thêm `--timeout` cho banner grabber.

