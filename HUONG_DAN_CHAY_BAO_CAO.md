# Bao cao huong dan chay chuong trinh Topic 02

Kinh gui thay,

Em xin trinh bay cach chay chuong trinh **Network Recon + Risk Profiler** va cach
xem file bao cao ket qua cua do an. Project nay thuc hien theo Topic 02: quet
thong tin mang co uy quyen, cham diem rui ro bang ML va tao bao cao Markdown co
MITRE ATT&CK mapping.

## 1. Chuan bi moi truong

Truoc tien, thay mo terminal tai thu muc goc cua project:

```powershell
cd <duong_dan_project>\Dack-LAPTRINHMANG
```

Sau do cai cac thu vien can thiet:

```powershell
pip install -r requirements.txt
```

Em co the kiem tra nhanh code Python co loi cu phap hay khong bang lenh:

```powershell
python -m compileall .pi\tools
```

Neu lenh nay khong bao loi thi cac file tool Python da compile thanh cong.

## 2. Chay demo local de bao ve

Cach demo on dinh nhat la chay tren `localhost`. Em mo mot HTTP server don gian
tren port `8000`, sau do chay pipeline chinh.

Terminal 1:

```powershell
python -m http.server 8000 --bind 127.0.0.1
```

Terminal 2:

```powershell
python .pi\tools\main_pipeline.py --target localhost --ports "8000,8080,3306,5432,6379" --offline
```

Y nghia cua lenh tren:

- `--target localhost`: em chi demo tren may cuc bo.
- `--ports "8000,8080,3306,5432,6379"`: danh sach port ung vien de quet.
- `--offline`: tao bao cao bang template offline, khong phu thuoc OpenAI API.

Neu chay thanh cong, man hinh se hien:

```text
Pipeline completed.
- port_scan_result: .pi\triage\port_scan_result.json
- dns_enum_result: .pi\triage\dns_enum_result.json
- banner_result: .pi\triage\banner_result.json
- risk_profile: .pi\triage\risk_profile.json
- report: .pi\results\ket_qua.md
- log: .pi\logs\pipeline_run.log
```

File bao cao cuoi cung nam tai:

```text
.pi\results\ket_qua.md
```

De mo file bao cao, em dung:

```powershell
notepad .pi\results\ket_qua.md
```

## 3. Chay voi target public trong allowlist

Thua thay, project khong chi gioi han o local. File `.pi\data\allowed_targets.json`
co hai nhom target duoc phep:

- Nhom local demo: `localhost`, `127.0.0.1`, `::1`.
- Nhom public classroom/lab demo: `scanme.nmap.org`, `pentest-ground.com`,
  `demo.testfire.net`, va cac domain test cua `vulnweb.com`.

Vi du neu em muon demo voi mot target public da nam trong allowlist:

```powershell
python .pi\tools\main_pipeline.py --target testasp.vulnweb.com --ports "80,443,8080"
```

Em luu y: cac target public nay duoc dua vao de phuc vu lab/demo. Project khong
co nghia la duoc quet moi website tren Internet. Voi target khong nam trong
allowlist, em chi dung `--authorized` khi that su co quyen kiem thu.

## 4. Tao lai bao cao tu risk_profile co san

Trong truong hop em da co file `.pi\triage\risk_profile.json` va chi muon tao
lai file bao cao Markdown, em chay:

```powershell
python .pi\tools\reporting\ai_reporter.py --risk-profile .pi\triage\risk_profile.json --output .pi\results\ket_qua.md --prompt .pi\prompts\report_prompt.md --offline
```

Sau lenh nay, bao cao moi se duoc ghi lai vao:

```text
.pi\results\ket_qua.md
```

## 5. Che do dung OpenAI API

Mac dinh khi bao ve, em nen dung `--offline` de chuong trinh chay on dinh va
khong phu thuoc API. Neu thay muon xem che do dung AI de viet report, em tao
file `.env` nhu sau:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

Sau do em chay pipeline khong can `--offline`:

```powershell
python .pi\tools\main_pipeline.py --target localhost --ports "8000,8080,3306,5432,6379"
```

Neu khong co API key hoac API loi, chuong trinh van fallback ve offline template,
nen qua trinh demo khong bi dung.

## 6. Cac file ket qua quan trong

Sau khi pipeline chay xong, cac file chinh gom:

- `.pi\triage\port_scan_result.json`: ket qua quet port TCP.
- `.pi\triage\dns_enum_result.json`: ket qua truy van DNS.
- `.pi\triage\banner_result.json`: banner va service guess.
- `.pi\triage\risk_profile.json`: diem risk, ML features, findings va MITRE mapping.
- `.pi\results\ket_qua.md`: bao cao cuoi cung de nop va trinh bay.
- `.pi\logs\pipeline_run.log`: log qua trinh chay pipeline.

## 7. Giai thich ngan gon khi thay hoi

Neu thay hoi project chay nhu the nao, em tra loi:

Project cua em co 4 stage. Stage 0 la Safety Gate de chan target khong duoc
phep. Stage 1 chay song song ba tool: port scan, DNS enum va banner grab. Stage
2 trich xuat feature va cham diem rui ro bang Simple Isolation Forest. Stage 3
tao bao cao Markdown co MITRE ATT&CK mapping va khuyen nghi phong thu.

Neu thay hoi song song nam o dau, em tra loi:

Song song nam trong ham `run_recon_stage()` cua `main_pipeline.py`. Em dung
`ThreadPoolExecutor(max_workers=3)` de chay dong thoi port scan, DNS enum va
banner grab vi ba tac vu nay khong phu thuoc du lieu lan nhau.

Neu thay hoi vi sao allowlist co target public, em tra loi:

Allowlist cua em co hai nhom. Nhom mot la local loopback de demo offline. Nhom
hai la public classroom/lab target duoc thiet ke de kiem thu nhu `scanme.nmap.org`
va cac domain test cua `vulnweb.com`. Cac target public khac van bi chan neu
khong co `--authorized`.

## 8. Loi thuong gap va cach xu ly

**Bi chan boi Permission Gate**

Nguyen nhan la target khong nam trong allowlist va em chua truyen `--authorized`.
Em se doi ve `localhost`, dung target lab trong allowlist, hoac chi truyen
`--authorized` khi co quyen.

**Port 8000 khong hien open**

Nguyen nhan thuong la em chua mo HTTP server local. Em chay lai Terminal 1:

```powershell
python -m http.server 8000 --bind 127.0.0.1
```

**Khong co OpenAI API key**

Khong anh huong den demo. Em chi can chay them `--offline`, bao cao van duoc tao
bang template offline.

## 9. Ket luan

Tom lai, de bao ve on dinh nhat, em se chay demo local voi `--offline`, sau do
mo file `.pi\results\ket_qua.md` de trinh bay ket qua. Neu can chung minh project
co xu ly public exposure, em co the chay them mot target public classroom/lab da
nam trong allowlist.

