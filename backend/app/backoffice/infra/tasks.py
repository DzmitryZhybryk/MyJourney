"""
Procrastinate-таски модуля backoffice: применение событий других модулей к строкам списка аккаунтов.

Задачи ставит издатель событий по таблице подписок composition root'а, а не use case этого модуля: таблица
берёт имя у самой задачи, поэтому отдельных констант имён нет. Сессию БД таска открывает сама из
``SessionMaker`` реестра воркера — на один запуск.
"""

from procrastinate import Blueprint, JobContext, RetryStrategy

from app.backoffice.application.ports.account_repository import AccountAuthPart, AccountProfilePart
from app.backoffice.application.schemas.commands import ApplyAccountChangedCommand, ApplyProfileChangedCommand
from app.backoffice.application.services.account import AccountService
from app.backoffice.infra.uow import BackofficeUnitOfWork
from app.shared.events import AccountChangedEvent, ProfileChangedEvent
from app.shared.infra.db.postgres.component import SessionMaker
from app.shared.infra.di.registry import ComponentRegistry
from app.shared.infra.procrastinate.component import WORKER_REGISTRY_KEY
from app.shared.types import DictStrAny

backoffice_blueprint = Blueprint()


@backoffice_blueprint.task(
    name="backoffice.apply_account_changed",
    pass_context=True,
    retry=RetryStrategy(max_attempts=3, wait=10, exponential_wait=2),
)
async def apply_account_changed(context: JobContext, *, event: DictStrAny) -> None:
    """
    Применяет снимок учётной записи к строке списка аккаунтов.

    Любой сбой повторяется: до 3 повторов, экспоненциальный backoff от 10 сек. Повтор безопасен — снимок
    не новее записанного не применяется.

    Scenarios:
        - фоновое обновление списка аккаунтов после регистрации или подтверждения email

    Args:
        context: Procrastinate JobContext с реестром компонентов воркера в ``additional_context``
        event: ``AccountChangedEvent`` в JSON
    """
    account_changed_event = AccountChangedEvent.model_validate(event)
    command = ApplyAccountChangedCommand(
        auth_part=AccountAuthPart(
            email=account_changed_event.email,
            username=account_changed_event.username,
            role=account_changed_event.role,
            plan=account_changed_event.plan,
            email_verified_at=account_changed_event.email_verified_at,
            registered_at=account_changed_event.registered_at,
            deleted_at=account_changed_event.deleted_at,
            version=account_changed_event.version,
        ),
    )
    registry: ComponentRegistry = context.additional_context[WORKER_REGISTRY_KEY]
    async with registry.get(SessionMaker)() as session:
        account_service = AccountService(BackofficeUnitOfWork(session))
        await account_service.apply_account_changed(user_id=account_changed_event.user_id, command=command)


@backoffice_blueprint.task(
    name="backoffice.apply_profile_changed",
    pass_context=True,
    retry=RetryStrategy(max_attempts=3, wait=10, exponential_wait=2),
)
async def apply_profile_changed(context: JobContext, *, event: DictStrAny) -> None:
    """
    Применяет снимок профиля к строке списка аккаунтов.

    Любой сбой повторяется: до 3 повторов, экспоненциальный backoff от 10 сек. Повтор безопасен — снимок
    не новее записанного не применяется.

    Scenarios:
        - фоновое обновление списка аккаунтов после регистрации или правки профиля

    Args:
        context: Procrastinate JobContext с реестром компонентов воркера в ``additional_context``
        event: ``ProfileChangedEvent`` в JSON
    """
    profile_changed_event = ProfileChangedEvent.model_validate(event)
    command = ApplyProfileChangedCommand(
        profile_part=AccountProfilePart(
            display_name=profile_changed_event.display_name,
            marketing_emails_consent=profile_changed_event.marketing_emails_consent,
            terms_accepted_at=profile_changed_event.terms_accepted_at,
            version=profile_changed_event.version,
        ),
    )
    registry: ComponentRegistry = context.additional_context[WORKER_REGISTRY_KEY]
    async with registry.get(SessionMaker)() as session:
        account_service = AccountService(BackofficeUnitOfWork(session))
        await account_service.apply_profile_changed(user_id=profile_changed_event.user_id, command=command)
