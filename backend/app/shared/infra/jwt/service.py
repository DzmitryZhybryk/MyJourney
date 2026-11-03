import datetime as dt
from functools import cache
from uuid import UUID

import jwt

from app.shared.settings import settings


class JWTDecodeError(Exception):
    """Декодирование access-токена не удалось — подпись/exp/формат."""


class JWTService:
    """Реализация ``AccessTokenIssuerPort`` и проверка access-токенов запроса."""

    def __init__(self, *, secret: str, algorithm: str, access_token_expire_minutes: int) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._expire_minutes = access_token_expire_minutes

    def create_access_token(self, *, user_id: UUID, role: str, email_verified: bool) -> str:
        now = dt.datetime.now(tz=dt.UTC)
        payload = {
            "sub": str(user_id),
            "role": role,
            "email_verified": email_verified,
            "iat": now,
            "exp": now + dt.timedelta(minutes=self._expire_minutes),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode_access_token(self, token: str) -> UUID:
        """
        Декодирует access-токен и возвращает идентификатор пользователя.

        Все ошибки PyJWT (истёкший срок, неверная подпись, искажённый формат)
        и невалидный ``sub`` оборачиваются в ``JWTDecodeError`` — инкапсулируем
        зависимость от pyjwt в инфраструктурном слое, presentation работает
        только с этим типом.

        Scenarios:
            - любой эндпоинт, которому нужен текущий пользователь

        Args:
            token: Plaintext JWT access-токен из заголовка Authorization

        Returns:
            UUID пользователя из claim'а ``sub``

        Raises:
            JWTDecodeError: Если токен не проходит валидацию или ``sub`` отсутствует/некорректен
        """
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.PyJWTError as exc:
            raise JWTDecodeError() from exc

        sub = payload.get("sub")
        if not isinstance(sub, str):
            raise JWTDecodeError()

        try:
            return UUID(sub)
        except ValueError as exc:
            raise JWTDecodeError() from exc


@cache
def get_jwt_service() -> JWTService:
    """
    Возвращает singleton ``JWTService`` с конфигом из глобальных настроек.

    JWTService stateless и иммутабельный — пересоздавать на каждый запрос
    бессмысленно. Тестируемость сохраняется через ``app.dependency_overrides``
    на presentation-обёртке.

    Scenarios:
        - выпуск access-токена
        - любой эндпоинт, которому нужен текущий пользователь
    """
    return JWTService(
        secret=settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
        access_token_expire_minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    )
