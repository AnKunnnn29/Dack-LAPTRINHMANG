---
description: Network reconnaissance skill for port scanning, DNS enumeration, and banner grabbing
---

# Recon Skill

## Description

Skill nay dung de thu thap thong tin reconnaissance co ban tren target duoc uy quyen.
No gom port scanning, DNS enumeration va banner grabbing o muc an toan.

## Inputs

- Target hostname, domain hoac IP.
- Danh sach port TCP nho can kiem tra.
- Co xac nhan `--authorized` neu target khong nam trong allowlist local/classroom-lab demo.

## Outputs

- `.pi/triage/port_scan_result.json`
- `.pi/triage/dns_enum_result.json`
- `.pi/triage/banner_result.json`

## Safety Rules

- Chi scan localhost, lab machine, public classroom/lab target trong allowlist, hoac target duoc uy quyen ro rang.
- Khong exploit, khong brute force, khong bypass.
- Khong quet port so luong lon.
- Dung timeout ngan de tranh gay tai.

## Steps

1. Kiem tra permission gate.
2. Quet danh sach port TCP co gioi han.
3. Bo qua DNS enum neu target la localhost; voi IP thi thu PTR reverse DNS.
4. Lay banner tu cac port ung vien, khong doi port scanner, de giu Stage 1 song song.
5. Luu ket qua thanh JSON trong thu muc triage.
