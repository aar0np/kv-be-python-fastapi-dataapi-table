from prometheus_client import Histogram

# ---------------------------------------------------------------------------
# Custom Prometheus metrics – exported via /metrics route exposed by
# prometheus_fastapi_instrumentator in app.utils.observability.configure_observability().
# ---------------------------------------------------------------------------

ASTRA_DB_QUERY_DURATION_SECONDS = Histogram(
    "astra_db_query_duration_seconds",
    "Latency of Astra DB Data API queries (seconds)",
    ["operation"],
)

YOUTUBE_FETCH_DURATION_SECONDS = Histogram(
    "youtube_fetch_duration_seconds",
    "Latency of YouTube metadata fetches (seconds)",
    ["method"],
)

VECTOR_SEARCH_DURATION_SECONDS = Histogram(
    "vector_search_duration_seconds",
    "Latency of semantic vector search operations (seconds)",
)

RECOMMENDATION_DURATION_SECONDS = Histogram(
    "recommendation_generation_duration_seconds",
    "Latency of recommendation engine stub (seconds)",
)
