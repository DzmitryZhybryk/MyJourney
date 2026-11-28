from uuid import UUID

from app.backoffice.application.ports.unit_of_work import BackofficeUnitOfWorkPort
from app.backoffice.application.schemas.commands import (
    ApplyAccountChangedCommand,
    ApplyProfileChangedCommand,
    ListAccountsCommand,
)
from app.backoffice.application.schemas.results import ListAccountsResult


class AccountService:
    """Сервис строк списка аккаунтов: применяет снимки учётной записи и профиля и отдаёт список админу."""

    def __init__(self, uow: BackofficeUnitOfWorkPort) -> None:
        self._uow = uow

    async def apply_account_changed(self, *, user_id: UUID, command: ApplyAccountChangedCommand) -> None:
        """
        Записывает в строку аккаунта новый снимок учётной записи; снимок не новее записанного пропускается.

        Scenarios:
            - фоновое обновление списка аккаунтов после регистрации или подтверждения email

        Args:
            user_id: Id аккаунта
            command: Снимок учётной записи
        """
        async with self._uow.transaction():
            await self._uow.account_repository.upsert_account_auth_part(user_id=user_id, auth_part=command.auth_part)
            await self._uow.commit()

    async def apply_profile_changed(self, *, user_id: UUID, command: ApplyProfileChangedCommand) -> None:
        """
        Записывает в строку аккаунта новый снимок профиля; снимок не новее записанного пропускается.

        Scenarios:
            - фоновое обновление списка аккаунтов после регистрации или правки профиля

        Args:
            user_id: Id аккаунта
            command: Снимок профиля
        """
        async with self._uow.transaction():
            await self._uow.account_repository.upsert_account_profile_part(
                user_id=user_id,
                profile_part=command.profile_part,
            )
            await self._uow.commit()

    async def list_accounts(self, command: ListAccountsCommand) -> ListAccountsResult:
        """
        Отдаёт страницу списка аккаунтов под фильтром и число всех аккаунтов под ним.

        Scenarios:
            - админский раздел «Аккаунты»: переход по страницам, фильтры по email, имени, роли, согласию на
              рассылку, показ удалённых, смена направления сортировки по дате регистрации

        Args:
            command: Страница, фильтр и направление сортировки

        Returns:
            Аккаунты страницы и их общее число под фильтром
        """
        async with self._uow.transaction():
            accounts_page = await self._uow.account_repository.find_accounts_page(
                page=command.page,
                filters=command.filters,
                sort_direction=command.sort_direction,
            )

        return ListAccountsResult(items=accounts_page.items, total=accounts_page.total)
