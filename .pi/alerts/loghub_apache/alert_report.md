# Defensive Monitoring Alerts

- Generated at: `2026-06-10T15:54:14.456487+00:00`
- Events analyzed: `2000`
- Alerts: `1`
- ML anomalies: `56`
- Monitoring risk: `4/10` (Medium)

## [Medium] ML log anomaly candidates detected

- ID: `ML_LOG_ANOMALY-a7822cb1a1`
- Category: `ml_log_anomaly`
- Evidence: Isolation Forest trained on 2000 events and flagged 56 anomaly candidates; top lines: [1421, 1890, 132, 1060, 588]
- MITRE: `T1087, T1110, T1190`
- Recommendation: Review the ranked anomalous log lines and correlate them with rule-based alerts.

## Notes

- Defensive monitoring demo only.
- Validate alerts before taking incident response action.