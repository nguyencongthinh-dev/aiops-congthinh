# A1: Target-State Architecture Diagram

This document presents the target-state architecture for the observability stack, focusing on achieving a "Single Pane of Glass" via Grafana and dramatically reducing storage costs by using S3-backed OSS databases.

![Architecture Diagram](./image/architecture-target.png)



## Operational Data Flow (Luồng hoạt động)

Dưới đây là chú thích chi tiết cho các luồng dữ liệu được đánh số trên sơ đồ:

### 1. Data Collection (Thu thập dữ liệu)
- **[1a] eBPF Telemetry**: Grafana Beyla chạy ở tầng nhân (Kernel) tự động thu thập HTTP/gRPC metrics và distributed tracing từ các ứng dụng không cần sửa code và đẩy qua OTel Collector.
- **[1b] Log Ingestion**: Vector Agent thu thập log ứng dụng và hệ thống, thực hiện định dạng và gán nhãn thô trước khi chuyển tiếp.
- **[1c] Uptime Metrics**: Hệ thống Blackbox Exporter liên tục "ping" kiểm tra sức khỏe của các điểm neo (endpoints) và gửi số liệu Uptime về hệ thống.

### 2. Ingestion & Routing & Buffering (Điều phối & Bộ đệm)
- **[2] Redpanda Buffer**: Toàn bộ luồng dữ liệu logs, metrics và traces đi qua **Redpanda Cluster** làm bộ đệm trung gian chịu tải cao. Điều này bảo vệ các storage backend (Loki, VictoriaMetrics, Tempo) khỏi bị log storm/DDoS đánh sập và tránh mất dữ liệu khi storage nodes bảo trì.
- **[3a] Metrics**: Redpanda ghi metrics ổn định vào VictoriaMetrics.
- **[3b] Logs**: Redpanda ghi logs vào Grafana Loki.
- **[3c] Traces**: Redpanda ghi traces vào Grafana Tempo.
- **[3d] Audit Logs**: Logs kiểm toán đi thẳng từ OTel Collector sang AWS S3 Glacier phục vụ lưu trữ lâu dài.
- **[3e] Anomaly Detection (AIOps)**: VictoriaMetrics `vmanomaly` kéo số liệu lịch sử từ VictoriaMetrics, tính toán các điểm bất thường bằng mô hình ML và đẩy ngược kết quả về VictoriaMetrics làm time-series mới.

### 3. Archiving (Lưu trữ lạnh)
- **[4a, 4b, 4c] Blocks/Chunks**: Thay vì lưu trữ vĩnh viễn trên đĩa cứng đắt đỏ, VictoriaMetrics, Loki và Tempo được cấu hình để định kỳ nén dữ liệu cũ thành các khối (Blocks/Chunks) và đẩy xuống kho lạnh S3. 

### 4. Alerting & Auto-Remediation (Cảnh báo & Tự sửa lỗi)
- **[5a, 5b] Alerts**: Khi có bất thường (CPU cao, Anomaly Score > 1.0, hoặc Loki alert), các luật cảnh báo kích hoạt và gửi tín hiệu Alert về Alertmanager.
- **[5c] Self-Healing webhook**: Alertmanager gửi webhook cảnh báo đến **Keep (Remediation Engine)**.
- **[6] Auto-Remediation**: Keep tự động chạy các playbooks khắc phục sự cố (ví dụ: giải phóng dung lượng đĩa, reboot service, scale-out pod).
- **[7] Escalation**: Nếu Keep tự sửa lỗi thất bại hoặc đối với các lỗi nghiêm trọng cấp độ High/Critical, Keep sẽ kích hoạt PagerDuty để réo gọi kỹ sư On-call trực ca.


### 5. UI & Human Interaction (Tương tác con người)
- **[8a, 8b, 8c] Query**: Khi nhận được cảnh báo, Kỹ sư mở Grafana lên. Grafana sẽ truy vấn ngược lại VictoriaMetrics, Loki, Tempo để lấy dữ liệu vẽ biểu đồ. Grafana Machine Learning cũng đồng thời cung cấp dải dự báo động (adaptive thresholds) trực quan trên dashboard.
- **[9] Dashboards**: Kỹ sư On-call theo dõi diễn biến sự cố qua "Single Pane of Glass" (Màn hình duy nhất) trên Grafana Cloud.
- **[10, 11] SQL Audit**: Đối với đội Bảo mật (Security Team), họ có thể dùng AWS Athena để truy vấn trực tiếp kho Audit Logs lưu trên S3 bằng lệnh SQL tiêu chuẩn để rà soát lỗ hổng.
- **[12] Update Status**: Cuối cùng, kỹ sư chủ động cập nhật tình trạng khắc phục lỗi lên Atlassian Statuspage để thông báo cho khách hàng ngoài internet.

---

## Design Notes

- **Ingestion Path:** All signals (Metrics, Logs, Traces) emitted by the services are sent in OTLP format to the OpenTelemetry (OTel) Collector. The OTel Collector acts as the universal router, handling tail-based sampling for traces and dropping noisy/unnecessary logs before they incur storage costs.
- **Storage and Retention Tier:**
  - **Metrics:** VictoriaMetrics (Hot tier on local disk, long-term on S3).
  - **Logs:** Grafana Loki (Index is only labels; bulk data chunks are pushed directly to S3). Audit logs bypass Loki entirely and are routed by OTel as Parquet files to AWS S3 Glacier.
  - **Traces:** Grafana Tempo (Stores 100% of sampled traces backed by S3).
- **Alerting and AIOps Surface:** Alert rules are evaluated by VictoriaMetrics and Loki. **VictoriaMetrics `vmanomaly`** continuously runs ML models to calculate anomaly scores, which are fed back to VictoriaMetrics as metrics to trigger dynamic alerts. Grafana Cloud ML also runs adaptive alerting on telemetry dashboards. All alerts are fired to **Prometheus Alertmanager**, which groups them by service topology (Service Graph) before sending a single deduplicated webhook to PagerDuty.
- **Human-facing Query Surface:** **Grafana Cloud** is the sole UI. On-call engineers use it to view dashboards, search logs, and examine traces without switching context.
- **Color Coding:** Blue = In-house, Green = Self-hosted OSS, Orange = SaaS, Gray = Cloud Storage.

