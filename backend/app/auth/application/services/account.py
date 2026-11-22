from uuid import UUID

from app.auth.application.ports.unit_of_work import AuthUnitOfWorkPort
from app.auth.application.schemas.commands import FindAccountsByIdsCommand
from app.auth.application.schemas.results import Account, AccountsResult, CurrentAccountResult
from app.auth.exceptions import AccountNotFoundError


class AccountService:
    """Учётная запись: то, по чему пользователь входит в систему."""

    def __init__(self, uow: AuthUnitOfWorkPort) -> None:
        self._uow = uow

    async def get_current_account(self, user_id: UUID) -> CurrentAccountResult:
        """
        Возвращает email, username и статус подтверждения email текущего пользователя.

        Scenarios:
            - username и email на странице профиля и email в меню профиля в шапке

        Args:
            user_id: Идентификатор пользователя из access-токена.

        Returns:
            Данные учётной записи.

        Raises:
            AccountNotFoundError: Если учётной записи с таким ``user_id`` не существует.
        """
        async with self._uow.transaction():
            user_credentials_entity = await self._uow.user_credentials_repository.find_user_credentials_by_user_id(
                user_id
            )
            if user_credentials_entity is None:
                raise AccountNotFoundError()

        return CurrentAccountResult(
            email=user_credentials_entity.email,
            username=user_credentials_entity.username,
            email_verified=user_credentials_entity.is_email_verified,
        )

    async def find_accounts_by_ids(self, command: FindAccountsByIdsCommand) -> AccountsResult:
        """
        Возвращает учётные записи по их id; удалённые тоже возвращаются, с пометкой.

        Read-only use case: транзакция закрывается без ``commit()``.

        Scenarios:
            - подпись аккаунта по его id в админке: кто последним сохранил настройки

        Args:
            command: Id учётных записей.

        Returns:
            Найденные учётные записи; id без записи пропускаются.
        """
        async with self._uow.transaction():
            user_credentials_entities = await self._uow.user_credentials_repository.find_user_credentials_by_user_ids(
                command.user_ids
            )

        return AccountsResult(
            accounts=tuple(
                Account(
                    id=user_credentials_entity.user_id,
                    email=user_credentials_entity.email,
                    is_deleted=user_credentials_entity.is_deleted,
                )
                for user_credentials_entity in user_credentials_entities
            ),
        )
