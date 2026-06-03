# Quản lý Allowed Targets

## Cách 1: Sửa trực tiếp file JSON

Mở file `.pi/data/allowed_targets.json` và thêm target vào mảng `allowed_targets`:

```json
{
  "allowed_targets": [
    "localhost",
    "127.0.0.1",
    "::1",
    "scanme.nmap.org",
    "192.168.1.100",
    "myapp.com"
  ]
}
```

## Cách 2: Dùng script helper

### Xem danh sách targets hiện tại:
```bash
python .pi/tools/manage_targets.py list
```

### Thêm target mới:
```bash
python .pi/tools/manage_targets.py add 192.168.1.100
python .pi/tools/manage_targets.py add myapp.com
```

### Xoá target:
```bash
python .pi/tools/manage_targets.py remove 192.168.1.100
```

## Cách 3: Dùng flag --authorized

Nếu không muốn thêm vào whitelist, dùng flag `--authorized`:

```bash
python .pi/tools/main_pipeline.py --target 192.168.1.100 --authorized
```

⚠️ **Chỉ dùng khi bạn có quyền scan target đó!**

## Ví dụ targets hợp lệ:

### ✅ An toàn (không cần --authorized):
- `localhost`, `127.0.0.1` - Máy local
- `scanme.nmap.org` - Target công khai cho testing

### ✅ Cần thêm vào whitelist hoặc dùng --authorized:
- `192.168.1.x` - Mạng nội bộ của bạn
- `10.0.0.x` - Mạng nội bộ của bạn
- `myapp.com` - Domain/server của bạn

### ❌ KHÔNG BAO GIỜ scan:
- Website/server của người khác
- Hệ thống công ty không được phép
- Bất kỳ target nào bạn không có quyền

## Lưu ý pháp lý:

🚨 **Scan port/network mà không được phép là BẤT HỢP PHÁP ở hầu hết các quốc gia!**

Chỉ scan:
1. Máy của bạn (localhost)
2. Mạng nội bộ của bạn (với sự đồng ý)
3. Target công khai cho testing (như scanme.nmap.org)
4. Hệ thống bạn được ủy quyền rõ ràng
