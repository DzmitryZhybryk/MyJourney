"""Middleware для логирования HTTP запросов и исключений."""

import logging
import time
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.shared.logging.classify import get_log_level_for_exception
from app.shared.logging.config import get_logger
from app.shared.logging.context import (
    build_error_log_context,
    build_log_context,
    extract_request_context,
)
from app.shared.logging.events import get_event_name

logger = get_logger(__name__)


class HTTPLoggingMiddleware(BaseHTTPMiddleware):
    """
    Unified middleware для логирования HTTP запросов и исключений.

    Заменяет стандартное логирование uvicorn.access и позволяет
    обогащать логи дополнительными данными (user_id и т.д.).
    Также перехватывает необработанные исключения на уровне ASGI и логирует их
    в нужном формате. Исключения AppError сюда не доходят как exception: их
    раньше конвертирует ExceptionMiddleware, и они приходят готовым Response.
    """

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """
        Обрабатывает запрос, логирует его и перехватывает исключения.

        Scenarios:
            - каждый HTTP-запрос
        """
        start_time = time.perf_counter()

        request_context = extract_request_context(request)

        try:
            response = await call_next(request)
        except Exception as exc:
            process_time = time.perf_counter() - start_time

            log_context, _, include_traceback = build_error_log_context(
                request=request,
                exc=exc,
                process_time=process_time,
                context=request_context,
            )

            log_level = get_log_level_for_exception(exc)

            event = get_event_name(request)

            if log_level == logging.ERROR:
                logger.exception(
                    event=event,
                    exc_info=exc if include_traceback else None,
                    **log_context,
                )
            elif log_level == logging.WARNING:
                logger.warning(event=event, **log_context)
            else:
                logger.info(event=event, **log_context)

            raise
        else:
            process_time = time.perf_counter() - start_time

            log_context = build_log_context(
                request=request,
                status_code=response.status_code,
                process_time=process_time,
                context=request_context,
            )

            event = get_event_name(request)

            # Уровень лога зависит от статуса: 5xx -> error, 4xx -> warning, иначе info.
            # Исключения AppError конвертируются ExceptionMiddleware в Response
            # и приходят сюда как готовый response, а не exception.
            match response.status_code:
                case status if status >= 500:
                    logger.error(event=event, **log_context)
                case status if status >= 400:
                    logger.warning(event=event, **log_context)
                case _:
                    logger.info(event=event, **log_context)

            return response
