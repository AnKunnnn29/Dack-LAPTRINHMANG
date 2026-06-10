# Defensive Monitoring Skill

## Description

Skill nay theo doi log duoc uy quyen va phat hien cac dau hieu phong thu:
malware-like indicator, brute force, exploit probe, traffic anomaly, ML anomaly
detection va alerting.

## Inputs

- Log JSONL/text duoc phep doc.
- Optional Discord webhook.
- Optional SMTP email configuration.

## Outputs

- `.pi/alerts/alerts.json`
- `.pi/alerts/alert_report.md`
- Discord/email dispatch status neu co cau hinh.

## Steps

1. Doc log mot lan hoac poll trong live mode.
2. Parse tung event.
3. Trich xuat feature va train Isolation Forest tren log duoc chon.
4. Ket hop ML anomaly candidates voi detector rule-based.
5. Deduplicate alert theo stable alert id.
6. Ghi alert JSON/Markdown.
7. Gui Discord/email neu co bien moi truong.

## Safety Rules

- Chi monitor log duoc uy quyen.
- Khong tao traffic tan cong that.
- Khong thuc thi malware.
- Khong brute force.
- Khong dua payload/hack steps trong alert.
