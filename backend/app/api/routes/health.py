"""Health and metrics endpoints."""

from fastapi import APIRouter, Response

from app.core.metrics import get_metrics, get_metrics_content_type

router = APIRouter()


@router.get(
    "/healthz",
    summary="Health check",
    description="Basic health check endpoint.",
    responses={
        200: {"description": "Service is healthy"},
    },
)
async def health_check() -> dict:
    """Health check endpoint.
    
    Returns:
        Health status.
    """
    return {"status": "healthy", "service": "clinician-copilot"}


@router.get(
    "/readyz",
    summary="Readiness check",
    description="Check if service is ready to accept requests.",
    responses={
        200: {"description": "Service is ready"},
    },
)
async def readiness_check() -> dict:
    """Readiness check endpoint.
    
    Returns:
        Readiness status.
    """
    # Could add database connectivity check here
    return {"status": "ready"}


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Prometheus-format metrics endpoint.",
)
async def metrics() -> Response:
    """Prometheus metrics endpoint.
    
    Returns:
        Prometheus metrics in text format.
    """
    return Response(
        content=get_metrics(),
        media_type=get_metrics_content_type(),
    )
