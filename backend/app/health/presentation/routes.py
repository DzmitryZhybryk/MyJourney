from fastapi import APIRouter, Response, status

health_router = APIRouter(tags=["health"])


@health_router.get("/healthz/")
async def healthz() -> Response:
    """
    Liveness-проба для контейнерного healthcheck и reverse-proxy.

    Намеренно не трогает БД и внешние сервисы — это liveness, а не readiness:
    контейнер не должен уходить в рестарт из-за временной недоступности
    зависимостей (за переподключение отвечают пул и retry самих клиентов).
    Пробы конкретных зависимостей (postgres, procrastinate) добавятся сюда
    отдельными readiness-эндпоинтами по мере необходимости.

    Returns:
        Пустой ответ со статусом 200, если процесс обрабатывает запросы.
    """
    return Response(status_code=status.HTTP_200_OK)
