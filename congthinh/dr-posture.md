# Bonus Section E: Disaster Recovery (DR) Posture & RTO/RPO Targets

This document defines the Disaster Recovery (DR) strategy for the redesigned self-hosted observability stack. Since we are moving from high-availability SaaS providers (Datadog/Splunk) to self-hosted open-source components, we must ensure high availability across AWS Availability Zones (AZs) and establish clear Recovery Time Objectives (RTO) and Recovery Point Objectives (RPO).

---

## 1. DR Targets by Component

| Component | Architecture Type | Hot Storage Location | Cold Storage Location | RTO Target | RPO Target |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **VictoriaMetrics** | Clustered (RF=3) | Local NVMe SSD | AWS S3 Standard | 30 minutes | 5 minutes |
| **Grafana Loki** | Microservices Mode | Local EBS (Write Buffer) | AWS S3 Standard | 15 minutes | 1 minute |
| **Grafana Tempo** | Distributed Mode | Local EBS (Write Buffer) | AWS S3 Standard | 15 minutes | 5 minutes |
| **Redpanda Cluster** | 3-Node Cluster (RF=3) | Local EBS (GP3) | N/A | 5 minutes | 0 (Multi-AZ Sync) |
| **Alertmanager** | HA Cluster (Gossip) | Memory / Local Disk | N/A | 1 minute | 0 |
| **Keep** | Remediation Engine | Memory | Git Playbook Repo | 5 minutes | 0 (Stateless) |
| **Grafana Cloud** | Managed SaaS | Multi-Region SaaS | Git Dashboard Repo | 5 minutes | Daily (Config) |
| **`vmanomaly`** | Python Deployment | Memory | AWS S3 (Models) | 10 minutes | 1 hour |

---

## 2. Component Failover & Durability Specifications

### VictoriaMetrics (Metrics)
- **Replication Strategy:** In the upgraded clustered target state, VictoriaMetrics runs with a Replication Factor of 3 (`-replicationFactor=3`). Every metric write is mirrored across three different storage nodes located in separate AWS Availability Zones.
- **Failover:** If one storage node goes down, the remaining nodes absorb the write traffic. If an entire AZ goes down, the load balancer routes writes to the other two AZs.
- **Data Recovery:** Historical blocks are backed up to S3. In a worst-case cluster-wide failure, a new cluster can be provisioned via Terraform, and S3 blocks can be read immediately via the VictoriaMetrics VM-storage engine.

### Grafana Loki (Logs)
- **Replication Strategy:** Loki is stateless; log chunks are written directly to AWS S3. 
- **Backpressure Handling (Ingest Protection):** If the Loki writer tier is temporarily unavailable, the **Redpanda Cluster** buffers the incoming log streams. If the Redpanda Cluster is also unavailable, the local **Vector Agents** buffer logs on their local disks. This multi-tiered backpressure queue prevents log loss during any downstream database or buffer outage.
- **RTO & RPO:** Since S3 stores the primary log data, Loki read/write pods can be deleted and re-created in under 15 minutes. The maximum data loss is limited to logs currently in the Vector agents' or Redpanda's un-flushed buffers.

### Grafana Tempo (Traces)
- **Replication Strategy:** Tracing is highly transactional. Tempo writes block data to S3 immediately.
- **Failover & Buffering:** Traces from Grafana Beyla and OpenTelemetry SDKs are routed through the clustered **Redpanda queue**, which buffers them to handle ingestion spikes. If Tempo is temporarily unavailable, Redpanda retains the traces in queue. If both Redpanda and Tempo are offline, the OTel Collector gateway maintains a small in-memory queue to retry trace writes.

### Redpanda Cluster (Telemetry Buffer)
- **Replication Strategy:** Redpanda runs as a 3-node cluster with a Replication Factor of 3 (`RF=3`) spanning three different AWS Availability Zones.
- **Failover:** Writes are acknowledged only after being replicated to a quorum of brokers (Raft consensus). If a single Redpanda node crashes, the remaining nodes automatically re-elect leaders for affected partitions within milliseconds, causing no data loss (RPO = 0) and zero service interruption.
- **Disk Saturation Mitigation:** We enforce a strict 6-hour message retention window. If disk space exceeds 75%, alertmanager webhooks trigger Vector agents to temporarily throttle debug-level telemetry at the source.

### Prometheus Alertmanager (Alerts Routing)
- **Replication Strategy:** Deployed as an active-active cluster of two nodes. The nodes communicate using the Gossip protocol (`mesh-network`) to synchronize silences, alert state, and notification histories.
- **Failover:** If one Alertmanager node crashes, the secondary node automatically processes alerts and routes them to Keep/PagerDuty. The Gossip protocol ensures that duplicated alerts are not fired, preventing duplicate phone calls/SMS.

### Keep (Remediation Engine)
- **Replication Strategy:** Runs as a containerized deployment in Kubernetes. Playbooks and configurations are stored in a version-controlled Git repository, making Keep entirely stateless.
- **Failover:** If the Keep container fails, Kubernetes automatically reschedules it onto an active node. Keep re-pulls its playbook configurations from Git upon startup, resuming active Alertmanager webhook processing.
- **Self-Healing Protection:** Enforces strict execution limits (e.g. max 1 execution per 15 minutes for any specific alert) to prevent cascade failures and resource loops during multi-service outages.

### Grafana Cloud (Single Pane of Glass UI)
- **Replication Strategy:** Grafana Cloud is a fully managed SaaS. Grafana Labs guarantees multi-region failover for the UI.
- **Config Backup:** All Grafana dashboards, folders, and datasources are managed via a GitOps repository. Every night, a pipeline exports active dashboard configurations to Git. In the event of a Grafana Cloud outage, we can stand up a self-hosted Grafana instance and restore all dashboards within 5 minutes.

### `vmanomaly` (AIOps Python Engine)
- **Replication Strategy:** Runs as a Kubernetes deployment. Model coefficient files are saved periodically to an S3 bucket.
- **Failover:** If the `vmanomaly` container crashes, Kubernetes automatically reschedules it. Upon boot, the container downloads the latest model baseline coefficients from S3 and resumes inference.
- **RTO & RPO:** Rescheduling is automatic and takes under 10 minutes. If S3 coefficients are corrupted, the container starts a cold retraining loop using the last 14 days of metrics from VictoriaMetrics (taking ~1 hour to complete).
