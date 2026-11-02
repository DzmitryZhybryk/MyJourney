"""Трейсинг OpenTelemetry: даёт каждому HTTP-запросу номер (trace_id), который логирование пишет в строки."""

from functools import cache
from typing import TYPE_CHECKING

from opentelemetry.sdk.trace import TracerProvider

if TYPE_CHECKING:
    from fastapi.telemetry import TelemetryConfig


@cache
def get_tracer_provider() -> TracerProvider:
    """
    Возвращает провайдер трейсинга процесса.

    Трейсы никуда не отправляются: провайдер нужен, чтобы у запроса появился trace_id. Закрывать у него нечего,
    поэтому это фабрика, а не компонент; с появлением отправки трейсов станет компонентом.

    Scenarios:
        - номер запроса в строках лога API

    Returns:
        Один на процесс ``TracerProvider`` без обработчиков span'ов
    """
    return TracerProvider()


def get_api_telemetry_config() -> TelemetryConfig:
    """
    Возвращает настройки нативной телеметрии FastAPI для API.

    Дочерние span'ы выключены — трейсы не отправляются, и их сборка была бы пустой работой. OTel-логи выключены —
    ошибки запроса пишет middleware логирования, и с подключённым ``LoggerProvider`` каждая попала бы в лог дважды.

    Scenarios:
        - запуск API-процесса
        - тестовое приложение, проверяющее строку лога запроса

    Returns:
        Словарь для аргумента ``telemetry`` приложения FastAPI
    """
    return {
        "tracer_provider": get_tracer_provider(),
        "operation_spans": False,
        "logs": False,
    }
