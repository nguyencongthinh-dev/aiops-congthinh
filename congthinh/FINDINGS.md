# A7 & 5: FINDINGS.md

## POC Plan (A7)
The most uncertain components in our target design are the **OpenTelemetry (OTel) Collector's tail-based sampling capability** under high load, the **precision of VictoriaMetrics `vmanomaly` ML models**, the **CPU overhead of Grafana Beyla (eBPF)**, and **Redpanda buffering throughput**. If we had three days of engineering time, we would spike these first.

**1. OpenTelemetry Tail-based Sampling:**
- **Assumption to validate:** The OTel Collector can process 10,000 spans per second and successfully retain 100% of the traces containing an error, while dropping 99% of successful traces, without exceeding 2 GB of RAM per collector node.
- **Measurement:** Run a load test script against the OTel Collector, assert that the error trace count in Tempo matches the injected error count exactly, and measure the Collector's RSS memory usage.

**2. VictoriaMetrics `vmanomaly` ML Accuracy & Resource Footprint:**
- **Assumption to validate:** The Prophet and Isolation Forest models running on a single `m5.large` instance can detect synthetic anomaly injections (e.g. simulated 5x traffic spikes or 90% CPU usage) with >90% precision and recall, and generate anomaly scores within 15 seconds.
- **Measurement:** Run a mock metrics generator with normal seasonality. Inject anomalies (spikes and dips) at specific times, verify that `vmanomaly` correctly registers these as anomalies (anomaly score > 1.0) in VictoriaMetrics, and measure the Python process CPU/RAM consumption during the training loops.

**3. eBPF CPU/Memory Overhead (Grafana Beyla):**
- **Assumption to validate:** Running Grafana Beyla on application hosts to capture kernel-level socket metrics and distributed tracing consumes less than 1% additional host CPU and less than 50 MB RSS RAM per service instance.
- **Measurement:** Benchmark service pods under a simulated traffic load of 1,000 req/sec with and without Grafana Beyla running, measuring container CPU throttling and RSS memory.

**4. Redpanda Buffering Ingestion Limits:**
- **Assumption to validate:** A 3-node `t3.medium` Redpanda cluster can handle a peak log storm of 50,000 write ops/sec (5x normal load) with a replication write latency of under 5ms, without saturating EBS disk I/O.
- **Measurement:** Run a Vector load generator to push simulated log messages into Redpanda at escalating rates. Monitor Redpanda partition replication lag and disk write I/O metrics.



---

## Required Reflection Questions

**1. Which capability turned out hardest to replace, and why? What did you compromise on?**
The hardest capability to replace was Datadog's out-of-the-box APM UI and automatic database query profiling. We compromised on "instant gratification." By moving to Grafana Tempo and using Grafana Beyla (eBPF) for auto-instrumentation, developers get instant golden signals and tracing without code edits, but the platform team must now build and maintain custom Grafana Dashboards and teach developers to read TraceQL, losing the zero-configuration dashboard luxury of Datadog.

**2. Where did your design trade resilience for cost? Quantify the trade-off.**
In our initial design, we traded ingest resilience for cost by forwarding logs and metrics directly from OTel to Loki/VictoriaMetrics. This saved ~$17,000/month but risked a telemetry blackout during backend database maintenance windows or AZ outages. We mitigated this by upgrading the architecture to include a **3-node Redpanda cluster** and **Vector agents with disk-backed buffers**. This provides durable cross-AZ ingestion buffering for only **$120/month** in additional compute, preserving our **75.8% cost savings** ($32,050/mo saved) while fully reclaiming ingestion resilience.

**3. If the budget cut requirement were 60% instead of 40%, which decisions would change and which would not? What does that tell you about the structure of cost in this stack?**
Our target design achieves a **75.8% cost reduction** (reducing monthly spend from $42,300 to ~$10,250), exceeding even a 60% mandate. However, if pushed to cut costs further (e.g., an 85% cut requirement), we would look at our final SaaS dependencies: **PagerDuty** ($3,900/mo) and Atlassian **Statuspage** ($290/mo). We would migrate incident routing to Grafana OnCall (OSS, self-hosted) and Statuspage to an OSS alternative like Cachet. This demonstrates that observability costs are divided into: volume-based ingest/storage (which we solved using S3-backed OSS databases) and seat-based SaaS licensing (which is the final frontier for extreme cost-cutting).

**4. Identify one pattern in your design that you copied from a real-world system you know. Name the system, the pattern, and what you changed.**
We copied the **"Auto-Remediation Event-Driven Loop"** pattern, commonly seen in **Kubernetes Operators and Event-driven Ansible**. We implemented this by placing **Keep** between Prometheus Alertmanager and PagerDuty. Instead of alerting paging paths immediately, Alertmanager triggers a Keep webhook which runs automated playbooks to remediate low-severity incidents (e.g. freeing disk space, restarting pod). We modified this pattern to include a strict circuit breaker: if self-healing fails twice or the alert is High/Critical, it escalates to PagerDuty immediately.

**5. What is the biggest unknown in your plan — something that could derail the migration at week N? What would you spike in the first week to de-risk it?**
The biggest unknown is **eBPF Kernel Compatibility** and **Security Team's Splunk Queries**:
1. Some legacy EC2 hosts might run old Linux kernels (< 5.6) that block Grafana Beyla from attaching probes. In Week 1, we will audit all host OS kernels to schedule upgrades or arrange OTel SDK fallbacks.
2. The audit team's compliance reports might rely on obscure Splunk SPL macros that are difficult to write in Athena SQL. In Week 1, we will export 1GB of logs to S3 as Parquet and pair-program with the security lead to translate their most complex report. If it fails, we will maintain a downscaled, cheaper Splunk index exclusively for security data.

