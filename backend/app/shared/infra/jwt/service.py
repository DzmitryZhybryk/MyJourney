import datetime as dt
from functools import cache

import jwt
from pydantic import ValidationError

from app.shared.infra.jwt.ports import AccessTokenClaims
from app.shared.infra.jwt.schemas import AccessTokenPayload
from app.shared.settings import settings


class JWTDecodeError(Exception):
    """Декодирование access-токена не удалось — подпись/exp/формат."""


class JWTService:
    """Реализация ``AccessTokenIssuerPort`` и проверка access-токенов запроса."""

    def __init__(self, *, secret: str, algorithm: str, access_token_expire_minutes: int) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._expire_minutes = access_token_expire_minutes

    def create_access_token(self, *, claims: AccessTokenClaims) -> str:
        now = dt.datetime.now(tz=dt.UTC)
        payload = AccessTokenPayload(
            sub=claims.user_id,
            role=claims.role,
            plan=claims.plan,
            email_verified=claims.email_verified,
            permissions=sorted(claims.permissions),
            iat=int(now.timestamp()),
            exp=int((now + dt.timedelta(minutes=self._expire_minutes)).timestamp()),
        )
        return jwt.encode(payload.model_dump(mode="json"), self._secret, algorithm=self._algorithm)

    def decode_access_token(self, token: str) -> AccessTokenClaims:
        """
        Декодирует access-токен и возвращает его содержимое.

        Все ошибки PyJWT (истёкший срок, неверная подпись, искажённый формат)
        и claim неверного типа оборачиваются в ``JWTDecodeError`` — инкапсулируем
        зависимость от pyjwt в инфраструктурном слое, presentation работает
        только с этим типом.

        Scenarios:
            - любой эндпоинт, которому нужен текущий пользователь или право

        Args:
            token: Plaintext JWT access-токен из заголовка Authorization

        Returns:
            Содержимое токена

        Raises:
            JWTDecodeError: Токен не проходит валидацию или claim отсутствует/неверного типа
        """
        try:
            raw_payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
            payload = AccessTokenPayload.model_validate(raw_payload)
        except (jwt.PyJWTError, ValidationError) as exc:
            raise JWTDecodeError() from exc

        return AccessTokenClaims(
            user_id=payload.sub,
            role=payload.role,
            plan=payload.plan,
            permissions=frozenset(payload.permissions),
            email_verified=payload.email_verified,
        )


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
