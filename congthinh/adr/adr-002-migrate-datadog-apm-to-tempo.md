# ADR 002: Replace Datadog APM with Grafana Tempo and 100% Tail-based Sampling

## Context
We currently spend $11,800/month on Datadog APM hosts, yet distributed tracing is sampled heavily upfront at 1%. As a result, tail-latency issues are invisible, and engineers frequently must fall back to reading raw logs to diagnose incidents (Pain Point 2). Additionally, there is no service-graph based alert correlation, leading to an 8-minute gap before an engineer forms a hypothesis during a cascade failure (Pain Point 3).

## Decision
We will terminate the Datadog APM contract. We will deploy **Grafana Beyla (eBPF)** for zero-code auto-instrumentation on the host nodes to capture HTTP/gRPC traces automatically, combined with OpenTelemetry SDKs for custom application-level spans. The OTel Collector will perform tail-based sampling (retaining 100% of errors and slow requests, dropping successful fast requests) and route them to a clustered **Redpanda queue** for resilient buffering before ingestion into **Grafana Tempo**, which is backed by cheap S3 storage.

## Alternatives considered + rejected
1. **Pay Datadog more to increase sampling rate:** 
   - *Reason for rejection:* Datadog's pricing for storing traces is exorbitant. Increasing the sample rate from 1% to 10% (let alone 100% for errors) would explode the bill, directly violating the CTO's cost-cut mandate.
2. **Use Jaeger (Self-hosted) backed by Cassandra/Elasticsearch:** 
   - *Reason for rejection:* Jaeger is a proven OSS standard, but running a Cassandra or Elasticsearch cluster just to hold trace data introduces significant operational burden and infrastructure cost. Tempo leverages S3, making it virtually stateless and an order of magnitude cheaper to run.

## Consequences
### Positive
- **100% Error Visibility:** Engineers will never again be missing a trace for a failed or slow request, drastically reducing MTTR.
- **Service Graph Generation:** Tempo automatically derives service graphs from traces, integrating natively into Grafana to visually identify the root cause service in a multi-service incident.
- **Cost Savings:** We eliminate $11,800/month in licensing.

### Negative
- **Loss of Datadog's Auto-Instrumentation Dashboards:** Datadog automatically generates beautiful database and endpoint performance dashboards without configuration. The Platform team will have to spend upfront engineering hours configuring Grafana Application Observability to mimic this behavior.
- **Operational Burden:** We take on the responsibility of managing the OpenTelemetry Collector fleet, the Redpanda buffer queue, and the Tempo ingestors. If the OTel Collector or Redpanda queue goes down, we are blind.
