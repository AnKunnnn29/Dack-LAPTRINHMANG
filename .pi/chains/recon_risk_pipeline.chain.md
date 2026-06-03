# recon_risk_pipeline

## Muc tieu

Pipeline ho tro giai doan reconnaissance trong pentest duoc uy quyen,
sau do du doan rui ro bang ML model nho va sinh bao cao Markdown co MITRE mapping.

## Stage 1: Recon Collection

Chay cac agent thu thap thong tin:

- `port_scan_agent`: quet danh sach port TCP nho bang socket.
- `dns_enum_agent`: truy van A, MX, NS, TXT neu target la domain.
- `banner_grab_agent`: thu lay banner tren cung danh sach port ung vien.

Phan song song:

- `port_scan_agent`, `dns_enum_agent` va `banner_grab_agent` duoc submit cung luc bang `ThreadPoolExecutor`.
- Banner grabbing khong cho ket qua port scan; no tu thu ket noi tren cung danh sach port ung vien.
- Cach nay the hien parallel recon phase dung yeu cau: 3 task doc lap chay song song de giam wall-clock time.

Pi Coding Agent orchestration co the mo ta bang fan-out `/parallel`:

```text
/parallel
  port_scan_agent(target, ports)
  dns_enum_agent(target)
  banner_grab_agent(target, ports)
/join
```

Ban Python runnable trong `.pi/tools/main_pipeline.py` hien thuc cung logic nay bang
`ThreadPoolExecutor(max_workers=3)` de demo duoc end-to-end tren may local.

## Stage 2: Risk Scoring

`risk_score_agent` doc cac file JSON trong `.pi/triage/` va du doan risk level:

- Trich xuat feature tu open ports, banner version leaks va DNS records.
- Dung supervised K-Nearest Neighbors model nho trong `risk_scorer.py`.
- Output gom score 0-10, Low/Medium/High, ML features, findings va MITRE ATT&CK mapping.

## Stage 3: AI Report Generation

`report_agent` doc `.pi/triage/risk_profile.json` va tao `.pi/results/ket_qua.md`.

- Neu co `OPENAI_API_KEY`: goi OpenAI API.
- Neu khong co key: dung template offline.
- Bao cao co muc MITRE ATT&CK Mapping va khuyen nghi phong thu.

## Vi du prompt chay pipeline

```bash
python .pi/tools/main_pipeline.py --target localhost
```

Neu demo voi web server local:

```bash
python -m http.server 8000
python .pi/tools/main_pipeline.py --target localhost
```
