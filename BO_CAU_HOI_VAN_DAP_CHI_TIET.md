# Bộ câu hỏi vấn đáp chi tiết Topic 02

> Góc nhìn: giáo viên dùng DeepSeek, Pi Coding Agent, ChatGPT hoặc model khác để đọc toàn bộ source code, file `.md`, skill, chain và report. Bộ câu hỏi này dùng để kiểm tra cả hai sinh viên có thật sự hiểu toàn bộ project, hiểu phần của nhau và có khả năng sửa code theo yêu cầu mới của thầy hay không.

## 1. Phân công nhiệm vụ chi tiết

| MSSV | Thành viên | Vai trò chính | Công việc cụ thể | File phụ trách / cần nắm | Hoàn thành |
|---|---|---|---|---|---|
| 23162098 | Vũ Văn Thông | Thiết kế pipeline, Safety Gate và phase Recon | Thiết kế luồng chạy chính của project từ lúc nhập target đến khi sinh báo cáo. Xây dựng Safety Gate để kiểm tra target có nằm trong allowlist hoặc có `--authorized` hay không. Cài đặt port scanner bằng TCP socket, DNS enumeration bằng `dnspython`, banner grabber bằng socket/HEAD request. Thiết kế Stage 1 chạy song song ba tác vụ recon bằng `ThreadPoolExecutor`. Kiểm thử phase recon và đảm bảo các output JSON được ghi đúng vào `.pi/triage`. | `.pi/tools/main_pipeline.py`, `.pi/tools/common/tool_utils.py`, `.pi/tools/recon/port_scanner.py`, `.pi/tools/recon/dns_enum.py`, `.pi/tools/recon/banner_grabber.py`, `.pi/data/allowed_targets.json`, `.pi/agents/orchestrator_agent.md`, `.pi/agents/permission_gate_agent.md`, `.pi/agents/port_scan_agent.md`, `.pi/agents/dns_enum_agent.md`, `.pi/agents/banner_grab_agent.md`, `.pi/chains/recon_risk_pipeline.chain.md`, `.pi/skills/recon/SKILL.md` | 100% |
| 23162001 | Nguyễn Thành An | Risk scoring, report generation và tổng hợp kết quả | Xây dựng phần trích xuất đặc trưng từ kết quả recon như số port mở, port nhạy cảm, port HTTP, database/cache port, banner lộ version và số DNS record. Cài đặt mô hình Simple Isolation Forest để tính anomaly score, kết hợp exposure severity để ra điểm rủi ro 0-10 và mức Low/Medium/High. Tạo findings, MITRE ATT&CK mapping và recommendations. Xây dựng phần sinh báo cáo Markdown, hỗ trợ OpenAI API nếu có key và fallback offline nếu không có key. Hoàn thiện báo cáo cuối cùng và phần agentic extension dùng OpenAI tool calling. | `.pi/tools/risk/risk_config.py`, `.pi/tools/risk/risk_features.py`, `.pi/tools/risk/risk_model.py`, `.pi/tools/risk/risk_scorer.py`, `.pi/tools/risk/risk_findings.py`, `.pi/tools/reporting/ai_reporter.py`, `.pi/tools/reporting/report_templates.py`, `.pi/tools/reporting/openai_report_client.py`, `.pi/prompts/report_prompt.md`, `.pi/agents/risk_score_agent.md`, `.pi/agents/report_agent.md`, `.pi/skills/risk-scoring/SKILL.md`, `.pi/skills/reporting/SKILL.md`, `.pi/tools/pi_recon_agent.py`, `.pi/results/ket_qua.md` | 100% |

## 2. Nguyên tắc giáo viên vấn đáp

- Cả hai sinh viên đều phải hiểu tổng thể project, không được chỉ nói "phần này bạn kia làm".
- Khi trả lời phải chỉ được file, hàm, input, output và lý do thiết kế.
- Với câu hỏi code, sinh viên phải biết sửa file nào, thêm logic ở đâu và output thay đổi thế nào.
- Các câu hỏi có thể yêu cầu mở trực tiếp source code và giải thích từng dòng quan trọng.
- Nội dung project là defensive/read-only, không được biến câu trả lời thành hướng dẫn tấn công.

## 3. Phần A - Câu hỏi chung bắt buộc cho cả hai thành viên

### Câu 1. Project này giải quyết bài toán gì?

**Đáp án tham khảo:**  
Project xây dựng pipeline Network Recon + Risk Profiler. Hệ thống kiểm tra target hợp lệ, chạy port scan, DNS enum và banner grabbing song song, sau đó dùng ML để chấm điểm rủi ro và sinh báo cáo Markdown có MITRE ATT&CK mapping.

**File cần mở:** `README.md`, `.pi/tools/main_pipeline.py`.

### Câu 2. Pipeline có những stage nào?

**Đáp án tham khảo:**

- Stage 0: Safety Gate.
- Stage 1: Parallel Recon.
- Stage 2: ML Risk Scoring.
- Stage 3: Report Generation.

Stage 0, 2, 3 chạy tuần tự. Stage 1 chạy song song.

**File cần mở:** `.pi/tools/main_pipeline.py`, `.pi/chains/recon_risk_pipeline.chain.md`.

### Câu 3. Stage nào chứng minh yêu cầu parallelism của đề tài?

**Đáp án tham khảo:**  
Stage 1 trong `run_recon_stage()` dùng `ThreadPoolExecutor(max_workers=3)` để chạy đồng thời `scan_ports`, `enumerate_dns`, `grab_banners`.

**File cần mở:** `.pi/tools/main_pipeline.py`.

### Câu 4. Vì sao port scan, DNS enum và banner grab có thể chạy song song?

**Đáp án tham khảo:**  
Ba tác vụ này không phụ thuộc dữ liệu lẫn nhau. DNS enum không cần biết port nào mở. Banner grab có thể thử trên candidate ports thay vì chờ output của port scan. Vì vậy chạy song song giúp giảm wall-clock time.

**File cần mở:** `.pi/tools/main_pipeline.py`, `.pi/tools/recon/banner_grabber.py`.

### Câu 5. Output của từng stage là gì?

**Đáp án tham khảo:**

- Port scan: `.pi/triage/port_scan_result.json`
- DNS enum: `.pi/triage/dns_enum_result.json`
- Banner grab: `.pi/triage/banner_result.json`
- Risk scoring: `.pi/triage/risk_profile.json`
- Report: `.pi/results/ket_qua.md`
- Log: `.pi/logs/pipeline_run.log`

**File cần mở:** `.pi/tools/main_pipeline.py`.

### Câu 6. Safety Gate nằm ở đâu và hoạt động thế nào?

**Đáp án tham khảo:**  
Safety Gate dùng `is_target_allowed(target, authorized)` trong `tool_utils.py`. Nếu target nằm trong allowlist hoặc user truyền `--authorized` thì cho chạy. Nếu không thì raise `PermissionError` và dừng trước khi có network activity.

**File cần mở:** `.pi/tools/common/tool_utils.py`, `.pi/data/allowed_targets.json`.

### Câu 7. Vì sao allowlist có cả target public?

**Đáp án tham khảo:**  
Allowlist có hai nhóm: local loopback demo và public classroom/lab demo. Các target như `scanme.nmap.org`, `pentest-ground.com`, `vulnweb.com` là target phục vụ lab/demo. Không có nghĩa là project được phép scan mọi website public.

**File cần mở:** `.pi/data/allowed_targets.json`, `.pi/agents/permission_gate_agent.md`.

### Câu 8. Nếu chạy target `google.com` không có `--authorized` thì chuyện gì xảy ra?

**Đáp án tham khảo:**  
Nếu `google.com` không nằm trong allowlist, `is_target_allowed()` trả về `False`, pipeline báo `[BLOCKED]` và dừng. Không chạy port scan, DNS enum hay banner grab.

**File cần mở:** `.pi/tools/main_pipeline.py`, `.pi/tools/common/tool_utils.py`.

### Câu 9. Nếu không có OpenAI API key thì project có chạy được không?

**Đáp án tham khảo:**  
Có. Nếu có `--offline`, thiếu API key hoặc API lỗi, `ai_reporter.py` sẽ gọi `build_offline_report()` để sinh report offline.

**File cần mở:** `.pi/tools/reporting/ai_reporter.py`, `.pi/tools/reporting/report_templates.py`.

### Câu 10. File `.pi/chains/recon_risk_pipeline.chain.md` có phải code chạy không?

**Đáp án tham khảo:**  
Không. Đây là file mô tả orchestration/chain bằng Markdown, dùng làm tài liệu thiết kế multi-agent. Pipeline thật chạy trong `main_pipeline.py`.

**File cần mở:** `.pi/chains/recon_risk_pipeline.chain.md`, `.pi/tools/main_pipeline.py`.

## 4. Phần B - Câu hỏi chung về hiểu code

### Câu 11. `parse_target()` xử lý target URL như thế nào?

**Đáp án tham khảo:**  
Nếu input có `://`, code dùng `urlparse()` để lấy hostname và optional port. Nếu input dạng `host:port`, code tách host và port. Cuối cùng gọi `validate_target()` và `validate_port()`.

**File cần mở:** `.pi/tools/common/tool_utils.py`.

### Câu 12. `parse_ports()` hỗ trợ những dạng input nào?

**Đáp án tham khảo:**  
Hỗ trợ danh sách cách nhau bằng dấu phẩy như `80,443,8000` và range như `1-1000`. Hàm validate port từ 1 đến 65535 và giới hạn tổng số port không quá `MAX_PORT_COUNT`.

**File cần mở:** `.pi/tools/common/tool_utils.py`.

### Câu 13. Vì sao phải có `validate_timeout()`?

**Đáp án tham khảo:**  
Để tránh timeout âm, quá nhỏ hoặc quá lớn. Code giới hạn timeout từ 0.01 đến 30 giây để tránh treo pipeline hoặc scan quá nặng.

**File cần mở:** `.pi/tools/common/tool_utils.py`.

### Câu 14. `write_json()` có vai trò gì?

**Đáp án tham khảo:**  
Tạo thư mục cha nếu chưa tồn tại và ghi dict ra JSON đẹp với `indent=2`, `ensure_ascii=False`. Các stage dùng hàm này để ghi output vào `.pi/triage`.

**File cần mở:** `.pi/tools/common/tool_utils.py`, `.pi/tools/main_pipeline.py`.

### Câu 15. Vì sao `run_pipeline()` gọi `resolve_target()` sau Safety Gate?

**Đáp án tham khảo:**  
Safety Gate phải chạy trước để tránh network activity với target không hợp lệ. Sau khi target được phép, `resolve_target()` kiểm tra hostname resolve được hay không và trả về danh sách IP.

**File cần mở:** `.pi/tools/main_pipeline.py`, `.pi/tools/common/tool_utils.py`.

## 5. Phần C - Câu hỏi riêng cho Vũ Văn Thông

### Câu 16. Em giải thích vai trò của `main_pipeline.py`.

**Đáp án tham khảo:**  
`main_pipeline.py` là entrypoint chính. File này parse CLI args, kiểm tra Safety Gate, chạy Stage 1 song song, chạy Stage 2 risk scoring, chạy Stage 3 report và in các đường dẫn output.

**File cần mở:** `.pi/tools/main_pipeline.py`.

### Câu 17. Trong `run_recon_stage()`, vì sao dùng dict `{future: "port"}`?

**Đáp án tham khảo:**  
Vì `as_completed()` trả về future theo thứ tự hoàn thành, không theo thứ tự submit. Map future sang tên task giúp biết future đó là port scan, DNS enum hay banner grab để ghi đúng file output.

**File cần mở:** `.pi/tools/main_pipeline.py`.

### Câu 18. Port scanner đang dùng kỹ thuật scan gì?

**Đáp án tham khảo:**  
Dùng TCP connect scan bằng `socket.create_connection()`. Nếu connect được thì port open. Nếu lỗi hoặc timeout thì coi là closed/filtered.

**File cần mở:** `.pi/tools/recon/port_scanner.py`.

### Câu 19. `scan_ports()` có mấy lớp song song?

**Đáp án tham khảo:**  
Ngoài Stage 1 song song ở `main_pipeline.py`, bên trong `scan_ports()` còn có per-port parallelism. Mỗi port được submit thành một future trong `ThreadPoolExecutor`.

**File cần mở:** `.pi/tools/recon/port_scanner.py`.

### Câu 20. Vì sao `max_workers = min(50, max(1, len(selected_ports)))`?

**Đáp án tham khảo:**  
Đảm bảo có ít nhất 1 worker, nhưng không tạo quá 50 thread để tránh quá tải khi scan range lớn.

**File cần mở:** `.pi/tools/recon/port_scanner.py`.

### Câu 21. DNS enum xử lý localhost, IP và domain khác nhau thế nào?

**Đáp án tham khảo:**  
Localhost thì skip. IP address thì query PTR reverse DNS. Domain thì query A, CNAME, MX, NS, SOA, TXT.

**File cần mở:** `.pi/tools/recon/dns_enum.py`.

### Câu 22. Vì sao mỗi DNS record type có try/except riêng?

**Đáp án tham khảo:**  
Để fail-safe. Nếu MX không tồn tại hoặc lỗi, các record A, NS, TXT vẫn tiếp tục được query. Lỗi được ghi vào `errors`.

**File cần mở:** `.pi/tools/recon/dns_enum.py`.

### Câu 23. Vì sao TXT record cần decode riêng?

**Đáp án tham khảo:**  
Trong `dnspython`, TXT record thường là các bytes string. Code decode từng phần bằng UTF-8 và join lại thành chuỗi.

**File cần mở:** `.pi/tools/recon/dns_enum.py`.

### Câu 24. Vì sao HTTP port phải gửi HEAD request?

**Đáp án tham khảo:**  
HTTP server thường không tự gửi banner khi client mới connect. Client phải gửi request. `HEAD /` lấy header mà không lấy body, nhẹ hơn GET.

**File cần mở:** `.pi/tools/recon/banner_grabber.py`.

### Câu 25. `inspect_tls()` lấy thông tin gì?

**Đáp án tham khảo:**  
Nếu port nằm trong `TLS_PORTS`, code tạo TLS socket và lấy protocol, cipher, subject, issuer, not_after từ certificate. Đây là metadata công khai phục vụ phòng thủ.

**File cần mở:** `.pi/tools/recon/banner_grabber.py`.

### Câu 26. `identify_service()` đoán service bằng cách nào?

**Đáp án tham khảo:**  
Đầu tiên tìm marker trong banner như `ssh-`, `smtp`, `mysql`, `http/`. Nếu không có marker thì fallback sang map `SERVICE_BY_PORT`.

**File cần mở:** `.pi/tools/recon/banner_grabber.py`.

### Câu 27. File agent `.md` có vai trò gì trong phần của em?

**Đáp án tham khảo:**  
Các file agent mô tả vai trò, input, action, output và safety rule cho từng agent. Chúng là evidence cho thiết kế multi-agent, còn logic chạy thật nằm trong Python tools.

**File cần mở:** `.pi/agents/*.md`.

### Câu 28. Nếu thầy hỏi "em kiểm thử recon thế nào" thì trả lời sao?

**Đáp án tham khảo:**  
Em chạy HTTP server local ở port 8000, sau đó chạy pipeline với target `localhost` và danh sách port demo. Em kiểm tra 3 output JSON trong `.pi/triage`: port scan, DNS enum và banner result.

**File cần mở:** `.pi/triage/*.json`, `.pi/tools/main_pipeline.py`.

## 6. Phần D - Câu hỏi riêng cho Nguyễn Thành An

### Câu 29. `risk_config.py` chứa những nhóm cấu hình nào?

**Đáp án tham khảo:**  
Chứa `SERVICE_NAMES`, nhóm port HTTP, sensitive, high-risk, database/cache, danh sách `FEATURE_NAMES`, `FEATURE_WEIGHTS` và regex phát hiện banner version.

**File cần mở:** `.pi/tools/risk/risk_config.py`.

### Câu 30. `extract_features()` tạo feature vector như thế nào?

**Đáp án tham khảo:**  
Hàm nhận `open_ports`, `banners`, `dns_result`. Sau đó đếm số port mở, số port nhạy cảm, high-risk, database/cache, HTTP, số banner lộ version và số DNS record.

**File cần mở:** `.pi/tools/risk/risk_features.py`.

### Câu 31. `banner_has_version()` phát hiện version bằng cách nào?

**Đáp án tham khảo:**  
Hàm dùng regex trong `BANNER_VERSION_PATTERNS`, ví dụ `OpenSSH_8.9`, `Apache/2.4`, `nginx/1.24`. Nếu banner là `No banner` thì trả về False.

**File cần mở:** `.pi/tools/risk/risk_features.py`, `.pi/tools/risk/risk_config.py`.

### Câu 32. Simple Isolation Forest trong project "học" từ đâu?

**Đáp án tham khảo:**  
Model fit trên `BASELINE_SAMPLES` trong `risk_model.py`. Đây là các mẫu exposure thấp/trung bình để demo anomaly detection.

**File cần mở:** `.pi/tools/risk/risk_model.py`.

### Câu 33. `to_vector()` có nhiệm vụ gì?

**Đáp án tham khảo:**  
Chuyển `feature_map` từ dict sang list theo đúng thứ tự `FEATURE_NAMES`, vì model cần vector số.

**File cần mở:** `.pi/tools/risk/risk_model.py`.

### Câu 34. `average_path_length()` dùng để làm gì?

**Đáp án tham khảo:**  
Đây là hệ số chuẩn hóa trong công thức anomaly score của Isolation Forest. Nó giúp so sánh path length với kích thước training set.

**File cần mở:** `.pi/tools/risk/risk_model.py`.

### Câu 35. `exposure_severity()` khác anomaly score thế nào?

**Đáp án tham khảo:**  
Anomaly score đến từ model Isolation Forest. Exposure severity là domain knowledge dựa trên trọng số `FEATURE_WEIGHTS`, giúp score 0-10 gần với rủi ro network dễ giải thích hơn.

**File cần mở:** `.pi/tools/risk/risk_model.py`, `.pi/tools/risk/risk_config.py`.

### Câu 36. Vì sao target public được cộng thêm 1 điểm?

**Đáp án tham khảo:**  
Trong `risk_scorer.py`, nếu `target_exposure == "public"` và có open port thì cộng thêm 1 điểm. Vì một port mở trên public Internet có exposure cao hơn localhost.

**File cần mở:** `.pi/tools/risk/risk_scorer.py`.

### Câu 37. MITRE mapping được tạo ở đâu?

**Đáp án tham khảo:**  
Trong `risk_findings.py`. Open port map với T1046/T1595, DNS records map với T1590, version banner map với T1592.002.

**File cần mở:** `.pi/tools/risk/risk_findings.py`.

### Câu 38. Report offline được build bằng cách nào?

**Đáp án tham khảo:**  
`build_offline_report(profile, reason)` đọc các trường trong `risk_profile`: target, recon summary, risk level, ML model, findings, MITRE mapping, recommendations rồi ghép thành Markdown.

**File cần mở:** `.pi/tools/reporting/report_templates.py`.

### Câu 39. Khi nào code gọi OpenAI API?

**Đáp án tham khảo:**  
Khi không có `--offline`, có `OPENAI_API_KEY` hợp lệ và API không lỗi. Khi đó `generate_ai_report()` trong `openai_report_client.py` được gọi.

**File cần mở:** `.pi/tools/reporting/ai_reporter.py`, `.pi/tools/reporting/openai_report_client.py`.

### Câu 40. `pi_recon_agent.py` dùng để làm gì?

**Đáp án tham khảo:**  
Đây là Week 5 agentic extension. File này khai báo OpenAI tool schemas, runtime safety wrapper và vòng lặp Observe-Think-Act/tool calling. Nó dùng lại các tool Python của pipeline chính.

**File cần mở:** `.pi/tools/pi_recon_agent.py`.

### Câu 41. `ToolRuntime` bảo vệ pipeline như thế nào?

**Đáp án tham khảo:**  
`ToolRuntime` check target bằng `_check_target()`, rate limit bằng `_check_rate_limit()`, parse ports an toàn, chạy tool thật và ghi output JSON vào `.pi/triage`.

**File cần mở:** `.pi/tools/pi_recon_agent.py`.

## 7. Phần E - Câu hỏi hiểu chéo giữa hai thành viên

### Câu 42. Vũ Văn Thông hãy giải thích `risk_profile.json` gồm gì.

**Đáp án tham khảo:**  
Gồm target, score, risk_level, target_exposure, score_adjustments, ml_model, mitre_mapping, findings, recommendations, recon_summary và notes.

**File cần mở:** `.pi/tools/risk/risk_scorer.py`.

### Câu 43. Nguyễn Thành An hãy giải thích `run_recon_stage()`.

**Đáp án tham khảo:**  
Hàm tạo 3 future cho port scan, DNS enum và banner grab. Khi future hoàn thành, ghi kết quả vào file JSON tương ứng. Cuối cùng trả về 3 dict kết quả để risk stage xử lý.

**File cần mở:** `.pi/tools/main_pipeline.py`.

### Câu 44. Cả hai hãy mô tả data flow bằng file.

**Đáp án tham khảo:**  
Stage 1 tạo 3 file JSON trong `.pi/triage`. Stage 2 đọc 3 file đó và tạo `risk_profile.json`. Stage 3 đọc `risk_profile.json` và tạo `ket_qua.md`.

**File cần mở:** `.pi/tools/main_pipeline.py`.

### Câu 45. Cả hai hãy giải thích vì sao report có phần Scope & Authorization.

**Đáp án tham khảo:**  
Để thầy thấy rõ project chỉ scan local, classroom/lab allowlist hoặc target có `--authorized`. Phần này tránh hiểu nhầm project cho phép scan tùy tiện target public.

**File cần mở:** `.pi/tools/reporting/report_templates.py`.

### Câu 46. Nếu thầy xóa `.env`, project còn demo được không?

**Đáp án tham khảo:**  
Còn. Chạy với `--offline` thì report dùng template offline. `.env` chỉ cần khi muốn dùng OpenAI API.

**File cần mở:** `.pi/tools/reporting/ai_reporter.py`.

## 8. Phần F - Câu hỏi code tay cho Vũ Văn Thông

### Bài code 1. Thêm `closed_count` vào kết quả port scan

**Yêu cầu của thầy:**  
Trong `port_scan_result.json`, ngoài `open_count` phải có thêm `closed_count`.

**File cần sửa:** `.pi/tools/recon/port_scanner.py`

**Gợi ý sửa:**

```python
"closed_count": len(selected_ports) - len(open_ports),
```

**Giải thích cần nói:**  
`closed_count` được tính từ tổng số port đã scan trừ số port open.

### Bài code 2. Thêm port mặc định 27017 vào scanner

**Yêu cầu của thầy:**  
Khi không truyền `--ports`, scanner phải scan thêm MongoDB port 27017.

**File cần sửa:** `.pi/tools/recon/port_scanner.py`

**Gợi ý sửa:**  
Thêm `27017` vào `DEFAULT_PORTS`.

### Bài code 3. Thêm CLI `--timeout` cho `banner_grabber.py`

**Yêu cầu của thầy:**  
Khi chạy riêng banner grabber, người dùng có thể truyền timeout.

**File cần sửa:** `.pi/tools/recon/banner_grabber.py`

**Gợi ý sửa:**

```python
parser.add_argument("--timeout", type=float, default=1.0)
result = grab_banners(args.target, ports, args.timeout)
```

### Bài code 4. DNS enum thêm record CAA

**Yêu cầu của thầy:**  
DNS enum phải query thêm CAA record.

**File cần sửa:** `.pi/tools/recon/dns_enum.py`

**Gợi ý sửa:**

```python
DNS_RECORD_TYPES = ["A", "CNAME", "MX", "NS", "SOA", "TXT", "CAA"]
```

### Bài code 5. Nếu port list rỗng trong banner grabber thì dùng DEFAULT_PORTS

**Yêu cầu của thầy:**  
Khi chạy `banner_grabber.py` không truyền `--ports`, tool không được trả rỗng mà dùng port mặc định giống port scanner.

**File cần sửa:** `.pi/tools/recon/banner_grabber.py`

**Gợi ý sửa:**  
Import `DEFAULT_PORTS` từ `port_scanner.py` hoặc khai báo danh sách mặc định riêng, sau đó:

```python
ports = parse_ports(args.ports) if args.ports else DEFAULT_PORTS
```

### Bài code 6. Thêm target lab mới vào allowlist

**Yêu cầu của thầy:**  
Thêm `example-lab.local` vào allowlist demo.

**File cần sửa:** `.pi/data/allowed_targets.json`

**Giải thích cần nói:**  
Chỉ thêm target có lý do lab/authorized. Không mở allow toàn bộ public domain.

### Bài code 7. Thêm log khi Safety Gate block target

**Yêu cầu của thầy:**  
Khi target bị block, log phải ghi rõ target nào bị block.

**File cần sửa:** `.pi/tools/main_pipeline.py`

**Gợi ý sửa:**

```python
logging.warning("Permission gate blocked target=%s: %s", target, message)
```

### Bài code 8. Thêm output `stage="recon"` vào 3 kết quả recon

**Yêu cầu của thầy:**  
Mỗi JSON recon phải có trường `stage`.

**File cần sửa:**  
`.pi/tools/recon/port_scanner.py`, `.pi/tools/recon/dns_enum.py`, `.pi/tools/recon/banner_grabber.py`

**Gợi ý:**  
Thêm `"stage": "recon"` vào dict return.

## 9. Phần G - Câu hỏi code tay cho Nguyễn Thành An

### Bài code 9. Thêm service MongoDB vào risk config

**Yêu cầu của thầy:**  
Nếu port 27017 mở, report phải biết đây là MongoDB và tính là database/cache port.

**File cần sửa:** `.pi/tools/risk/risk_config.py`

**Gợi ý sửa:**

```python
SERVICE_NAMES[27017] = "MongoDB"
DATABASE_CACHE_PORTS.add(27017)
SENSITIVE_PORTS.add(27017)
```

Khi sửa thật trong file, nên thêm trực tiếp vào dict/set thay vì gọi `.add()` ở cuối.

### Bài code 10. Thêm recommendation riêng cho MongoDB

**Yêu cầu của thầy:**  
Nếu port 27017 mở, recommendations phải có câu khuyên không public MongoDB.

**File cần sửa:** `.pi/tools/risk/risk_findings.py`

**Gợi ý sửa:**

```python
if 27017 in open_ports:
    recommendations.append("Khong public MongoDB; bat authentication va chi bind noi bo/VPN.")
```

### Bài code 11. Đổi ngưỡng risk label

**Yêu cầu của thầy:**  
Low 0-2, Medium 3-5, High 6-10.

**File cần sửa:** `.pi/tools/risk/risk_model.py`

**Gợi ý sửa:**

```python
def label_from_score(score: int) -> str:
    if score <= 2:
        return "Low"
    if score <= 5:
        return "Medium"
    return "High"
```

### Bài code 12. Thêm feature `tls_port_count`

**Yêu cầu của thầy:**  
Risk profile phải có thêm feature đếm số port có TLS metadata.

**File cần sửa:**  
`.pi/tools/risk/risk_config.py`, `.pi/tools/risk/risk_features.py`, `.pi/tools/risk/risk_scorer.py`

**Gợi ý hướng làm:**

- Thêm `"tls_port_count"` vào `FEATURE_NAMES`.
- Thêm weight vào `FEATURE_WEIGHTS`.
- Sửa `extract_features()` hoặc truyền thêm TLS data từ `score_risk()`.

**Điểm cần giải thích:**  
Đây là thay đổi liên quan contract giữa banner result và risk feature, không chỉ thêm một dòng.

### Bài code 13. Thêm section Evidence Files vào report offline

**Yêu cầu của thầy:**  
Report offline phải liệt kê các file bằng chứng đầu ra.

**File cần sửa:** `.pi/tools/reporting/report_templates.py`

**Gợi ý sửa:**  
Thêm section:

```python
"## Evidence Files",
"- `.pi/triage/port_scan_result.json`",
"- `.pi/triage/dns_enum_result.json`",
"- `.pi/triage/banner_result.json`",
"- `.pi/triage/risk_profile.json`",
```

### Bài code 14. Report tiếng Việt

**Yêu cầu của thầy:**  
Thêm option sinh report offline bằng tiếng Việt.

**File cần sửa:** `.pi/tools/reporting/report_templates.py`, `.pi/tools/reporting/ai_reporter.py`

**Gợi ý hướng làm:**  
Tạo thêm hàm `build_offline_report_vn(profile, reason)` hoặc thêm parameter `language`.

### Bài code 15. Nếu API key là placeholder thì luôn offline

**Yêu cầu của thầy:**  
Nếu `OPENAI_API_KEY` là `your_api_key_here` hoặc rỗng thì không gọi API.

**File cần sửa:** `.pi/tools/reporting/ai_reporter.py`

**Giải thích:**  
Code hiện đã check `not api_key` và `api_key == "your_api_key_here"`. Sinh viên phải chỉ được đoạn này.

### Bài code 16. Thêm MITRE mapping cho database/cache exposed

**Yêu cầu của thầy:**  
Nếu có port database/cache mở, MITRE mapping phải có thêm một mục defensive context.

**File cần sửa:** `.pi/tools/risk/risk_findings.py`

**Gợi ý:**  
Kiểm tra `any(port in open_ports for port in DATABASE_CACHE_PORTS)` và append mapping mới. Phải import `DATABASE_CACHE_PORTS` nếu chưa có.

## 10. Phần H - Tình huống thầy hỏi phản biện

### Câu 47. Nếu scan 10,000 port thì code hiện tại có cho không?

**Đáp án tham khảo:**  
Không, vì `MAX_PORT_COUNT = 4096`. Nếu muốn hỗ trợ 10,000 port cần tăng giới hạn, cân nhắc timeout, số worker và tài nguyên socket/thread.

**File cần mở:** `.pi/tools/common/tool_utils.py`.

### Câu 48. Nếu DNS MX lỗi thì pipeline có fail không?

**Đáp án tham khảo:**  
Không. Mỗi record type có try/except riêng, lỗi được ghi vào `errors`, record đó là list rỗng.

**File cần mở:** `.pi/tools/recon/dns_enum.py`.

### Câu 49. Nếu port 8000 không open khi demo thì debug thế nào?

**Đáp án tham khảo:**  
Kiểm tra Terminal 1 đã chạy `python -m http.server 8000 --bind 127.0.0.1` chưa. Nếu chưa có service nghe trên port 8000 thì port scanner trả closed là đúng.

**File cần mở:** `.pi/tools/recon/port_scanner.py`.

### Câu 50. Nếu report không có MITRE mapping thì nguyên nhân có thể là gì?

**Đáp án tham khảo:**  
Có thể không có open port, không có DNS record và không có version leak, nên `build_mitre_mapping()` không append mapping nào.

**File cần mở:** `.pi/tools/risk/risk_findings.py`.

### Câu 51. Nếu thầy muốn bỏ OpenAI API hoàn toàn thì sửa ở đâu?

**Đáp án tham khảo:**  
Có thể luôn gọi `build_offline_report()` trong `generate_report()`, hoặc luôn chạy CLI với `--offline`.

**File cần mở:** `.pi/tools/reporting/ai_reporter.py`.

### Câu 52. Nếu thầy hỏi vì sao không dùng nmap thì trả lời sao?

**Đáp án tham khảo:**  
Project là đồ án lập trình mạng nên tự cài TCP socket scan để hiểu cơ chế. Nmap mạnh hơn, nhưng dùng nmap sẽ làm mất phần tự xây dựng tool network programming.

### Câu 53. Nếu thầy hỏi vì sao ML baseline chỉ có ít sample thì trả lời sao?

**Đáp án tham khảo:**  
Đây là classroom demo, mục tiêu là explainable ML pipeline. Baseline nhỏ giúp dễ giải thích. Nếu production cần dataset lớn hơn, validation và model evaluation rõ ràng hơn.

### Câu 54. Nếu thầy hỏi "đây có phải tấn công không" thì trả lời sao?

**Đáp án tham khảo:**  
Không. Project chỉ read-only reconnaissance trên target được phép. Không exploit, không brute force, không bypass, có Safety Gate và report chỉ đưa khuyến nghị phòng thủ.

## 11. Phần I - Câu hỏi chạy demo trước mặt thầy

### Câu 55. Em hãy chạy demo local từ đầu đến cuối.

**Lệnh mẫu:**

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

### Câu 56. Em hãy chạy riêng từng tool recon.

**Lệnh mẫu:**

```powershell
python .pi\tools\recon\port_scanner.py --target localhost --ports "8000,8080"
python .pi\tools\recon\dns_enum.py --target scanme.nmap.org
python .pi\tools\recon\banner_grabber.py --target localhost --ports "8000,8080"
```

### Câu 57. Em hãy chạy riêng risk scorer từ file JSON có sẵn.

**Lệnh mẫu:**

```powershell
python .pi\tools\risk\risk_scorer.py --port-file .pi\triage\port_scan_result.json --dns-file .pi\triage\dns_enum_result.json --banner-file .pi\triage\banner_result.json --output .pi\triage\risk_profile.json
```

### Câu 58. Em hãy tạo lại report từ risk profile có sẵn.

**Lệnh mẫu:**

```powershell
python .pi\tools\reporting\ai_reporter.py --risk-profile .pi\triage\risk_profile.json --output .pi\results\ket_qua.md --prompt .pi\prompts\report_prompt.md --offline
```

## 12. Phần J - Checklist thầy dùng để chấm nhanh

| Mục kiểm tra | Thành viên cần trả lời được | Đạt nếu |
|---|---|---|
| Tổng quan project | Cả hai | Nói đúng Stage 0-3 và output từng stage |
| Parallelism | Cả hai | Chỉ đúng `ThreadPoolExecutor` trong `run_recon_stage()` |
| Safety Gate | Cả hai | Giải thích allowlist, `--authorized`, local/lab public target |
| Port scanner | Vũ Văn Thông chính, Nguyễn Thành An hiểu chéo | Giải thích TCP connect scan và per-port threads |
| DNS enum | Vũ Văn Thông chính, Nguyễn Thành An hiểu chéo | Giải thích localhost/IP/domain và try/except từng record |
| Banner grab | Vũ Văn Thông chính, Nguyễn Thành An hiểu chéo | Giải thích HEAD request, `No banner`, service guess |
| Risk feature | Nguyễn Thành An chính, Vũ Văn Thông hiểu chéo | Nói được 7 feature và ý nghĩa |
| ML model | Nguyễn Thành An chính, Vũ Văn Thông hiểu chéo | Giải thích baseline, anomaly score, score 0-10 |
| Report | Nguyễn Thành An chính, Vũ Văn Thông hiểu chéo | Giải thích API/offline fallback và section report |
| Code tay | Từng người theo file phụ trách | Sửa đúng file, code chạy, không phá safety |

