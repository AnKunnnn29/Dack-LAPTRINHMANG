# Defensive Monitoring Alerts

- Generated at: `2026-06-08T17:42:47.219014+00:00`
- Events analyzed: `2000`
- Alerts: `19`

## [High] Possible brute-force login activity

- ID: `BRUTE_FORCE-31adde9494`
- Category: `brute_force`
- Evidence: 48 failed logins from 112.95.230.3 for user root
- MITRE: `T1110`
- Recommendation: Review authentication logs, block or rate-limit the source, and enforce MFA/account lockout policy.

## [High] Possible brute-force login activity

- ID: `BRUTE_FORCE-6d09a73e11`
- Category: `brute_force`
- Evidence: 14 failed logins from 123.235.32.19 for user root
- MITRE: `T1110`
- Recommendation: Review authentication logs, block or rate-limit the source, and enforce MFA/account lockout policy.

## [High] Possible brute-force login activity

- ID: `BRUTE_FORCE-0f7a9c7493`
- Category: `brute_force`
- Evidence: 11 failed logins from 5.188.10.180 for user unknown
- MITRE: `T1110`
- Recommendation: Review authentication logs, block or rate-limit the source, and enforce MFA/account lockout policy.

## [High] Possible brute-force login activity

- ID: `BRUTE_FORCE-2a5d5cf76a`
- Category: `brute_force`
- Evidence: 16 failed logins from 5.188.10.180 for user admin
- MITRE: `T1110`
- Recommendation: Review authentication logs, block or rate-limit the source, and enforce MFA/account lockout policy.

## [High] Possible brute-force login activity

- ID: `BRUTE_FORCE-828023464c`
- Category: `brute_force`
- Evidence: 10 failed logins from 185.190.58.151 for user unknown
- MITRE: `T1110`
- Recommendation: Review authentication logs, block or rate-limit the source, and enforce MFA/account lockout policy.

## [High] Possible brute-force login activity

- ID: `BRUTE_FORCE-7be8fe160d`
- Category: `brute_force`
- Evidence: 19 failed logins from 185.190.58.151 for user admin
- MITRE: `T1110`
- Recommendation: Review authentication logs, block or rate-limit the source, and enforce MFA/account lockout policy.

## [High] Possible brute-force login activity

- ID: `BRUTE_FORCE-ebc1e585f4`
- Category: `brute_force`
- Evidence: 20 failed logins from 103.99.0.122 for user admin
- MITRE: `T1110`
- Recommendation: Review authentication logs, block or rate-limit the source, and enforce MFA/account lockout policy.

## [High] Possible brute-force login activity

- ID: `BRUTE_FORCE-774a0243f7`
- Category: `brute_force`
- Evidence: 35 failed logins from 103.99.0.122 for user unknown
- MITRE: `T1110`
- Recommendation: Review authentication logs, block or rate-limit the source, and enforce MFA/account lockout policy.

## [High] Possible brute-force login activity

- ID: `BRUTE_FORCE-257aeecd28`
- Category: `brute_force`
- Evidence: 12 failed logins from 103.99.0.122 for user root
- MITRE: `T1110`
- Recommendation: Review authentication logs, block or rate-limit the source, and enforce MFA/account lockout policy.

## [High] Possible brute-force login activity

- ID: `BRUTE_FORCE-99959f5969`
- Category: `brute_force`
- Evidence: 92 failed logins from 187.141.143.180 for user root
- MITRE: `T1110`
- Recommendation: Review authentication logs, block or rate-limit the source, and enforce MFA/account lockout policy.

## [High] Possible brute-force login activity

- ID: `BRUTE_FORCE-aa6db1a62a`
- Category: `brute_force`
- Evidence: 29 failed logins from 187.141.143.180 for user unknown
- MITRE: `T1110`
- Recommendation: Review authentication logs, block or rate-limit the source, and enforce MFA/account lockout policy.

## [High] Possible brute-force login activity

- ID: `BRUTE_FORCE-446787b292`
- Category: `brute_force`
- Evidence: 10 failed logins from 60.2.12.12 for user root
- MITRE: `T1110`
- Recommendation: Review authentication logs, block or rate-limit the source, and enforce MFA/account lockout policy.

## [High] Possible brute-force login activity

- ID: `BRUTE_FORCE-32b3f86a26`
- Category: `brute_force`
- Evidence: 553 failed logins from 183.62.140.253 for user root
- MITRE: `T1110`
- Recommendation: Review authentication logs, block or rate-limit the source, and enforce MFA/account lockout policy.

## [Medium] Possible brute-force login activity

- ID: `BRUTE_FORCE-ce5a198399`
- Category: `brute_force`
- Evidence: 5 failed logins from ec2-52-80-34-196.cn-north-1.compute.amazonaws.com.cn for user unknown
- MITRE: `T1110`
- Recommendation: Review authentication logs, block or rate-limit the source, and enforce MFA/account lockout policy.

## [Medium] Possible brute-force login activity

- ID: `BRUTE_FORCE-afce93f021`
- Category: `brute_force`
- Evidence: 6 failed logins from 52.80.34.196 for user matlab
- MITRE: `T1110`
- Recommendation: Review authentication logs, block or rate-limit the source, and enforce MFA/account lockout policy.

## [Medium] Possible brute-force login activity

- ID: `BRUTE_FORCE-9c1f1fbee6`
- Category: `brute_force`
- Evidence: 8 failed logins from 103.99.0.122 for user user
- MITRE: `T1110`
- Recommendation: Review authentication logs, block or rate-limit the source, and enforce MFA/account lockout policy.

## [Medium] Possible brute-force login activity

- ID: `BRUTE_FORCE-d34af1f4f5`
- Category: `brute_force`
- Evidence: 8 failed logins from 187.141.143.180 for user oracle
- MITRE: `T1110`
- Recommendation: Review authentication logs, block or rate-limit the source, and enforce MFA/account lockout policy.

## [Medium] Possible brute-force login activity

- ID: `BRUTE_FORCE-d732323fa5`
- Category: `brute_force`
- Evidence: 7 failed logins from 119.4.203.64 for user admin
- MITRE: `T1110`
- Recommendation: Review authentication logs, block or rate-limit the source, and enforce MFA/account lockout policy.

## [Medium] Possible brute-force login activity

- ID: `BRUTE_FORCE-31ff939ca5`
- Category: `brute_force`
- Evidence: 9 failed logins from 183.62.140.253 for user unknown
- MITRE: `T1110`
- Recommendation: Review authentication logs, block or rate-limit the source, and enforce MFA/account lockout policy.

## Notes

- Defensive monitoring demo only.
- Validate alerts before taking incident response action.