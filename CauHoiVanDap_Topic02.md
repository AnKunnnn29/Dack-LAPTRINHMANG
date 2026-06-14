# Câu hỏi Vấn đáp — Topic 02: Network Recon + Risk Profiler

> **Môn:** Lập trình Mạng với AI/ML cho An ninh mạng  
> **Giảng viên:** Sử dụng DeepSeek để đọc code, .md, báo cáo → tạo câu hỏi vấn đáp  
> **Nhóm:** 2 sinh viên  
> **Ngày:** 12/06/2026

---

## Phân công vai trò trong nhóm

| MSSV | Họ tên | Vai trò | File phụ trách chính |
|------|--------|---------|----------------------|
| 23162098 | Vũ Văn Thông | Data Ingestion + Safety Gate + Pipeline Design + Recon Tools | `main_pipeline.py`, `tool_utils.py`, `port_scanner.py`, `dns_enum.py`, `banner_grabber.py`, `orchestrator_agent.md`, `permission_gate_agent.md`, `port_scan_agent.md`, `dns_enum_agent.md`, `banner_grab_agent.md`, `recon_risk_pipeline.chain.md`, `recon/SKILL.md` |
| 23162001 | Nguyễn Thành An | Risk Scoring + Report Generation + Aggregation + Agentic Extension | `risk_scorer.py`, `risk_model.py`, `risk_features.py`, `risk_config.py`, `risk_findings.py`, `ai_reporter.py`, `report_templates.py`, `openai_report_client.py`, `pi_recon_agent.py`, `risk_score_agent.md`, `report_agent.md`, `report_prompt.md`, `risk-scoring/SKILL.md`, `reporting/SKILL.md` |

---

## A. Câu hỏi cho Vũ Văn Thông (23162098)

**Phạm vi:** Thiết kế pipeline, Safety Gate, port scanner, DNS enum, banner grabber, kiểm thử phase recon.

---

### A.1 — Level 1: Hiểu cơ bản (Em đã làm gì?)

**Câu 1.** Em hãy vẽ sơ đồ (hoặc mô tả bằng lời) toàn bộ pipeline của Topic 02 — từ lúc nhập lệnh cho đến khi có file báo cáo cuối cùng. Có bao nhiêu stage? Stage nào chạy song song, stage nào tuần tự?

> [!success]- Đáp án tham khảo
>
> ```
> Stage 0 (Safety Gate): permission_gate_agent → kiểm tra target có trong allowlist không
>                         ↓ (nếu allowed)
> Stage 1 (Parallel Recon): chạy ĐỒNG THỜI 3 agent
>     ├── port_scan_agent    → .pi/triage/port_scan_result.json
>     ├── dns_enum_agent     → .pi/triage/dns_enum_result.json
>     └── banner_grab_agent  → .pi/triage/banner_result.json
>                         ↓ (khi cả 3 file đã có)
> Stage 2 (ML Risk Scoring): risk_score_agent → .pi/triage/risk_profile.json
>                         ↓
> Stage 3 (Report): report_agent → .pi/results/ket_qua.md
> ```
>
> - **Tuần tự:** Stage 0 → 1 → 2 → 3 (có data dependency)
> - **Song song:** Bên trong Stage 1, 3 agent chạy đồng thời vì không phụ thuộc dữ liệu lẫn nhau
> - **Per-port parallelism:** Bên trong port_scanner.py và banner_grabber.py, mỗi port được quét trong 1 thread riêng

---

**Câu 2.** File `.pi/chains/recon_risk_pipeline.chain.md` có vai trò gì trong project? Nó có phải là code Python không? Nếu không có file này thì pipeline có chạy được không?

> [!success]- Đáp án tham khảo
>
> - Đây là file **orchestration specification** (đặc tả điều phối), viết bằng Markdown, không phải code Python.
> - Nó mô tả:
>   - Vai trò của từng agent
>   - Thứ tự các stage
>   - Handoff contract (ràng buộc chuyển giao giữa các stage)
>   - Output path của từng stage
>   - Safety boundary
> - **Vai trò:** Làm tài liệu thiết kế để orchestrator_agent và người đọc hiểu pipeline. Trong kiến trúc Pi Coding Agent, file chain.md được dùng làm system prompt cho orchestrator.
> - **Không có chain.md:** Pipeline Python (`main_pipeline.py`) vẫn chạy được độc lập vì logic đã được code cứng trong Python. Nhưng chain.md giúp **giải thích thiết kế** và là evidence cho phần "multi-agent orchestration" của đồ án.

---

### A.2 — Level 2: Hiểu code (Dòng code này làm gì?)

**Câu 3.** Trong file `.pi/tools/recon/port_scanner.py`, giải thích ý nghĩa của `ThreadPoolExecutor` và `as_completed` trong đoạn code sau:

```python
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
```

a) Tại sao dùng `dict {future: port}` thay vì list?  
b) `as_completed` khác gì với `for future in futures` thông thường?  
c) `max_workers = min(50, max(1, len(selected_ports)))` có ý nghĩa gì?

> [!success]- Đáp án tham khảo
>
> **a) Dict `{future: port}`:**
> - Mỗi `executor.submit()` trả về một `Future` object. Khi task hoàn thành, `as_completed` yield các future theo **thứ tự hoàn thành** (không phải thứ tự submit).
> - Dict map `future → port` giúp ta biết future nào tương ứng với port nào. Nếu dùng list, khi `as_completed` trả về future, ta không biết đó là port mấy.
>
> **b) `as_completed` vs `for future in futures`:**
> - `for future in futures` duyệt theo thứ tự submit. Nếu port 8000 mất 0.5s timeout nhưng port 80 mất 0.01s → vẫn phải đợi port 8000 xong mới xử lý port 80.
> - `as_completed` trả về future nào **xong trước**. Port 80 (0.01s) sẽ được xử lý ngay, không phải chờ port chậm.
>
> **c) `max_workers = min(50, max(1, len(selected_ports)))`**:
> - `max(1, len(ports))` đảm bảo ít nhất 1 worker (kể cả khi ports rỗng về lý thuyết).
> - `min(50, ...)` giới hạn tối đa 50 thread — nếu scan 1000 ports cũng không tạo 1000 thread, tránh quá tải hệ thống.
> - Ví dụ: 3 ports → 3 workers; 16 ports → 16 workers; 1000 ports → 50 workers.

---

**Câu 4.** Trong file `.pi/tools/recon/dns_enum.py`, có đoạn code:

```python
for record_type in DNS_RECORD_TYPES:
    try:
        answers = resolver.resolve(domain, record_type)
        records[record_type] = [_format_answer(record_type, answer) for answer in answers]
    except Exception as exc:
        records[record_type] = []
        errors[record_type] = str(exc)
```

a) Tại sao mỗi record type (A, CNAME, MX, NS, SOA, TXT) được query trong try/except riêng?  
b) Nếu 1 record type fail (ví dụ domain không có MX record) thì có làm hỏng toàn bộ DNS enum không?  
c) Hàm `_format_answer()` xử lý khác nhau cho MX và TXT — tại sao?

> [!success]- Đáp án tham khảo
>
> **a) Try/except riêng cho từng record type:** Đây là thiết kế **fail-safe**. Mỗi record type độc lập — nếu MX query fail thì chỉ MX bị ghi vào `errors`, các record A, NS, TXT,... vẫn được query tiếp.
>
> **b) Không làm hỏng toàn bộ:** Exception được bắt riêng trong vòng lặp. `errors` dict ghi lại lỗi để report, `records` dict ghi record type đó là `[]`. Pipeline tiếp tục bình thường.
>
> **c) Format khác nhau:**
> - **MX record:** Có cấu trúc `(preference, exchange)`, VD: `10 mail.example.com` → `_format_answer` trả về `"10 mail.example.com"`.
> - **TXT record:** Là list các bytes string → cần decode UTF-8 và join lại thành 1 string.
> - **Các record khác (A, NS, CNAME, SOA):** Chỉ cần `str(answer).rstrip(".")` để bỏ dấu chấm cuối.

---

**Câu 5.** Trong file `.pi/tools/recon/banner_grabber.py`, có đoạn:

```python
if port in HTTP_PORTS:
    request = f"HEAD / HTTP/1.1\r\nHost: {target}\r\nConnection: close\r\n\r\n"
    sock.sendall(request.encode("utf-8"))
```

a) Tại sao với HTTP port phải **gửi HEAD request** mà không chỉ đọc passive?  
b) `Connection: close` có ý nghĩa gì?  
c) Nếu port 8000 đang chạy SSH thay vì HTTP, chuyện gì xảy ra khi gửi HEAD request?

> [!success]- Đáp án tham khảo
>
> **a) HTTP là giao thức request-response:** HTTP server **không tự gửi banner** khi có kết nối. Nó chờ client gửi request trước. Nếu không gửi HEAD, socket sẽ đợi server nói trước → timeout → trả về "No banner" (sai).
>
> **b) `Connection: close`:** Báo cho server biết client muốn đóng kết nối sau khi nhận response. Không dùng keep-alive vì banner grabber chỉ cần đọc 1 lần. Tránh giữ connection treo không cần thiết.
>
> **c) Gửi HEAD request đến non-HTTP port:**
> - Server SSH nhận được text `"HEAD / HTTP/1.1..."` → không hiểu giao thức → có thể gửi banner SSH (VD: `SSH-2.0-OpenSSH_8.9`) hoặc đóng connection.
> - Đoạn code vẫn đọc được banner SSH đó (qua `sock.recv(1024)`) vì nó được gửi trước khi server nhận ra sai giao thức.
> - Đây là lý do `grab_banner` chạy độc lập với port scan: banner có thể thu được ngay cả khi service không phải HTTP.

---

### A.3 — Level 3: Thiết kế & Lý do (Tại sao em làm vậy?)

**Câu 6.** Trong `main_pipeline.py`, hàm `run_recon_stage()` dùng `ThreadPoolExecutor(max_workers=3)`. Tại sao **banner_grab_agent không dùng output từ port_scan_agent** (chỉ grab banner trên port đã biết open) mà quét lại toàn bộ `candidate_ports`? Điều này có lãng phí không?

> [!success]- Đáp án tham khảo
>
> Đây là **quyết định thiết kế có chủ đích**, phục vụ yêu cầu Stage 1 parallelism:
>
> - **Lý do chính:** Topic 02 yêu cầu Stage 1 chạy **song song** 3 agent vì **không có data dependency**. Nếu banner_grab_agent phải đợi port_scan_agent hoàn thành (để biết port nào open) → mất tính song song → wall-clock time tăng gấp đôi (phải đợi port scan xong mới bắt đầu banner).
>
> - **Lãng phí không?** Có lãng phí nhẹ về network (gửi request đến port đóng), nhưng:
>   - Mỗi request đến port đóng chỉ tốn ~timeout (0.5s).
>   - Port đóng trả về connection refused **ngay lập tức** → không tốn full timeout.
>   - Lợi ích về wall-clock time (3 task chạy đồng thời) lớn hơn nhiều so với chi phí gửi thêm request.
>
> - **Trade-off:** Đánh đổi một chút network overhead để đạt parallelism tối đa. Đây là điểm quan trọng để bảo vệ khi vấn đáp về "tại sao song song".

---

**Câu 7.** Hãy giải thích cơ chế **Safety Gate** trong project. Điều gì xảy ra nếu người dùng chạy `python .pi/tools/main_pipeline.py --target google.com` mà không có `--authorized`?

> [!success]- Đáp án tham khảo
>
> Safety Gate nằm ở `is_target_allowed()` trong `tool_utils.py`:
>
> ```python
> def is_target_allowed(target: str, authorized: bool) -> bool:
>     return authorized or target.lower() in load_allowed_targets()
> ```
>
> **Logic:**
> 1. Nếu user truyền `--authorized` → luôn cho phép (người dùng tự chịu trách nhiệm).
> 2. Nếu không có `--authorized` → kiểm tra target có trong `allowed_targets.json` không.
> 3. `allowed_targets.json` chứa: `localhost`, `127.0.0.1`, `::1`, `scanme.nmap.org`, `pentest-ground.com`, `vulnweb.com`,...
> 4. Mặc định là **deny**.
>
> **Với `google.com` không có `--authorized`:**
> - `google.com` không có trong allowlist → `is_target_allowed` trả về `False`.
> - `main_pipeline.py` raise `PermissionError` với message: *"Permission gate blocked this target..."*.
> - Pipeline **dừng ngay**, không có bất kỳ network activity nào.

---

### A.4 — Level 4: Mở rộng & Phản biện (Nếu thầy đổi yêu cầu thì sao?)

**Câu 8.** Hiện tại `port_scanner.py` giới hạn `max_workers=50`. Nếu thầy yêu cầu scan **10,000 port**, em cần thay đổi những gì? Có vấn đề gì với cách dùng `ThreadPoolExecutor` khi số lượng port lớn không?

> [!success]- Đáp án tham khảo
>
> **Những thay đổi cần thiết:**
>
> 1. **`MAX_PORT_COUNT`** trong `tool_utils.py`: hiện là 4096 → cần tăng lên hoặc bỏ giới hạn này, thay bằng warning.
> 2. **`max_workers`**: 50 workers với 10,000 ports → 200 batches. Có thể tăng lên 100-200. Nhưng cần cẩn thận vì mỗi thread tạo 1 socket → OS có giới hạn file descriptor.
> 3. **Timeout**: 0.5s × 10,000 ports = tối đa 5,000s nếu chạy tuần tự. Với 100 workers song song: 10,000/100 = 100 batches × 0.5s = ~50s. Hợp lý hơn.
>
> **Vấn đề với `ThreadPoolExecutor` khi port lớn:**
>
> - **GIL (Global Interpreter Lock):** Python thread không thực sự song song cho CPU-bound task. Nhưng socket I/O là I/O-bound → thread vẫn hiệu quả vì GIL được release khi chờ I/O.
> - **Tài nguyên OS:** Mỗi thread ~8MB stack → 100 threads = 800MB. 1000 threads = 8GB. Cần giới hạn hợp lý.
> - **Giải pháp thay thế:** Dùng `asyncio` + `asyncio.open_connection()` cho I/O non-blocking → 1 thread duy nhất có thể xử lý hàng nghìn kết nối đồng thời. Nhưng code phức tạp hơn.

---

**Câu 9.** Nếu thầy yêu cầu thêm **UDP scanning** vào Stage 1 (chạy song song cùng 3 agent hiện tại), em sẽ implement như thế nào? UDP scan có khó khăn gì khác TCP scan?

> [!success]- Đáp án tham khảo
>
> **Cách implement:**
>
> 1. Project đã có file `.pi/tools/udp_scanner.py` làm helper → có thể dùng lại.
> 2. Trong `run_recon_stage()` của `main_pipeline.py`, thêm future thứ 4:
>
> ```python
> futures = {
>     executor.submit(scan_ports, target, ports, timeout): "port",
>     executor.submit(enumerate_dns, target, timeout): "dns",
>     executor.submit(grab_banners, target, ports, timeout): "banner",
>     executor.submit(scan_udp_ports, target, udp_ports, timeout): "udp",  # THÊM
> }
> ```
>
> 3. Tăng `max_workers` từ 3 lên 4.
> 4. Cập nhật `run_risk_stage()` để nhận thêm `udp_result`.
> 5. Cập nhật chain.md, orchestrator_agent.md, thêm feature UDP vào `risk_features.py`.
>
> **Khó khăn của UDP so với TCP:**
>
> | TCP | UDP |
> |-----|-----|
> | 3-way handshake → biết chắc port open/closed | Gửi datagram, không có handshake |
> | Connection refused → port closed | Không nhận được gì → **open hoặc filtered** (không phân biệt được) |
> | Dễ dùng `socket.create_connection()` | Phải dùng raw socket + `sendto()`/`recvfrom()` |
> | Không cần payload đặc biệt | Cần gửi payload protocol-specific (VD: DNS query cho port 53) để server trả lời |

---

## B. Câu hỏi cho Nguyễn Thành An (23162001)

**Phạm vi:** Risk scoring, report generation, tổng hợp kết quả, agentic extension, hoàn thiện báo cáo.

---

### B.1 — Level 1: Hiểu cơ bản (Em đã làm gì?)

**Câu 1.** Em hãy mô tả Input → Process → Output của Stage 2 (Risk Scoring). Mô hình ML em dùng là gì? Nó "học" từ đâu? Output `risk_profile.json` chứa những trường quan trọng nào?

> [!success]- Đáp án tham khảo
>
> **Input:** 3 file JSON từ Stage 1:
> - `port_scan_result.json` (danh sách port mở)
> - `dns_enum_result.json` (DNS records)
> - `banner_result.json` (banners + services)
>
> **Process:**
> 1. **Feature Extraction** (`risk_features.py`): Trích xuất 7 features từ recon output.
> 2. **Isolation Forest** (`risk_model.py`): Dự đoán anomaly score.
> 3. **Calibration** (`risk_scorer.py`): Kết hợp anomaly score + exposure severity → score 0-10.
> 4. **Findings + MITRE Mapping** (`risk_findings.py`): Tạo danh sách finding và ánh xạ MITRE ATT&CK.
>
> **Output:** `risk_profile.json` chứa:
> - `score` (0-10)
> - `risk_level` (Low/Medium/High)
> - `ml_model` (tên model, anomaly score, features, risk drivers,...)
> - `findings` (danh sách phát hiện)
> - `mitre_mapping` (ánh xạ MITRE ATT&CK)
> - `recommendations` (khuyến nghị phòng thủ)
> - `recon_summary` (tóm tắt kết quả recon)
>
> **Mô hình học từ đâu?**
> - Isolation Forest fit trên 8 **baseline samples** hardcode trong `risk_model.py`, đại diện cho các tình huống exposure thấp/trung bình.
> - Mẫu mới (target đang scan) có đặc trưng **khác biệt** với baseline → anomaly score cao → risk cao.

---

**Câu 2.** File báo cáo `.pi/results/ket_qua.md` được tạo ra như thế nào? Có mấy chế độ sinh báo cáo? Nếu không có API key của OpenAI thì sao?

> [!success]- Đáp án tham khảo
>
> **Quy trình sinh báo cáo (Stage 3):**
> 1. Đọc `risk_profile.json`.
> 2. Đọc `report_prompt.md` (prompt template).
> 3. **Chọn chế độ sinh báo cáo:**
>    - **AI mode:** Nếu có `OPENAI_API_KEY` → gọi OpenAI GPT-4o với prompt + risk_profile JSON.
>    - **Offline mode:** Nếu không có key / `--offline` / API lỗi → dùng `build_offline_report()` trong `report_templates.py`.
>
> **Kết quả:** File `ket_qua.md` luôn có các section: Target, Recon Summary, Risk Level, ML Risk Model, Findings, MITRE ATT&CK Mapping, Recommendations, Conclusion.
>
> **Nếu không có API key:**
> - Pipeline **không crash** — tự động fallback về offline template.
> - Báo cáo offline có format giống AI report nhưng đơn giản hơn, liệt kê số liệu thô.
> - Có dòng `> Offline fallback used: No API key found` ở cuối báo cáo.
>
> **Đây là điểm mạnh của thiết kế:** Demo bảo vệ đồ án không phụ thuộc vào API bên ngoài.

---

### B.2 — Level 2: Hiểu code (Dòng code này làm gì?)

**Câu 3.** Trong file `.pi/tools/risk/risk_model.py`, giải thích thuật toán Isolation Forest qua phương thức `_build_tree()`:

```python
def _build_tree(self, rows, depth, rng):
    if depth >= self.max_depth or len(rows) <= 1 or self._all_rows_same(rows):
        return IsolationNode(size=len(rows), depth=depth)

    splittable_features = [
        index for index in range(len(FEATURE_NAMES))
        if min(row[index] for row in rows) < max(row[index] for row in rows)
    ]
    if not splittable_features:
        return IsolationNode(size=len(rows), depth=depth)

    feature_index = rng.choice(splittable_features)
    minimum = min(row[feature_index] for row in rows)
    maximum = max(row[feature_index] for row in rows)
    threshold = rng.uniform(minimum, maximum)
    ...
```

a) Điều kiện dừng đệ quy là gì?  
b) `splittable_features` lọc ra những feature như thế nào? Tại sao cần bước này?  
c) `threshold = rng.uniform(minimum, maximum)` — tại sao chọn ngẫu nhiên mà không chọn median?

> [!success]- Đáp án tham khảo
>
> **a) 3 điều kiện dừng:**
> 1. `depth >= max_depth` — đạt độ sâu tối đa (`ceil(log2(n))`), tránh cây quá sâu.
> 2. `len(rows) <= 1` — chỉ còn ≤1 mẫu, không thể split tiếp.
> 3. `self._all_rows_same(rows)` — tất cả mẫu giống hệt nhau ở mọi feature → không thể phân biệt.
>
> **b) `splittable_features`:**
> - Lọc ra các feature có giá trị **không đồng nhất** (`min < max`).
> - Nếu tất cả mẫu có `open_port_count = 3` → feature này vô dụng để split.
> - Nếu không có splittable feature nào → dừng sớm thành leaf node.
> - Nếu không check mà vẫn split: `left_rows` hoặc `right_rows` sẽ rỗng → fallback thành leaf → cây không hiệu quả.
>
> **c) Chọn ngẫu nhiên, không phải median:**
> - Đây là **ý tưởng cốt lõi của Isolation Forest**: cô lập mẫu bất thường nhanh nhất có thể.
> - Chọn **ngẫu nhiên** → mẫu bình thường (nằm trong vùng dày đặc) cần nhiều lần split để cô lập. Mẫu bất thường (nằm ngoài) bị cô lập sau ít split hơn.
> - Nếu dùng median (như Decision Tree) → cây cân bằng → mọi mẫu đều cần ~log(n) split → không phân biệt được bình thường / bất thường.

---

**Câu 4.** Trong `risk_scorer.py`, có dòng tính final score:

```python
exposure_adjustment = 1 if target_exposure == "public" and open_ports else 0
final_score = min(10, prediction["predicted_score"] + exposure_adjustment)
```

a) Tại sao public target bị **cộng thêm 1 điểm**?  
b) Việc này có làm sai lệch kết quả ML không?  
c) Tại sao kết quả này được ghi vào `score_adjustments` riêng?

> [!success]- Đáp án tham khảo
>
> **a) Public target + có port mở = rủi ro thực tế cao hơn:**
> - `localhost` có 10 ports mở → chỉ local user mới tiếp cận được.
> - `vulnweb.com` có 1 port mở → cả Internet đều tiếp cận được → rủi ro cao hơn.
> - +1 điểm là **domain knowledge** bổ sung, không đến từ ML model.
>
> **b) Không sai lệch, mà là post-processing có chủ đích:**
> - ML model chỉ thấy feature vector (số lượng port, loại port,...) — **không biết** target là localhost hay public IP.
> - `classify_target_exposure()` bổ sung thông tin này sau khi ML đã predict.
> - Đây là kiến trúc phổ biến: ML cho raw score → business logic điều chỉnh.
>
> **c) Ghi vào `score_adjustments` riêng:**
> - Để **minh bạch** — người đọc biết score gốc từ ML là bao nhiêu, cộng thêm bao nhiêu từ business logic.
> - Dễ debug và giải thích khi bảo vệ đồ án.
> - Ví dụ output: `"score_adjustments": [{"reason": "Public target with exposed services", "points": 1}]`.

---

**Câu 5.** Trong `.pi/tools/reporting/ai_reporter.py`, có logic:

```python
if offline or not api_key or api_key == "your_api_key_here":
    reason = "Offline mode requested" if offline else "No API key found"
    report = build_offline_report(profile, reason=reason)
else:
    try:
        report = generate_ai_report(profile, prompt, selected_model)
    except Exception as exc:
        report = build_offline_report(profile, reason=f"OpenAI API error: {exc}")
```

a) Tại sao phải check `api_key == "your_api_key_here"`?  
b) Nếu OpenAI API bị lỗi (network, rate limit,...), điều gì xảy ra?  
c) Tại sao không để pipeline crash khi API lỗi?

> [!success]- Đáp án tham khảo
>
> **a) Check `"your_api_key_here"`:**
> - Đây là **placeholder** mặc định trong `.env` template. Nếu sinh viên chưa thay bằng key thật → coi như không có key.
> - Tránh gọi OpenAI API với key giả → sẽ bị lỗi authentication → tốn thời gian chờ timeout.
> - Coi đây là trường hợp "offline" để pipeline chạy nhanh với template.
>
> **b) Nếu API lỗi:**
> - Exception được bắt bởi `except Exception as exc`.
> - Fallback về `build_offline_report()` với reason mô tả lỗi cụ thể.
> - Pipeline **không crash**, vẫn có báo cáo để demo.
>
> **c) Không để crash vì:**
> - **Graceful degradation**: Đây là nguyên tắc thiết kế quan trọng — hệ thống vẫn hoạt động (dù ở chế độ giảm cấp) khi dependency bên ngoài fail.
> - Demo bảo vệ đồ án diễn ra suôn sẻ dù không có Internet.
> - Pipeline có 2 chế độ: stable (offline) và enhanced (AI). Offline là baseline không bao giờ fail.

---

### B.3 — Level 3: Thiết kế & Lý do (Tại sao em làm vậy?)

**Câu 6.** Tại sao chọn **Isolation Forest** mà không phải mô hình khác (Random Forest, SVM, Neural Network)? Và tại sao phải **tự implement** từ đầu thay vì dùng `sklearn.ensemble.IsolationForest`?

> [!success]- Đáp án tham khảo
>
> **Tại sao Isolation Forest:**
>
> | Mô hình | Vấn đề với project này |
> |---------|----------------------|
> | Random Forest / SVM | **Supervised** — cần dữ liệu labeled (tấn công / bình thường). Project không có labeled dataset. |
> | Neural Network / Autoencoder | Cần lượng lớn dữ liệu để train. 8 baseline samples không đủ. Phức tạp, khó giải thích. |
> | **Isolation Forest** | **Unsupervised** — chỉ cần baseline "bình thường". Phát hiện anomaly tự nhiên. Đơn giản, dễ giải thích. |
>
> **Tại sao tự implement (không dùng sklearn):**
>
> 1. **Mục đích học thuật:** Đây là môn Lập trình Mạng, không phải production. Tự implement chứng tỏ **hiểu sâu thuật toán**.
> 2. **Giải thích được:** Khi vấn đáp, có thể giải thích từng dòng code `_build_tree()`, `anomaly_score()`. Nếu dùng sklearn → chỉ có 2 dòng `fit()` và `predict()` → không chứng minh được gì.
> 3. **Zero dependency:** Không cần cài sklearn, numpy. Code chạy với Python thuần.
> 4. **Deterministic:** `random_seed=42` đảm bảo kết quả reproducible.

---

**Câu 7.** Trong `risk_model.py`, có công thức calibration:

```python
combined = (calibrated_anomaly * 0.55) + (exposure * 0.45)
```

Tại sao chọn trọng số 0.55 và 0.45? Em đã thử nghiệm các trọng số khác chưa? Nếu thầy bảo "phải là 0.7 và 0.3", em có đồng ý không?

> [!success]- Đáp án tham khảo
>
> **Ý nghĩa của trọng số:**
>
> - **0.55 cho calibrated_anomaly:** Tín hiệu từ ML model (Isolation Forest) — phát hiện mẫu khác biệt với baseline. Chiếm tỉ trọng cao hơn một chút vì đây là **data-driven**.
> - **0.45 cho exposure_severity:** Domain knowledge (số lượng port × trọng số theo loại) — phản ánh mức độ nguy hiểm thực tế. Quan trọng nhưng không áp đảo ML.
>
> **Tại sao 0.55/0.45:**
> - Đây là trọng số **empirical** (thực nghiệm), được chọn để kết quả demo hợp lý:
>   - localhost 1 port HTTP → score thấp (Low)
>   - target public nhiều port nhạy cảm → score cao (High)
> - Có thể tuning qua thử nghiệm.
>
> **Nếu thầy đề xuất 0.7/0.3:**
> - Có thể đồng ý nếu lý do là "ưu tiên ML signal hơn domain knowledge".
> - Nhưng cần kiểm tra: 0.7/0.3 có thể làm localhost 1 port → score quá thấp (bỏ sót risk), hoặc target nhiều port nhưng không nhạy cảm → score quá cao (false positive).
> - Trả lời đúng: "Trọng số này là hyperparameter, có thể điều chỉnh dựa trên validation. Em chọn 0.55/0.45 vì cân bằng giữa ML và domain knowledge cho demo classroom."

---

### B.4 — Level 4: Mở rộng & Phản biện (Nếu thầy đổi yêu cầu thì sao?)

**Câu 8.** Baseline samples hiện tại chỉ có 8 mẫu hardcode. Nếu thầy yêu cầu mô hình học từ **1000 target đã scan** (dữ liệu thực tế), em sẽ mở rộng như thế nào? Có vấn đề gì với Isolation Forest khi dữ liệu lớn không?

> [!success]- Đáp án tham khảo
>
> **Cách mở rộng:**
>
> 1. **Lưu baseline ra file JSON** thay vì hardcode `BASELINE_SAMPLES` trong code:
>    - Mỗi lần scan 1 target → lưu feature vector vào `baseline_data.json`.
>    - Khi đủ 1000 mẫu → dùng file đó để fit model.
>
> 2. **Subsampling:** Isolation Forest không cần fit trên toàn bộ 1000 mẫu. Có thể sample ngẫu nhiên 256 mẫu cho mỗi cây:
>
> ```python
> def fit(self, samples, subsample_size=256):
>     for _ in range(self.n_trees):
>         subset = rng.sample(samples, min(subsample_size, len(samples)))
>         self.trees.append(self._build_tree(subset, 0, rng))
> ```
>
> 3. **Retrain định kỳ:** Khi có dữ liệu mới, retrain model để cập nhật baseline.
>
> **Vấn đề với dữ liệu lớn:**
>
> - **Contamination:** 1000 target "bình thường" có thể chứa outlier thực sự → làm baseline bị "bẩn" → model kém nhạy.
> - **Giải pháp:** Thêm contamination ratio (VD: `contamination=0.1`) để bỏ qua 10% mẫu bất thường nhất khi xây baseline.
> - **Memory:** 1000 samples × 7 features × 64 trees → nhẹ, không vấn đề.
> - **Training time:** O(n_trees × subsample_size × log(subsample_size)) — nhanh.

---

**Câu 9.** Trong file `.pi/tools/pi_recon_agent.py`, có vòng lặp Observe-Think-Act với `max_iterations=8`. Nếu thầy yêu cầu bỏ giới hạn này và để agent chạy đến khi hoàn thành, có vấn đề gì không? Làm sao để đảm bảo agent không loop vô hạn?

> [!success]- Đáp án tham khảo
>
> **Vấn đề nếu bỏ `max_iterations`:**
>
> 1. **Infinite loop:** Model có thể rơi vào trạng thái liên tục gọi tool mà không dừng (VD: liên tục gọi `scan_ports` với tham số khác nhau).
> 2. **Token usage không kiểm soát:** Mỗi iteration tốn token → chi phí API tăng không giới hạn.
> 3. **Không có escape hatch:** Nếu agent "đi lạc" (gọi tool sai, nhận lỗi, thử lại,...) → chạy mãi.
>
> **Cách đảm bảo không loop vô hạn (dù bỏ max_iterations):**
>
> 1. **Rate limiting:** `ToolRuntime._check_rate_limit()` đã có — mỗi tool tối đa 6 lần/60s. Agent sẽ nhận error nếu gọi quá nhiều.
> 2. **Semantic stop condition:** Theo dõi xem đã có `risk_profile.json` và `ket_qua.md` chưa. Nếu cả 2 tồn tại → force stop.
> 3. **Timeout toàn cục:** Wrap toàn bộ agent run trong `signal.alarm()` hoặc `asyncio.wait_for()`.
> 4. **Token budget:** Giới hạn tổng token sử dụng (VD: 10,000 tokens).
> 5. **Circuit breaker:** Nếu 3 lần liên tiếp tool trả về error → stop.
>
> **Trả lời gợi ý:** "`max_iterations=8` là safety net. Trong production, em sẽ kết hợp rate limiting, semantic stop condition, và timeout-based circuit breaker để agent tự dừng an toàn mà không cần hard limit."

---

**Câu 10.** Em hãy mở file `.pi/results/ket_qua.md` và giải thích kết quả cho target `testasp.vulnweb.com`. Tại sao chỉ có 1 port mở (80) nhưng risk level là **Medium** (4/10) chứ không phải Low?

> [!success]- Đáp án tham khảo
>
> Kết quả từ `ket_qua.md`:
>
> | Trường | Giá trị |
> |--------|---------|
> | Target | `testasp.vulnweb.com` |
> | Open ports | `[80]` |
> | Risk Score | **4/10 (Medium)** |
> | Anomaly | 0.5149 |
> | Exposure | 0.335 |
> | Features | open=1, sensitive=0, high_risk=0, db_cache=0, http=1, version_banner=1, dns=3 |
>
> **Tại sao Medium (4) dù chỉ 1 port?**
>
> 1. **Version banner leak:** Port 80 trả về banner có version → `version_banner_count=1` → đây là tín hiệu rủi ro (kẻ tấn công biết version để tìm CVE).
>
> 2. **Target public:** `testasp.vulnweb.com` là public domain → `target_exposure = "public"`.
>    - `exposure_adjustment = +1` (public + có port mở).
>    - ML score gốc: 3 → cộng 1 = 4 (Medium).
>
> 3. **DNS records:** `dns_record_count=3` → domain có public DNS → tăng exposure.
>
> 4. **Công thức calibration:**
>    - `calibrated_anomaly * 0.55 + exposure * 0.45`
>    - `0.5149 * 0.55 + 0.335 * 0.45 = 0.283 + 0.151 = 0.434`
>    - `combined * 10 = 4.34` → làm tròn 4
>
> 5. **So sánh:** Nếu localhost có 1 port HTTP 80, không version leak → score ~2 (Low). Target public + version leak → +2 điểm → Medium. Đây là kết quả hợp lý.

---

## A.5 — Level 5: Code lại theo yêu cầu (Hands-on Coding) — Vũ Văn Thông

> **Hình thức:** Giáo viên yêu cầu sinh viên **mở editor và viết code trực tiếp** để sửa/thêm chức năng.
> **Tiêu chí:** Code chạy được, đúng logic, giải thích được từng dòng.

---

**Câu A5.1 — Sửa `port_scanner.py`: Thêm service name detection**

> **Yêu cầu:** Sửa hàm `scan_ports()` để output JSON có thêm field `services` — mapping từ port sang tên service (dùng dictionary `SERVICE_NAMES` từ `risk_config.py`). Không được import thêm thư viện ngoài.

*Sinh viên phải gõ code trước mặt giáo viên.*

> [!example]- Code mẫu cần viết
>
> ```python
> # Thêm dictionary ở đầu file port_scanner.py (copy từ risk_config hoặc tự định nghĩa)
> SERVICE_NAMES = {
>     21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
>     80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS", 445: "SMB",
>     3306: "MySQL", 5432: "PostgreSQL", 6379: "Redis", 8000: "HTTP-dev",
>     8080: "HTTP-alt",
> }
>
> # Trong hàm scan_ports(), đổi return thành:
> return {
>     "target": target,
>     "scanned_ports": selected_ports,
>     "open_ports": sorted(open_ports),
>     "open_count": len(open_ports),
>     "services": {
>         str(port): SERVICE_NAMES.get(port, "unknown")
>         for port in open_ports
>     },
> }
> ```
>
> **Câu hỏi phụ:** `SERVICE_NAMES.get(port, "unknown")` — tại sao dùng `.get()` thay vì `SERVICE_NAMES[port]`?
> > **Đáp án:** Để tránh `KeyError` nếu port không có trong dictionary.

---

**Câu A5.2 — Sửa `banner_grabber.py`: Thêm FTP banner handler**

> **Yêu cầu:** Thêm xử lý cho port **21 (FTP)**. FTP server tự gửi banner `220 ...` khi kết nối, không cần gửi request. Sửa hàm `grab_banner()` để:
> - Nếu port == 21: **chỉ đọc** banner (không gửi request)
> - Banner trả về phải được cắt 500 ký tự như các port khác
> - Nếu port 21 timeout → vẫn trả về `"No banner"`

*Sinh viên phải gõ code trước mặt giáo viên.*

> [!example]- Code mẫu cần viết
>
> ```python
> def grab_banner(target: str, port: int, timeout: float = 1.0) -> str:
>     try:
>         with socket.create_connection((target, port), timeout=timeout) as sock:
>             sock.settimeout(timeout)
>
>             # FTP handler: server gửi banner ngay khi kết nối
>             if port == 21:
>                 try:
>                     data = sock.recv(1024)
>                     return _clean_banner(data)
>                 except socket.timeout:
>                     return "No banner"
>
>             # HTTP handler: server chờ request mới gửi response
>             if port in HTTP_PORTS:
>                 request = f"HEAD / HTTP/1.1\r\nHost: {target}\r\nConnection: close\r\n\r\n"
>                 sock.sendall(request.encode("utf-8"))
>
>             try:
>                 data = sock.recv(1024)
>                 return _clean_banner(data)
>             except socket.timeout:
>                 return "No banner"
>     except OSError:
>         return "No banner"
> ```
>
> **Câu hỏi phụ:** Tại sao code FTP phải nằm **trước** HTTP check? Nếu đảo thứ tự thì sao?
> > **Đáp án:** Port 21 không nằm trong `HTTP_PORTS` nên thứ tự không ảnh hưởng. Nhưng nếu một port vừa là FTP vừa là HTTP_PORT (không thể), thì check FTP trước sẽ đúng với behavior của protocol. Quan trọng là phải `return` ngay sau khi xử lý FTP để không rơi vào code HTTP.

---

**Câu A5.3 — Sửa `tool_utils.py`: Thêm CIDR range parsing**

> **Yêu cầu:** Viết thêm hàm `expand_cidr(cidr: str) -> list[str]` để parse CIDR notation (VD: `192.168.1.0/30` → `['192.168.1.0', '192.168.1.1', '192.168.1.2', '192.168.1.3']`). Không dùng thư viện `ipaddress` (vì project muốn giữ dependency nhẹ).

*Sinh viên phải gõ code trước mặt giáo viên.*

> [!example]- Code mẫu cần viết
>
> ```python
> def expand_cidr(cidr: str) -> list[str]:
>     """Parse CIDR notation without external libraries.
>     Example: '192.168.1.0/30' -> ['192.168.1.0', '192.168.1.1', '192.168.1.2', '192.168.1.3']
>     """
>     ip_part, prefix_part = cidr.split("/")
>     prefix = int(prefix_part)
>
>     if not 0 <= prefix <= 32:
>         raise ValueError(f"Invalid prefix length: {prefix}")
>
>     # Convert IP to 32-bit integer
>     octets = [int(octet) for octet in ip_part.split(".")]
>     if len(octets) != 4 or any(o < 0 or o > 255 for o in octets):
>         raise ValueError(f"Invalid IP: {ip_part}")
>
>     ip_int = (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]
>
>     # Calculate network mask
>     mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
>     network = ip_int & mask
>     broadcast = network | (~mask & 0xFFFFFFFF)
>
>     # Generate all IPs in range
>     result = []
>     for addr in range(network, broadcast + 1):
>         result.append(
>             f"{(addr >> 24) & 0xFF}."
>             f"{(addr >> 16) & 0xFF}."
>             f"{(addr >> 8) & 0xFF}."
>             f"{addr & 0xFF}"
>         )
>     return result
> ```
>
> **Câu hỏi phụ:** CIDR `/30` có bao nhiêu IP usable? `/24`? `/32`?
> > **Đáp án:** `/30` → 4 IP (2 usable, bỏ network & broadcast). `/24` → 256 IP (254 usable). `/32` → 1 IP (chính nó).

---

**Câu A5.4 — Sửa `dns_enum.py`: Thêm CAA record query**

> **Yêu cầu:** Thêm record type **CAA** (Certification Authority Authorization) vào `DNS_RECORD_TYPES`. Record CAA cho biết CA nào được phép cấp TLS certificate cho domain. Không cần format đặc biệt — dùng `str(answer).rstrip(".")` như các record khác.

*Sinh viên phải gõ code trước mặt giáo viên.*

> [!example]- Code mẫu cần viết
>
> ```python
> # Sửa dòng 14 trong dns_enum.py
> DNS_RECORD_TYPES = ["A", "CNAME", "MX", "NS", "SOA", "TXT", "CAA"]
> ```
>
> **Chỉ cần 1 dòng.** Nhưng sinh viên phải giải thích:
> - Tại sao thêm CAA không cần sửa `_format_answer()` — vì CAA không có format đặc biệt như MX hay TXT, nên `str(answer).rstrip(".")` dùng được.
> - CAA record format: `flags tag value` (VD: `0 issue "letsencrypt.org"`) — `str(answer)` sẽ trả về chuỗi này.
> - Không cần sửa vòng lặp `for record_type in DNS_RECORD_TYPES` — nó tự động query thêm CAA.
>
> **Câu hỏi phụ:** CAA record giúp ích gì cho defensive recon?
> > **Đáp án:** Biết được CA nào được phép cấp certificate → phát hiện misconfiguration (VD: CA lạ được authorize). Nếu attacker cố tình thêm CAA record giả, có thể phát hiện sớm.

---

**Câu A5.5 — Sửa `main_pipeline.py`: Thêm progress callback**

> **Yêu cầu:** Sửa `run_recon_stage()` để **in ra màn hình** tên task mỗi khi một task hoàn thành. Dùng `print()` với format: `[DONE] <task_name>` (thay vì chỉ dùng `logging.info()` ghi ra file log).

*Sinh viên phải gõ code trước mặt giáo viên.*

> [!example]- Code mẫu cần viết
>
> ```python
> # Trong vòng lặp as_completed của run_recon_stage()
> for future in as_completed(futures):
>     task_name = futures[future]
>     if task_name == "port":
>         port_result = future.result()
>         write_json(port_path, port_result)
>         print("[DONE] port_scan")              # THÊM DÒNG NÀY
>         logging.info("Port scan completed: %s", port_result.get("open_ports", []))
>     elif task_name == "dns":
>         dns_result = future.result()
>         write_json(dns_path, dns_result)
>         print("[DONE] dns_enum")               # THÊM DÒNG NÀY
>         logging.info("DNS enumeration completed")
>     else:
>         banner_result = future.result()
>         write_json(banner_path, banner_result)
>         print("[DONE] banner_grab")            # THÊM DÒNG NÀY
>         logging.info("Banner grabbing completed")
> ```
>
> **Câu hỏi phụ:** Nếu 3 task in ra màn hình theo thứ tự khác nhau mỗi lần chạy, điều đó chứng tỏ điều gì?
> > **Đáp án:** Chứng tỏ các task **thực sự chạy song song** và hoàn thành không theo thứ tự submit. Port scan có thể xong cuối cùng, DNS xong đầu tiên, hoặc ngược lại — phụ thuộc vào network condition.

---

**Câu A5.6 — Sửa `permission_gate_agent.md`: Thêm quy tắc thời gian**

> **Yêu cầu:** Sửa file `.pi/agents/permission_gate_agent.md` để thêm quy tắc: **Chỉ cho phép scan trong giờ hành chính (8:00-18:00)**. Nếu ngoài giờ, trả về `blocked` với reason: `"Scanning only allowed between 08:00-18:00"`.

*Sinh viên chỉ cần sửa file .md (system prompt của agent), không cần code Python.*

> [!example]- Nội dung cần thêm vào permission_gate_agent.md
>
> Thêm vào phần **Action** (sau bước 2):
>
> ```markdown
> 3. Kiem tra thoi gian hien tai. Neu ngoai khoang 08:00-18:00, tra ve blocked
>    voi reason: "Scanning only allowed between 08:00-18:00".
> ```
>
> Và đánh số lại các bước cũ. Hoặc thêm vào phần **Safety**:
>
> ```markdown
> - Chi cho phep scan trong gio hanh chinh (08:00-18:00) de tranh scan ngoai gio.
> ```
>
> **Câu hỏi phụ:** Trong Python, làm sao để check giờ hiện tại?
> > **Đáp án:**
> ```python
> from datetime import datetime
> now = datetime.now().hour
> if not 8 <= now < 18:
>     return {"allowed": False, "reason": "Scanning only allowed between 08:00-18:00"}
> ```

---

**Câu A5.7 — Sửa `recon_risk_pipeline.chain.md`: Thêm Stage 4 — Cleanup**

> **Yêu cầu:** Thêm **Stage 4 vào chain.md** có tên `cleanup_agent`. Agent này sẽ xóa các file tạm (`.pi/triage/*.json`) sau khi report đã được tạo thành công. Mô tả input, output, handoff contract.

*Sinh viên chỉ cần viết markdown.*

> [!example]- Nội dung cần thêm vào chain.md
>
> ```markdown
> ## Stage 4: Cleanup
>
> Agent:
> - `cleanup_agent`
>
> Process:
> 1. Confirm `.pi/results/ket_qua.md` exists.
> 2. Delete all `.json` files in `.pi/triage/`.
> 3. Log cleanup result.
>
> Output:
> - Clean `.pi/triage/` directory.
>
> Handoff Contract:
> - Only run after Stage 3 has successfully generated the report.
> - Do not delete `ket_qua.md` or log files.
> - If cleanup fails, log the error but do not fail the pipeline.
> ```
>
> Và cập nhật handoff summary:
>
> ```text
> orchestrator_agent
>   -> permission_gate_agent
>   -> /parallel
>        port_scan_agent
>        dns_enum_agent
>        banner_grab_agent
>      /join
>   -> risk_score_agent
>   -> report_agent
>   -> cleanup_agent       # THÊM
> ```

---

## B.5 — Level 5: Code lại theo yêu cầu (Hands-on Coding) — Nguyễn Thành An

> **Hình thức:** Giáo viên yêu cầu sinh viên **mở editor và viết code trực tiếp** để sửa/thêm chức năng.
> **Tiêu chí:** Code chạy được, đúng logic, giải thích được từng dòng.

---

**Câu B5.1 — Sửa `risk_config.py`: Thêm port group mới**

> **Yêu cầu:** Thêm một port group mới `MAIL_PORTS = {25, 110, 143, 465, 587, 993, 995}` và thêm feature `mail_port_count` vào `FEATURE_NAMES`. Cập nhật tất cả các file liên quan.

*Sinh viên phải xác định được những file nào cần sửa và gõ code.*

> [!success]- Các file cần sửa
>
> **1. `risk_config.py`:**
> ```python
> MAIL_PORTS = {25, 110, 143, 465, 587, 993, 995}
>
> FEATURE_NAMES = [
>     "open_port_count",
>     "sensitive_port_count",
>     "high_risk_port_count",
>     "database_cache_port_count",
>     "http_port_count",
>     "version_banner_count",
>     "dns_record_count",
>     "mail_port_count",  # THÊM
> ]
> ```
>
> **2. `risk_features.py` — thêm vào `extract_features()`:**
> ```python
> feature_map = {
>     # ... existing features ...
>     "mail_port_count": len([port for port in open_ports if port in MAIL_PORTS]),  # THÊM
> }
> ```
> Nhớ import `MAIL_PORTS` từ `risk_config`.
>
> **3. `risk_model.py` — sửa `BASELINE_SAMPLES`:**
> Thêm 1 phần tử thứ 8 (mail_port_count) vào mỗi baseline sample. VD:
> ```python
> [0, 0, 0, 0, 0, 0, 0, 0],  # thêm số 0 cuối
> [1, 0, 0, 0, 1, 0, 0, 0],
> # ...
> ```
>
> **4. `risk_model.py` — sửa `exposure_severity()` và `explain_exposure()`:**
> Thêm trọng số cho `mail_port_count`:
> ```python
> + feature_map["mail_port_count"] * 1.0
> ```

---

**Câu B5.2 — Sửa `risk_model.py`: Đổi số cây Isolation Forest**

> **Yêu cầu:** Sửa `SimpleIsolationForestRiskModel` để dùng **128 cây** thay vì 64, và thêm `random_seed` làm tham số truyền từ ngoài vào (hiện tại đang hardcode `42`). Cập nhật `predict_with_isolation_forest()` để cho phép tùy chỉnh `n_trees` và `seed`.

*Sinh viên phải gõ code trước mặt giáo viên.*

> [!example]- Code cần sửa
>
> **1. Sửa `predict_with_isolation_forest()` trong `risk_model.py`:**
>
> ```python
> def predict_with_isolation_forest(
>     feature_map: dict,
>     n_trees: int = 128,        # ĐỔI từ 64 → 128
>     random_seed: int = 42,
> ) -> dict:
>     vector = to_vector(feature_map)
>     model = SimpleIsolationForestRiskModel(
>         n_trees=n_trees,        # TRUYỀN THAM SỐ
>         random_seed=random_seed,
>     )
>     model.fit(BASELINE_SAMPLES)
>     # ... phần còn lại giữ nguyên ...
> ```
>
> **2. Cập nhật `risk_scorer.py` nếu cần:**
> ```python
> prediction = predict_with_isolation_forest(feature_map, n_trees=128, random_seed=42)
> ```
>
> **3. Cập nhật output `ml_model`:**
> ```python
> "n_trees": prediction["n_trees"],  # sẽ tự động là 128
> ```
>
> **Câu hỏi phụ:** Tăng số cây từ 64 → 128 có tác dụng gì? Có nhược điểm gì không?
> > **Đáp án:** 
> > - **Tác dụng:** Ổn định hơn (reduced variance), anomaly score ít bị ảnh hưởng bởi ngẫu nhiên.
> > - **Nhược điểm:** Chậm gấp đôi khi fit (128 cây thay vì 64), tốn gấp đôi bộ nhớ. Với baseline 8 mẫu, không đáng kể.

---

**Câu B5.3 — Sửa `report_templates.py`: Thêm báo cáo tiếng Việt**

> **Yêu cầu:** Viết hàm mới `build_offline_report_vn(profile, reason)` tạo báo cáo Markdown **bằng tiếng Việt**. Tất cả section headers, labels phải bằng tiếng Việt: "Mục tiêu", "Tóm tắt Recon", "Mức độ rủi ro", "Mô hình ML", "Phát hiện", "Ánh xạ MITRE ATT&CK", "Khuyến nghị", "Kết luận". Giữ nguyên logic.

*Sinh viên phải gõ code trước mặt giáo viên.*

> [!example]- Code mẫu cần viết
>
> ```python
> def build_offline_report_vn(profile: dict, reason: str = "Khong co API key") -> str:
>     """Tao bao cao Markdown bang tieng Viet."""
>     summary = profile.get("recon_summary", {})
>     open_ports = summary.get("open_ports", [])
>     dns_message = summary.get("dns_message", "")
>     banners = summary.get("banners", {})
>     services = summary.get("services", {})
>     findings = profile.get("findings", [])
>     mitre_mapping = profile.get("mitre_mapping", [])
>     ml_model = profile.get("ml_model", {})
>     recommendations = profile.get("recommendations", [])
>
>     risk_label_vn = {"Low": "Thấp", "Medium": "Trung bình", "High": "Cao"}
>     risk_level = profile.get("risk_level", "Low")
>
>     lines = [
>         "# Báo cáo Network Recon + Risk Profiler",
>         "",
>         "## Mục tiêu",
>         f"- Mục tiêu: `{profile.get('target', 'không xác định')}`",
>         "",
>         "## Tóm tắt Recon",
>         f"- Port đang mở: `{open_ports}`",
>         f"- Trạng thái DNS: {dns_message or 'N/A'}",
>         f"- Banner: `{banners}`",
>         f"- Dịch vụ: `{services}`",
>         "",
>         "## Mức độ rủi ro",
>         f"- Điểm: `{profile.get('score', 0)}`",
>         f"- Mức: **{risk_label_vn.get(risk_level, risk_level)}**",
>         "",
>         "## Mô hình ML",
>         f"- Mô hình: {ml_model.get('name', 'N/A')}",
>         f"- Loại: {ml_model.get('type', 'N/A')}",
>         f"- Điểm bất thường: `{ml_model.get('anomaly_score', 'N/A')}`",
>         f"- Đặc trưng: `{ml_model.get('features', {})}`",
>         "",
>         "## Phát hiện",
>     ]
>
>     if findings:
>         for finding in findings:
>             techniques = ", ".join(finding.get("mitre_technique_ids", [])) or "N/A"
>             lines.append(f"- {finding.get('description')} MITRE: `{techniques}`")
>     else:
>         lines.append("- Không có phát hiện đáng chú ý.")
>
>     lines.extend(["", "## Ánh xạ MITRE ATT&CK"])
>
>     if mitre_mapping:
>         for item in mitre_mapping:
>             lines.append(
>                 f"- `{item.get('technique_id')}` {item.get('technique')} "
>                 f"({item.get('tactic')}): {item.get('defensive_note')}"
>             )
>     else:
>         lines.append("- Không có ánh xạ MITRE.")
>
>     lines.extend(["", "## Khuyến nghị"])
>     for item in recommendations:
>         lines.append(f"- {item}")
>
>     lines.extend([
>         "",
>         "## Kết luận",
>         "Báo cáo này chỉ dành cho mục đích đánh giá phòng thủ trên hệ thống được ủy quyền. "
>         "Ưu tiên đóng các dịch vụ không cần thiết, giới hạn phạm vi truy cập, "
>         "giảm thiểu lộ thông tin banner và xem xét kết quả scan cùng chuyên gia.",
>         "",
>         f"> Chế độ offline: {reason}",
>     ])
>
>     return "\n".join(lines)
> ```
>
> **Câu hỏi phụ:** Làm thế nào để `ai_reporter.py` tự động chọn báo cáo tiếng Việt?
> > **Đáp án:** Thêm tham số `lang="en"` vào `generate_report()`. Nếu `lang="vi"` và không có API key → gọi `build_offline_report_vn()`. Nếu có API key → thêm "Write in Vietnamese" vào prompt.

---

**Câu B5.4 — Sửa `report_prompt.md`: Thêm section "Timeline"**

> **Yêu cầu:** Sửa file `.pi/prompts/report_prompt.md` để thêm 1 section bắt buộc mới: **"Timeline"** — mô tả thời gian hoàn thành từng stage (dựa trên `stage_durations` trong pipeline output). Cập nhật danh sách `Required sections`.

*Sinh viên sửa file .md, sau đó giải thích code Python cần thay đổi theo.*

> [!example]- Nội dung sửa
>
> **Sửa `report_prompt.md`:**
> ```markdown
> Required sections:
>
> 1. Target
> 2. Recon Summary
> 3. Timeline
> 4. Risk Level
> 5. ML Risk Model
> 6. Findings
> 7. MITRE ATT&CK Mapping
> 8. Recommendations
> 9. Conclusion
> ```
>
> **Code Python cần thay đổi (`report_templates.py`):**
> Thêm vào `build_offline_report()`:
> ```python
> stage_durations = profile.get("recon_summary", {}).get("stage_durations", {})
> # Hoặc lấy từ pipeline output dict
>
> lines.extend([
>     "## Timeline",
>     f"- Recon: {stage_durations.get('recon', 'N/A')}s",
>     f"- Risk Scoring: {stage_durations.get('risk', 'N/A')}s",
>     f"- Report: {stage_durations.get('report', 'N/A')}s",
>     "",
> ])
> ```
>
> **Câu hỏi phụ:** Timeline data hiện đang nằm ở đâu trong pipeline? Làm sao để risk_profile.json có được thông tin này?
> > **Đáp án:** Timeline data hiện nằm trong return dict của `run_pipeline()` trong `main_pipeline.py` nhưng **không được lưu vào risk_profile.json**. Cần sửa `score_risk()` hoặc `save_risk_profile()` để nhận thêm `stage_durations` và đưa vào `recon_summary`.

---

**Câu B5.5 — Sửa `risk_scorer.py`: Thay đổi ngưỡng phân loại**

> **Yêu cầu:** Sửa hàm `label_from_score()` trong `risk_model.py` (được gọi từ `risk_scorer.py`) để thay đổi ngưỡng:
> - **0-2: Low**
> - **3-7: Medium**
> - **8-10: High**
>
> *(Hiện tại: 0-3 Low, 4-6 Medium, 7-10 High)*
>
> Sau đó giải thích: với kết quả hiện tại (`testasp.vulnweb.com` score=4), risk level sẽ thay đổi thế nào?

*Sinh viên phải gõ code trước mặt giáo viên.*

> [!example]- Code cần sửa
>
> ```python
> # Trong risk_model.py, sửa hàm label_from_score:
> def label_from_score(score: int) -> str:
>     """Map numeric score sang risk label."""
>     if score <= 2:       # ĐỔI từ 3 → 2
>         return "Low"
>     if score <= 7:       # ĐỔI từ 6 → 7
>         return "Medium"
>     return "High"
> ```
>
> **Ảnh hưởng đến `testasp.vulnweb.com` (score=4):**
> - Cũ: 4 ≤ 6 → **Medium** ✓
> - Mới: 4 ≤ 7 → **Medium** (vẫn là Medium)
> - Nhưng 1 target có score=3:
>   - Cũ: 3 ≤ 3 → **Low**
>   - Mới: 3 > 2 → **Medium** (tăng mức rủi ro!)
>
> **Câu hỏi phụ:** Việc thay đổi ngưỡng này có ý nghĩa gì trong thực tế?
> > **Đáp án:** Giảm false negative (bỏ sót rủi ro) — target điểm 3 bây giờ được coi là Medium thay vì Low. Nhưng tăng false positive (báo động giả). Đây là trade-off giữa sensitivity và specificity. Trong security, thường ưu tiên giảm false negative (không bỏ sót mối đe dọa).

---

**Câu B5.6 — Sửa `ai_reporter.py`: Hỗ trợ streaming response**

> **Yêu cầu:** Sửa `generate_ai_report()` để dùng **streaming** (in từng chunk ra màn hình khi GPT đang generate report) thay vì đợi toàn bộ response rồi mới trả về. Sử dụng `stream=True` trong OpenAI API call.

*Sinh viên phải gõ code trước mặt giáo viên.*

> [!example]- Code mẫu cần viết
>
> ```python
> def generate_ai_report(profile: dict, prompt: str, model: str) -> str:
>     """Call OpenAI API with streaming to create the Markdown report."""
>     from openai import OpenAI
>
>     base_url = os.getenv("OPENAI_BASE_URL", "").strip() or DEFAULT_OPENAI_BASE_URL
>     client = OpenAI(base_url=base_url)
>
>     stream = client.chat.completions.create(
>         model=model,
>         temperature=0.2,
>         stream=True,  # BẬT STREAMING
>         messages=[
>             {
>                 "role": "system",
>                 "content": "You write concise defensive cybersecurity reports in Markdown.",
>             },
>             {
>                 "role": "user",
>                 "content": (
>                     f"{prompt}\n\n"
>                     "Risk profile JSON:\n"
>                     f"```json\n{json.dumps(profile, indent=2, ensure_ascii=False)}\n```"
>                 ),
>             },
>         ],
>     )
>
>     # Thu thập từng chunk và in ra màn hình
>     full_report = []
>     print("[AI] Dang sinh bao cao...", end=" ", flush=True)
>     for chunk in stream:
>         if chunk.choices[0].delta.content is not None:
>             content = chunk.choices[0].delta.content
>             full_report.append(content)
>             print(content, end="", flush=True)  # In từng chunk
>     print()  # newline
>
>     return "".join(full_report).strip()
> ```
>
> **Câu hỏi phụ:** Streaming có lợi ích gì so với non-streaming trong project này?
> > **Đáp án:**
> > - **UX tốt hơn:** Người dùng thấy report được tạo dần, không phải chờ 5-10 giây rồi hiện toàn bộ.
> > - **Demo ấn tượng hơn:** Khi bảo vệ đồ án, streaming cho thấy AI đang hoạt động.
> > - **Early abort:** Nếu thấy output sai hướng, có thể dừng sớm (không tốn thêm token).

---

**Câu B5.7 — Sửa `risk_findings.py`: Thêm MITRE technique T1190**

> **Yêu cầu:** Thêm ánh xạ MITRE ATT&CK `T1190 — Exploit Public-Facing Application` vào `build_mitre_mapping()` khi target có **HTTP port (80, 443, 8000, 8080) đang mở**. Mapping này chỉ mang tính cảnh báo phòng thủ: "Public-facing web apps are common attack vectors".

*Sinh viên phải gõ code trước mặt giáo viên.*

> [!example]- Code cần thêm
>
> ```python
> # Trong build_mitre_mapping(), thêm sau phần check open_ports:
>
> if any(port in open_ports for port in HTTP_PORTS):
>     mappings.append(
>         {
>             "technique_id": "T1190",
>             "technique": "Exploit Public-Facing Application",
>             "tactic": "Initial Access",
>             "evidence": f"HTTP service detected on ports: "
>                         f"{[p for p in open_ports if p in HTTP_PORTS]}",
>             "defensive_note": (
>                 "Keep web servers patched, use WAF, and regularly test "
>                 "for common vulnerabilities (OWASP Top 10)."
>             ),
>         }
>     )
> ```
>
> Nhớ import `HTTP_PORTS` từ `risk_config`.
>
> **Câu hỏi phụ:** `T1190` thuộc tactic nào trong MITRE ATT&CK? Tactic đó nằm ở giai đoạn nào của kill chain?
> > **Đáp án:** T1190 thuộc tactic **Initial Access** — đây là giai đoạn đầu tiên trong cyber kill chain, khi attacker tìm cách xâm nhập vào hệ thống qua lỗ hổng ở ứng dụng public-facing. Khác với T1046 (Discovery) và T1595 (Reconnaissance) là các bước trước đó.

---

**Câu B5.8 — Tổng hợp: Viết agent mới `notify_agent.md`**

> **Yêu cầu:** Viết file `.pi/agents/notify_agent.md` — một agent mới gửi email thông báo sau khi pipeline hoàn thành. File phải có đầy đủ frontmatter (name, description, tools) và system prompt với các phần: Role, Input, Action, Output, Safety.

*Sinh viên phải viết toàn bộ file .md trước mặt giáo viên.*

> [!success]- File mẫu cần viết
>
> ```markdown
> ---
> name: notify_agent
> description: Agent gui email thong bao ket qua pipeline cho admin.
> tools:
>   - .pi/tools/notify/smtp_sender.py
> ---
>
> # System Prompt
>
> Ban la Notify Agent cua Topic 02.
>
> ## Role
>
> Gui email thong bao ket qua pipeline sau khi report da duoc tao thanh cong.
>
> ## Input
>
> - `.pi/results/ket_qua.md`: bao cao hoan chinh.
> - `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `NOTIFY_EMAIL` tu `.env`.
>
> ## Action
>
> 1. Doc file bao cao.
> 2. Tao email voi tieu de: "[Topic 02] Pipeline completed for <target>".
> 3. Noi dung email gom: target, risk level, score, link den report (neu co).
> 4. Gui email qua SMTP.
> 5. Ghi log ket qua gui mail.
>
> ## Output
>
> Tra ve `{"sent": true/false, "recipient": "...", "error": "..."}`.
>
> ## Safety
>
> - Khong gui email neu khong co NOTIFY_EMAIL trong .env.
> - Khong gui attachment report ra ngoai neu chua duoc uy quyen.
> - Gioi han toi da 1 email moi lan chay pipeline.
> ```

---

## A.6 — Level 6: Chuyên sâu — Vũ Văn Thông

> **Mục tiêu:** Kiểm tra hiểu biết sâu về network programming, socket, thread, và kiến trúc pipeline.
> **Hình thức:** Hỏi đáp + vẽ sơ đồ + giải thích từng dòng code phức tạp.

---

**Câu A6.1 — Socket programming: `create_connection` vs raw socket**

> Trong `port_scanner.py`, em dùng `socket.create_connection((target, port), timeout=timeout)`. Hãy viết lại hàm `scan_port()` **không dùng `create_connection`** mà dùng raw socket với `socket()`, `settimeout()`, `connect()`. Giải thích sự khác biệt.

> [!example]- Code mẫu & giải thích
>
> ```python
> # Cách hiện tại (dùng create_connection)
> def scan_port(target, port, timeout=0.5):
>     try:
>         with socket.create_connection((target, port), timeout=timeout):
>             return True
>     except (OSError, socket.timeout):
>         return False
>
> # Viết lại bằng raw socket
> def scan_port_raw(target, port, timeout=0.5):
>     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
>     sock.settimeout(timeout)
>     try:
>         sock.connect((target, port))
>         return True
>     except (OSError, socket.timeout):
>         return False
>     finally:
>         sock.close()
> ```
>
> **Sự khác biệt:**
>
> | `create_connection` | Raw socket |
> |---------------------|------------|
> | Tự động resolve hostname (gọi `getaddrinfo`) | Phải resolve thủ công trước |
> | Tự động thử tất cả địa chỉ IP trả về (IPv4, IPv6) | Chỉ connect đến 1 địa chỉ |
> | Return socket object đã connect | Phải gọi `connect()` thủ công |
> | Dùng `with` statement (context manager) | Phải tự `close()` trong `finally` |
> | Ngắn gọn, an toàn hơn | Kiểm soát chi tiết hơn (VD: chọn `AF_INET` vs `AF_INET6`) |

---

**Câu A6.2 — Race condition trong parallel execution**

> Trong `main_pipeline.py`, 3 task chạy song song và cùng ghi ra 3 file JSON khác nhau. Có thể xảy ra race condition không? Nếu có, khi nào? Nếu không, tại sao?

> [!success]- Đáp án
>
> **Không có race condition trong trường hợp này** vì:
>
> 1. **3 file output khác nhau:** Mỗi task ghi vào file riêng:
>    - `port_scan_result.json`
>    - `dns_enum_result.json`
>    - `banner_result.json`
>
> 2. **Không chia sẻ biến mutable:** Các task không ghi vào cùng 1 dict hay list. Kết quả được `return` riêng, sau đó `as_completed` loop gán vào biến cục bộ khác nhau (`port_result`, `dns_result`, `banner_result`).
>
> 3. **`write_json` là atomic ở mức file:** Mỗi lần gọi `write_json` mở file mới, ghi toàn bộ nội dung rồi đóng. Không có append.
>
> **Khi nào có thể xảy ra race condition:**
>
> - Nếu 2 task cùng ghi vào **cùng 1 file** (VD: cùng ghi log).
> - Nếu 2 task cùng modify **cùng 1 list/dict** không có lock.
> - Trong project này, `logging` module đã có built-in thread-safety cho file handler.

---

**Câu A6.3 — DNS resolution flow trong `tool_utils.py`**

> Giải thích từng bước trong hàm `resolve_target()`:
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
- `socket.getaddrinfo()` trả về cấu trúc gì? Tại sao lại là `item[4][0]`?
- Tại sao dùng `set` comprehension `{...}` thay vì `list`?
- `type=socket.SOCK_STREAM` có ý nghĩa gì?

> [!success]- Đáp án
>
> **`socket.getaddrinfo(host, port, ...)` trả về list of tuples:**
> ```python
> [
>     (family, socktype, proto, canonname, sockaddr),
>     # VD: (<AddressFamily.AF_INET>, <SocketKind.SOCK_STREAM>, 6, '', ('93.184.216.34', 0))
> ]
> ```
> - `item[4]` = `sockaddr` → tuple `(ip, port)`
> - `item[4][0]` = IP address (string)
>
> **Dùng set comprehension:**
> - Một hostname có thể resolve ra nhiều IP (VD: load balancer, dual-stack IPv4+IPv6).
> - `set` tự động deduplicate nếu trùng IP.
>
> **`type=socket.SOCK_STREAM`:**
> - Lọc chỉ lấy địa chỉ phù hợp với **TCP** (SOCK_STREAM).
> - Bỏ qua SOCK_DGRAM (UDP) hoặc SOCK_RAW.
> - Phù hợp với project chỉ scan TCP.

---

**Câu A6.4 — Timeout handling: Tại sao cần `validate_timeout`?**

> Hàm `validate_timeout()` trong `tool_utils.py`:
```python
def validate_timeout(timeout: float) -> float:
    if not 0.01 <= timeout <= 30:
        raise ValueError("Timeout must be between 0.01 and 30 seconds.")
    return timeout
```
- Tại sao chặn dưới 0.01s? Điều gì xảy ra nếu timeout = 0?
- Tại sao chặn trên 30s?

> [!success]- Đáp án
>
> **Chặn dưới 0.01s:**
> - Timeout = 0 → non-blocking socket → `connect()` trả về ngay lập tức, thường là lỗi `BlockingIOError` → mọi port đều bị đánh dấu là closed/filtered (sai).
> - Timeout quá nhỏ (0.001s) → không đủ thời gian cho TCP 3-way handshake, đặc biệt qua mạng LAN/WAN.
> - 0.01s là đủ nhanh để không treo pipeline nhưng vẫn cho phép RTT trong LAN.
>
> **Chặn trên 30s:**
> - Với 16 ports × 30s = 480s (8 phút) — quá lâu cho demo lớp học.
> - Nếu 1 port treo 30s, nhân với 50 workers song song → vẫn 30s wall-clock, nhưng có thể che giấu vấn đề mạng.
> - 30s là đủ cho hầu hết kịch bản thực tế.
>
> **Trong thực tế nmap:**
> - nmap dùng timeout động (dynamic timeout) — bắt đầu với timeout cao, giảm dần dựa trên response time của các port trước đó.

---

**Câu A6.5 — HTTP HEAD vs GET trong banner grabber**

> Trong `banner_grabber.py`, em dùng `HEAD /` request. Tại sao không dùng `GET /`? Sự khác biệt là gì? Nếu server không hỗ trợ HEAD method thì sao?

> [!success]- Đáp án
>
> | HEAD | GET |
> |------|-----|
> | Chỉ trả về **header** (status line + headers) | Trả về header **+ body** (toàn bộ nội dung trang) |
> | Nhẹ, nhanh, tốn ít băng thông | Có thể tải về hàng MB HTML không cần thiết |
> | Server **bắt buộc** phải hỗ trợ HEAD (theo HTTP spec) | Luôn được hỗ trợ |
> | Đủ để lấy `Server`, `X-Powered-By` headers cho banner | Lấy được cả nội dung nhưng không cần cho recon |
>
> **Nếu server không hỗ trợ HEAD:**
> - Một số server (đặc biệt là custom/embedded) có thể trả về `405 Method Not Allowed` hoặc `501 Not Implemented`.
> - Vẫn có thể đọc được response headers → vẫn hữu ích cho banner grabbing.
> - Fallback: có thể thử GET nếu HEAD bị từ chối — nhưng project chọn đơn giản, không retry.

---

**Câu A6.6 — Tại sao `banner_grabber.py` inspect TLS riêng?**

> Hàm `inspect_tls()` dùng `ssl.create_default_context()` với `check_hostname=False` và `verify_mode=ssl.CERT_NONE`. Tại sao lại tắt verify? Có nguy hiểm không?

> [!success]- Đáp án
>
> ```python
> context = ssl.create_default_context()
> context.check_hostname = False   # Không check hostname match
> context.verify_mode = ssl.CERT_NONE  # Không verify certificate chain
> ```
>
> **Tại sao tắt verify:**
> 1. **Mục đích là recon, không phải security audit:** Chỉ muốn đọc certificate metadata (subject, issuer, not_after) — không cần validate.
> 2. **Self-signed certificate:** Lab target (localhost, internal IP) thường dùng self-signed cert → nếu verify sẽ fail → không đọc được metadata.
> 3. **Expired certificate:** Vẫn muốn ghi nhận thông tin cert dù đã hết hạn.
>
> **Có nguy hiểm không?**
> - **Không**, vì:
>   - Chỉ đọc thông tin public của certificate (không gửi data nhạy cảm).
>   - Không tin tưởng certificate — chỉ thu thập metadata.
>   - Kết quả được ghi rõ là từ TLS inspection không verified.

---

**Câu A6.7 — Data flow: Cách các file JSON kết nối các stage**

> Vẽ sơ đồ data flow: mỗi file JSON được tạo ra ở stage nào, được đọc ở stage nào. File nào là "hợp đồng" (contract) giữa các stage? Nếu đổi format của `port_scan_result.json` thì những file nào bị ảnh hưởng?

> [!success]- Đáp án
>
> ```
> Stage 1 (Parallel Recon)
>   port_scanner.py        ──write──▶ port_scan_result.json
>   dns_enum.py            ──write──▶ dns_enum_result.json
>   banner_grabber.py      ──write──▶ banner_result.json
>                                          │
>                                          │ read (all 3)
>                                          ▼
> Stage 2 (Risk Scoring)
>   risk_scorer.py         ──read───▶ (3 files above)
>        │
>        └──write──▶ risk_profile.json
>                          │
>                          │ read
>                          ▼
> Stage 3 (Report)
>   ai_reporter.py         ──read───▶ risk_profile.json
>        │
>        └──write──▶ ket_qua.md
> ```
>
> **Contract files (giao diện giữa các stage):**
> - `port_scan_result.json` — contract giữa Stage 1 và Stage 2
> - `dns_enum_result.json` — contract giữa Stage 1 và Stage 2
> - `banner_result.json` — contract giữa Stage 1 và Stage 2
> - `risk_profile.json` — contract giữa Stage 2 và Stage 3
>
> **Nếu đổi format `port_scan_result.json`:**
> Ảnh hưởng đến:
> - `risk_scorer.py` dòng `open_ports = [int(port) for port in port_result.get("open_ports", [])]`
> - `risk_features.py` dùng `open_ports` làm input
> - `risk_findings.py` dùng `open_ports` để build findings
> - Các file chỉ **đọc** `port_scan_result.json`

---

## B.6 — Level 6: Chuyên sâu — Nguyễn Thành An

> **Mục tiêu:** Kiểm tra hiểu biết sâu về ML model, feature engineering, calibration, và kiến trúc agent.
> **Hình thức:** Hỏi đáp + vẽ sơ đồ + giải thích công thức toán.

---

**Câu B6.1 — Toán học Isolation Forest: Công thức `c(n)`**

> Trong `risk_model.py`, hàm `average_path_length()` tính `c(n)`:
```python
def average_path_length(sample_size: int) -> float:
    if sample_size <= 1:
        return 0.0
    if sample_size == 2:
        return 1.0
    harmonic = math.log(sample_size - 1) + 0.5772156649
    return 2.0 * harmonic - (2.0 * (sample_size - 1) / sample_size)
```
- Hằng số `0.5772156649` là gì?
- Tại sao `n <= 1` trả về 0.0 và `n == 2` trả về 1.0?
- Công thức này dùng để làm gì trong anomaly score?

> [!success]- Đáp án
>
> **Hằng số Euler-Mascheroni (γ ≈ 0.5772156649):**
> - Đây là hằng số toán học γ, xuất hiện trong ước lượng harmonic number: `H(n) ≈ ln(n) + γ`.
> - Dùng để tính kỳ vọng độ dài đường đi trung bình trong cây nhị phân ngẫu nhiên.
>
> **Trường hợp đặc biệt:**
> - `n ≤ 1`: không có cây → path length = 0.
> - `n = 2`: cây có 2 node → 1 split là đủ để cô lập → path length = 1.
>
> **Vai trò trong anomaly score:**
> - `c(n)` là **normalization factor**.
> - Anomaly score = `2^(-E(h(x)) / c(n))`.
> - `E(h(x))` = path length trung bình của mẫu x qua tất cả các cây.
> - Nếu `E(h(x)) << c(n)` → mẫu bị cô lập nhanh hơn mong đợi → anomaly score cao → bất thường.
> - Nếu `E(h(x)) ≈ c(n)` → mẫu có độ sâu trung bình → anomaly score ≈ 0.5 → bình thường.

---

**Câu B6.2 — Feature Engineering: Giải thích trọng số**

> Trong `exposure_severity()`, mỗi feature có trọng số khác nhau:
```python
weighted_total = (
    feature_map["open_port_count"] * 0.8
    + feature_map["sensitive_port_count"] * 1.2
    + feature_map["high_risk_port_count"] * 2.0
    + feature_map["database_cache_port_count"] * 1.4
    + feature_map["http_port_count"] * 0.7
    + feature_map["version_banner_count"] * 1.1
    + feature_map["dns_record_count"] * 0.25
)
```
- Tại sao `high_risk_port_count` có trọng số cao nhất (2.0)?
- Tại sao `dns_record_count` có trọng số thấp nhất (0.25)?
- Tại sao `http_port_count` lại **thấp hơn** `open_port_count` (0.7 < 0.8) dù HTTP là service phổ biến nhất?

> [!success]- Đáp án
>
> **`high_risk_port_count` = 2.0 (cao nhất):**
> - Các port: Telnet (23), SMB (445), Redis (6379).
> - Telnet: không mã hóa, truyền password plaintext.
> - SMB: từng có lỗ hổng EternalBlue (WannaCry).
> - Redis: thường không có auth mặc định → RCE.
> - Mỗi port này mở là **red flag** nghiêm trọng.
>
> **`dns_record_count` = 0.25 (thấp nhất):**
> - DNS records là thông tin **public** theo thiết kế.
> - Nhiều DNS record không đồng nghĩa với rủi ro cao (VD: domain lớn có nhiều MX, NS).
> - Nhưng **có** record → target là domain thật (không phải IP ẩn danh) → vẫn có chút exposure.
>
> **`http_port_count` = 0.7 < `open_port_count` = 0.8:**
> - HTTP port **phổ biến** và **cần thiết** cho web app → không phải lúc nào cũng là rủi ro.
> - Nhưng mở port HTTP không cần thiết (VD: dev server port 8000 public) vẫn là rủi ro.
> - `open_port_count` cao hơn vì **mọi port mở đều tăng attack surface**, không phân biệt loại.

---

**Câu B6.3 — Tại sao cần calibration 2 bước?**

> Trong `predict_with_isolation_forest()`, score cuối cùng được tính qua 3 bước:
> 1. `anomaly_score` (từ Isolation Forest)
> 2. `calibrated_anomaly` (dùng baseline stats)
> 3. `combined = calibrated_anomaly * 0.55 + exposure * 0.45`
>
> Tại sao không dùng thẳng `anomaly_score`?

> [!success]- Đáp án
>
> **Vấn đề với `anomaly_score` thô:**
>
> - Isolation Forest anomaly score ∈ [0, 1], nhưng không tuyến tính với mức độ rủi ro.
> - Score 0.5 không hẳn là "rủi ro 50%".
> - Baseline samples cũng có anomaly score > 0 (vì chúng cũng có độ khác biệt nhỏ với nhau).
>
> **Bước 1: `calibrated_anomaly`**
> - So sánh anomaly score của target với **phân phối baseline**.
> - Nếu target nằm trong 1 std của baseline mean → calibrated = 0 (coi như bình thường).
> - Nếu target vượt ngưỡng → scale lên [0, 1].
> - Cắt nhiễu: target hơi khác baseline không bị coi là bất thường.
>
> **Bước 2: Kết hợp `exposure_severity`**
> - `calibrated_anomaly`: ML model nói "target này khác baseline".
> - `exposure_severity`: Domain knowledge nói "các features này nguy hiểm".
> - Kết hợp 0.55/0.45: cân bằng giữa data-driven và expert knowledge.
>
> **Nếu bỏ calibration:**
> - Target bình thường có thể có score 3-4 → false positive.
> - Khó giải thích "tại sao score này" khi bảo vệ.

---

**Câu B6.4 — Agent loop state management**

> Trong `pi_recon_agent.py`, lịch sử hội thoại (messages list) được quản lý như thế nào qua từng iteration? Vẽ sơ đồ state của `messages` list sau mỗi bước: system prompt → user request → assistant (tool_calls) → tool results → assistant (final).

> [!success]- Đáp án
>
> ```
> Iteration 0 (khởi tạo):
> messages = [
>     {"role": "system", "content": "You are the Topic 02 Orchestrator..."},
>     {"role": "user", "content": "Investigate target localhost..."},
> ]
>
> Iteration 1 (model chọn tools):
> response = client.chat.completions.create(messages, tools=TOOLS, tool_choice="auto")
> → finish_reason = "tool_calls"
> → message.tool_calls = [
>     {id: "call_1", function: {name: "scan_ports", arguments: '{"target":"localhost"}'}},
>     {id: "call_2", function: {name: "enumerate_dns", arguments: '{"target":"localhost"}'}},
>     {id: "call_3", function: {name: "grab_banners", arguments: '{"target":"localhost"}'}},
> ]
>
> messages.append({
>     "role": "assistant",
>     "content": None,
>     "tool_calls": [{"id": "call_1", ...}, {"id": "call_2", ...}, {"id": "call_3", ...}]
> })
>
> # Gọi 3 tool song song
> messages.extend([
>     {"role": "tool", "tool_call_id": "call_1", "content": '{"open_ports": [80]}'},
>     {"role": "tool", "tool_call_id": "call_2", "content": '{"skipped": true}'},
>     {"role": "tool", "tool_call_id": "call_3", "content": '{"banners": {...}}'},
> ])
>
> Iteration 2 (model gọi risk scoring):
> → finish_reason = "tool_calls"
> → message.tool_calls = [{id: "call_4", function: {name: "score_risk_from_triage"}}]
>
> messages.append(assistant + tool_calls)
> messages.append(tool result for call_4)
>
> Iteration 3 (model gọi report):
> → finish_reason = "tool_calls"
> → message.tool_calls = [{id: "call_5", function: {name: "generate_markdown_report"}}]
>
> messages.append(assistant + tool_calls)
> messages.append(tool result for call_5)
>
> Iteration 4 (model kết thúc):
> → finish_reason = "stop"
> → message.content = "Pipeline completed. Outputs: ..."
> ```
>
> **Tại sao phải append assistant message (có tool_calls) TRƯỚC khi append tool results?**
>
> OpenAI API yêu cầu: sau mỗi assistant message có `tool_calls`, phải có các `role: "tool"` message với `tool_call_id` khớp. Nếu không, API sẽ báo lỗi `400: missing tool results`.

---

**Câu B6.5 — Safety constraints trong AI prompt**

> File `report_prompt.md` có 4 quy tắc bắt buộc:
> - Do not include exploit steps.
> - Do not include payloads.
> - Do not include brute-force, bypass, or real attack guidance.
> - Only provide defensive observations and recommendations.
>
> Nếu bỏ 4 dòng này khỏi prompt, GPT-4o có tự động viết nội dung tấn công không? Prompt injection có phải là rủi ro trong project này không?

> [!success]- Đáp án
>
> **GPT-4o có tự viết nội dung tấn công không?**
>
> - GPT-4o có **safety filter** tích hợp, thường từ chối viết exploit/payload.
> - Nhưng nếu input chứa chi tiết kỹ thuật (VD: port SMB 445 open, version Windows XP), model có thể suy luận ra CVE và mô tả cách khai thác trong bối cảnh "phân tích kỹ thuật".
> - Prompt constraint là **defense-in-depth**: chặn từ phía application, không phụ thuộc hoàn toàn vào model safety.
>
> **Prompt injection:**
>
> - CÓ rủi ro: `risk_profile.json` được tạo từ output của công cụ recon. Nếu target trả về banner chứa text độc hại (VD: embedded prompt injection), nó sẽ được đưa vào JSON → vào GPT prompt.
> - Mitigation:
>   - Banner bị cắt 500 ký tự (`_clean_banner`) → giới hạn độ dài injection.
>   - Prompt constraint cứng ở đầu → model ưu tiên tuân theo system prompt.
>   - Offline template fallback → nếu API bị abuse, vẫn có backup.

---

**Câu B6.6 — Tại sao `BASELINE_SAMPLES` chỉ có 8 mẫu? Đủ không?**

> Baseline của Isolation Forest chỉ có 8 mẫu hardcode. Nếu thầy nói "8 mẫu là quá ít, em hãy chứng minh nó đủ hoặc đề xuất cách cải thiện", em trả lời thế nào?

> [!success]- Đáp án
>
> **Tại sao 8 mẫu hiện tại đủ cho demo:**
>
> 1. **Không gian feature nhỏ:** Chỉ có 7 features, mỗi feature có giá trị nguyên nhỏ (0-5). Tổng số tổ hợp khả dĩ ~ vài trăm. 8 mẫu đã phủ được các trường hợp thấp/trung bình.
>
> 2. **Mục đích học thuật:** Đây là classroom demo, không phải production. 8 mẫu đủ để minh họa Isolation Forest hoạt động, và sinh viên có thể giải thích từng mẫu.
>
> 3. **Isolation Forest không cần nhiều dữ liệu:** Không như deep learning, Isolation Forest hoạt động tốt với sample nhỏ vì nó dựa trên cấu trúc cây ngẫu nhiên.
>
> **Cách cải thiện:**
>
> 1. **Tự động sinh baseline:** Chạy scan trên 50-100 target đã biết là "an toàn" → lưu feature vectors.
> 2. **Data augmentation:** Từ 8 mẫu, tạo biến thể bằng cách ±1 cho mỗi feature → mở rộng lên ~50-100 mẫu.
> 3. **Kết nối dataset thực:** Dùng CICIDS hoặc NSL-KDD để có baseline lớn hơn.
> 4. **Dynamic baseline:** Mỗi lần scan target mới và được xác nhận là "bình thường" → thêm vào baseline.

---

**Câu B6.7 — So sánh agentic mode vs deterministic mode**

> Khi nào dùng `main_pipeline.py` (deterministic), khi nào dùng `pi_recon_agent.py` (agentic)? Cho ví dụ cụ thể về một tình huống mà agentic mode **tốt hơn** deterministic mode, và một tình huống ngược lại.

> [!success]- Đáp án
>
> | Tiêu chí | Deterministic (`main_pipeline.py`) | Agentic (`pi_recon_agent.py`) |
> |----------|-----------------------------------|-------------------------------|
> | **Kết quả** | Luôn giống nhau với cùng input | Có thể khác nhau (model quyết định tool) |
> | **Tốc độ** | Nhanh (không gọi API) | Chậm hơn (nhiều API calls) |
> | **Chi phí** | Miễn phí | Tốn OpenAI token |
> | **Phụ thuộc** | Không cần Internet | Cần Internet + API key |
> | **Linh hoạt** | Cứng nhắc (cố định 3 stage) | Linh hoạt (model chọn tool, thứ tự) |
>
> **Agentic tốt hơn khi:**
> - Target không xác định trước: model có thể thử scan port trước, thấy HTTP thì probe thêm, thấy database thì dừng.
> - Cần xử lý lỗi thông minh: port scan fail → model tự quyết định retry với timeout lớn hơn.
> - Người dùng không rành CLI: model tự chọn ports, tự quyết định workflow.
>
> **Deterministic tốt hơn khi:**
> - Demo bảo vệ đồ án (cần kết quả reproducible).
> - Môi trường offline (không Internet).
> - Cần audit trail chính xác (mỗi lần chạy giống hệt nhau).
> - Batch processing 1000 targets (agentic sẽ quá chậm + tốn kém).

---

## D. Câu hỏi chung — Cả 2 sinh viên cùng trả lời

> **Mục tiêu:** Đảm bảo cả 2 sinh viên đều hiểu **toàn bộ dự án**, không chỉ phần mình phụ trách.
> **Hình thức:** Giáo viên hỏi 1 sinh viên, sinh viên kia bổ sung. Hoặc hỏi cả 2 cùng lúc.

---

### D.1 — Kiến trúc tổng thể

**Câu D1.** Vẽ lên bảng toàn bộ kiến trúc dự án: có bao nhiêu stage, mỗi stage có những agent nào, input/output là gì. Chỉ rõ đâu là **file Python**, đâu là **file .md**, đâu là **file cấu hình**.

> [!success]- Đáp án tham khảo
>
> ```
> ┌─────────────────────────────────────────────────────────┐
> │ NGƯỜI DÙNG                                               │
> │ python .pi/tools/main_pipeline.py --target localhost     │
> └──────────────────────┬──────────────────────────────────┘
>                        ▼
> ┌─────────────────────────────────────────────────────────┐
> │ STAGE 0: SAFETY GATE                                     │
> │ Agent:  permission_gate_agent.md       (.md system prompt)│
> │ Tool:   tool_utils.py (is_target_allowed)  (.py function)│
> │ Config: allowed_targets.json            (.json data)     │
> │ Output: allowed/blocked decision                         │
> └──────────────────────┬──────────────────────────────────┘
>                        ▼ (nếu allowed)
> ┌─────────────────────────────────────────────────────────┐
> │ STAGE 1: PARALLEL RECON  (ThreadPoolExecutor, workers=3) │
> │                                                          │
> │ Agent 1A: port_scan_agent.md                             │
> │ Tool:     port_scanner.py (scan_ports)                   │
> │ Output:   port_scan_result.json                          │
> │                                                          │
> │ Agent 1B: dns_enum_agent.md                              │
> │ Tool:     dns_enum.py (enumerate_dns)                    │
> │ Output:   dns_enum_result.json                           │
> │                                                          │
> │ Agent 1C: banner_grab_agent.md                           │
> │ Tool:     banner_grabber.py (grab_banners)               │
> │ Output:   banner_result.json                             │
> └──────────────────────┬──────────────────────────────────┘
>                        ▼ (cả 3 file JSON đã có)
> ┌─────────────────────────────────────────────────────────┐
> │ STAGE 2: ML RISK SCORING                                 │
> │ Agent:  risk_score_agent.md                              │
> │ Tools:  risk_scorer.py, risk_model.py,                   │
> │         risk_features.py, risk_findings.py, risk_config.py│
> │ Input:  port_scan_result.json, dns_enum_result.json,     │
> │         banner_result.json                               │
> │ Output: risk_profile.json                                │
> └──────────────────────┬──────────────────────────────────┘
>                        ▼
> ┌─────────────────────────────────────────────────────────┐
> │ STAGE 3: REPORT GENERATION                               │
> │ Agent:  report_agent.md                                  │
> │ Tools:  ai_reporter.py, report_templates.py,             │
> │         openai_report_client.py                          │
> │ Input:  risk_profile.json, report_prompt.md              │
> │ Config: .env (OPENAI_API_KEY)                            │
> │ Output: ket_qua.md                                       │
> └─────────────────────────────────────────────────────────┘
>
> ORCHESTRATION:
>   Chain:   recon_risk_pipeline.chain.md  (đặc tả pipeline)
>   Runner:  main_pipeline.py              (code chạy pipeline)
>   Skills:  recon/SKILL.md, risk-scoring/SKILL.md, reporting/SKILL.md
>
> WEEK 5 EXTENSION:
>   Agentic: pi_recon_agent.py  (OpenAI Observe-Think-Act loop)
> ```

---

**Câu D2.** Mô tả **data flow** giữa các stage bằng đúng 1 câu cho mỗi lần chuyển giao. Dùng format: "Stage X tạo ra file Y → Stage Z đọc file Y để làm gì".

> [!success]- Đáp án
>
> 1. **Stage 0 → Stage 1:** Permission Gate Agent trả về `allowed=True` → Orchestrator gọi 3 Recon Agent song song.
> 2. **Stage 1 → Stage 2:** 3 Recon Agent tạo ra 3 file JSON → Risk Score Agent đọc cả 3 file để trích xuất features và dự đoán risk.
> 3. **Stage 2 → Stage 3:** Risk Score Agent tạo ra `risk_profile.json` → Report Agent đọc file này để sinh báo cáo Markdown.
> 4. **Stage 3 → User:** Report Agent ghi `ket_qua.md` → User mở file để xem kết quả.

---

### D.2 — Hiểu về Parallelism

**Câu D3.** Cả nhóm hãy giải thích: **Parallelism trong project này nằm ở đâu?** Có mấy tầng parallelism? Tại sao không cần lock hay mutex?

> [!success]- Đáp án
>
> **3 tầng parallelism:**
>
> | Tầng | Vị trí | Cơ chế | Số workers |
> |------|--------|--------|------------|
> | **1. Inter-agent** | `main_pipeline.py` → `run_recon_stage()` | `ThreadPoolExecutor` | 3 (port, dns, banner) |
> | **2. Per-port (scan)** | `port_scanner.py` → `scan_ports()` | `ThreadPoolExecutor` | ≤50 (mỗi port 1 thread) |
> | **3. Per-port (banner)** | `banner_grabber.py` → `grab_banners()` | `ThreadPoolExecutor` | ≤50 (mỗi port 1 thread) |
>
> **Tại sao không cần lock/mutex:**
> - Mỗi task ghi vào **file output riêng** (3 file JSON khác nhau).
> - Mỗi thread scan 1 port → append vào **list riêng**, không share biến mutable.
> - Kết quả được thu thập qua `future.result()` trong main thread → tuần tự hóa tự nhiên.
> - Nếu dùng chung 1 list, sẽ cần `threading.Lock()`.

---

**Câu D4.** Nếu chạy pipeline với tham số `--ports "1-1000"` (1000 ports), hãy ước tính thời gian chạy:
- Với serial execution (không parallelism): ? giây
- Với per-port parallelism (50 workers): ? giây
- Với cả inter-agent + per-port parallelism: ? giây

> [!success]- Đáp án
>
> Giả định: mỗi port mất trung bình **0.1s** (port đóng trả lời ngay) đến **0.5s** (port mở/timeout).
> Trung bình ~0.3s/port.
>
> | Chế độ | Công thức | Thời gian (1000 ports) |
> |--------|-----------|----------------------|
> | Serial (1 thread) | 1000 × 0.3s | **300s (5 phút)** |
> | Per-port only (50 workers) | 1000/50 × 0.3s | **6s** |
> | Inter-agent + per-port | max(port_scan, dns, banner) ≈ 6s | **~6-7s** |
>
> **Lưu ý:**
> - DNS enum chạy độc lập, thường <1s → không ảnh hưởng.
> - Banner grab chạy song song với port scan, cũng mất ~6s → wall-clock ≈ max(6s, 6s, <1s) ≈ 6s.
> - **Tổng pipeline:** 6s (recon) + 1s (risk) + 1s (report offline) ≈ **8s**.

---

### D.3 — Hiểu về Agent, Tool, Skill, Chain

**Câu D5.** Trong Pi Coding Agent framework, phân biệt 4 khái niệm:
- **Agent** (`.pi/agents/*.md`)
- **Tool** (`.pi/tools/*.py`)
- **Skill** (`.pi/skills/*/SKILL.md`)
- **Chain** (`.pi/chains/*.chain.md`)

Cho ví dụ cụ thể từ project này.

> [!success]- Đáp án
>
> | Khái niệm | Định nghĩa | Ví dụ trong project |
> |-----------|------------|---------------------|
> | **Agent** | File `.md` định nghĩa **vai trò, system prompt, tools được phép dùng** của một AI agent. Frontmatter có `name`, `description`, `tools`. | `port_scan_agent.md`: agent chuyên quét port, chỉ được dùng tool `port_scanner.py` |
> | **Tool** | File `.py` implement **hàm cụ thể** có thể được gọi bởi agent hoặc pipeline. | `port_scanner.py` với hàm `scan_ports()` — thực hiện TCP connect scan |
> | **Skill** | File `SKILL.md` mô tả **quy trình/năng lực** mà agent có thể thực hiện, bao gồm nhiều tools. | `recon/SKILL.md`: mô tả skill "thu thập thông tin recon", gồm port scan + DNS enum + banner grab |
> | **Chain** | File `.chain.md` đặc tả **thứ tự và điều kiện chuyển giao** giữa các agent trong pipeline. | `recon_risk_pipeline.chain.md`: định nghĩa Stage 0→1→2→3, handoff contract, /parallel directive |
>
> **Quan hệ:** Chain → gọi Agent → Agent dùng Tool → nhiều Tool hợp thành Skill.

---

### D.4 — An toàn & Đạo đức

**Câu D6.** Project có những cơ chế an toàn nào? Nếu một sinh viên khác copy code của em và scan `https://vnexpress.net` thì chuyện gì xảy ra?

> [!success]- Đáp án
>
> **Các cơ chế an toàn:**
>
> 1. **Permission Gate (Stage 0):** Mọi target phải qua `is_target_allowed()`.
> 2. **Allowlist:** Chỉ `localhost`, `127.0.0.1`, `scanme.nmap.org`, `vulnweb.com`,... được phép mặc định.
> 3. **`--authorized` flag:** Phải có xác nhận tường minh từ user.
> 4. **Timeout giới hạn:** 0.01-30s, tránh treo kết nối.
> 5. **Read-only:** Không gửi payload exploit, không brute force.
> 6. **Rate limiting (agentic mode):** Mỗi tool tối đa 6 lần/60s.
> 7. **Prompt constraints:** Report prompt cấm exploit steps, payload, bypass.
>
> **Nếu scan `vnexpress.net`:**
>
> ```
> [BLOCKED] Permission gate blocked this target. Use localhost, 127.0.0.1,
> scanme.nmap.org, or add --authorized only when you have permission.
> ```
>
> - `vnexpress.net` không có trong `allowed_targets.json`.
> - Không có `--authorized` → `is_target_allowed()` trả về `False`.
> - `PermissionError` được raise → pipeline dừng **trước khi có bất kỳ kết nối mạng nào**.

---

### D.5 — Vận hành & Gỡ lỗi

**Câu D7.** Giáo viên gõ lệnh:
```bash
python .pi/tools/main_pipeline.py --target localhost --ports "8000,8080"
```
Nhưng pipeline báo lỗi: `ConnectionRefusedError: [Errno 61] Connection refused` cho tất cả các port. Hãy debug:
- Lỗi này xảy ra ở đâu trong code?
- Nguyên nhân có thể là gì?
- Cách khắc phục?

> [!success]- Đáp án
>
> **Lỗi xảy ra ở đâu:**
> - Trong `port_scanner.py`, hàm `scan_port()`, dòng `socket.create_connection((target, port), timeout=timeout)`.
> - `ConnectionRefusedError` bị bắt bởi `except (OSError, socket.timeout)` → trả về `False` (port closed).
> - **Nhưng** nếu `ConnectionRefusedError` xuất hiện ở **tất cả** port, có thể là:
>
> **Nguyên nhân có thể:**
> 1. **Không có service nào chạy trên localhost:8000 và localhost:8080.** → Hợp lệ! Pipeline vẫn chạy bình thường, tất cả port đều `closed`. Không phải lỗi.
> 2. **Firewall chặn loopback.** (Hiếm, nhưng có thể trên Windows với firewall strict).
> 3. **Sai host.** Dùng `localhost` nhưng `/etc/hosts` bị sai.
>
> **Cách khắc phục:**
> 1. Mở terminal khác, chạy: `python -m http.server 8000 --bind 127.0.0.1`
> 2. Chạy lại pipeline → port 8000 sẽ là `open`.

---

**Câu D8.** Làm thế nào để **chạy thử từng stage riêng lẻ** mà không cần chạy toàn bộ pipeline? Viết lệnh cụ thể.

> [!success]- Đáp án
>
> **Chạy riêng từng tool:**
>
> ```bash
> # Stage 1A: Chỉ chạy port scanner
> python .pi/tools/recon/port_scanner.py --target localhost --ports "8000,8080"
>
> # Stage 1B: Chỉ chạy DNS enumeration
> python .pi/tools/recon/dns_enum.py --target scanme.nmap.org
>
> # Stage 1C: Chỉ chạy banner grabber
> python .pi/tools/recon/banner_grabber.py --target localhost --ports "8000,8080"
> ```
>
> **Chạy Stage 2 riêng (cần có sẵn 3 file JSON):**
>
> ```bash
> python .pi/tools/risk/risk_scorer.py \
>   --port-file .pi/triage/port_scan_result.json \
>   --dns-file .pi/triage/dns_enum_result.json \
>   --banner-file .pi/triage/banner_result.json \
>   --output .pi/triage/risk_profile.json
> ```
>
> **Chạy Stage 3 riêng (cần có risk_profile.json):**
>
> ```bash
> python .pi/tools/reporting/ai_reporter.py \
>   --risk-profile .pi/triage/risk_profile.json \
>   --output .pi/results/ket_qua.md \
>   --offline
> ```
>
> **Tại sao cần chạy riêng từng stage:**
> - Debug: Stage 2 lỗi → không cần chạy lại Stage 1 (mất thời gian).
> - Phát triển: Sinh viên A sửa port scanner → chỉ test Stage 1.
> - Demo: Có thể demo từng phần riêng biệt.

---

### D.6 — So sánh với công cụ thực tế

**Câu D9.** So sánh project này với các công cụ thực tế:
- Port scanner trong project vs **nmap**: khác gì?
- DNS enum trong project vs **dig**: khác gì?
- Banner grabber trong project vs **netcat/telnet**: khác gì?
- Risk scoring trong project vs **Nessus/OpenVAS**: khác gì?

> [!success]- Đáp án
>
> | Tính năng | Project (Topic 02) | Công cụ thực tế |
> |-----------|-------------------|-----------------|
> | **Port scan** | TCP connect scan, 16 ports default, Python socket | **nmap**: SYN scan (stealth), UDP scan, OS detection, NSE scripts, 1000 ports default |
> | **DNS enum** | A/MX/NS/TXT/SOA/CNAME, dnspython | **dig**: mọi record type, DNSSEC, +trace, recursive query control |
> | **Banner grab** | HEAD request cho HTTP, đọc passive cho TCP | **netcat/telnet**: manual, không tự động. **nmap -sV**: probe-based version detection |
> | **Risk scoring** | Isolation Forest nhỏ, 7 features, 8 baseline | **Nessus/OpenVAS**: CVE database, CVSS scoring, plugin-based, authenticated scan |
>
> **Điểm mạnh của project so với công cụ thực tế:**
> - **Tích hợp AI/ML**: Kết hợp recon + ML scoring + AI report trong 1 pipeline.
> - **Multi-agent**: Kiến trúc agent-based, dễ mở rộng.
> - **Giải thích được**: Từng dòng code đều hiểu và giải thích được → phù hợp học thuật.

---

### D.7 — Mở rộng dự án

**Câu D10.** Nếu được thêm **1 tính năng** vào project này, em sẽ thêm gì? Giải thích:
- Tính năng đó là gì?
- Cần thêm/sửa những file nào?
- Thêm vào stage nào?

> [!success]- Gợi ý trả lời (mở, tùy sinh viên)
>
> **Ví dụ 1: Web vulnerability scanner nhẹ (cho port HTTP)**
> - Thêm vào Stage 1 (song song): probe SQLi, XSS cơ bản trên form.
> - File mới: `.pi/tools/recon/web_scanner.py`, `.pi/agents/web_scan_agent.md`.
> - Cập nhật: `risk_features.py` thêm feature `web_vuln_count`.
>
> **Ví dụ 2: Historical comparison**
> - Lưu kết quả mỗi lần scan vào database.
> - So sánh với lần scan trước → phát hiện port mới mở, port bị đóng.
> - File mới: `.pi/tools/history/db.py`.
> - Thêm Stage 4: `diff_agent`.
>
> **Ví dụ 3: Real-time alerting (Telegram/Slack webhook)**
> - Nếu risk = High → gửi alert qua webhook.
> - File mới: `.pi/tools/notify/webhook.py`.
> - Thêm Stage 4: `alert_agent`.

---

### D.8 — Câu hỏi tổng hợp cuối cùng

**Câu D11.** Cả 2 em hãy cùng nhau chạy pipeline **từ đầu đến cuối** trước mặt thầy (không cần code, chỉ chạy). Giải thích từng dòng output xuất hiện trên màn hình. Khi pipeline hoàn thành, mở file `ket_qua.md` và giải thích từng phần trong báo cáo.

> [!success]- Các bước thực hiện
>
> **Terminal 1:**
> ```bash
> python -m http.server 8000 --bind 127.0.0.1
> # Output: Serving HTTP on 127.0.0.1 port 8000 ...
> ```
>
> **Terminal 2:**
> ```bash
> python .pi/tools/main_pipeline.py --target localhost --ports "8000,8080,3306" --offline
> ```
>
> **Output mong đợi + giải thích:**
>
> ```
> Pipeline completed.                                     ← Pipeline không lỗi
> - status: "completed"                                   ← Trạng thái
> - target: "localhost"                                   ← Target đã scan
> - resolved_addresses: ["127.0.0.1"]                     ← DNS resolve kết quả
> - offline_report: true                                   ← Dùng offline template
> - duration_seconds: 1.2345                               ← Tổng thời gian
> - stage_durations:                                       ← Thời gian từng stage
>     recon: 0.8s         ← Stage 1 nhanh vì 3 task song song
>     risk: 0.3s          ← Stage 2 nhanh (model nhỏ)
>     report: 0.1s        ← Stage 3 offline template rất nhanh
> - port_scan_result: .pi/triage/port_scan_result.json    ← Output Stage 1A
> - dns_enum_result: .pi/triage/dns_enum_result.json      ← Output Stage 1B
> - banner_result: .pi/triage/banner_result.json          ← Output Stage 1C
> - risk_profile: .pi/triage/risk_profile.json            ← Output Stage 2
> - report: .pi/results/ket_qua.md                        ← Output Stage 3
> - log: .pi/logs/pipeline_run.log                        ← Log file
> ```
>
> **Mở `ket_qua.md`:**
> - Target: `localhost`
> - Recon Summary: open ports `[8000]` (HTTP server đang chạy), DNS skipped
> - Risk Level: Low (vì chỉ 1 HTTP port, localhost)
> - ML Risk Model: SimpleIsolationForestRiskModel
> - Findings: Port 8000 open
> - MITRE ATT&CK Mapping: T1046, T1595
> - Recommendations: đóng port không cần thiết,...
> - Conclusion: defensive only

---

### Cách dùng cho giáo viên (khi vấn đáp)

1. **Chọn câu hỏi theo level phù hợp với năng lực sinh viên.**
2. **Câu hỏi Level 2** — yêu cầu sinh viên **mở code** và giải thích trực tiếp.
3. **Câu hỏi Level 4** — dùng để phân loại sinh viên giỏi; có thể bỏ qua nếu sinh viên trung bình.
4. **Đáp án là tham khảo** — sinh viên có thể trả lời theo cách khác nhưng vẫn đúng ý chính.

### Cách dùng cho DeepSeek (sinh thêm câu hỏi mới)

Gửi prompt sau cho DeepSeek:

> Dựa trên file CauHoiVanDap_Topic02.md và toàn bộ code project Topic 02, hãy tạo thêm 3 câu hỏi Level 3 cho sinh viên [A/B] về [tên file cụ thể].

### Gợi ý phân bố thời gian vấn đáp

| Sinh viên | Thời gian | Số câu hỏi gợi ý |
|-----------|-----------|-------------------|
| Vũ Văn Thông | 15-20 phút | 5-6 câu (1 L1 + 1-2 L2 + 1 L3 + 1 L4 + **1 L5 code tay**) |
| Nguyễn Thành An | 15-20 phút | 5-6 câu (1 L1 + 1-2 L2 + 1 L3 + 1 L4 + **1 L5 code tay**) |

### Cách chọn câu Level 5 (Code tay)

- **Sinh viên trung bình:** Chọn câu dễ như A5.1 (thêm service name), A5.4 (thêm CAA record), B5.1 (thêm port group), B5.4 (sửa report_prompt.md).
- **Sinh viên khá:** Chọn câu trung bình như A5.2 (FTP handler), A5.5 (progress callback), B5.3 (báo cáo tiếng Việt), B5.5 (đổi ngưỡng).
- **Sinh viên giỏi:** Chọn câu khó như A5.3 (CIDR parser), B5.2 (128 trees + seed tham số), B5.6 (streaming API), B5.8 (viết agent mới từ số 0).

### Tổng số câu hỏi trong file

| Sinh viên | L1 | L2 | L3 | L4 | L5 Code tay | L6 Chuyên sâu | Tổng |
|-----------|----|----|----|----|-------------|---------------|------|
| Vũ Văn Thông | 2 | 3 | 2 | 2 | 7 | 7 | **23** |
| Nguyễn Thành An | 2 | 3 | 2 | 3 | 8 | 7 | **25** |
| Chung cả nhóm | — | — | — | — | — | — | **11** |
| **Tổng toàn file** | **4** | **6** | **4** | **5** | **15** | **14** | **59** |
