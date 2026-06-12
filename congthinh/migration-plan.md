# A5: Eight-Week Migration Plan

This plan outlines the migration from Datadog/Splunk to the OSS Grafana Stack. We guarantee **no observability blackout** by running systems in parallel ("shadow mode") before each cut-over.

## Week 1-2: Infrastructure Provisioning & Single Pane Foundation
- **Goal:** Stand up the OSS backend (VictoriaMetrics, Loki, Tempo, OTel) and Grafana UI without disrupting current data.
- **Actions:** 
  - Provision EC2 instances (including dedicated m5.large for vmanomaly, a 3-node t3.medium Redpanda cluster, and a Keep runner node) and S3 buckets.
  - Deploy Grafana Cloud, connect it to Datadog APIs (so engineers can start using Grafana immediately while data is still in Datadog).
- **Go/No-go Gate:** Can engineers view the two existing "exec dashboards" in Grafana via the Datadog API?
- **Rollback:** No cut-over yet. Delete OSS resources if the test fails.

## Week 3-4: Dual-Routing (Shadow Mode)
- **Goal:** Deploy OpenTelemetry Collector alongside Datadog Agent.
- **Actions:** 
  - Deploy Vector Log Collector and Grafana Beyla eBPF agents on application hosts alongside OTel Collector.
  - Configure Vector to dual-emit logs to Splunk and Redpanda (which buffers and writes to Loki). Configure Beyla and OTel to dual-emit metrics and traces to Datadog and Redpanda (buffering to VictoriaMetrics/Tempo).
  - Deploy and run VictoriaMetrics `vmanomaly` in a "silent dry-run" mode, letting ML models train on incoming metric streams to establish baselines. Deploy Keep in silent "audit-only" mode.
- **Go/No-go Gate:** Does Loki show the exact same log volume and errors as Splunk for a 24-hour period? Is VictoriaMetrics query latency under 2 seconds at p99?
- **Rollback:** Disable OTel emission from the application. Datadog remains untouched.

## Week 5: Cut-Over Traces and Metrics
- **Goal:** Disable Datadog APM and Metrics ingestion.
- **Actions:**
  - Switch Grafana dashboards to point fully to VictoriaMetrics and Tempo.
  - Turn off the Datadog Agent on all hosts (saving $17,200/month immediately).
- **Go/No-go Gate:** On-call engineer successfully independently triages a synthetic incident using only Grafana + Tempo + VictoriaMetrics in staging.
- **Rollback:** Turn the Datadog Agent back on via Ansible/Chef. Revert Grafana dashboard data sources to Datadog API. Time to rollback: < 15 minutes.

## Week 6: Rebuilding Alert Rules
- **Goal:** Translate Datadog Monitors to PromQL / Alertmanager.
- **Actions:**
  - Platform team translates top 50 critical alerts (incorporating dynamic thresholds and ML-based anomaly rules from `vmanomaly` for highly-seasonal traffic/performance metrics).
  - Configure Keep with auto-remediation playbooks (e.g. automated pod restart on memory leaks, temporary file cleanup on disk space low).
  - Route Alertmanager webhooks to Keep in shadow mode (Keep executes remediation scripts but does not escalate to PagerDuty).
- **Go/No-go Gate:** 95% of historical alert rules reproduced and firing accurately in shadow mode compared to Datadog.
- **Rollback:** Leave Datadog alerts active. Do not hook Alertmanager to the production PagerDuty service.

## Week 7: Cut-Over Logs and Alerts
- **Goal:** Disable Splunk ingestion and cut over to Alertmanager.
- **Actions:**
  - Route Alertmanager webhooks to Keep production. Keep routes unresolved/high-severity alerts to production PagerDuty. Disable Datadog webhook to PagerDuty.
  - Stop sending operational logs to Splunk. Turn off Datadog Logs.
- **Go/No-go Gate:** Security team verifies they can query Parquet logs in Athena.
- **Rollback:** Re-enable Splunk log forwarder. Re-enable Datadog webhook. Time to rollback: < 30 minutes.

## Week 8: Splunk Historical Export & Decommission
- **Goal:** Export historical data from Splunk before contract ends.
- **Actions:**
  - Use the remaining 100 GB/day Splunk export quota to pull the last 30 days of compliance data into S3.
  - Initiate formal cancellation of Datadog and Splunk contracts.
- **Go/No-go Gate:** S3 bucket byte count matches expected historical export volume.
- **Rollback:** If export fails, keep Splunk running for 1 more month (contract allows up to 7 months).
