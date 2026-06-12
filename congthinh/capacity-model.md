# Bonus Section B: 12-Month Ingestion Capacity & Cost Model

This document projects the data ingestion volume and operating costs of the redesigned observability stack over the next 12 months. We model three growth scenarios (Slow, Expected, and Fast) and contrast them with the cost trajectory of the legacy SaaS-only stack.

## 1. Baseline Ingestion & Scale
Our baseline scale is derived from current operational metrics:
- **Logs:** 52 GB/day (~1.56 TB/month).
- **Traces:** APM running on 295 hosts. In the legacy stack, tracing was heavily sampled at 1%. In the target stack, we implement **100% tail-based sampling** for errors and latency anomalies (retaining ~5% of total traces, dropping ~95% of fast, successful traces).
- **Metrics:** Custom metrics at ~440K excess active series.
- **Compute:** Self-hosted nodes are sized at a target 60% CPU utilization to provide a 40% head-room cushion for spikes.

---

## 2. Ingestion Spikes and Incident Realities
Telemetry ingestion is not flat. Data from [incidents_history.json](file:///e:/aio/aiops-thinh/w2/lab-w2-observability-stack-redesign-20260611/data-pack/incidents_history.json) shows historical incident activity driving major telemetry storms:
- **[INC-2026-03-20](file:///e:/aio/aiops-thinh/w2/lab-w2-observability-stack-redesign-20260611/data-pack/incidents_history.json#L28) (DDoS attack):** Resulted in a **5x normal traffic spike**. In the legacy stack, this created a massive, immediate bill spike in Datadog Log ingestion.
- **[INC-2026-05-18](file:///e:/aio/aiops-thinh/w2/lab-w2-observability-stack-redesign-20260611/data-pack/incidents_history.json#L33) (Notification spam):** Triggered a **5x normal log volume spike** due to an un-gated feature flag.

In our target S3-backed stack, a 5x spike in logs for 24 hours adds only **~260 GB** of data. 
- **S3 storage cost for this spike:** 260 GB * $0.023/GB = **$5.98**.
- **Legacy stack cost for this spike:** ~5.4 million extra log events in Datadog * $1.70/million = **$9.18** in Datadog overage, plus Splunk workload-based peak licensing penalties.

---

## 3. 12-Month Growth Scenarios

### Scenario 1: Slow Growth (10% YoY)
*   **Assumptions:** Stable business model. No major changes in application complexity. Team size remains stable at 65 engineers.
*   **Ingestion Volume:**
    *   Logs: 57.2 GB/day (~1.72 TB/month).
    *   Metrics/Traces: 10% increase in active time-series.
*   **Target Stack Cost:**
    *   *Compute:* Remains unchanged at **$3,440/month** (ASG nodes do not scale up as current headroom absorbs 10% growth).
    *   *S3 Storage:* 1.72 TB * $0.023/GB = **$39.56/month**.
    *   *SaaS licensing (PagerDuty, Statuspage, Grafana Cloud Pro):* **$6,690/month**.
    *   *Total Monthly Target Cost:* **~$10,270/month**.
*   **Legacy Stack Cost (under same growth):** Linear SaaS scaling would push the bill to **~$46,500/month**.

### Scenario 2: Expected Growth (30% YoY)
*   **Assumptions:** Organic growth. The engineering team expands to 80 users, and we deploy 2 new microservices (expanding the topology to 12 services).
*   **Ingestion Volume:**
    *   Logs: 67.6 GB/day (~2.03 TB/month).
    *   Metrics/Traces: 30% increase in host count and custom metric series.
*   **Target Stack Cost:**
    *   *Compute:* Remains at **$3,440/month** (the 40% headroom on our instances accommodates the additional 2 microservices).
    *   *S3 Storage:* 2.03 TB * $0.023/GB = **$46.69/month**.
    *   *SaaS licensing (PagerDuty + Grafana Cloud Pro seats increase):* Seat additions push SaaS costs to **$7,600/month**.
    *   *Total Monthly Target Cost:* **~$11,180/month**.
*   **Legacy Stack Cost (under same growth):** Legacy bill would escalate to **~$54,900/month** due to host licensing increases.

### Scenario 3: Hyper-Growth (100% YoY)
*   **Assumptions:** Sudden company expansion. We double our microservices from 10 to 20, hosts double to 600, and the engineering team grows to 100+ active users.
*   **Ingestion Volume:**
    *   Logs: 104 GB/day (~3.12 TB/month).
    *   Metrics/Traces: Double current volume.
*   **Target Stack Cost:**
    *   *Compute:* Auto Scaling Groups scale out the OTel Collector and Loki/Tempo ingestors, adding 3 additional `m5.2xlarge` instances (+ $831/month). Total compute: **$4,271/month**.
    *   *S3 Storage:* 3.12 TB * $0.023/GB = **$71.76/month**.
    *   *SaaS licensing (100 user seats):* Seat additions push SaaS licenses to **$9,800/month**.
    *   *Total Monthly Target Cost:* **~$14,240/month**.
*   **Legacy Stack Cost (under same growth):** Legacy bill would explode to **~$84,000/month** as Datadog APM and Splunk licensing double.

---

## 4. Cost Projection Comparison (Target vs Legacy)

| Growth Scenario | YoY Increase | Legacy SaaS Cost (Forecast) | New Target Stack Cost (Forecast) | Monthly Net Savings |
| :--- | :--- | :--- | :--- | :--- |
| **Current Baseline** | 0% | $42,300 | $10,250 | **$32,050 (75.8%)** |
| **Slow Growth** | 10% | $46,500 | $10,270 | **$36,230 (77.9%)** |
| **Expected Growth** | 30% | $54,900 | $11,180 | **$43,720 (79.6%)** |
| **Hyper-Growth** | 100% | $84,000 | $14,240 | **$69,760 (83.0%)** |

> [!TIP]
> **Key Finding:** In the legacy stack, costs scale linearly with host count and log volume. In the target stack, costs scale sub-linearly because storage is decoupled from compute. S3 object storage is incredibly cheap ($23 per TB), meaning hyper-growth increases our storage costs by only a few dollars, and compute scales only when ingestion thresholds are breached.
