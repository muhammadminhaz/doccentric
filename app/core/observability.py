from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI

from app.core.logging import get_logger


logger = get_logger(__name__)


def setup_observability(app: FastAPI, service_name: str = "doccentric", sqlalchemy_engine=None) -> None:
    """
    Enables distributed tracing with OpenTelemetry.

    Configuration via env:
    - OTEL_SERVICE_NAME (optional)
    - OTEL_EXPORTER_OTLP_ENDPOINT (optional)
    - OTEL_TRACES_EXPORTER: "otlp" (default when endpoint set) or "console"
    """
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    except Exception as e:
        logger.warning("otel_disabled", extra={"reason": str(e)})
        return

    svc = os.getenv("OTEL_SERVICE_NAME") or service_name
    resource = Resource.create({"service.name": svc})
    provider = TracerProvider(resource=resource)

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    traces_exporter = os.getenv("OTEL_TRACES_EXPORTER")

    span_exporter = None
    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            span_exporter = OTLPSpanExporter(endpoint=endpoint)
        except Exception as e:
            logger.warning("otel_otlp_exporter_failed", extra={"reason": str(e)})

    if span_exporter is None:
        if traces_exporter and traces_exporter.lower() == "none":
            logger.info("otel_tracing_disabled")
            return
        span_exporter = ConsoleSpanExporter()

    provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(provider)

    # Auto-instrumentation (best-effort).
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except Exception as e:
        logger.warning("otel_fastapi_instrument_failed", extra={"reason": str(e)})

    try:
        from opentelemetry.instrumentation.requests import RequestsInstrumentor

        RequestsInstrumentor().instrument()
    except Exception as e:
        logger.warning("otel_requests_instrument_failed", extra={"reason": str(e)})

    if sqlalchemy_engine is not None:
        try:
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

            SQLAlchemyInstrumentor().instrument(engine=sqlalchemy_engine)
        except Exception as e:
            logger.warning("otel_sqlalchemy_instrument_failed", extra={"reason": str(e)})

    logger.info("otel_enabled", extra={"service_name": svc, "otlp_endpoint": endpoint})


def get_tracer(name: str):
    try:
        from opentelemetry import trace

        return trace.get_tracer(name)
    except Exception:
        return None

