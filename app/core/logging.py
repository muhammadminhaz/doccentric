import logging
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Optional

from app.core.config import LOG_LEVEL


request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or "-"

        # Best-effort OpenTelemetry correlation (avoid hard dependency).
        record.trace_id = "-"
        record.span_id = "-"
        try:
            from opentelemetry import trace

            span = trace.get_current_span()
            ctx = span.get_span_context()
            if ctx and ctx.is_valid:
                record.trace_id = format(ctx.trace_id, "032x")
                record.span_id = format(ctx.span_id, "016x")
        except Exception:
            pass

        return True


def _configure_json_logging(level: int) -> None:
    try:
        from pythonjsonlogger import jsonlogger

        handler = logging.StreamHandler(sys.stdout)
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s "
            "%(request_id)s %(trace_id)s %(span_id)s"
        )
        handler.setFormatter(formatter)
    except Exception:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s "
            "request_id=%(request_id)s trace_id=%(trace_id)s span_id=%(span_id)s"
        )
        handler.setFormatter(formatter)

    handler.addFilter(ContextFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def setup_logging() -> None:
    level_name = LOG_LEVEL.upper()
    level = getattr(logging, level_name, logging.INFO)
    _configure_json_logging(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def new_request_id() -> str:
    # Shorter than UUID4 while still unique enough for log correlation.
    return uuid.uuid4().hex


class log_timing:
    def __init__(self, logger: logging.Logger, event: str, **fields):
        self._logger = logger
        self._event = event
        self._fields = fields
        self._t0 = 0.0

    def __enter__(self):
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        elapsed_ms = (time.perf_counter() - self._t0) * 1000.0
        if exc is None:
            self._logger.info(self._event, extra={"elapsed_ms": elapsed_ms, **self._fields})
            return False
        self._logger.exception(
            self._event,
            extra={"elapsed_ms": elapsed_ms, **self._fields},
        )
        return False
