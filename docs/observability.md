# Observability & Performance Profiling

This guide explains how to trace, measure and visualise the runtime performance
of the KillrVideo FastAPI backend once **Issue #7 – Deep Instrumentation** is
merged.

---

## 1 Tracing (OpenTelemetry)

* Tracing is enabled when **both** `OBSERVABILITY_ENABLED=true` and
  `OTEL_TRACES_ENABLED=true` (default).  The exporter endpoint / protocol are
  configured via:

  * `OTEL_EXPORTER_OTLP_ENDPOINT`
  * `OTEL_EXPORTER_OTLP_PROTOCOL` (grpc | http)

* Automatic FastAPI spans are provided by `FastAPIInstrumentor`.
* Manual spans have been added to:

  | Span name                           | Code Path                                            |
  |------------------------------------|------------------------------------------------------|
  | `youtube.fetch_v3_api`             | `app.external_services.youtube_metadata`             |
  | `youtube.fetch_oembed`             | same as above                                        |
  | `vector.search`                    | `app.services.vector_search_utils`                   |
  | `astra.list_videos`                | `app.services.video_service.list_videos_with_query`  |
  | `recommend.related_videos`         | `app.services.recommendation_service`               |
  | `recommend.for_you`                | same as above                                        |

These spans include useful attributes such as `duration_ms`, `result_count`
and `vector.dim` (where applicable).

---

## 2 Metrics (Prometheus)

Custom Prometheus **Histogram** metrics are registered in `app/metrics.py` and
exposed via the `/metrics` route that already existed on every service:

| Metric Name                               | Labels      | Description                                   |
|-------------------------------------------|-------------|-----------------------------------------------|
| `astra_db_query_duration_seconds`         | operation   | Data API query latency                        |
| `youtube_fetch_duration_seconds`          | method      | YouTube metadata fetch latency                |
| `vector_search_duration_seconds`          | –           | Semantic search end-to-end latency            |
| `recommendation_generation_duration_seconds`| –          | Time to build related / for-you lists         |

All histograms use Prometheus default buckets which work well for service
latencies (≤ 10 seconds).  If you need sub-millisecond resolution you can tune
the buckets by calling `Histogram(..., buckets=[...])`.

### 2.1 Scraping

If you are running the monolith on port 8000 the scrape job in `prometheus.yml`
would look like:

```yaml	scheme: http
scrape_configs:
  - job_name: killrvideo_monolith
    scrape_interval: 10s
    static_configs:
      - targets: ['killrvideo:8000']
```

For the micro-services pattern simply add additional targets (8001–8006).

---

## 3 Grafana Dashboards

The JSON definitions for two ready-made dashboards live under
`docs/grafana/`:

1. **API Latency by Route** – breaks down request duration by HTTP path.
2. **Backend Hot-Path** – focuses on the four custom histograms above and
   shows p50/p95 across time.

Import them into Grafana via *Dashboards → Import → Upload JSON*.

---

## 4 Local Profiling Workflow

1.  Start the stack (monolith example):

    ```bash
    poetry run uvicorn app.main:app --port 8000
    ```
2.  Run a realistic workload (pytest, k6, or the Cypress e2e suite).
3.  Point Prometheus at `localhost:8000/metrics` and Grafana at Prometheus.
4.  Navigate to the *Backend Hot-Path* dashboard and observe the impact of
    your test run.  Spikes typically indicate an optimisation opportunity in
    the corresponding code path.

---

## 5 Automated Regression Tests

The test `tests/services/test_prometheus_metrics_route.py` asserts that the
/metrics endpoint exposes all custom histograms.  CI will fail if a future
refactor removes them by accident. 