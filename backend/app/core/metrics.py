"""Prometheus metrics for observability."""

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Request metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

ERROR_COUNT = Counter(
    "http_errors_total",
    "Total HTTP errors",
    ["method", "endpoint", "error_type"],
)

# Gemini LLM metrics
GEMINI_REQUEST_COUNT = Counter(
    "gemini_requests_total",
    "Total Gemini API requests",
    ["model", "status"],
)

GEMINI_LATENCY = Histogram(
    "gemini_request_duration_seconds",
    "Gemini API request latency in seconds",
    ["model"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

GEMINI_FAILURES = Counter(
    "gemini_failures_total",
    "Total Gemini API failures",
    ["model", "error_type"],
)

# AI Generation metrics
AI_GENERATION_COUNT = Counter(
    "ai_generations_total",
    "Total AI note generations",
    ["status", "safety_mode"],
)

INJECTION_DETECTED_COUNT = Counter(
    "injection_detected_total",
    "Total prompt injection attempts detected",
)


def get_metrics() -> bytes:
    """Generate Prometheus metrics output."""
    return generate_latest()


def get_metrics_content_type() -> str:
    """Get the content type for Prometheus metrics."""
    return CONTENT_TYPE_LATEST
