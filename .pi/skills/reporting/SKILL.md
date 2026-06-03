# Reporting Skill

## Description

Skill nay tao bao cao Markdown tu `risk_profile.json`, gom recon summary,
ML risk model, findings, MITRE ATT&CK mapping va khuyen nghi phong thu.
Neu co `OPENAI_API_KEY`, pipeline goi OpenAI API. Neu khong co key, dung template offline.

## Inputs

- `.pi/triage/risk_profile.json`
- `.pi/prompts/report_prompt.md`
- Bien moi truong `OPENAI_API_KEY` neu muon dung AI report.

## Outputs

- `.pi/results/ket_qua.md`

## Safety Rules

- Bao cao chi viet khuyen nghi phong thu.
- Khong dua payload, khong huong dan khai thac.
- Khong khuyen khich scan target khi chua duoc uy quyen.

## Steps

1. Doc risk profile.
2. Doc prompt bao cao.
3. Goi OpenAI API neu co API key.
4. Neu API loi hoac thieu key, tao report offline.
5. Luu ket qua vao `ket_qua.md`.
