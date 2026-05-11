"""OpenTelemetry tracer. Disabled by default; enable with TAGENT_OTEL_ENABLED=true."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from loguru import logger

from runtime.config.settings import get_settings

_initialized = False


def init_tracing(service_name: str = "test-agent-runtime") -> None:
    global _initialized
    if _initialized:
        return
    s = get_settings()
    if not s.otel_enabled:
        logger.debug("OTel disabled (TAGENT_OTEL_ENABLED=false)")
        _initialized = True
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as e:
        logger.warning("OTel libs missing: {}; tracing disabled", e)
        _initialized = True
        return
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=s.otel_endpoint, insecure=True)))
    trace.set_tracer_provider(provider)
    _initialized = True
    logger.info("OTel initialized service={} endpoint={}", service_name, s.otel_endpoint)


@contextmanager
def span(name: str, **attrs) -> Iterator[None]:
    s = get_settings()
    if not s.otel_enabled:
        yield
        return
    try:
        from opentelemetry import trace
    except ImportError:
        yield
        return
    tracer = trace.get_tracer("test-agent-runtime")
    with tracer.start_as_current_span(name) as sp:
        for k, v in attrs.items():
            sp.set_attribute(k, v)
        yield
