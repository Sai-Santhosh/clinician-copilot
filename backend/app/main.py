"""FastAPI application entry point."""

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.metrics import REQUEST_COUNT, REQUEST_LATENCY, ERROR_COUNT

settings = get_settings()
logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Clinician Copilot API")
    yield
    # Shutdown
    logger.info("Shutting down Clinician Copilot API")


app = FastAPI(
    title="Clinician Copilot API",
    description="AI-powered psychiatry notes and care plans assistant",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Remaining"],
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to collect request metrics."""
    start_time = time.time()
    
    # Get route path for metrics (use pattern, not actual path)
    route_path = request.url.path
    method = request.method

    try:
        response = await call_next(request)
        
        # Record metrics
        duration = time.time() - start_time
        REQUEST_COUNT.labels(
            method=method,
            endpoint=route_path,
            status_code=response.status_code,
        ).inc()
        REQUEST_LATENCY.labels(
            method=method,
            endpoint=route_path,
        ).observe(duration)

        return response

    except Exception as e:
        # Record error
        duration = time.time() - start_time
        ERROR_COUNT.labels(
            method=method,
            endpoint=route_path,
            error_type=type(e).__name__,
        ).inc()
        raise


@app.middleware("http")
async def request_size_limit(request: Request, call_next):
    """Middleware to enforce request size limits."""
    # Limit request body to 10MB
    max_size = 10 * 1024 * 1024  # 10MB
    
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > max_size:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"detail": "Request body too large"},
        )
    
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages."""
    errors = []
    for error in exc.errors():
        loc = ".".join(str(l) for l in error["loc"])
        errors.append({
            "field": loc,
            "message": error["msg"],
            "type": error["type"],
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": errors},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(f"Uncaught exception: {type(exc).__name__}: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Clinician Copilot API",
        "version": "0.1.0",
        "docs": "/docs",
    }
