# 📋 VỤ VĂN THÔNG - TỔNG QUAN HỆ THỐNG

**Topic 02: Network Recon + Risk Profiler Pipeline**

---

## 📑 MỤC LỤC

1. [Tổng quan kiến trúc](#tổng-quan-kiến-trúc)
2. [Luồng dữ liệu Pipeline](#luồng-dữ-liệu-pipeline)
3. [Main Pipeline (`main_pipeline.py`)](#main-pipeline)
4. [3 Recon Tools (DNS, Port, Banner)](#3-recon-tools)
5. [7 Agents và vai trò](#7-agents-và-vai-trò)
6. [Chain Definition và Prompt](#chain-definition-và-prompt)
7. [Triage Folder (Dữ liệu trung gian)](#triage-folder)
8. [Safety Boundaries](#safety-boundaries)

---

## 🎯 Tổng quan kiến trúc

### Sơ đồ cao cấp

```
┌─────────────────────────────────────────────────────────────┐
│                  orchestrator_agent.md                      │
│          (Điều phối toàn bộ pipeline theo thứ tự)           │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────▼─────────────┐
         │  permission_gate_agent.md │
         │  (GATE 0: Kiểm quyền)     │
         └─────────────┬─────────────┘
                       │ allowed?
         ┌─────────────▼─────────────────────────────┐
         │      STAGE 1: PARALLEL RECON (3 agents)  │
         │  ┌──────────────────────────────────────┐ │
         │  │ port_scan_agent.md                   │ │
         │  │ (TCP: 80, 443, 22, ...)              │ │
         │  └──────────────────────────────────────┘ │
         │  ┌──────────────────────────────────────┐ │
         │  │ dns_enum_agent.md                    │ │ (Song song)
         │  │ (A, MX, NS, TXT, PTR)                │ │
         │  └──────────────────────────────────────┘ │
         │  ┌──────────────────────────────────────┐ │
         │  │ banner_grab_agent.md                 │ │
         │  │ (HTTP HEAD, TLS cert, Services)      │ │
         │  └──────────────────────────────────────┘ │
         └─────────────┬─────────────────────────────┘
                       │ (3 JSON files)
         ┌─────────────▼──────────────────┐
         │  risk_score_agent.md           │
         │  (ML Isolation Forest Model)   │
         └─────────────┬──────────────────┘
                       │ (risk_profile.json)
         ┌─────────────▼──────────────────┐
         │  report_agent.md               │
         │  (Markdown Report + MITRE)     │
         └─────────────┬──────────────────┘
                       │
                       ▼
         ┌──────────────────────────┐
         │  ket_qua.md (Report)     │
         │  + Triage JSON files     │
         │  + Pipeline logs         │
         └──────────────────────────┘
```

---

## 🔄 Luồng dữ liệu Pipeline

### Dữ liệu đầu vào (Input)
```
CLI Arguments:
- target: "localhost" (hostname, IP, hoặc URL)
- ports: [21, 22, 80, 443, 3306, 5432, 8080, ...] (danh sách cổng)
- authorized: true/false (xác nhận có quyền)
- timeout: 0.5s (socket timeout an toàn)
- offline: true/false (không gọi OpenAI API)
```

### Giai đoạn xử lý

| Giai đoạn | Mô tả | Đầu vào | Đầu ra | Kiểu |
|----------|-------|---------|---------|------|
| **GATE 0** | Permission check | target, authorized | allowed/blocked | Serial |
| **STAGE 1** | Recon song song | target, ports | 3 JSON files | Parallel (3 workers) |
| **STAGE 2** | ML risk scoring | 3 triage JSON | risk_profile.json | Serial |
| **STAGE 3** | Report generation | risk_profile.json | ket_qua.md | Serial |

### Dữ liệu đầu ra (Output)
```
.pi/triage/port_scan_result.json
.pi/triage/dns_enum_result.json
.pi/triage/banner_result.json
.pi/triage/risk_profile.json
.pi/results/ket_qua.md
.pi/logs/pipeline_run.log
```

---

## 🔧 Main Pipeline

### File: `.pi/tools/main_pipeline.py`

**Mục đích:** Entrypoint chính điều phối toàn bộ pipeline theo thứ tự.

### 4 Hàm chính

#### 1️⃣ **`run_recon_stage(target, ports, timeout) → (dict, dict, dict)`**

**STAGE 1: Khảo sát song song**

**Cơ chế:**
```python
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {
        executor.submit(scan_ports, target, ports, timeout): "port",
        executor.submit(enumerate_dns, target, timeout): "dns",
        executor.submit(grab_banners, target, ports, timeout): "banner",
    }
    
    for future in as_completed(futures):
        # Xử lý task nào xong trước ghi output trước
```

**Đặc điểm:**
- ✅ Chạy 3 tác vụ **cùng lúc** (song song)
- ✅ `as_completed()` không chờ cả 3
- ✅ Mỗi tool cũng song song internal (50 workers)
- ✅ Tiết kiệm thời gian (1-2s thay vì 50-100s)

**Output:** 3 dictionaries → lưu vào triage folder

---

#### 2️⃣ **`run_risk_stage(port_result, dns_result, banner_result) → dict`**

**STAGE 2: ML Risk Scoring**

**Cơ chế:**
```python
risk_profile = score_risk(port_result, dns_result, banner_result)
save_risk_profile(risk_profile, risk_path)
```

**Quá trình:**
1. Trích xuất 7 features từ 3 recon kết quả
2. Chạy Isolation Forest model (64 trees)
3. Tính anomaly score → Calibrate sang 0-10
4. Tạo MITRE ATT&CK mapping
5. Sinh findings + recommendations

**Output:** `risk_profile.json` chứa `score`, `risk_level`, `ml_model`, `findings`, `mitre_mapping`

---

#### 3️⃣ **`run_report_stage(offline) → None`**

**STAGE 3: Report Generation**

**Cơ chế:**
```python
generate_report(risk_path, report_path, prompt_path, offline=offline)
```

**Logic:**
- Đọc `risk_profile.json`
- Tham chiếu `report_prompt.md` (hướng dẫn cấu trúc)
- Nếu `offline=False` + có API key → Gọi OpenAI GPT
- Nếu `offline=True` hoặc API lỗi → Dùng template cố định
- Sinh Markdown report với 9 sections + MITRE mapping

**Output:** `ket_qua.md` - Báo cáo Markdown chi tiết

---

#### 4️⃣ **`run_pipeline(target, ports, authorized, timeout, offline) → dict`**

**Hợp nhất toàn bộ pipeline**

**Quy trình:**
```python
1. ensure_output_dirs()      # Tạo thư mục
2. setup_logging()           # Chuẩn bị log
3. load_env()                # Load .env

4. SAFETY GATE: is_target_allowed(target, authorized)
   if not allowed: raise PermissionError → STOP

5. Stage 1: run_recon_stage()       # ~1-2s
6. Stage 2: run_risk_stage()        # ~0.1-1s
7. Stage 3: run_report_stage()      # ~1-30s (tùy AI)

8. Return {
     "status": "completed",
     "target": target,
     "duration_seconds": total_time,
     "stage_durations": {...},
     "port_scan_result": path,
     "dns_enum_result": path,
     "banner_result": path,
     "risk_profile": path,
     "report": path,
     "log": path
   }
```

**🔑 Điểm quan trọng:**
- ✅ **Safety Gate bắt buộc** - Chạy trước mọi network activity
- ✅ **Stage 1 song parallel** - 3 tasks độc lập
- ✅ **Stage 2-3 tuần tự** - Phụ thuộc data stage trước
- ✅ **Timing chi tiết** - Đo thời gian từng stage

---

## 🔍 3 Recon Tools

### 1. **Port Scanner** (`port_scanner.py`)

**Mục đích:** Quét cổng TCP để tìm cổng mở.

#### Hàm: `scan_port(target, port, timeout) → bool`
```python
try:
    with socket.create_connection((target, port), timeout=timeout):
        return True  # Port mở
except (OSError, socket.timeout):
    return False  # Port đóng
```

**Cơ chế:**
- Tạo TCP socket đến (target, port)
- Timeout ngắn (0.5s) - An toàn, nhanh
- Không gửi payload - Chỉ handshake TCP

#### Hàm: `scan_ports(target, ports, timeout) → dict`
```python
with ThreadPoolExecutor(max_workers=50) as executor:
    futures = {executor.submit(scan_port, target, port, timeout): port
               for port in ports}
    for future in as_completed(futures):
        if future.result():
            open_ports.append(port)
```

**Đặc điểm:**
- ✅ Parallelism 50 workers → Quét nhanh
- ✅ `as_completed()` → Không chờ
- ✅ DEFAULT_PORTS = [21, 22, 80, 443, 3306, 5432, 8080, ...] (16 cổng)

#### Output: `port_scan_result.json`
```json
{
  "target": "localhost",
  "scanned_ports": [21, 22, 80, 443, ...],
  "open_ports": [80, 445, 5432],
  "open_count": 3
}
```

---

### 2. **DNS Enumeration** (`dns_enum.py`)

**Mục đích:** Truy vấn DNS records để khám phá cơ sở hạ tầng.

#### Hàm: `enumerate_dns(domain, timeout) → dict`

**Logic:**
```python
1. is_localhost(domain)?
   → Yes: skip, return skipped=True
   
2. is_ip_address(domain)?
   → Yes: Query PTR reverse DNS chỉ
   → No: Query A, CNAME, MX, NS, SOA, TXT

3. Mỗi record_type:
   - Thử resolver.resolve(domain, record_type)
   - Nếu OK → records[type] = [...]
   - Nếu lỗi → errors[type] = "Error message"
   (Không fail toàn bộ, skip record đó)
```

**DNS Record Types:**
- **A:** IPv4 address
- **MX:** Mail exchange (email servers)
- **NS:** Nameservers
- **TXT:** Text records (SPF, DKIM, v=spf1, ...)
- **SOA:** Start of authority
- **CNAME:** Canonical name (alias)
- **PTR:** Pointer (reverse DNS for IPs)

#### Output: `dns_enum_result.json`
```json
{
  "target": "localhost",
  "skipped": true,
  "message": "DNS enumeration skipped for localhost target",
  "records": {},
  "errors": {}
}
```

**Nếu target là domain:**
```json
{
  "target": "example.com",
  "records": {
    "A": ["93.184.216.34"],
    "MX": ["10 mail.example.com"],
    "NS": ["a.iana-servers.net"],
    "TXT": ["v=spf1 include:_spf.google.com ~all"]
  },
  "errors": {}
}
```

---

### 3. **Banner Grabber** (`banner_grabber.py`)

**Mục đích:** Đọc banner dịch vụ để phát hiện phiên bản phần mềm.

#### Hàm: `grab_banner(target, port, timeout) → str`

**Cơ chế:**
```python
1. Socket TCP đến (target, port)
2. Nếu HTTP port (80, 3000, 8000, 8080):
   - Gửi "HEAD / HTTP/1.1\r\n..."
   - Server trả HTTP header
3. Nếu port khác:
   - Đợi server tự gửi banner (SSH, SMTP, ...)
4. Đọc max 1024 bytes, clean up (max 500 ký tự)
```

**Ví dụ output:**
- Port 22 (SSH): `SSH-2.0-OpenSSH_7.4`
- Port 80 (HTTP): `HTTP/1.1 200 OK\r\nServer: nginx/1.17.0`
- Port 3306 (MySQL): `MySQL version 5.7.30-0ubuntu0.18.04.1`

#### Hàm: `inspect_tls(target, port, timeout) → dict`

**Lấy SSL/TLS certificate metadata (chỉ TLS ports: 443, 465, 636, 993, 995, 8443)**

```python
context = ssl.create_default_context()
context.check_hostname = False      # Không validate domain
context.verify_mode = ssl.CERT_NONE # Không validate trust

# Lấy metadata: protocol, cipher, subject, issuer, expiry
return {
    "protocol": "TLSv1.3",
    "cipher": "TLS_AES_256_GCM_SHA384",
    "subject": [["CN", "example.com"]],
    "issuer": [["CN", "Let's Encrypt Authority X3"]],
    "not_after": "2025-06-15"
}
```

#### Hàm: `identify_service(port, banner) → str`

**Nhận dạng service từ port + banner markers:**
```python
markers = [
    ("ssh-", "ssh"),
    ("smtp", "smtp"),
    ("mysql", "mysql"),
    ("postgresql", "postgresql"),
    ("redis", "redis"),
    ("http/", "http")
]
# Nếu không match → SERVICE_BY_PORT.get(port, "unknown")
```

#### Hàm: `grab_banners(target, candidate_ports, timeout) → dict`

**Song parallel 50 workers:**
```python
with ThreadPoolExecutor(max_workers=50) as executor:
    futures = {executor.submit(grab_banner, target, port, timeout): port
               for port in candidate_ports}
    for future in as_completed(futures):
        port = futures[future]
        banners[str(port)] = future.result()
        services[str(port)] = identify_service(port, banners[str(port)])
        tls_result = inspect_tls(target, port, timeout)
        if tls_result:
            tls[str(port)] = tls_result
```

#### Output: `banner_result.json`
```json
{
  "target": "localhost",
  "attempted_ports": [21, 22, 80, 443, ...],
  "banners": {
    "80": "HTTP/1.1 302 Moved Temporarily\r\nServer: PRTG\r\n...",
    "445": "No banner",
    "5432": "No banner"
  },
  "services": {
    "80": "http",
    "445": "smb",
    "5432": "postgresql"
  },
  "tls": {}
}
```

---

## 👥 7 Agents và vai trò

### 1️⃣ **Orchestrator Agent** (`orchestrator_agent.md`)

**Vai trò:** 🎯 **Điều phối viên** - Quản lý flow pipeline theo đúng thứ tự

**Trách nhiệm:**
```
1. Chuẩn hóa input (target, ports, authorized)
2. Gọi permission_gate_agent TRƯỚC bất kỳ network activity
3. Chạy 3 recon agents SONG SONG
4. Chờ cả 3 hoàn tất → Gọi risk_score_agent
5. Gọi report_agent
6. Trả về tất cả output paths
```

**Quy tắc Handoff:**
- ❌ Không chạy Stage 1 nếu permission gate block
- ❌ Không chạy risk scoring nếu thiếu JSON recon
- ❌ Không chạy report nếu thiếu risk_profile.json

**Output:**
```python
{
    "port_scan_result": ".pi/triage/port_scan_result.json",
    "dns_enum_result": ".pi/triage/dns_enum_result.json",
    "banner_result": ".pi/triage/banner_result.json",
    "risk_profile": ".pi/triage/risk_profile.json",
    "report": ".pi/results/ket_qua.md",
    "log": ".pi/logs/pipeline_run.log"
}
```

---

### 2️⃣ **Permission Gate Agent** (`permission_gate_agent.md`)

**Vai trò:** 🔐 **Gatekeeper** - Bảo vệ pipeline bằng cách xác minh quyền

**Quy tắc (Decision Logic):**

| Target | Điều kiện | Kết luận |
|--------|-----------|---------|
| `localhost`, `127.0.0.1`, `::1` | - | ✅ **ALLOW** (local demo) |
| Public lab target | Nằm trong `.pi/data/allowed_targets.json` | ✅ **ALLOW** |
| Bất kỳ target | `--authorized=true` | ✅ **ALLOW** |
| **Mọi target khác** | - | ❌ **BLOCK** (deny by default) |

**Ví dụ:**
```bash
# ✅ ALLOW
python main_pipeline.py --target=localhost
python main_pipeline.py --target=127.0.0.1
python main_pipeline.py --target=lab.classroom.com  # (nếu có trong allowlist)
python main_pipeline.py --target=192.168.1.100 --authorized

# ❌ BLOCK
python main_pipeline.py --target=192.168.1.100
# ERROR: Permission gate blocked this target
```

**Output:**
```json
{
  "allowed": true/false,
  "target": "localhost",
  "reason": "...",
  "next_stage": "parallel_recon" or "blocked"
}
```

---

### 3️⃣ **Port Scan Agent** (`port_scan_agent.md`)

**Vai trò:** 🔍 **Port Finder** - Quét TCP để tìm cổng mở

**Action:**
```python
for port in ports:
    try:
        socket.create_connection((target, port), timeout=0.5)
        open_ports.append(port)
    except:
        pass  # Closed
```

**Input:** `target`, `ports`  
**Output:** `.pi/triage/port_scan_result.json` - `open_ports: [80, 445, 5432]`

---

### 4️⃣ **DNS Enum Agent** (`dns_enum_agent.md`)

**Vai trò:** 🌐 **DNS Investigator** - Truy vấn DNS records

**Quy tắc:**
- Localhost → Skip
- IP address → PTR reverse DNS
- Domain → A, MX, NS, SOA, TXT, CNAME

**Input:** `target`  
**Output:** `.pi/triage/dns_enum_result.json` - `records: {...}`, `errors: {...}`

---

### 5️⃣ **Banner Grab Agent** (`banner_grab_agent.md`)

**Vai trò:** 📜 **Service Recognizer** - Đọc banner dịch vụ

**Action:**
```python
for port in ports:
    banner = grab_banner(target, port)      # TCP read
    service = identify_service(port, banner) # Guess service
    tls = inspect_tls(target, port)          # If TLS
```

**Input:** `target`, `ports`  
**Output:** `.pi/triage/banner_result.json` - `banners: {...}`, `services: {...}`, `tls: {...}`

---

### 6️⃣ **Risk Score Agent** (`risk_score_agent.md`)

**Vai trò:** 🤖 **ML Risk Predictor** - Tính điểm rủi ro từ recon data

**Quá trình:**

**Step 1: Trích xuất Features**
```python
features = {
    "open_port_count": 3,              # [80, 445, 5432]
    "sensitive_port_count": 2,         # [445, 5432] = SMB + DB
    "high_risk_port_count": 1,         # [445] hoặc [5432]
    "database_cache_port_count": 1,    # [5432] = PostgreSQL
    "http_port_count": 1,              # [80]
    "version_banner_count": 0,         # Không có version leak
    "dns_record_count": 0              # localhost skip DNS
}
feature_vector = [3, 2, 1, 1, 1, 0, 0]
```

**Step 2: Chạy Isolation Forest Model**
```python
model = IsolationForest(n_estimators=64, max_depth=3, random_state=42)
anomaly_score = 0.5789  # Cao hơn baseline (0.4945)
```

**Step 3: Calibrate sang Risk Level**
```python
score = 4           # 0-10 scale
risk_level = "Medium"  # Low, Medium, High
```

**Step 4: MITRE ATT&CK Mapping**
```python
[
    {
        "technique_id": "T1046",
        "technique": "Network Service Discovery",
        "tactic": "Discovery"
    },
    {
        "technique_id": "T1595",
        "technique": "Active Scanning",
        "tactic": "Reconnaissance"
    }
]
```

**Input:** `.pi/triage/{port_scan,dns_enum,banner}_result.json`  
**Output:** `.pi/triage/risk_profile.json` - `score`, `risk_level`, `ml_model`, `mitre_mapping`, `findings`, `recommendations`

---

### 7️⃣ **Report Agent** (`report_agent.md`)

**Vai trò:** 📝 **Report Writer** - Sinh báo cáo Markdown

**Process:**
1. Đọc `risk_profile.json`
2. Tham chiếu `report_prompt.md` (hướng dẫn cấu trúc)
3. Nếu có API key + `offline=False` → Gọi OpenAI GPT
4. Nếu `offline=True` hoặc API lỗi → Dùng template cố định
5. Sinh Markdown với 9 sections

**Mandatory Rules:**
- ❌ Không exploit steps
- ❌ Không payloads
- ❌ Không brute-force / bypass / attack guidance
- ✅ Chỉ defensive observations + recommendations
- ✅ MITRE ATT&CK mapping
- ✅ ML model explanation

**Input:** `.pi/triage/risk_profile.json`, `.pi/prompts/report_prompt.md`  
**Output:** `.pi/results/ket_qua.md` - Report Markdown 9 sections

---

## 📊 Chain Definition và Prompt

### Chain: `recon_risk_pipeline.chain.md`

**Blueprint** - Định nghĩa toàn bộ flow pipeline.

**Cấu trúc:**
```markdown
# Stage 0: Permission Gate
permission_gate_agent(target, authorized)
→ allowed? → continue : blocked

# Stage 1: Parallel Recon
/parallel
  port_scan_agent(target, ports)
  dns_enum_agent(target)
  banner_grab_agent(target, ports)
/join
→ 3 JSON files

# Stage 2: ML Risk Scoring
risk_score_agent()
→ risk_profile.json

# Stage 3: Report Generation
report_agent()
→ ket_qua.md
```

**Đặc điểm:**
- ✅ **Deterministic pipeline** - Quy tắc cứng
- ✅ **Stage 1 parallelism** - 3 recon song parallel
- ✅ **Per-port parallelism** - 50 workers mỗi tool
- ✅ **Stage 2-3 sequential** - Phụ thuộc data
- ✅ **Safety boundary** - Read-only, allowlist gate

---

### Prompt: `report_prompt.md`

**Template guide** - Hướng dẫn cách sinh báo cáo.

**Mandatory Sections:**
```
1. Target
2. Scope & Authorization
3. Recon Summary
4. Risk Level
5. ML Risk Model
6. Findings
7. MITRE ATT&CK Mapping
8. Recommendations
9. Conclusion
```

---

## 📁 Triage Folder (Dữ liệu trung gian)

**Vai trò:** `.pi/triage/` lưu intermediate JSON files giữa các giai đoạn.

### 4 File Triage

#### 1️⃣ **`port_scan_result.json`**

**Từ:** port_scan_agent  
**Dùng cho:** risk_score_agent, report_agent

```json
{
  "target": "localhost",
  "scanned_ports": [21, 22, 23, 25, 53, 80, 110, 139, 143, 443, 445, 3306, 5432, 6379, 8000, 8080],
  "open_ports": [80, 445, 5432],
  "open_count": 3
}
```

**Ý nghĩa:**
- 16 cổng quét (default list)
- 3 cổng mở: HTTP (80), SMB (445), PostgreSQL (5432)

---

#### 2️⃣ **`dns_enum_result.json`**

**Từ:** dns_enum_agent  
**Dùng cho:** risk_score_agent

```json
{
  "target": "localhost",
  "skipped": true,
  "message": "DNS enumeration skipped for localhost target",
  "records": {},
  "errors": {}
}
```

**Ý nghĩa:**
- Localhost không cần DNS lookup
- DNS record count = 0 → Ảnh hưởng risk score

---

#### 3️⃣ **`banner_result.json`**

**Từ:** banner_grab_agent  
**Dùng cho:** risk_score_agent, report_agent

```json
{
  "target": "localhost",
  "attempted_ports": [21, 22, ..., 8080],
  "banners": {
    "80": "HTTP/1.1 302 Moved Temporarily\r\nServer: PRTG\r\n...",
    "445": "No banner",
    "5432": "No banner"
  },
  "services": {
    "80": "http",
    "445": "smb",
    "5432": "postgresql"
  },
  "tls": {}
}
```

**Ý nghĩa:**
- Port 80 banner tiết lộ **PRTG** server
- Port 445 = SMB, Port 5432 = PostgreSQL
- Không có TLS/SSL

---

#### 4️⃣ **`risk_profile.json`** (Lớn nhất)

**Từ:** risk_score_agent  
**Dùng cho:** report_agent

```json
{
  "target": "localhost",
  "score": 4,
  "risk_level": "Medium",
  "ml_model": {
    "name": "SimpleIsolationForestRiskModel",
    "type": "unsupervised Isolation Forest",
    "n_trees": 64,
    "features": {
      "open_port_count": 3,
      "sensitive_port_count": 2,
      "high_risk_port_count": 1,
      "database_cache_port_count": 1,
      "http_port_count": 1,
      "version_banner_count": 0,
      "dns_record_count": 0
    },
    "anomaly_score": 0.5789,
    "exposure_severity": 0.89,
    "risk_drivers": [
      {
        "feature": "open_port_count",
        "value": 3,
        "contribution": 2.4
      },
      {
        "feature": "sensitive_port_count",
        "value": 2,
        "contribution": 2.4
      }
    ]
  },
  "mitre_mapping": [
    {
      "technique_id": "T1046",
      "technique": "Network Service Discovery",
      "tactic": "Discovery"
    },
    {
      "technique_id": "T1595",
      "technique": "Active Scanning",
      "tactic": "Reconnaissance"
    }
  ],
  "findings": [
    {"type": "open_port", "port": 80, "service": "HTTP"},
    {"type": "open_port", "port": 445, "service": "SMB"},
    {"type": "open_port", "port": 5432, "service": "PostgreSQL"}
  ],
  "recommendations": [
    "Restrict Unnecessary Services",
    "Update Systems",
    "Secure Database Access",
    "Audit Web Server Configuration",
    "Enable Logging"
  ]
}
```

**Ý nghĩa:**
- **Trung tâm dữ liệu** - Tất cả decision scoring, MITRE mapping, findings ở đây
- Được dùng làm source duy nhất cho report_agent

---

## 🔐 Safety Boundaries

### ✅ Cho phép

- ✅ Read-only reconnaissance
- ✅ Local targets (localhost, 127.0.0.1)
- ✅ Lab/classroom allowlist targets
- ✅ External targets với `--authorized` flag
- ✅ TCP connect test (nhanh, không gây hại)
- ✅ DNS query (standard queries, không brute force)
- ✅ Banner read (passive, không trigger)
- ✅ TLS cert inspection (no validation skip)

### ❌ Cấm

- ❌ Exploit, payload, brute-force
- ❌ Bypass, unauthorized access
- ❌ Expanding scope ngoài allowlist
- ❌ Attack guidance trong report
- ❌ Modifying target data
- ❌ Scanning multiple IPs/CIDR ranges (ngoài scope)

### Allowlist Mechanism

**File:** `.pi/data/allowed_targets.json`

**Quy tắc:**
```
1. Localhost targets (127.0.0.1, ::1) → Always allow
2. Classroom/lab targets → Check allowlist
3. External targets → Require --authorized flag
4. Default: Deny unless explicitly allowed
```

---

## 📈 Luồng dữ liệu Chi tiết

### Ví dụ thực tế (localhost)

```
INPUT:
  target: "localhost"
  ports: [21, 22, 80, 443, 445, 3306, 5432, 8080, ...]
  authorized: false

         ▼
┌─────────────────────────────────────────────────────┐
│ Permission Gate: is_target_allowed("localhost", F) │
│ → Yes (localhost always allowed)                   │
└──────────┬──────────────────────────────────────────┘
           │
    ┌──────▼──────────────────────────────────────────┐
    │ STAGE 1: Parallel Recon (3 workers, async)      │
    │                                                  │
    │ ┌─────────────────────────────────────────────┐ │
    │ │ port_scan_agent (50 per-port workers)      │ │
    │ │ → Quét 16 cổng song parallel              │ │
    │ │ → Kết quả: open_ports = [80, 445, 5432]   │ │
    │ │ → Lưu: port_scan_result.json               │ │
    │ └─────────────────────────────────────────────┘ │
    │                                                  │
    │ ┌─────────────────────────────────────────────┐ │
    │ │ dns_enum_agent                              │ │
    │ │ → is_localhost(target)? Yes                 │ │
    │ │ → Skip DNS lookup                           │ │
    │ │ → Lưu: dns_enum_result.json (skipped=true) │ │
    │ └─────────────────────────────────────────────┘ │
    │                                                  │
    │ ┌─────────────────────────────────────────────┐ │
    │ │ banner_grab_agent (50 per-port workers)    │ │
    │ │ → Thử lấy banner từ 16 cổng                 │ │
    │ │ → Port 80: "HTTP/1.1 302... Server: PRTG"  │ │
    │ │ → Port 445, 5432: "No banner"              │ │
    │ │ → Lưu: banner_result.json                   │ │
    │ └─────────────────────────────────────────────┘ │
    │                                                  │
    │ ⏱ Total Stage 1 Time: ~1-2s                    │
    └──────┬───────────────────────────────────────────┘
           │ (3 JSON files ready)
           │
    ┌──────▼──────────────────────────────────────────┐
    │ STAGE 2: Risk Scoring (ML)                      │
    │                                                  │
    │ 1. Đọc 3 triage JSON                           │
    │ 2. Trích 7 features:                            │
    │    - open_port_count: 3                         │
    │    - sensitive_port_count: 2                    │
    │    - high_risk_port_count: 1                    │
    │    - database_cache_port_count: 1              │
    │    - http_port_count: 1                         │
    │    - version_banner_count: 0                    │
    │    - dns_record_count: 0                        │
    │ 3. Run Isolation Forest (64 trees)             │
    │ 4. anomaly_score = 0.5789 > baseline 0.4945    │
    │ 5. Calibrate → score=4, level="Medium"         │
    │ 6. MITRE mapping: T1046, T1595                 │
    │ 7. Sinh findings + recommendations             │
    │ 8. Lưu: risk_profile.json                       │
    │                                                  │
    │ ⏱ Total Stage 2 Time: ~0.5s                     │
    └──────┬───────────────────────────────────────────┘
           │ (risk_profile.json ready)
           │
    ┌──────▼──────────────────────────────────────────┐
    │ STAGE 3: Report Generation                      │
    │                                                  │
    │ 1. Đọc risk_profile.json                        │
    │ 2. Tham chiếu report_prompt.md                  │
    │ 3. Nếu offline=True:                            │
    │    → Dùng template markdown cố định             │
    │ 4. Sinh 9 sections:                             │
    │    - Target, Scope & Authorization             │
    │    - Recon Summary (3 ports mở)                │
    │    - Risk Level (Medium, 4/10)                  │
    │    - ML Risk Model (Isolation Forest)           │
    │    - Findings (3 open ports)                    │
    │    - MITRE ATT&CK Mapping                       │
    │    - Recommendations                            │
    │    - Conclusion                                 │
    │ 5. Lưu: ket_qua.md                              │
    │                                                  │
    │ ⏱ Total Stage 3 Time: ~1s                       │
    └──────┬───────────────────────────────────────────┘
           │
    ┌──────▼────────────────────────────────────────┐
    │ OUTPUT FILES                                   │
    │ ✓ .pi/triage/port_scan_result.json            │
    │ ✓ .pi/triage/dns_enum_result.json             │
    │ ✓ .pi/triage/banner_result.json               │
    │ ✓ .pi/triage/risk_profile.json                │
    │ ✓ .pi/results/ket_qua.md (Report)             │
    │ ✓ .pi/logs/pipeline_run.log                   │
    │                                                │
    │ ⏱ Total Pipeline Time: ~2-4s                  │
    └────────────────────────────────────────────────┘
```

---

## 📊 Tóm tắt vai trò 7 Agents

| Agent | Giai đoạn | Vai trò | Input | Output |
|-------|----------|--------|-------|--------|
| **Orchestrator** | - | Điều phối thứ tự | CLI args | 6 file paths |
| **Permission Gate** | **GATE 0** | Kiểm quyền | target, authorized | allowed/blocked |
| **Port Scan** | **Stage 1** | Quét cổng TCP | target, ports | `port_scan_result.json` |
| **DNS Enum** | **Stage 1** | Query DNS | target | `dns_enum_result.json` |
| **Banner Grab** | **Stage 1** | Đọc banner | target, ports | `banner_result.json` |
| **Risk Score** | **Stage 2** | Tính ML risk | 3 triage JSON | `risk_profile.json` |
| **Report** | **Stage 3** | Sinh báo cáo | risk_profile.json | `ket_qua.md` |

---

## 🚀 Extension: Week 5 Agentic Loop

File `.pi/tools/pi_recon_agent.py` sử dụng **OpenAI tool-calling loop:**

```python
while True:
    1. Send message + history to GPT
    2. GPT returns tool_calls (JSON schema)
    3. Execute tool_calls (scan_ports, enumerate_dns, ...)
    4. Append results back to history
    5. If finish_reason="stop": break
    6. Else: continue loop
```

**Lợi ích:**
- ✅ Agent autonomy - Self-deciding what to scan
- ✅ Adaptive flow - Không tuân fixed pipeline
- ✅ Natural language - "Scan this target thoroughly"

---

## 📚 Tài liệu Liên quan

- `HUONG_DAN_CHAY_BAO_CAO.md` - Hướng dẫn chạy
- `.pi/agents/` - 7 agent definitions
- `.pi/chains/recon_risk_pipeline.chain.md` - Pipeline blueprint
- `.pi/tools/` - Tất cả implementation tools
- `.pi/triage/` - Intermediate data files
- `.pi/results/ket_qua.md` - Final report

---

## 🎓 Kết luận

**Network Recon + Risk Profiler** là hệ thống **phân tán, an toàn, có kiểm soát** cho reconnaissance và risk profiling:

✅ **Parallelism** - Stage 1 chạy 3 recon cùng lúc + per-port workers  
✅ **Safety** - Permission gate + allowlist trước network activity  
✅ **Transparency** - Tất cả intermediate data lưu JSON  
✅ **Explainability** - ML model (Isolation Forest) + MITRE mapping  
✅ **Educational** - Phù hợp student final project  

---

**Tài liệu tổng quản này được tạo ngày:** June 15, 2026

