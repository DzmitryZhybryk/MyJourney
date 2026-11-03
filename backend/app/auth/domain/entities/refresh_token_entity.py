import datetime as dt
from typing import Self
from uuid import UUID, uuid4

from app.shared.domain.domain_mixins import TimestampedEntityMixin


class RefreshTokenEntity(TimestampedEntityMixin):
    def __init__(
        self,
        *,
        token_id: UUID,
        user_id: UUID,
        token_hash: str,
        expires_at: dt.datetime,
        revoked_at: dt.datetime | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        **timestamp_kwargs: dt.datetime | None,
    ) -> None:
        super().__init__(**timestamp_kwargs)
        self.token_id = token_id
        self.user_id = user_id
        self.token_hash = token_hash
        self.expires_at = expires_at
        self.revoked_at = revoked_at
        self.ip_address = ip_address
        self.user_agent = user_agent

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        token_hash: str,
        ttl_days: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Self:
        return cls(
            token_id=uuid4(),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=dt.datetime.now(tz=dt.UTC) + dt.timedelta(days=ttl_days),
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @property
    def is_revoked(self) -> bool:
        """
        Признак того, что токен отозван и больше не должен приниматься.

        Scenarios:
            - выход из аккаунта
            - обновление сессии: отозванный токен — признак утечки
        """
        return self.revoked_at is not None

    @property
    def is_expired(self) -> bool:
        """
        Признак того, что срок действия токена истёк.

        Scenarios:
            - обновление сессии
        """
        return self.expires_at < dt.datetime.now(tz=dt.UTC)

    def revoke(self) -> None:
        """
        Отмечает токен отозванным.

        Идемпотентно: повторный вызов на уже revoked-токене не меняет состояние,
        чтобы logout/reuse-detection могли звать его без предварительной проверки.

        Scenarios:
            - выход из аккаунта
            - обновление сессии: старый токен отзывается при выпуске нового
        """
        if self.is_revoked:
            return

        self.revoked_at = dt.datetime.now(tz=dt.UTC)
        self._mark_updated()
