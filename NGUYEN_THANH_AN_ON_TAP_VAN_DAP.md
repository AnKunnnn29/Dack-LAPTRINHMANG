# Nguyễn Thành An - Bộ ôn vấn đáp, code tay và debug

> File này dành riêng cho **Nguyễn Thành An - MSSV 23162001**.  
> Phạm vi chính: risk scoring, feature extraction, Simple Isolation Forest, findings, MITRE mapping, report generation và agentic extension.

## 1. Phần em phụ trách

| Nhóm việc | Nội dung em cần nắm |
|---|---|
| Risk config | Khai báo service names, nhóm port rủi ro, feature names, feature weights, regex banner version |
| Feature extraction | Biến kết quả recon thành feature vector cho model ML |
| ML risk model | Simple Isolation Forest, anomaly score, exposure severity, risk label |
| Risk profile | Tổng hợp score, risk_level, findings, MITRE mapping, recommendations, recon_summary |
| Report generation | Sinh Markdown report, dùng OpenAI API nếu có key, fallback offline nếu không |
| Agentic extension | `pi_recon_agent.py` dùng OpenAI tool calling để điều phối các tool |

## 2. File em phải mở được khi thầy hỏi

- `.pi/tools/risk/risk_config.py`
- `.pi/tools/risk/risk_features.py`
- `.pi/tools/risk/risk_model.py`
- `.pi/tools/risk/risk_scorer.py`
- `.pi/tools/risk/risk_findings.py`
- `.pi/tools/reporting/ai_reporter.py`
- `.pi/tools/reporting/report_templates.py`
- `.pi/tools/reporting/openai_report_client.py`
- `.pi/prompts/report_prompt.md`
- `.pi/agents/risk_score_agent.md`
- `.pi/agents/report_agent.md`
- `.pi/skills/risk-scoring/SKILL.md`
- `.pi/skills/reporting/SKILL.md`
- `.pi/tools/pi_recon_agent.py`
- `.pi/results/ket_qua.md`

## 3. Tóm tắt 60 giây khi thầy hỏi em làm gì

Em phụ trách phần xử lý sau recon. Sau khi phần recon tạo ra 3 file JSON gồm
port scan, DNS enum và banner result, em trích xuất các feature như số port mở,
port nhạy cảm, port HTTP, database/cache port, banner lộ version và số DNS
record. Sau đó em dùng Simple Isolation Forest để tính anomaly score, kết hợp
với exposure severity để ra điểm rủi ro 0-10 và mức Low/Medium/High. Từ đó em
tạo findings, MITRE ATT&CK mapping, recommendations và sinh báo cáo Markdown.
Report có thể dùng OpenAI API nếu có key, còn không thì fallback offline để demo
ổn định.

## 4. Câu hỏi vấn đáp tổng quan dành cho em

### Câu 1. Phần risk scoring nhận input từ đâu?

**Trả lời:**  
Risk scoring nhận 3 kết quả từ Stage 1: `port_scan_result.json`,
`dns_enum_result.json` và `banner_result.json`. Trong pipeline chính, các dict
kết quả này được truyền trực tiếp vào `score_risk()`.

**File cần mở:** `.pi/tools/risk/risk_scorer.py`, `.pi/tools/main_pipeline.py`

### Câu 2. Output trung tâm của phần em là gì?

**Trả lời:**  
Output trung tâm là `.pi/triage/risk_profile.json`. File này chứa target, score,
risk_level, ml_model, findings, MITRE mapping, recommendations và recon_summary.

**File cần mở:** `.pi/tools/risk/risk_scorer.py`

### Câu 3. Vì sao cần feature extraction?

**Trả lời:**  
Recon output là dữ liệu dạng JSON có port, DNS, banner. Model ML không xử lý trực
tiếp dữ liệu đó, nên cần chuyển thành feature vector số như open_port_count,
sensitive_port_count, version_banner_count.

**File cần mở:** `.pi/tools/risk/risk_features.py`

### Câu 4. Vì sao dùng Simple Isolation Forest?

**Trả lời:**  
Đây là mô hình anomaly detection không cần label tấn công/bình thường. Đồ án
không có dataset gán nhãn lớn, nên Isolation Forest phù hợp để demo phát hiện
exposure bất thường dựa trên baseline nhỏ, dễ giải thích khi vấn đáp.

**File cần mở:** `.pi/tools/risk/risk_model.py`

### Câu 5. Report cuối cùng sinh từ file nào?

**Trả lời:**  
Report đọc `.pi/triage/risk_profile.json` và ghi ra `.pi/results/ket_qua.md`.

**File cần mở:** `.pi/tools/reporting/ai_reporter.py`

## 5. Câu hỏi về `risk_config.py`

### Câu 6. `SERVICE_NAMES` dùng để làm gì?

**Trả lời:**  
Map port sang tên dịch vụ để findings và report dễ đọc. Ví dụ 5432 là
PostgreSQL, 6379 là Redis.

### Câu 7. `SENSITIVE_PORTS`, `HIGH_RISK_PORTS`, `DATABASE_CACHE_PORTS` khác nhau thế nào?

**Trả lời:**  
`SENSITIVE_PORTS` là các port cần chú ý như SSH, SMB, database. `HIGH_RISK_PORTS`
là nhóm nguy hiểm hơn như Telnet, SMB, Redis. `DATABASE_CACHE_PORTS` là các port
database/cache như MySQL, PostgreSQL, Redis.

### Câu 8. `FEATURE_NAMES` quan trọng ở đâu?

**Trả lời:**  
`FEATURE_NAMES` quy định thứ tự feature khi chuyển `feature_map` thành vector.
Model cần thứ tự ổn định để train và predict đúng.

### Câu 9. `FEATURE_WEIGHTS` dùng để làm gì?

**Trả lời:**  
Dùng trong `exposure_severity()` để tính mức độ rủi ro theo domain knowledge.
High-risk/database/version leak có weight cao hơn HTTP/DNS thông thường.

### Câu 10. `BANNER_VERSION_PATTERNS` dùng ở đâu?

**Trả lời:**  
Dùng trong `banner_has_version()` để phát hiện banner có lộ phiên bản dịch vụ
như `OpenSSH_8.9`, `Apache/2.4`, `nginx/1.24`.

## 6. Câu hỏi về `risk_features.py`

### Câu 11. `banner_has_version()` hoạt động thế nào?

**Trả lời:**  
Nếu banner rỗng hoặc `"No banner"` thì trả False. Ngược lại, hàm dùng regex trong
`BANNER_VERSION_PATTERNS` để kiểm tra có dấu hiệu version hay không.

### Câu 12. `count_dns_records()` đếm gì?

**Trả lời:**  
Đếm tổng số DNS record lấy được trong `dns_result["records"]`, chỉ đếm những giá
trị là list.

### Câu 13. `extract_features()` trả về gì?

**Trả lời:**  
Trả về `feature_map` và `version_leaks`. `feature_map` là dict các feature số.
`version_leaks` là danh sách port có banner lộ version.

### Câu 14. 7 feature hiện tại là gì?

**Trả lời:**

- `open_port_count`
- `sensitive_port_count`
- `high_risk_port_count`
- `database_cache_port_count`
- `http_port_count`
- `version_banner_count`
- `dns_record_count`

### Câu 15. Vì sao `version_banner_count` làm tăng risk?

**Trả lời:**  
Banner lộ version giúp người phòng thủ biết dịch vụ đang tiết lộ thông tin phần
mềm. Trong thực tế, attacker có thể dùng version để tra CVE, nên đây là tín hiệu
rủi ro cần giảm.

## 7. Câu hỏi về `risk_model.py`

### Câu 16. `BASELINE_SAMPLES` là gì?

**Trả lời:**  
Là các mẫu exposure thấp/trung bình dùng để fit Simple Isolation Forest. Mẫu mới
khác baseline nhiều thì anomaly score cao hơn.

### Câu 17. `to_vector()` làm gì?

**Trả lời:**  
Chuyển `feature_map` thành list số theo đúng thứ tự `FEATURE_NAMES`.

### Câu 18. `IsolationNode` biểu diễn gì?

**Trả lời:**  
Biểu diễn một node trong isolation tree, gồm size, depth, feature_index,
threshold, left, right. Nếu không có feature split hoặc child thì là leaf.

### Câu 19. `_build_tree()` hoạt động thế nào?

**Trả lời:**  
Hàm chọn ngẫu nhiên một feature có thể split, chọn threshold ngẫu nhiên giữa min
và max của feature, rồi chia dữ liệu thành left/right. Lặp lại đến max_depth hoặc
khi không thể split.

### Câu 20. `path_length()` có ý nghĩa gì?

**Trả lời:**  
Là độ dài đường đi của một vector trong isolation tree. Mẫu càng dễ bị cô lập thì
path length càng ngắn, thường có anomaly score cao hơn.

### Câu 21. `anomaly_score()` tính gì?

**Trả lời:**  
Tính average path length qua nhiều tree, chuẩn hóa bằng `average_path_length()`
rồi dùng công thức `2 ** (-average_length / normalizer)`.

### Câu 22. `calibrate_anomaly_score()` để làm gì?

**Trả lời:**  
Dùng baseline distribution để chuẩn hóa anomaly score. Score nằm trong vùng bình
thường của baseline thì xem như 0, score vượt xa baseline thì scale về 0-1.

### Câu 23. `exposure_severity()` khác anomaly score thế nào?

**Trả lời:**  
Anomaly score đến từ Isolation Forest. Exposure severity là điểm domain knowledge
dựa trên `FEATURE_WEIGHTS`, giúp risk score dễ giải thích với rủi ro network.

### Câu 24. `predict_with_isolation_forest()` trả về gì?

**Trả lời:**  
Trả về thông tin model, feature vector, anomaly score, calibrated anomaly,
baseline stats, exposure severity, predicted_score, predicted_label và risk_drivers.

### Câu 25. Risk label được map thế nào?

**Trả lời:**  
`label_from_score()` map score 0-3 là Low, 4-6 là Medium, 7-10 là High.

## 8. Câu hỏi về `risk_scorer.py`

### Câu 26. `classify_target_exposure()` phân loại target thế nào?

**Trả lời:**  
Nếu target là `localhost` hoặc IP loopback thì local. Nếu IP private thì private.
Nếu hostname hoặc IP public thì public.

### Câu 27. Vì sao public target được cộng thêm 1 điểm?

**Trả lời:**  
Nếu target public có open port, exposure cao hơn localhost nên code cộng thêm 1
điểm domain adjustment.

### Câu 28. `score_risk()` gom những phần nào?

**Trả lời:**  
Hàm lấy target, open_ports, banners, extract features, predict bằng model, tính
target exposure, final score, rồi tạo ml_model, MITRE mapping, findings,
recommendations và recon_summary.

### Câu 29. `score_risk_from_files()` dùng khi nào?

**Trả lời:**  
Dùng để chạy riêng Stage 2 từ 3 file JSON đã có sẵn mà không cần chạy lại recon.

## 9. Câu hỏi về `risk_findings.py`

### Câu 30. `build_findings()` tạo những loại finding nào?

**Trả lời:**  
Tạo finding cho open port, banner version leak và DNS records.

### Câu 31. Open port map với MITRE nào?

**Trả lời:**  
Open port map với T1046 Network Service Discovery và T1595 Active Scanning.

### Câu 32. DNS records map với MITRE nào?

**Trả lời:**  
DNS records map với T1590 Gather Victim Network Information.

### Câu 33. Version banner leak map với MITRE nào?

**Trả lời:**  
Version banner leak map với T1592.002 Gather Victim Host Information: Software.

### Câu 34. Recommendations được tạo theo logic nào?

**Trả lời:**  
Luôn có khuyến nghị chung. Nếu có FTP, SSH, Telnet, database/cache, HTTP hoặc
version leak thì thêm khuyến nghị riêng tương ứng.

## 10. Câu hỏi về report generation

### Câu 35. `generate_report()` có mấy chế độ?

**Trả lời:**  
Có 2 chế độ. Nếu có API key hợp lệ và không dùng `--offline` thì gọi OpenAI API.
Nếu offline, thiếu key hoặc API lỗi thì dùng offline template.

**File cần mở:** `.pi/tools/reporting/ai_reporter.py`

### Câu 36. Vì sao cần fallback offline?

**Trả lời:**  
Để demo không phụ thuộc API key hoặc mạng. Dù không có OpenAI API, project vẫn
sinh được report.

### Câu 37. `build_offline_report()` tạo những section nào?

**Trả lời:**  
Target, Scope & Authorization, Recon Summary, Risk Level, ML Risk Model,
Findings, MITRE ATT&CK Mapping, Recommendations, Conclusion.

### Câu 38. Vì sao report có Scope & Authorization?

**Trả lời:**  
Để giải thích rõ phạm vi scan: local loopback, classroom/lab allowlist target
hoặc target được authorized. Phần này giúp thầy thấy project có ràng buộc an toàn.

### Câu 39. `openai_report_client.py` gửi gì lên model?

**Trả lời:**  
Gửi system message yêu cầu viết report phòng thủ và user message gồm prompt +
risk profile JSON.

### Câu 40. Nếu OpenAI API lỗi thì report có mất không?

**Trả lời:**  
Không. `generate_report()` bắt exception và chuyển sang `build_offline_report()`.

## 11. Câu hỏi về `pi_recon_agent.py`

### Câu 41. `pi_recon_agent.py` khác `main_pipeline.py` thế nào?

**Trả lời:**  
`main_pipeline.py` là pipeline deterministic để demo ổn định. `pi_recon_agent.py`
là Week 5 extension dùng OpenAI tool calling để LLM chọn tool, nhưng vẫn dùng lại
các Python tools của project.

### Câu 42. `TOOLS` trong agentic mode là gì?

**Trả lời:**  
Là danh sách schema cho các function tool: `scan_ports`, `enumerate_dns`,
`grab_banners`, `score_risk_from_triage`, `generate_markdown_report`.

### Câu 43. `ToolRuntime` có vai trò gì?

**Trả lời:**  
Là lớp wrapper an toàn. LLM có thể yêu cầu gọi tool, nhưng `ToolRuntime` mới kiểm
tra target, rate limit, chọn ports, chạy tool thật và ghi JSON.

### Câu 44. `_check_rate_limit()` để làm gì?

**Trả lời:**  
Giới hạn số lần gọi tool trong một khoảng thời gian để agent không loop hoặc gọi
quá nhiều lần.

### Câu 45. `_execute_tool_batch()` có gì đặc biệt?

**Trả lời:**  
Nếu model gọi nhiều tool trong một turn, hàm này chạy các tool call song song và
trả về tool messages tương ứng.

### Câu 46. Vì sao cần `_compact_for_llm()`?

**Trả lời:**  
Để rút gọn result gửi lại model, tránh context quá dài. Full data vẫn được lưu ở
`.pi/triage`.

## 12. Câu hỏi hiểu chéo phần Vũ Văn Thông

### Câu 47. Trước khi risk scoring chạy, phần recon tạo ra gì?

**Trả lời:**  
Tạo 3 JSON: `port_scan_result.json`, `dns_enum_result.json`, `banner_result.json`.

### Câu 48. Stage 1 song song nằm ở đâu?

**Trả lời:**  
Trong `run_recon_stage()` của `main_pipeline.py`, dùng `ThreadPoolExecutor(max_workers=3)`.

### Câu 49. Banner result ảnh hưởng risk scoring thế nào?

**Trả lời:**  
`banner_result["banners"]` được dùng để phát hiện version leak. `services` và
`tls` được đưa vào `recon_summary` trong risk profile.

### Câu 50. DNS result ảnh hưởng risk scoring thế nào?

**Trả lời:**  
`dns_result["records"]` được dùng để tính `dns_record_count` và tạo MITRE mapping
T1590 nếu có DNS records.

## 13. Bài code tay thầy dễ bắt phần em

### Bài 1. Thêm service MongoDB 27017 vào risk config

**File sửa:** `.pi/tools/risk/risk_config.py`

**Code mẫu:**

```python
SERVICE_NAMES = {
    # ...
    27017: "MongoDB",
}

SENSITIVE_PORTS = {21, 22, 23, 445, 3306, 5432, 6379, 27017}
DATABASE_CACHE_PORTS = {3306, 5432, 6379, 27017}
```

**Giải thích:**  
Khi port 27017 open, finding sẽ hiển thị MongoDB và feature database/cache tăng.

### Bài 2. Thêm recommendation riêng cho MongoDB

**File sửa:** `.pi/tools/risk/risk_findings.py`

**Code mẫu:**

```python
if 27017 in open_ports:
    recommendations.append("Khong public MongoDB; bat authentication va chi bind noi bo/VPN.")
```

### Bài 3. Đổi ngưỡng risk label

**File sửa:** `.pi/tools/risk/risk_model.py`

**Yêu cầu:** Low 0-2, Medium 3-5, High 6-10.

**Code mẫu:**

```python
def label_from_score(score: int) -> str:
    if score <= 2:
        return "Low"
    if score <= 5:
        return "Medium"
    return "High"
```

### Bài 4. Thêm section Evidence Files vào report offline

**File sửa:** `.pi/tools/reporting/report_templates.py`

**Code mẫu:**

```python
lines.extend([
    "",
    "## Evidence Files",
    "- `.pi/triage/port_scan_result.json`",
    "- `.pi/triage/dns_enum_result.json`",
    "- `.pi/triage/banner_result.json`",
    "- `.pi/triage/risk_profile.json`",
])
```

### Bài 5. Thêm feature `tls_port_count`

**File sửa:**  
`.pi/tools/risk/risk_config.py`, `.pi/tools/risk/risk_features.py`,
`.pi/tools/risk/risk_scorer.py`

**Hướng làm:**  
Thêm feature mới vào `FEATURE_NAMES`, thêm weight vào `FEATURE_WEIGHTS`, lấy TLS
metadata từ `banner_result["tls"]`, rồi đưa vào feature_map.

**Điểm cần giải thích:**  
Đây là thay đổi contract giữa banner result và risk feature, nên phải sửa nhiều
file chứ không chỉ một dòng.

### Bài 6. Thêm report tiếng Việt offline

**File sửa:** `.pi/tools/reporting/report_templates.py`, `.pi/tools/reporting/ai_reporter.py`

**Hướng làm:**  
Tạo hàm `build_offline_report_vn(profile, reason)` hoặc thêm tham số `language`.
Sau đó CLI hoặc `generate_report()` chọn template theo ngôn ngữ.

### Bài 7. Thêm MITRE mapping cho database/cache exposed

**File sửa:** `.pi/tools/risk/risk_findings.py`

**Code mẫu:**

```python
if any(port in open_ports for port in DATABASE_CACHE_PORTS):
    mappings.append({
        "technique_id": "T1046",
        "technique": "Database/Cache Exposure",
        "tactic": "Discovery",
        "evidence": "Database/cache service is exposed.",
        "defensive_note": "Restrict database/cache access to internal networks or VPN.",
    })
```

### Bài 8. Nếu API key là placeholder thì bắt buộc offline

**File sửa:** `.pi/tools/reporting/ai_reporter.py`

**Giải thích:**  
Code hiện đã check `not api_key` và `api_key == "your_api_key_here"`. Nếu thầy
yêu cầu thêm placeholder khác, thêm vào điều kiện hoặc tạo set placeholder.

## 14. Lệnh chạy và debug phần em

### Chạy pipeline đầy đủ

```powershell
python .pi\tools\main_pipeline.py --target localhost --ports "8000,8080,3306,5432,6379" --offline
```

### Chạy riêng risk scorer từ 3 JSON

```powershell
python .pi\tools\risk\risk_scorer.py --port-file .pi\triage\port_scan_result.json --dns-file .pi\triage\dns_enum_result.json --banner-file .pi\triage\banner_result.json --output .pi\triage\risk_profile.json
```

### Chạy riêng report generator

```powershell
python .pi\tools\reporting\ai_reporter.py --risk-profile .pi\triage\risk_profile.json --output .pi\results\ket_qua.md --prompt .pi\prompts\report_prompt.md --offline
```

### Mở risk profile

```powershell
notepad .pi\triage\risk_profile.json
```

### Mở report

```powershell
notepad .pi\results\ket_qua.md
```

### Compile check

```powershell
python -m compileall .pi\tools
```

## 15. Debug lỗi thường gặp

### Lỗi 1. `risk_profile.json` không tồn tại

**Nguyên nhân:**  
Chưa chạy Stage 2 hoặc pipeline chưa chạy xong.

**Cách xử lý:**  
Chạy lại pipeline hoặc chạy riêng `risk_scorer.py` từ 3 JSON recon.

### Lỗi 2. Report không sinh ra

**Nguyên nhân:**  
Thiếu `risk_profile.json`, output path sai hoặc exception khi đọc JSON.

**Cách xử lý:**  
Kiểm tra `.pi/triage/risk_profile.json`, sau đó chạy `ai_reporter.py --offline`.

### Lỗi 3. Không có OpenAI API key

**Cách xử lý:**  
Dùng `--offline`. Đây là chế độ demo ổn định.

### Lỗi 4. Risk score thấp dù có port mở

**Giải thích:**  
Score phụ thuộc loại port, số port, banner version, DNS record và target exposure.
Một port HTTP local có thể vẫn Low vì exposure thấp.

### Lỗi 5. Risk score public target cao hơn localhost

**Giải thích:**  
`risk_scorer.py` cộng thêm `exposure_adjustment = 1` nếu target public có open port.

### Lỗi 6. Findings rỗng

**Giải thích:**  
Nếu không có open port, không có DNS record và không có version leak thì findings
có thể rỗng hoặc ít. Đây là kết quả hợp lệ.

## 16. Các câu thầy rất dễ hỏi nhanh

1. Feature vector có bao nhiêu feature?  
   7 feature.

2. Model tên gì?  
   `SimpleIsolationForestRiskModel`.

3. Baseline nằm ở đâu?  
   `BASELINE_SAMPLES` trong `risk_model.py`.

4. Score 0-10 được tính từ đâu?  
   Kết hợp calibrated anomaly và exposure severity.

5. Low/Medium/High map ở đâu?  
   `label_from_score()` trong `risk_model.py`.

6. MITRE mapping nằm ở đâu?  
   `risk_findings.py`.

7. Report offline build ở đâu?  
   `build_offline_report()` trong `report_templates.py`.

8. Agentic mode nằm ở đâu?  
   `pi_recon_agent.py`.

9. Nếu API lỗi thì sao?  
   Fallback offline report.

10. Public target vì sao cộng điểm?  
    Vì exposure Internet cao hơn local/private.

## 17. Checklist trước khi vào vấn đáp

- Em mở được `risk_config.py` và nói được các nhóm port, feature, weight.
- Em mở được `risk_features.py` và giải thích được `extract_features()`.
- Em mở được `risk_model.py` và giải thích được baseline, anomaly score, exposure severity.
- Em mở được `risk_scorer.py` và giải thích được cấu trúc `risk_profile.json`.
- Em mở được `risk_findings.py` và nói được MITRE mapping.
- Em mở được `ai_reporter.py` và nói được API/offline fallback.
- Em mở được `report_templates.py` và giải thích các section report.
- Em hiểu chéo Stage 1 recon của bạn Thông.
- Em sửa được ít nhất 3 bài code tay: MongoDB port, đổi threshold, thêm Evidence Files.

