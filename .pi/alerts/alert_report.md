# Defensive Monitoring Alerts

- Generated at: `2026-06-08T17:37:52.260838+00:00`
- Events analyzed: `11`
- Alerts: `5`

## [High] Malware-like process or command indicator

- ID: `MALWARE_INDICATOR-36437b98d3`
- Category: `malware_indicator`
- Evidence: Pattern `\bpowershell(\.exe)?\b.*(-enc|-encodedcommand)\b` matched event line 6: powershell.exe powershell.exe -EncodedCommand <redacted-demo-value>  Suspicious encoded PowerShell command observed
- MITRE: `T1059, T1105`
- Recommendation: Isolate the host if confirmed, collect process/file evidence, and run trusted endpoint scanning.

## [High] Possible web exploit attempt

- ID: `EXPLOIT_ATTEMPT-d74941f130`
- Category: `exploit_attempt`
- Evidence: Web exploit probe from 10.10.10.77; pattern `\bunion\b.+\bselect\b` matched:   /index.php?id=1 union select username,password from users HTTP exploit probe blocked by demo web server
- MITRE: `T1190`
- Recommendation: Review web access logs, patch exposed apps, add WAF rules, and verify no compromise occurred.

## [High] Possible web exploit attempt

- ID: `EXPLOIT_ATTEMPT-82d3a86713`
- Category: `exploit_attempt`
- Evidence: Web exploit probe from 10.10.10.88; pattern `\.\./` matched:   /../../../../etc/passwd Directory traversal probe
- MITRE: `T1190`
- Recommendation: Review web access logs, patch exposed apps, add WAF rules, and verify no compromise occurred.

## [High] Unusual network traffic pattern

- ID: `TRAFFIC_ANOMALY-4db9bfd39c`
- Category: `traffic_anomaly`
- Evidence: 3 network events from 127.0.0.1, outbound bytes=60000000
- MITRE: `T1041, T1046`
- Recommendation: Check the source host, destination list, expected workload, and firewall/proxy logs.

## [Medium] Possible brute-force login activity

- ID: `BRUTE_FORCE-b30111e07b`
- Category: `brute_force`
- Evidence: 5 failed logins from 10.10.10.50 for user admin
- MITRE: `T1110`
- Recommendation: Review authentication logs, block or rate-limit the source, and enforce MFA/account lockout policy.

## Notes

- Defensive monitoring demo only.
- Validate alerts before taking incident response action.