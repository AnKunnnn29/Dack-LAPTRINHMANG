# Oral Defense Q&A - Topic 02

Use this file to prepare for the oral test and quick coding questions.

## 0. One-Minute Summary

**Question:** What does your project do?

**Answer:** My project is Topic 02: Network Recon + Risk Profiler. It runs three
reconnaissance tasks in parallel: TCP port scanning, DNS enumeration, and banner
grabbing. Then it extracts simple features from the recon results, predicts a
Low/Medium/High risk level using a small KNN model, maps findings to MITRE
ATT&CK, and generates a defensive Markdown report.

**Question:** What are the three stages?

**Answer:**

1. Stage 1: Parallel Recon - port scan, DNS enum, banner grab.
2. Stage 2: ML Risk Scoring - feature extraction and KNN prediction.
3. Stage 3: Reporting - MITRE-mapped Markdown report with GPT or offline fallback.

**Question:** Where is the main code?

**Answer:** The stable runner is `.pi/tools/main_pipeline.py`. The Week 5
agentic runner is `.pi/tools/pi_recon_agent.py`.

## 1. Topic And Rubric Questions

**Q1. Why is this Topic 02?**

A: Topic 02 requires a recon pipeline that runs port scanning, DNS enumeration,
and banner grabbing simultaneously, then feeds combined results to an ML risk
scorer and a GPT/MITRE report. My code implements exactly these stages.

**Q2. Where are the Pi agent files?**

A: They are in `.pi/agents/*.md`: `port_scan_agent`, `dns_enum_agent`,
`banner_grab_agent`, `risk_score_agent`, and `report_agent`.

**Q3. Where are the skills?**

A: In `.pi/skills/recon`, `.pi/skills/risk_scoring`, and `.pi/skills/reporting`.

**Q4. Where is the chain file?**

A: `.pi/chains/recon_risk_pipeline.chain.md`.

**Q5. Where is the prompt file?**

A: `.pi/prompts/report_prompt.md`.

**Q6. Where is at least one parallel stage?**

A: In `.pi/tools/main_pipeline.py`, function `run_recon_stage()`. It uses
`ThreadPoolExecutor(max_workers=3)` to run `scan_ports`, `enumerate_dns`, and
`grab_banners` at the same time.

**Q7. Why does Stage 1 run in parallel?**

A: The three tasks do not depend on each other. They are mostly network I/O, so
parallel execution reduces waiting time.

**Q8. Is the project offensive or defensive?**

A: Defensive. It only performs read-only recon on authorized targets and creates
risk recommendations. It does not exploit, brute force, bypass, or send payloads.

**Q9. What output files are created?**

A:

- `.pi/triage/port_scan_result.json`
- `.pi/triage/dns_enum_result.json`
- `.pi/triage/banner_result.json`
- `.pi/triage/risk_profile.json`
- `.pi/results/ket_qua.md`
- `.pi/logs/pipeline_run.log`

**Q10. Why is the code simple?**

A: It is designed for classroom explanation. Each tool has one job, the ML model
is explainable, and the pipeline is easy to redraw and rewrite.

## 2. Pipeline And Code Walkthrough

**Q11. What happens in `main_pipeline.py`?**

A: It parses CLI arguments, checks permission, runs Stage 1 parallel recon, runs
Stage 2 risk scoring, runs Stage 3 report generation, then prints output paths.

**Q12. What does `parse_target()` do?**

A: It accepts a raw target such as `localhost`, `localhost:8000`, or
`http://localhost:8000`, then returns `(host, optional_ports)`.

**Q13. What does `parse_ports()` do?**

A: It converts strings like `80,443,8000` or `1-1000` into a sorted list of
unique integers.

**Q14. What does `choose_ports()` do?**

A: It chooses ports in priority order: CLI `--ports`, then port from URL, then
default ports.

**Q15. Why use `ensure_output_dirs()`?**

A: To make sure `.pi/triage`, `.pi/logs`, and `.pi/results` exist before writing
JSON, logs, or reports.

**Q16. Why use `write_json()`?**

A: It centralizes JSON writing and uses `indent=2` and UTF-8 so output is easy to
read.

**Q17. Why does `run_pipeline()` check `is_target_allowed()` first?**

A: To enforce the safety boundary before any network scan starts.

**Q18. Why does `run_recon_stage()` write JSON files inside Stage 1?**

A: Each agent output becomes a file in `.pi/triage`, so Stage 2 can read or reuse
them later.

**Q19. Why does `as_completed()` appear in parallel code?**

A: It lets the program handle whichever task finishes first instead of waiting in
submission order.

**Q20. Why is banner grabbing independent from port scanning?**

A: For Topic 02 parallelism, banner grabbing tries the same candidate ports
directly instead of waiting for the scanner output. That keeps Stage 1 tasks
independent.

## 3. Networking And Socket Questions

**Q21. What socket function checks if a port is open?**

A: `socket.create_connection((target, port), timeout=timeout)`.

**Q22. Why set timeout?**

A: Without timeout, a closed or filtered port may block too long. Timeout makes
the scanner predictable and safe for demos.

**Q23. What does `scan_port()` return?**

A: `True` if TCP connection succeeds, otherwise `False`.

**Q24. Why catch `OSError` and `socket.timeout`?**

A: Closed, refused, filtered, or unreachable ports raise socket errors. We treat
those as not open.

**Q25. What is the difference between port scanning and banner grabbing?**

A: Port scanning only checks whether a TCP connection can be opened. Banner
grabbing reads service text or HTTP headers to identify software/version.

**Q26. Why does HTTP banner grabbing send a request?**

A: Many HTTP servers do not send data until the client sends an HTTP request.
The code sends a simple `HEAD / HTTP/1.1` request.

**Q27. Why use `sendall()`?**

A: `send()` may send only part of the buffer. `sendall()` keeps sending until the
whole request is written or an error occurs.

**Q28. What does `recv(1024)` mean?**

A: Read up to 1024 bytes. It may return fewer bytes depending on what the server
sends.

**Q29. Why clean banners?**

A: To decode bytes safely, remove surrounding whitespace, and cap long output for
the report.

**Q30. Why skip DNS enum for localhost or IP?**

A: DNS record lookup is meaningful for domains. Localhost and raw IPs usually do
not have A/MX/NS/TXT records in the same way.

## 4. Parallelism Questions

**Q31. What parallelism library is used?**

A: `concurrent.futures.ThreadPoolExecutor`.

**Q32. Why threads instead of processes?**

A: These tasks are I/O-bound, not CPU-bound. Threads are simpler and efficient
for waiting on network sockets.

**Q33. Where is per-port parallelism?**

A: In `.pi/tools/recon/port_scanner.py`, function `scan_ports()`.

**Q34. How many workers does the port scanner use?**

A: `min(100, max(1, len(selected_ports)))`. It avoids creating more than 100
threads.

**Q35. What is the benefit of parallel scanning?**

A: If many ports timeout, serial scanning is slow. Parallel scanning waits for
many ports at once and reduces wall-clock time.

**Q36. What is the risk of too much parallelism?**

A: It may overload the machine, trigger IDS alerts, or look like aggressive
scanning. That is why we keep a bounded worker count and small port list.

## 5. ML And Feature Engineering Questions

**Q37. What are the seven ML features?**

A:

1. `open_port_count`
2. `sensitive_port_count`
3. `high_risk_port_count`
4. `database_cache_port_count`
5. `http_port_count`
6. `version_banner_count`
7. `dns_record_count`

**Q38. What is a sensitive port in this project?**

A: Ports like FTP, SSH, Telnet, SMB, MySQL, PostgreSQL, and Redis. In code:
`{21, 22, 23, 445, 3306, 5432, 6379}`.

**Q39. What is a high-risk port in this project?**

A: Telnet 23, SMB 445, and Redis 6379.

**Q40. How does the project detect version leakage?**

A: `banner_has_version()` checks banners with regex patterns like `Server: ...1.0`,
`MySQL 8.0`, `Redis 7.2`, etc.

**Q41. What does KNN mean?**

A: K-Nearest Neighbors. It compares the current feature vector with labelled
training samples and uses the nearest samples to predict the class.

**Q42. What distance metric is used?**

A: Euclidean distance: square root of the sum of squared differences.

**Q43. Why is KNN suitable here?**

A: It is easy to explain and easy to code. The goal is not production IDS
accuracy, but an explainable classroom ML scoring layer.

**Q44. How is the final score calculated?**

A: The model takes the nearest 3 samples and averages their risk scores, then
rounds the result.

**Q45. How is the final label selected?**

A: It counts labels among the nearest neighbors. If tied, it keeps the label of
the closest sample.

**Q46. What is the limitation of this ML model?**

A: It uses small hand-written training samples, so it is a demonstration model,
not a production-trained classifier.

## 6. MITRE And Reporting Questions

**Q47. Which MITRE techniques are mapped?**

A:

- `T1046` Network Service Discovery
- `T1595` Active Scanning
- `T1590` Gather Victim Network Information
- `T1592.002` Gather Victim Host Information: Software

**Q48. Why map open ports to T1046?**

A: Discovering open network services matches Network Service Discovery.

**Q49. Why map banner versions to T1592.002?**

A: Banners may reveal software information, which maps to gathering host software
information.

**Q50. What report sections are required?**

A: Target, Recon Summary, Risk Level, ML Risk Model, Findings, MITRE ATT&CK
Mapping, Recommendations, and Conclusion.

**Q51. What happens if there is no API key?**

A: `generate_report()` uses `build_offline_report()` and still writes
`.pi/results/ket_qua.md`.

**Q52. Why have an offline report fallback?**

A: So the project can be demoed and graded even without network/API access.

**Q53. What safety rules are in the prompt?**

A: Do not include exploit steps, payloads, brute-force guidance, bypass steps, or
attack instructions.

## 7. Week 5 Agent Loop Questions

**Q54. What is the difference between the stable pipeline and agentic mode?**

A: The stable pipeline is deterministic Python orchestration. Agentic mode exposes
the same tools to GPT through function calling and lets the model request tools.

**Q55. Where is the agentic runner?**

A: `.pi/tools/pi_recon_agent.py`.

**Q56. What is the Observe-Think-Act loop here?**

A:

1. Observe: model receives user request and previous messages.
2. Think: model decides whether to call tools.
3. Act: Python executes tool calls and appends tool results.
4. Repeat until `finish_reason == "stop"`.

**Q57. Why keep message history?**

A: The model needs to see previous assistant turns and tool results to decide the
next step.

**Q58. Why preserve assistant `tool_calls`?**

A: OpenAI tool calling requires the assistant message with its tool call IDs to be
in history before appending matching tool results.

**Q59. Why match `tool_call_id`?**

A: It tells the model which result belongs to which requested tool call.

**Q60. What tools are exposed to the agent?**

A: `scan_ports`, `enumerate_dns`, `grab_banners`, `score_risk_from_triage`, and
`generate_markdown_report`.

**Q61. What safety exists in agentic mode?**

A: Target allowlist, `--authorized`, simple rate limiting, limited max iterations,
and defensive system prompt.

## 8. Safety And Testing Questions

**Q62. What is the allowlist?**

A: A list of targets allowed for scanning, stored in `.pi/data/allowed_targets.json`.

**Q63. What does `--authorized` mean?**

A: The user explicitly confirms they have permission to scan a target outside the
allowlist.

**Q64. Why not allow arbitrary targets by default?**

A: Unauthorized scanning may be illegal and unsafe.

**Q65. What is tested in `tests/test_project02.py`?**

A: Port parsing, target parsing, allowlist behavior, and risk profile structure.

**Q66. Why test simple helper functions?**

A: They are small but important. If parsing or safety gates break, the whole
pipeline becomes unreliable.

**Q67. What command runs tests?**

A: `python -m unittest discover -s tests`.

**Q68. What command checks syntax?**

A: `python -m compileall test_api.py .pi/tools`.

## 9. Coding Drills

### Drill 1: Re-code `parse_ports()`

**Task:** Convert `"80,443,1-3"` to `[1, 2, 3, 80, 443]`.

**Key idea:** Split by comma. If part has `-`, expand range. Use `set` to remove
duplicates, then sort.

```python
def parse_ports(raw_ports):
    ports = []
    for part in raw_ports.split(","):
        item = part.strip()
        if not item:
            continue
        if "-" in item:
            start, end = item.split("-", 1)
            start, end = int(start), int(end)
            if start > end:
                start, end = end, start
            ports.extend(range(start, end + 1))
        else:
            ports.append(int(item))
    return sorted(set(ports))
```

### Drill 2: Re-code `scan_port()`

**Task:** Check whether one TCP port is open.

**Key idea:** Try `socket.create_connection`; success means open, error means
closed/filtered.

```python
import socket

def scan_port(target, port, timeout=0.5):
    try:
        with socket.create_connection((target, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False
```

### Drill 3: Re-code parallel `scan_ports()`

**Task:** Scan many ports with threads.

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def scan_ports(target, ports, timeout=0.5):
    open_ports = []
    with ThreadPoolExecutor(max_workers=min(100, len(ports))) as executor:
        futures = {executor.submit(scan_port, target, port, timeout): port for port in ports}
        for future in as_completed(futures):
            port = futures[future]
            if future.result():
                open_ports.append(port)
    return {"target": target, "scanned_ports": ports, "open_ports": sorted(open_ports)}
```

### Drill 4: Re-code `grab_banner()`

**Task:** Connect, optionally send HTTP HEAD, receive up to 1024 bytes.

```python
def grab_banner(target, port, timeout=1.0):
    try:
        with socket.create_connection((target, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            if port in {80, 3000, 8000, 8080}:
                req = f"HEAD / HTTP/1.1\r\nHost: {target}\r\nConnection: close\r\n\r\n"
                sock.sendall(req.encode())
            data = sock.recv(1024)
            return data.decode(errors="replace").strip() or "No banner"
    except OSError:
        return "No banner"
```

### Drill 5: Re-code `extract_features()`

**Task:** Count open ports, sensitive ports, version leaks, and DNS records.

```python
def extract_features(open_ports, banners, dns_result):
    sensitive = {21, 22, 23, 445, 3306, 5432, 6379}
    high_risk = {23, 445, 6379}
    db_cache = {3306, 5432, 6379}
    http = {80, 443, 3000, 8000, 8080}
    version_leaks = [int(p) for p, b in banners.items() if banner_has_version(str(b))]
    records = dns_result.get("records", {})
    return {
        "open_port_count": len(open_ports),
        "sensitive_port_count": len([p for p in open_ports if p in sensitive]),
        "high_risk_port_count": len([p for p in open_ports if p in high_risk]),
        "database_cache_port_count": len([p for p in open_ports if p in db_cache]),
        "http_port_count": len([p for p in open_ports if p in http]),
        "version_banner_count": len(version_leaks),
        "dns_record_count": sum(len(v) for v in records.values()),
    }, version_leaks
```

### Drill 6: Re-code Euclidean distance

```python
import math

def euclidean_distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
```

### Drill 7: Re-code KNN idea

**Task:** Sort training samples by distance and use nearest 3.

```python
def predict_with_knn(feature_vector, training_samples, k=3):
    distances = []
    for sample in training_samples:
        d = euclidean_distance(feature_vector, sample["features"])
        distances.append((d, sample))
    neighbors = [sample for _, sample in sorted(distances)[:k]]
    score = round(sum(n["score"] for n in neighbors) / k)
    labels = {}
    for n in neighbors:
        labels[n["label"]] = labels.get(n["label"], 0) + 1
    label = max(labels, key=labels.get)
    return score, label
```

### Drill 8: Re-code Stage 1 fan-out

```python
def run_recon_stage(target, ports, timeout):
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(scan_ports, target, ports, timeout): "port",
            executor.submit(enumerate_dns, target): "dns",
            executor.submit(grab_banners, target, ports, timeout): "banner",
        }
        results = {}
        for future in as_completed(futures):
            results[futures[future]] = future.result()
    return results["port"], results["dns"], results["banner"]
```

### Drill 9: Re-code simple safety gate

```python
def is_target_allowed(target, authorized):
    allowed = {"localhost", "127.0.0.1", "::1", "scanme.nmap.org"}
    return authorized or target.lower() in allowed
```

### Drill 10: Re-code agent loop skeleton

```python
messages = [{"role": "system", "content": system}, {"role": "user", "content": request}]
for _ in range(max_iterations):
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.0,
    )
    msg = resp.choices[0].message
    messages.append({
        "role": "assistant",
        "content": msg.content,
        "tool_calls": [tc.model_dump() for tc in (msg.tool_calls or [])],
    })
    if resp.choices[0].finish_reason == "tool_calls":
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments or "{}")
            result = tool_map[tc.function.name](**args)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            })
    else:
        return msg.content
```

## 10. Common Coding Mistakes To Avoid

**Mistake 1:** Forgetting timeout in socket code.

**Fix:** Always pass `timeout` to `socket.create_connection`.

**Mistake 2:** Using `send()` instead of `sendall()`.

**Fix:** Use `sendall()` for HTTP HEAD request.

**Mistake 3:** Making banner grab wait for port scan output.

**Fix:** In Topic 02, Stage 1 tasks should be independent and parallel.

**Mistake 4:** Forgetting to sort ports.

**Fix:** Return `sorted(set(ports))`.

**Mistake 5:** Calling API without fallback.

**Fix:** If `OPENAI_API_KEY` is missing or API fails, use offline template.

**Mistake 6:** Scanning unauthorized target.

**Fix:** Use allowlist and `--authorized` safety gate.

**Mistake 7:** In agent loop, appending tool result without assistant `tool_calls`.

**Fix:** Always append assistant message first, then append matching `role="tool"`
messages with `tool_call_id`.

## 11. Final Memory Map

```text
main_pipeline.py
  parse args
  safety gate
  run_recon_stage()
  run_risk_stage()
  run_report_stage()

recon/
  port_scanner.py   -> socket connect
  dns_enum.py       -> A/MX/NS/TXT
  banner_grabber.py -> HTTP HEAD + recv

risk/
  risk_features.py  -> 7 numeric features
  risk_model.py     -> KNN
  risk_findings.py  -> MITRE + recommendations
  risk_scorer.py    -> combine all into risk_profile

reporting/
  ai_reporter.py          -> GPT or offline fallback
  openai_report_client.py -> API call
  report_templates.py     -> offline Markdown

pi_recon_agent.py
  OpenAI tools
  tool map
  Observe-Think-Act loop
```
