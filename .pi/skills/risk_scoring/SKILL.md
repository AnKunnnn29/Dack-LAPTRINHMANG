# Risk Scoring Skill

## Description

Skill nay gom ket qua reconnaissance va du doan rui ro bang supervised KNN model nho.
Muc tieu la de sinh vien de giai thich feature engineering va ML classification.

## Inputs

- Ket qua port scan.
- Ket qua DNS enumeration.
- Ket qua banner grabbing.

## Outputs

- `.pi/triage/risk_profile.json`
- ML feature vector.
- Risk score 0-10.
- Risk level: Low, Medium, High.
- MITRE ATT&CK mapping.
- Findings va recommendations phong thu.

## Safety Rules

- Chi danh gia rui ro phong thu.
- Khong bien finding thanh huong dan khai thac.
- Khong su dung CVE lookup tu dong trong ban don gian nay.
- MITRE mapping chi dung de boi canh phong thu, khong phai huong dan tan cong.

## Steps

1. Doc danh sach port dang mo.
2. Trich xuat feature tu open ports, service groups, DNS records va banner version leaks.
3. Chay KNN classifier tren training samples nho.
4. Tao MITRE ATT&CK mapping cho finding phong thu.
5. Ghi profile ra JSON.
