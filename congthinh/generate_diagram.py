import os
import sys

try:
    from diagrams import Diagram, Cluster, Edge
    from diagrams.aws.storage import SimpleStorageServiceS3
    from diagrams.aws.analytics import Athena
    from diagrams.onprem.monitoring import Grafana, Prometheus
    from diagrams.onprem.logging import Loki
    from diagrams.onprem.tracing import Tempo
    from diagrams.saas.alerting import Pagerduty
    from diagrams.onprem.compute import Server
    from diagrams.onprem.client import User
    from diagrams.custom import Custom
except ImportError:
    print("Please install diagrams: pip install diagrams")
    sys.exit(1)

# Use standard lines (removed ortho as it causes missing edges bug in Windows Graphviz)
graph_attr = {
    "nodesep": "1.6",
    "ranksep": "2.4",
    "fontname": "Sans-Serif"
}

node_attr = {
    "fontsize": "24",
    "fontname": "Sans-Serif bold"
}

edge_attr = {
    "fontsize": "22",
    "fontname": "Sans-Serif bold",
    "color": "#1A202C",        # Mũi tên xám đậm rõ ràng
    "penwidth": "3.0",         # Độ dày nét mũi tên lớn (3.0) giúp nhìn rất rõ
    "arrowsize": "1.5"         # Kích thước đầu mũi tên lớn hơn (1.5) để không bị che khuất
}

def make_cluster_attr(title_size, bgcolor, border_color):
    return {
        "fontsize": str(title_size),
        "fontname": "Sans-Serif bold",
        "margin": "80",            # Tăng khoảng lề trong khung lớn (80) để đẩy các icon xa tiêu đề
        "bgcolor": bgcolor,
        "color": border_color,
        "penwidth": "3.5",
        "style": "rounded"
    }

attr_ingest = make_cluster_attr(32, "#EBF8FF", "#2B6CB0")   # Soft Blue
attr_buffer = make_cluster_attr(32, "#FFF9E6", "#DD6B20")   # Soft Orange/Amber
attr_storage = make_cluster_attr(32, "#E6FFFA", "#319795")  # Soft Teal
attr_cold = make_cluster_attr(32, "#F7FAFC", "#4A5568")     # Soft Gray
attr_alert = make_cluster_attr(32, "#FFF5F5", "#C53030")    # Soft Red
attr_visual = make_cluster_attr(32, "#F5F3FF", "#6366F1")   # Soft Indigo/Violet

def get_img(filename):
    return os.path.abspath(os.path.join("image", filename))

with Diagram("Target Architecture (Observability Stack)", filename="image/architecture-target", show=False, direction="LR", graph_attr=graph_attr, node_attr=node_attr, edge_attr=edge_attr):
    
    with Cluster("Ingestion & Synthetics", graph_attr=attr_ingest):
        apps = Server("\n\n10-Service Apps")
        beyla = Custom("\n\nGrafana Beyla\n(eBPF APM)", get_img("opentelemetry.png")) if os.path.exists(get_img("opentelemetry.png")) else Server("\n\nGrafana Beyla\n(eBPF APM)")
        vector = Custom("\n\nVector\n(Log Agent)", get_img("opentelemetry.png")) if os.path.exists(get_img("opentelemetry.png")) else Server("\n\nVector\n(Log Agent)")
        blackbox = Custom("\n\nBlackbox Exporter\n(Synthetics)", get_img("blackbox-exporter.png")) if os.path.exists(get_img("blackbox-exporter.png")) else Prometheus("\n\nBlackbox Exporter\n(Synthetics)")
        otel = Custom("\n\nOpenTelemetry", get_img("opentelemetry.png")) if os.path.exists(get_img("opentelemetry.png")) else Server("\n\nOpenTelemetry")

    with Cluster("Ingestion Buffer", graph_attr=attr_buffer):
        redpanda = Server("\n\nRedpanda Cluster")

    with Cluster("Storage & Query Backend (Hot/Warm)", graph_attr=attr_storage):
        vm = Custom("\n\nVictoriaMetrics", get_img("victoriametrics.png")) if os.path.exists(get_img("victoriametrics.png")) else Prometheus("\n\nVictoriaMetrics")
        vmanomaly = Custom("\n\nVM vmanomaly\n(AIOps)", get_img("victoriametrics.png")) if os.path.exists(get_img("victoriametrics.png")) else Prometheus("\n\nVM vmanomaly\n(AIOps)")
        loki = Loki("\n\nGrafana Loki")
        tempo = Tempo("\n\nGrafana Tempo")
        
    with Cluster("Cold Storage", graph_attr=attr_cold):
        s3 = SimpleStorageServiceS3("\n\nAWS S3 Glacier")

    with Cluster("Alerting & Self-Healing", graph_attr=attr_alert):
        alertmanager = Prometheus("\n\nAlertmanager")
        keep = Server("\n\nKeep\n(Remediation)")
        pd = Pagerduty("\n\nPagerDuty")

    with Cluster("Visualization & Audit", graph_attr=attr_visual):
        grafana = Grafana("\n\nGrafana Cloud")
        athena = Athena("\n\nAWS Athena")
        statuspage = Custom("\n\nAtlassian\nStatuspage", get_img("statuspage.png")) if os.path.exists(get_img("statuspage.png")) else Server("\n\nAtlassian\nStatuspage")

    oncall = User("\nOn-call Engineer")
    security = User("\nSecurity Team")

    def L(num, text):
        return f"<<TABLE BORDER='0' CELLBORDER='0' CELLSPACING='0' CELLPADDING='4' BGCOLOR='white'><TR><TD ALIGN='CENTER'><B><FONT POINT-SIZE='24' COLOR='#d32f2f'>[{num}]</FONT></B><BR/><FONT POINT-SIZE='16' COLOR='#1A202C'>{text}</FONT></TD></TR></TABLE>>"

    # Ingestion Flow (Left to Right)
    apps >> Edge(color="#8B5CF6", label=L("1a", "eBPF")) >> beyla
    apps >> Edge(color="#10B981", label=L("1b", "File Logs")) >> vector
    beyla >> Edge(color="#8B5CF6", label=L("1c", "Metrics/Traces")) >> otel
    blackbox >> Edge(color="#8B5CF6", label=L("2", "Uptime")) >> otel
    
    vector >> Edge(color="#10B981", label=L("2b", "Forward Logs")) >> redpanda
    otel >> Edge(color="#8B5CF6", label=L("2c", "Forward Telemetry")) >> redpanda
    otel >> Edge(color="#6B7280", label=L("3d", "Audit Logs"), minlen="3") >> s3
    
    redpanda >> Edge(color="#8B5CF6", label=L("3a", "Metrics")) >> vm
    redpanda >> Edge(color="#10B981", label=L("3b", "Logs")) >> loki
    redpanda >> Edge(color="#F59E0B", label=L("3c", "Traces")) >> tempo
    
    # vmanomaly ML loop
    vm >> Edge(color="#6366F1", style="dashed", label=L("3e", "Pull Metrics")) >> vmanomaly
    vmanomaly >> Edge(color="#6366F1", label=L("3f", "Push Scores")) >> vm

    # Archiving Flow
    vm >> Edge(color="#4B5563", style="dashed", label=L("4a", "Archive Blocks")) >> s3
    loki >> Edge(color="#4B5563", style="dashed", label=L("4b", "Archive Chunks")) >> s3
    tempo >> Edge(color="#4B5563", style="dashed", label=L("4c", "Archive Blocks")) >> s3
    
    # Alerting Flow (Left to Right)
    vm >> Edge(color="#EF4444", label=L("5a", "Alerts")) >> alertmanager
    loki >> Edge(color="#EF4444", label=L("5b", "Alerts")) >> alertmanager
    alertmanager >> Edge(color="#EF4444", label=L("5c", "Webhooks")) >> keep
    keep >> Edge(color="#059669", style="dashed", label=L("6", "Auto-Remediate")) >> apps
    keep >> Edge(color="#DC2626", label=L("7", "Escalate")) >> pd
    pd >> Edge(color="#DC2626", label=L("7b", "Paging (Call/SMS)"), minlen="3") >> oncall
    
    # Query Flow (Force Grafana to the Right, but arrows point back to Left)
    vm >> Edge(dir="back", color="#2563EB", style="dotted", label=L("8a", "Query Metrics")) >> grafana
    loki >> Edge(dir="back", color="#10B981", style="dotted", label=L("8b", "Query Logs")) >> grafana
    tempo >> Edge(dir="back", color="#F59E0B", style="dotted", label=L("8c", "Query Traces")) >> grafana
    
    # Human & Audit Flow (Force to the far right)
    grafana >> Edge(dir="back", label=L("9", "View Dashboards"), minlen="3") >> oncall
    s3 >> Edge(dir="back", style="dotted", label=L("10", "SQL Query"), minlen="3") >> athena
    athena >> Edge(dir="back", label=L("11", "Audit Review"), minlen="3") >> security
    statuspage >> Edge(dir="back", label=L("12", "Update Status"), minlen="3") >> oncall

print("Diagram generated successfully as architecture-target.png")
