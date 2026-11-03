import secrets
from typing import Final
from uuid import UUID

from pydantic import SecretStr

from app.auth.application.schemas.metadata import ClientMetadata
from app.auth.application.schemas.results import IssuedRefreshToken, TokenPairResult
from app.auth.domain.entities import RefreshTokenEntity, UserCredentialsEntity
from app.shared.infra.crypto import DeterministicHasherPort
from app.shared.infra.jwt import AccessTokenIssuerPort

_REFRESH_TOKEN_SECRET_BYTES: Final[int] = 32


class TokenIssuer:
    """
    Выпускает access/refresh-токены и собирает финальную пару для presentation-слоя.

    Инкапсулирует три детали выпуска, которые AuthService использовать должен,
    но знать про их устройство — нет: генерацию случайного refresh-секрета,
    его детерминированный hash для хранения в БД и подпись JWT access-токена.
    """

    def __init__(
        self,
        *,
        deterministic_hasher: DeterministicHasherPort,
        access_token_issuer: AccessTokenIssuerPort,
        refresh_token_ttl_days: int,
    ) -> None:
        self._deterministic_hasher = deterministic_hasher
        self._access_token_issuer = access_token_issuer
        self._refresh_token_ttl_days = refresh_token_ttl_days

    def hash_refresh_secret(self, refresh_secret: str) -> str:
        """
        Возвращает детерминированный hash plaintext-секрета для поиска в БД.

        Из cookie приходит plaintext, а в БД лежит только hash — нужно посчитать тот же hash,
        чтобы найти соответствующий ``RefreshTokenEntity``.

        Scenarios:
            - выход из аккаунта
            - обновление сессии по refresh-cookie

        Args:
            refresh_secret: Plaintext-секрет из cookie

        Returns:
            Hex-строка hash'а, по которой ищется запись в refresh_tokens
        """
        return self._deterministic_hasher.digest(secret=refresh_secret)

    def issue_refresh_token(
        self,
        *,
        user_id: UUID,
        client_metadata: ClientMetadata,
    ) -> tuple[str, RefreshTokenEntity]:
        """
        Генерирует plaintext-секрет и доменную сущность refresh-токена.

        Plaintext уходит в HttpOnly cookie, в БД лежит только его
        детерминированный hash — компрометация дампа БД не даёт rerun'нуть
        существующие сессии без знания самого секрета.

        Scenarios:
            - регистрация
            - вход
            - обновление сессии: старый токен меняется на новый

        Args:
            user_id: ID пользователя, которому выдаём токен
            client_metadata: IP/user-agent для аудита

        Returns:
            Кортеж ``(plaintext-секрет, RefreshTokenEntity готовый к insert'у)``
        """
        plaintext = secrets.token_urlsafe(_REFRESH_TOKEN_SECRET_BYTES)
        refresh_token_entity = RefreshTokenEntity.create(
            user_id=user_id,
            token_hash=self._deterministic_hasher.digest(secret=plaintext),
            ttl_days=self._refresh_token_ttl_days,
            ip_address=client_metadata.ip_address,
            user_agent=client_metadata.user_agent,
        )
        return plaintext, refresh_token_entity

    def build_token_pair(
        self,
        *,
        user_credentials_entity: UserCredentialsEntity,
        refresh_secret: str,
        refresh_token_entity: RefreshTokenEntity,
    ) -> TokenPairResult:
        """
        Собирает ``TokenPairResult`` из credentials и пары plaintext/entity.

        Scenarios:
            - регистрация
            - вход
            - обновление сессии

        Args:
            user_credentials_entity: Доменная сущность учётных данных (нужна для role + email_verified в JWT)
            refresh_secret: Plaintext-секрет refresh-токена
            refresh_token_entity: Доменная сущность refresh-токена (источник ``expires_at``)

        Returns:
            Готовый к отдаче через presentation-слой результат
        """
        access_token = self._access_token_issuer.create_access_token(
            user_id=user_credentials_entity.user_id,
            role=user_credentials_entity.role.value,
            email_verified=user_credentials_entity.is_email_verified,
        )
        return TokenPairResult(
            access_token=SecretStr(access_token),
            refresh_token=IssuedRefreshToken(
                secret=SecretStr(refresh_secret),
                expires_at=refresh_token_entity.expires_at,
            ),
        )
