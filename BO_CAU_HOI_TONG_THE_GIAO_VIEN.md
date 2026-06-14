# BỘ CÂU HỎI VẤN ĐÁP TỔNG THỂ TOÀN PROJECT
## Network Recon + Risk Profiler – Topic 02
### Dành cho cả Vũ Văn Thông & Nguyễn Thành An

---

## 🅰️ PHẦN TỔNG QUAN KIẾN TRÚC (Cả 2)

**Câu 1.** Mô tả pipeline của project từ Stage 0 đến Stage 3. Vẽ luồng dữ liệu giữa các stage.

**Câu 2.** Vì sao Stage 1 dùng `ThreadPoolExecutor(max_workers=3)` mà không dùng `multiprocessing`?

**Câu 3.** Nếu thầy muốn chạy Stage 1 với 5 worker thì sửa ở đâu? Hậu quả nếu tăng quá nhiều?

**Câu 4.** `run_pipeline()` trả về dict gồm những trường nào?

**Câu 5.** File output `stage_durations` giúp ích gì khi thầy hỏi về hiệu năng?

**Câu 6.** Nếu target là URL `http://localhost:8080`, pipeline xử lý thế nào?

**Câu 7.** Cơ chế fallback của report là gì? Giải thích chuỗi điều kiện trong `generate_report()`.

**Câu 8.** File `.pi/tools/udp_scanner.py` dùng để làm gì? Vì sao nó không nằm trong pipeline chính?

**Câu 9.** File `manage_targets.py` dùng để làm gì? Nếu thầy chạy `python manage_targets.py list`, flow thế nào?

**Câu 10.** File `.pi/chains/recon_risk_pipeline.chain.md` khác gì so với `main_pipeline.py`?

---

## 🅱️ PHẦN HIỂU CODE – TỪNG FILE, TỪNG HÀM (Cả 2)

### tool_utils.py

**Câu 11.** `project_root()` tính đường dẫn thế nào? Giải thích `parents[3]`.

**Câu 12.** `load_allowed_targets()` đọc file nào? Nếu file không tồn tại thì sao?

**Câu 13.** `resolve_target()` dùng hàm gì? Nếu hostname không resolve được, nó ném exception gì?

**Câu 14.** `parse_ports()` xử lý range `"1-1000"` như thế nào? Nếu start > end thì sao?

**Câu 15.** `validate_target()` kiểm tra những gì?

**Câu 16.** `choose_ports()` ưu tiên port từ đâu?

### main_pipeline.py

**Câu 17.** `run_recon_stage()` dùng `as_completed()` thay vì lặp `futures` theo thứ tự. Vì sao?

**Câu 18.** Vì sao `run_pipeline()` gọi `resolve_target()` sau Safety Gate mà không phải trước?

**Câu 19.** `main()` parse args gồm những gì? Nếu không truyền `--ports` thì port mặc định là gì?

**Câu 20.** Nếu thầy muốn thêm stage mới (Stage 4) sau Stage 3, em cần sửa file nào, thêm code ở đâu?

### port_scanner.py

**Câu 21.** `scan_port()` dùng `socket.create_connection()`. Nếu thầy hỏi em tự implement hàm connect TCP bằng `socket.socket()`, em làm thế nào?

**Câu 22.** Vì sao `closed_count = len(selected_ports) - len(open_ports)` không chính xác tuyệt đối?

**Câu 23.** `max_workers = min(50, max(1, len(selected_ports)))`. Vì sao giới hạn 50?

### dns_enum.py

**Câu 24.** `is_localhost()` kiểm tra những giá trị nào?

**Câu 25.** `is_ip_address()` dùng thư viện gì? Nếu truyền IPv6 `::1` thì sao?

**Câu 26.** Hàm `_format_answer()` xử lý MX record đặc biệt thế nào?

**Câu 27.** Trong vòng lặp DNS record, nếu một record lỗi, toàn bộ vòng lặp có dừng không?

### banner_grabber.py

**Câu 28.** `_clean_banner()` làm gì? Vì sao giới hạn 500 ký tự?

**Câu 29.** Hàm `grab_banner()` cho HTTP port gửi request gì? `Connection: close` có nghĩa gì?

**Câu 30.** `inspect_tls()` tạo ssl context với `check_hostname=False`, `verify_mode=CERT_NONE`. Vì sao?

**Câu 31.** `SERVICE_BY_PORT` map port nào? Nếu port 3000 có trong dict không?

**Câu 32.** Hàm `identify_service()` kiểm tra marker trong banner trước, rồi fallback `SERVICE_BY_PORT`. Vì sao?

### risk_config.py

**Câu 33.** `FEATURE_WEIGHTS` có những feature nào? Feature nào có weight cao nhất?

**Câu 34.** `BANNER_VERSION_PATTERNS` gồm những pattern nào cho Apache, Nginx, OpenSSH?

### risk_features.py

**Câu 35.** `extract_features()` nhận input gì, trả về gì?

**Câu 36.** `banner_has_version()` dùng regex pattern nào? Nếu banner là `No banner` thì sao?

### risk_model.py

**Câu 37.** `SimpleIsolationForestRiskModel` có 3 phương thức chính. Kể tên và giải thích.

**Câu 38.** `average_path_length(size)` dùng công thức gì?

**Câu 39.** Vì sao `exposure_severity()` không dùng Isolation Forest mà dùng trọng số thủ công?

**Câu 40.** `predict_with_isolation_forest()` kết hợp anomaly score và exposure_severity thế nào?

### risk_scorer.py

**Câu 41.** `classify_target_exposure()` phân loại target thế nào?

**Câu 42.** `score_risk()` cộng thêm điểm nào cho target public?

**Câu 43.** `score_risk_from_files()` đọc file từ đâu và gọi hàm nào?

### risk_findings.py

**Câu 44.** `build_findings()` tạo finding mấy loại?

**Câu 45.** `build_mitre_mapping()` map những technique ID nào?

### report_templates.py & ai_reporter.py

**Câu 46.** `build_offline_report()` có mấy section? Kể tên.

**Câu 47.** Vì sao report offline có dòng "Offline fallback used"?

**Câu 48.** `generate_ai_report()` gửi prompt gì cho model?

**Câu 49.** Vì sao `temperature=0.2`?

### pi_recon_agent.py

**Câu 50.** `ToolRuntime` có mấy method bảo vệ?

**Câu 51.** Vòng lặp agent trong `run_agent()` tối đa bao nhiêu iteration?

**Câu 52.** Nếu model trả tool calls dạng text (JSON) thay vì structured, code xử lý thế nào?

**Câu 53.** `_compact_for_llm()` làm gì?

---

## 🅲 PHẦN CÂU HỎI CODE TAY & SỬA CODE (Cả 2)

**Câu 54.** (Thông) Thêm `"service": "unknown"` vào port scan result khi port không open — có nên không? Vì sao?

**Câu 55.** (An) Thêm feature `"high_risk_port_count"` vào `explain_exposure()`. Code đã có chưa?

**Câu 56.** (Cả 2) Nếu thầy yêu cầu thêm feature `"total_banner_length"` để đo mức độ lộ thông tin, em sửa file nào?

**Câu 57.** (Thông) Viết hàm `ping_target(target, timeout)` dùng `socket`. Sửa file nào?

**Câu 58.** (An) Thêm section "Evidence Files" vào `build_offline_report()`.

**Câu 59.** (Thông) Thêm `--verbose` flag in ra log chi tiết ra console.

**Câu 60.** (An) Nếu `OPENAI_API_KEY` hết hạn, pipeline vẫn gọi API và fail. Làm sao để tự động fallback?

---

## 🅳 PHẦN DEBUG & TÌNH HUỐNG (Cả 2)

**Câu 61.** Chạy pipeline với target `google.com` không `--authorized`, output là gì?

**Câu 62.** Port 8000 không open dù đã chạy `python -m http.server 8000`. Nguyên nhân?

**Câu 63.** DNS enum báo lỗi "No DNS records found" cho domain thật. Có thể do đâu?

**Câu 64.** Banner toàn "No banner" dù port đang mở. Giải thích.

**Câu 65.** Report không có MITRE mapping. Debug thế nào?

**Câu 66.** Isolation Forest anomaly score luôn là 0.0. Vì sao?

---

## 🅴 PHẦN CÂU HỎI RIÊNG CHO VŨ VĂN THÔNG

### Thiết kế Pipeline & Safety Gate

**Câu T1.** Trình bày luồng `run_pipeline()` từ đầu đến cuối. Chỉ rõ từng hàm được gọi theo thứ tự.

**Câu T2.** Trong `run_recon_stage()`, vì sao em dùng `as_completed(futures)` thay vì duyệt `futures` dictionary?

**Câu T3.** Vì sao `run_pipeline()` return `resolved_addresses`? Nó có được dùng ở stage sau không?

**Câu T4.** Nếu `ensure_output_dirs()` chưa tạo thư mục, `write_json()` có lỗi không?

**Câu T5.** Viết lại `is_target_allowed()` và giải thích từng phần.

**Câu T6.** `load_allowed_targets()` đọc file JSON. Nếu file bị lỗi syntax, chuyện gì xảy ra?

**Câu T7.** Vì sao `DEFAULT_ALLOWED_TARGETS` và `allowed_targets.json` đều có `scanme.nmap.org`?

**Câu T8.** Thêm một target mới `"lab-server.local"` vào cả file JSON và default set — sửa thế nào?

### Port Scanner

**Câu T9.** Giải thích dòng `with socket.create_connection((target, port), timeout=timeout):` — `with` là gì? `create_connection` trả về gì?

**Câu T10.** Nếu thầy muốn scan UDP thay vì TCP, em sửa hàm `scan_port()` thế nào?

**Câu T11.** `scan_ports()` có song song bên trong. Vì sao không dùng `as_completed()` ở đây và cũng dùng ở `main_pipeline.py`?

**Câu T12.** Thêm port mới 9200 (Elasticsearch) vào `DEFAULT_PORTS`. Nếu quên thêm vào `SERVICE_BY_PORT` ở banner grabber thì sao?

**Câu T13.** Thầy bảo "thêm --reason flag để hiển thị lý do port không open" — em làm thế nào?

### DNS Enumeration

**Câu T14.** Giải thích `is_ip_address()` dùng `ipaddress.ip_address()`. Nếu truyền `"example.com"` thì sao?

**Câu T15.** Vì sao `enumerate_dns()` import `dns.resolver` bên trong try/except, không để ở đầu file?

**Câu T16.** Thêm record SRV vào DNS enum. Sửa file nào, thêm dòng nào?

**Câu T17.** Nếu thầy muốn DNS enum chỉ query A record cho nhanh, em sửa thế nào?

**Câu T18.** Giải thích `resolver.resolve_address(domain)` — hàm này dùng cho input nào?

### Banner Grabber

**Câu T19.** Trình bày luồng `grab_banner()` cho port HTTP.

**Câu T20.** Nếu thầy muốn banner grabber thử GET thay vì HEAD để lấy thêm thông tin, sửa ở đâu? Rủi ro?

**Câu T21.** `inspect_tls()` kiểm tra TLS port nào? Vì sao port 8443 có trong danh sách?

**Câu T22.** `inspect_tls()` nếu self-signed certificate thì có lỗi không?

**Câu T23.** Thầy muốn `_clean_banner()` giới hạn 200 ký tự thay vì 500. Sửa đâu?

**Câu T24.** Nếu server gửi banner chia làm nhiều gói TCP, `recv(1024)` chỉ nhận gói đầu. Có vấn đề gì?

### Tool Utils

**Câu T25.** Giải thích `validate_target()` kiểm tra path. Tại sao lại cấm "/" trong target?

**Câu T26.** `validate_timeout()` giới hạn 0.01 đến 30. Nếu ai đó truyền `--timeout 0.001` thì sao?

**Câu T27.** `parse_target()` xử lý `"http://localhost:8000"` như thế nào? `urlparse` trả về gì?

**Câu T28.** Vì sao `validate_target()` trim và lower target?

**Câu T29.** `choose_ports()` ưu tiên `url_ports` hơn `DEFAULT_PORTS` hay không?

### Cross-check với phần của An

**Câu T30.** Nếu em thêm port mới vào `DEFAULT_PORTS`, bạn An có cần sửa gì trong phần risk không?

**Câu T31.** Banner grabber trả `"No banner"` — feature `version_banner_count` có đếm port đó không?

**Câu T32.** `risk_scorer.py` đọc banner_result.json. Nếu em thêm field mới vào JSON đó, bạn An có cần sửa code không?

**Câu T33.** Nếu em sửa `scan_ports()` trả về thêm `"elapsed_seconds"`, bạn An có cần sửa gì không?

### Bài code tay nâng cao cho Thông

**Bài T34.** Thêm TCP connect timeout configurable vào `scan_port()` qua tham số, đảm bảo dưới 5 giây.

**Bài T35.** Viết wrapper function `safe_scan(target, ports, authorized)` tự động kiểm tra Safety Gate trước khi scan.

**Bài T36.** Thêm `--format json` flag cho CLI để tùy chọn in output dạng JSON hoặc text.

**Bài T37.** Viết unit test cho `parse_ports()`.

**Bài T38.** Thêm hàm `is_safe_target(target)` kiểm tra target có phải local/private không (không cần file JSON).

**Bài T39.** Sửa `banner_grabber.py` để thử 2 lần nếu lần đầu timeout.

**Bài T40.** Thêm hàm `validate_ports(ports, max_count=100)` chạy trước `scan_ports()` để cảnh báo nếu số port > 100.

### Tình huống vấn đáp

**T41.** Thầy hỏi: "Vì sao em không dùng `subprocess` gọi nmap cho nhanh?"

**T42.** Thầy hỏi: "Nếu thầy muốn pipeline hỗ trợ IPv6, em làm thế nào?"

**T43.** Thầy hỏi: "Em có biết mỗi port scan tạo ra bao nhiêu kết nối TCP không?"

**T44.** Thầy hỏi: "Vì sao em không scan toàn bộ 65535 port?"
