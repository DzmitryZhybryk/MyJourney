from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.shared.infra.jwt.exceptions import InvalidAccessTokenError
from app.shared.infra.jwt.service import JWTDecodeError, JWTService, get_jwt_service
from app.shared.logging import bind_log_context

bearer_scheme = HTTPBearer(auto_error=False)


def jwt_service_dependency() -> JWTService:
    return get_jwt_service()


async def current_user_id_dependency(
    *,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    jwt_service: Annotated[JWTService, Depends(jwt_service_dependency)],
) -> UUID:
    """
    Извлекает ``user_id`` из Bearer access-токена и привязывает его к строкам лога запроса.

    Заголовок ``Authorization: Bearer <token>`` обязателен — отсутствие
    или невалидный токен (просроченная подпись, искажённый формат, чужой
    secret) приводят к 401 ``InvalidAccessTokenError``.

    Функция асинхронная намеренно: синхронную зависимость FastAPI выполняет в потоке с копией
    контекста, и привязанный к логу ``user_id`` пропал бы вместе с копией.

    Живёт в shared (а не в auth/presentation): это инфраструктура аутентификации
    запроса, общая для всех доменов, — иначе каждый presentation-слой зависел бы
    от auth.presentation, замыкая цикл auth ↔ users.

    Scenarios:
        - любой эндпоинт, которому нужен текущий пользователь

    Args:
        credentials: Распарсенный ``Authorization`` (или ``None`` если заголовка нет)
        jwt_service: Сервис подписи/декодирования JWT

    Returns:
        UUID пользователя из claim'а ``sub``

    Raises:
        InvalidAccessTokenError: Заголовок отсутствует или токен не прошёл валидацию
    """
    if credentials is None:
        raise InvalidAccessTokenError()

    try:
        user_id = jwt_service.decode_access_token(token=credentials.credentials)
    except JWTDecodeError as exc:
        raise InvalidAccessTokenError() from exc

    bind_log_context(user_id=user_id)
    return user_id
