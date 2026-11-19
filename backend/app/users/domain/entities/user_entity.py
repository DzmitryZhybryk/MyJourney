import datetime as dt
from typing import Self
from uuid import UUID

from app.shared.domain.domain_mixins import TimestampedEntityMixin
from app.users.exceptions import UserDeletedError


class UserEntity(TimestampedEntityMixin):
    def __init__(
        self,
        *,
        user_id: UUID,
        display_name: str,
        terms_accepted_at: dt.datetime,
        marketing_emails_consent: bool,
        **timestamp_kwargs: dt.datetime | None,
    ) -> None:
        super().__init__(**timestamp_kwargs)
        self.user_id = user_id
        self.display_name = display_name
        self.terms_accepted_at = terms_accepted_at
        self.marketing_emails_consent = marketing_emails_consent

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        display_name: str,
        marketing_emails_consent: bool,
        terms_accepted_at: dt.datetime,
    ) -> Self:
        return cls(
            user_id=user_id,
            display_name=display_name,
            terms_accepted_at=terms_accepted_at,
            marketing_emails_consent=marketing_emails_consent,
        )

    def update_profile(
        self,
        *,
        display_name: str | None = None,
        marketing_emails_consent: bool | None = None,
    ) -> None:
        """
        Меняет переданные поля профиля; ``None`` — поле не меняется.

        Scenarios:
            - правка имени на странице профиля
            - отказ от рассылки или подписка на неё на странице профиля

        Args:
            display_name: Новое имя, уже обрезанное по краям
            marketing_emails_consent: Согласие на маркетинговые письма
        """
        if display_name is not None:
            self.display_name = display_name

        if marketing_emails_consent is not None:
            self.marketing_emails_consent = marketing_emails_consent

        self._mark_updated()

    def ensure_not_deleted(self) -> None:
        """
        Гарантирует, что пользователь не удалён.

        Scenarios:
            - чтение профиля (приветствие на главной, страница профиля, меню в шапке): удалённый
              пользователь разлогинивается по 410
            - правка профиля на странице профиля

        Raises:
            UserDeletedError: Если пользователь удалён (soft-delete).
        """
        if self.is_deleted:
            raise UserDeletedError()
