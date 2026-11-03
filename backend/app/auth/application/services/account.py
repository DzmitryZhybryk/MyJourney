from uuid import UUID

from app.auth.application.ports.unit_of_work import AuthUnitOfWorkPort
from app.auth.application.schemas.results import CurrentAccountResult
from app.auth.exceptions import AccountNotFoundError


class AccountService:
    """Учётная запись: то, по чему пользователь входит в систему."""

    def __init__(self, uow: AuthUnitOfWorkPort) -> None:
        self._uow = uow

    async def get_current_account(self, *, user_id: UUID) -> CurrentAccountResult:
        """
        Возвращает email, username и статус подтверждения email текущего пользователя.

        Scenarios:
            - данные входа текущего пользователя; фронт их пока не запрашивает

        Args:
            user_id: Идентификатор пользователя из access-токена.

        Returns:
            Данные учётной записи.

        Raises:
            AccountNotFoundError: Если учётной записи с таким ``user_id`` не существует.
        """
        async with self._uow.transaction():
            user_credentials_entity = await self._uow.user_credentials_repository.find_user_credentials_by_user_id(
                user_id=user_id
            )
            if user_credentials_entity is None:
                raise AccountNotFoundError()

        return CurrentAccountResult(
            email=user_credentials_entity.email,
            username=user_credentials_entity.username,
            email_verified=user_credentials_entity.is_email_verified,
        )
