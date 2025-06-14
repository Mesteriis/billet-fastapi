"""
Настройка OpenTelemetry для трассировки.
"""

from __future__ import annotations

import logging
from typing import Any

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.trace import Span

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def setup_telemetry() -> None:
    """Настройка OpenTelemetry трассировки и метрик."""
    if not settings.TRACING_ENABLED:
        logger.info("OpenTelemetry tracing disabled")
        return

    logger.info("Setting up OpenTelemetry tracing...")

    # Настройка ресурса приложения
    resource = Resource.create(
        {
            ResourceAttributes.SERVICE_NAME: settings.PROJECT_NAME,
            ResourceAttributes.SERVICE_VERSION: settings.VERSION,
            ResourceAttributes.SERVICE_NAMESPACE: "apps",
        }
    )

    # Настройка трейсинга
    setup_tracing(resource)

    # Настройка метрик
    setup_metrics(resource)

    # Автоинструментация
    setup_auto_instrumentation()

    logger.info("OpenTelemetry setup completed")


def setup_tracing(resource: Resource) -> None:
    """Настройка трейсинга."""
    # Создание провайдера трейсов
    tracer_provider = TracerProvider(resource=resource)

    # Настройка экспортера
    otlp_exporter = OTLPSpanExporter(
        endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        insecure=settings.OTEL_EXPORTER_OTLP_INSECURE,
    )

    # Создание процессора спанов
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)

    # Установка глобального провайдера
    trace.set_tracer_provider(tracer_provider)


def setup_metrics(resource: Resource) -> None:
    """Настройка метрик."""
    # Создание экспортера метрик
    metric_exporter = OTLPMetricExporter(
        endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        insecure=settings.OTEL_EXPORTER_OTLP_INSECURE,
    )

    # Создание ридера метрик
    metric_reader = PeriodicExportingMetricReader(
        exporter=metric_exporter,
        export_interval_millis=60000,  # 60 секунд
    )

    # Создание провайдера метрик
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader],
    )

    # Установка глобального провайдера
    metrics.set_meter_provider(meter_provider)


def setup_auto_instrumentation() -> None:
    """Настройка автоинструментации."""
    # Инструментация FastAPI (будет настроена позже)
    # Инструментация HTTP запросов
    RequestsInstrumentor().instrument()

    # Инструментация SQLAlchemy
    SQLAlchemyInstrumentor().instrument()


def instrument_fastapi_app(app) -> None:
    """Инструментация FastAPI приложения.

    Args:
        app: Экземпляр FastAPI приложения
    """
    if settings.TRACING_ENABLED:
        FastAPIInstrumentor.instrument_app(
            app,
            server_request_hook=server_request_hook,
            client_request_hook=client_request_hook,
        )


def server_request_hook(span: Span, scope: dict[str, Any]) -> None:
    """Хук для серверных запросов.

    Args:
        span: Текущий спан
        scope: ASGI scope
    """
    # Добавляем дополнительные атрибуты к спану
    if span and span.is_recording():
        # Добавляем информацию о пути
        path = scope.get("path", "")
        if path:
            span.set_attribute("http.route", path)

        # Добавляем информацию о пользователе если доступна
        headers = dict(scope.get("headers", []))
        user_agent = headers.get(b"user-agent", b"").decode("utf-8")
        if user_agent:
            span.set_attribute("http.user_agent", user_agent)


def client_request_hook(span: Span, scope: dict[str, Any], message: dict[str, Any]) -> None:
    """Хук для клиентских запросов.

    Args:
        span: Текущий спан
        scope: ASGI scope
        message: ASGI message
    """
    # Добавляем дополнительные атрибуты для исходящих запросов
    if span and span.is_recording():
        span.set_attribute("component", "http_client")
