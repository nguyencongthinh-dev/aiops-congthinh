# A3: Cost Model

Target: Cut observability spend by at least 40% (Target bill ≤ $25,200).

## Monthly Bill, By Line Item (Current vs Target)

| Line item / Service | Vendor / Component | Monthly Cost (Today) | Monthly Cost (Target) | Unit Driver (Target State) | Assumed Scale |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **APM / Tracing** | Datadog APM → Grafana Tempo | $12,100 | $0 | N/A (Moved to OSS Compute) | - |
| **Infra Metrics** | Datadog Pro → VictoriaMetrics | $5,400 | $0 | N/A (Moved to OSS Compute) | - |
| **Custom Metrics** | Datadog → VictoriaMetrics | $2,200 | $0 | N/A (Moved to OSS Compute) | - |
| **Datadog Hot Logs** | Datadog Logs → Grafana Loki | $1,800 | $0 | N/A (Moved to OSS Compute) | - |
| **Synthetic Checks** | Datadog Synthetics | $1,360 | $0 | Replaced with OSS blackbox-exporter | ~270 checks |
| **Log Storage & Search**| Splunk Cloud → S3/Loki/Athena | $13,900 | **$120** | $0.023/GB storage (S3) + Athena $5/TB scanned | ~52 GB/day, 30d hot Loki, long-term S3 |
| **Incident Routing** | PagerDuty Business | $3,900 | **$3,900** | $60 / user / month | 65 active users |
| **Status Page** | Statuspage by Atlassian | $290 | **$290** | Tiered subscription | Business tier |
| **Dashboards / UI** | Grafana Cloud Pro | $1,050 | **$2,500** | Expansion from 18 users to all 65+ eng | 65+ active engineers |
| **OSS Compute & Disk**| AWS EC2 + EBS (Self-hosted) | $300 | **$3,440** | $277/mo per m5.2xlarge + $70/mo vmanomaly + $90/mo Redpanda + $30/mo Keep | ~10 instances Loki/Tempo/VM + 1 m5.large + 3 t3.medium + 1 Keep |
| **Total** | | **$42,300** | **~$10,250** | | |

## Summary of Reduction
- **Current Spend:** ~$42,300 / month
- **Target Spend:** ~$10,250 / month
- **Reduction Achieved:** **75.8%**



## Sensitivity Analysis
**Scenario: What if data volume (Logs/Traces) grows 2x faster than projected?**
- In the current stack, a 2x log/trace volume spike would increase Datadog ($1,800) and Splunk ($13,900) ingestion costs dramatically, potentially adding $15,000+ to the bill immediately.
- In the Target stack, storage is backed by AWS S3. A 2x volume increase of 52 GB/day = 104 GB/day = ~3.1 TB/month.
- S3 Storage cost for 3.1 TB is barely ~$72/month.
- **What breaks the budget first?** The budget will not break from storage. It will break from **Compute CPU** required to ingest and compress the logs/traces on the OpenTelemetry/Loki nodes. If volume 2x's unexpectedly, we will need to auto-scale EC2 instances, adding roughly ~$800 in compute costs, which is completely safe and within the target margin.
