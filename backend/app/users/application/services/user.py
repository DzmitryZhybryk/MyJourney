from uuid import UUID

from app.users.application.ports.unit_of_work import UserUnitOfWorkPort
from app.users.application.schemas.commands import CreateUserCommand, UpdateCurrentUserCommand
from app.users.application.schemas.results import CurrentUserResult
from app.users.domain.entities import UserEntity
from app.users.exceptions import UserNotFoundError


class UserService:
    """Сервис управления пользователями."""

    def __init__(self, uow: UserUnitOfWorkPort) -> None:
        self._uow = uow

    async def create_user(self, command: CreateUserCommand) -> None:
        """
        Создаёт нового пользователя в рамках транзакции вызывающего.

        НЕ коммитит: ``create_user`` — cross-domain участник use-case'а, чьей
        входной точкой владеет вызывающий (``AuthService.register``). Запись
        кладётся в общую сессию и фиксируется единственным ``commit()`` вызывающего —
        атомарно вместе с ``user_credentials`` и refresh-токеном. Любой сбой до
        этого commit'а откатывает всё, осиротевшей учётки не остаётся
        (Option A транзакционной модели, см. ``BaseUnitOfWork``).

        Scenarios:
            - регистрация: профиль создаётся в транзакции вызывающего домена

        Args:
            command: Данные для создания пользователя.
        """
        user_entity = UserEntity.create(
            user_id=command.user_id,
            display_name=command.display_name,
            marketing_emails_consent=command.marketing_emails_consent,
            terms_accepted_at=command.terms_accepted_at,
        )
        await self._uow.user_repository.insert_user(user_entity=user_entity)

    async def get_current_user(self, user_id: UUID) -> CurrentUserResult:
        """
        Возвращает профиль текущего пользователя.

        Read-only use case: транзакция закрывается без ``commit()``, rollback-by-default
        ничего не откатывает.

        Scenarios:
            - чтение профиля: приветствие на главной, страница профиля, меню в шапке

        Args:
            user_id: Идентификатор пользователя из access-токена.

        Returns:
            Профиль пользователя.

        Raises:
            UserNotFoundError: Если пользователь не найден.
            UserDeletedError: Если пользователь удалён (soft-delete).
        """
        async with self._uow.transaction():
            user_entity = await self._uow.user_repository.find_user_by_id(user_id=user_id)
            if user_entity is None:
                raise UserNotFoundError()

            user_entity.ensure_not_deleted()

        return CurrentUserResult(
            display_name=user_entity.display_name,
            marketing_emails_consent=user_entity.marketing_emails_consent,
        )

    async def update_current_user(self, *, user_id: UUID, command: UpdateCurrentUserCommand) -> CurrentUserResult:
        """
        Меняет переданные поля профиля текущего пользователя.

        Scenarios:
            - правка имени на странице профиля
            - отказ от рассылки или подписка на неё на странице профиля

        Args:
            user_id: Идентификатор пользователя из access-токена.
            command: Новые значения полей; ``None`` — поле не меняется.

        Returns:
            Обновлённый профиль.

        Raises:
            UserNotFoundError: Если пользователь не найден.
            UserDeletedError: Если пользователь удалён (soft-delete).
        """
        async with self._uow.transaction():
            user_entity = await self._uow.user_repository.find_user_by_id_for_update(user_id=user_id)
            if user_entity is None:
                raise UserNotFoundError()

            user_entity.ensure_not_deleted()
            user_entity.update_profile(
                display_name=command.display_name,
                marketing_emails_consent=command.marketing_emails_consent,
            )
            await self._uow.user_repository.update_user_by_id(user_entity=user_entity)
            await self._uow.commit()

        return CurrentUserResult(
            display_name=user_entity.display_name,
            marketing_emails_consent=user_entity.marketing_emails_consent,
        )
