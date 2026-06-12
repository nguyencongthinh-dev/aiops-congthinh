# Bonus Section C: Vendor Exit-Clause Analysis & Transition Strategy

To ensure a legally safe and technically smooth migration from our current SaaS vendors, we must analyze the contract terms, notice periods, and data export limitations for Datadog, Splunk, and PagerDuty. This analysis guides our 8-week migration schedule to avoid double-billing or contract auto-renewals.

---

## 1. Datadog (Pro + APM + Logs + Custom Metrics)

### Contract Terms & Constraints:
- **Notice Period:** Monthly rolling contract with no annual commitment. Auto-renews monthly. Can be terminated with a 30-day notice window.
- **Data Export Limits:** Datadog does not provide a bulk data export tool. All metric configurations, dashboard definitions, and monitors must be exported via public REST APIs.
- **Trace/Log Retention:** Traces and logs are held for 15 days.

### Exit Action Plan:
- **Week 1 (API Configuration Export):** Run automated Python scripts using Datadog APIs to pull all Dashboard JSONs and Monitor rule definitions. Store them in a Git repository.
- **Week 4 (Notice Filing):** Submit the 30-day formal termination notice to Datadog.
- **Week 5 (Cut-Over & Key Revocation):** Shut down the Datadog Agent on all EC2 hosts. Revoke all Datadog API keys and Application keys via the Datadog console to immediately stop ingestion and prevent trailing overage fees.
- **Week 6 (Contract Termination):** Confirm account closure and verify that the invoice for the final month is processed.

---

## 2. Splunk Cloud (Security & Compliance Logs)

### Contract Terms & Constraints:
- **Notice Period:** 12-month contract, ending in **7 months**. A strict **90-day written notice** is required prior to the end date to prevent auto-renewal.
- **Data Export Limits:** Bulk export is contractually capped at **100 GB/day** during the migration transition window.
- **Retention:** 30 days hot retention.

### Exit Action Plan:
- **Week 1 (Notice Filing - Critical Path):** File the formal 90-day non-renewal notice immediately. Since the contract ends in 7 months, we must notify the vendor now to ensure we can exit cleanly at the end of the term.
- **Week 6 (Report Translation):** Review the security team's top Splunk queries. Translate the SPL query logic into AWS Athena SQL statements.
- **Week 7 (Divert Ingest):** Change the Vector configuration to stop forwarding operational logs to Splunk. All active log search shifts to Grafana Loki. This drops Splunk active ingest to 0.
- **Week 8 (Historical Export):** Leverage the **100 GB/day transition export quota**. Run daily export scripts to extract the last 30 days of historical compliance logs (~1.5 TB total) from Splunk and store them in AWS S3 Glacier in Parquet format.
- **Month 7 (Decommission):** Splunk contract ends. Confirm no trailing fees.

---

## 3. PagerDuty (Incident Paging)

### Contract Terms & Constraints:
- **Notice Period:** Monthly billing with a 30-day exit clause.
- **Data Export Limits:** User roster is easily exported via a single API call. Historical integration logs and escalation policies require a support ticket.

### Action Plan (Decouple & Retain):
- **Decision:** We are **not** exiting PagerDuty. The PagerDuty Business subscription ($3,900/month) is retained to ensure zero risk to paging reliability.
- **Week 6 (Decoupling):** Configure Prometheus Alertmanager to send webhooks to PagerDuty. Set up a "shadow" service in PagerDuty to verify alert routing rules.
- **Week 7 (Cut-Over):** Remove the Datadog and Splunk webhook integrations from PagerDuty. Direct all production alerts exclusively from Alertmanager to PagerDuty production escalation paths.

---

## Summary Timeline of Exit Events

| Target Week | Vendor | Action | Objective |
| :--- | :--- | :--- | :--- |
| **Week 1** | **Splunk** | File 90-day non-renewal notice | Prevent auto-renewal of the 12-month contract |
| **Week 1** | **Datadog** | Export Dashboards & Monitors via API | Retrieve telemetry metadata for translation |
| **Week 4** | **Datadog** | File 30-day termination notice | Set formal account closure date |
| **Week 5** | **Datadog** | Revoke API keys and stop agents | Freeze Datadog billing cycle |
| **Week 7** | **Splunk** | Divert log ingest to Grafana Loki | Drop Splunk active log ingestion |
| **Week 8** | **Splunk** | Bulk export 1.5 TB of compliance logs | Maintain historical log data in AWS S3 Glacier |
