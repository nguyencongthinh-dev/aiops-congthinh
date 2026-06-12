# ADR 001: Replace Splunk and Datadog Logs with Loki and S3 Athena

## Context
The observability bill is currently $42,000/month. Logs are the worst offender: Datadog Logs costs $1,800/month for only 15 days of hot retention, while Splunk Cloud costs $13,900/month for long-term storage and compliance. Despite this $15,700 spend, engineers face search latencies exceeding 25 seconds for queries over 7 days (Pain Point 1), and Splunk index rotations frequently break dashboards mid-incident (Pain Point 6).

## Decision
We will eliminate Splunk Cloud and Datadog Logs entirely. 
- Operational logs will be collected by **Vector agents** on hosts (with local disk-backed buffers), routed to a clustered **Redpanda queue** for resilient buffering, and then ingested into **Grafana Loki** (with chunks backed by S3).
- Security and compliance logs will be routed by the OpenTelemetry Collector directly to AWS S3 Glacier in Parquet format, to be queried by the audit team using **AWS Athena**.

## Alternatives considered + rejected
1. **Consolidate all logs into Datadog:** 
   - *Reason for rejection:* Datadog prices by the number of events indexed. Pushing Splunk's 52 GB/day into Datadog would cause a massive spike in licensing costs, making the 40% cost reduction mandate impossible.
2. **Move to Elasticsearch (ELK stack):** 
   - *Reason for rejection:* Elasticsearch still relies on heavy full-text indexing. While software licensing is free, the compute and SSD storage requirements to hold 52 GB/day + replicas would drastically inflate our AWS infrastructure bill and introduce immense operational overhead.

## Consequences
### Positive
- Massive cost savings (~$15,000/month) by leveraging S3 Object Storage instead of expensive block storage and indexing.
- Eliminates "index rotation" downtime (Pain Point 6) because Loki does not use traditional inverted indexes.
- Prevents Vendor lock-in; we own the data in our own S3 buckets.

### Negative
- **Loss of Splunk Query Language (SPL) for Audit Team:** The security team must rewrite all compliance reports into standard SQL for AWS Athena.
- **Slower full-text search without labels:** Loki is fast when filtering by labels. If an engineer searches for a completely un-labeled string across weeks of data, the brute-force search speed may be slow. We must mitigate this by ensuring Vector extracts key fields (e.g., `customer_id`, `trace_id`) as labels at ingestion.
