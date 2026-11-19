"""
Procrastinate-таски домена auth.

Локальный ``auth_blueprint`` коллекционирует декларации tasks этого домена
без зависимости от конкретного App-инстанса. Composition root собирает
blueprint'ы всех доменов и передаёт их в ``ProcrastinateComponent``,
который через ``add_tasks_from`` подключает их к App-инстансу.

Зависимости-ресурсы (пулы, клиенты) таска достаёт из реестра компонентов воркера — он лежит в
``context.additional_context`` под ``WORKER_REGISTRY_KEY`` — а не через module-level
синглтоны: воркер и API-процесс собирают registry по-разному. Stateless-объекты (шифратор)
берутся из своих ``@cache``-фабрик, как и в API-процессе.
"""

import datetime as dt

from procrastinate import Blueprint, JobContext

from app.auth.application.ports.tasks import SEND_VERIFICATION_EMAIL_TASK
from app.auth.infra.email_renderer import render_verification_email
from app.shared.exceptions import TemporaryError
from app.shared.infra.crypto import get_fernet_secret_cipher
from app.shared.infra.di.registry import ComponentRegistry
from app.shared.infra.email import EmailTransportPort
from app.shared.infra.procrastinate.component import WORKER_REGISTRY_KEY
from app.shared.infra.procrastinate.retry import RetryAfterStrategy
from app.shared.logging import get_logger

auth_blueprint = Blueprint()

logger = get_logger(__name__)


@auth_blueprint.task(
    name=SEND_VERIFICATION_EMAIL_TASK,
    pass_context=True,
    retry=RetryAfterStrategy(
        max_attempts=3,
        wait=10,
        exponential_wait=2,
        retry_exceptions={TemporaryError},
    ),
)
async def send_verification_email(
    context: JobContext,
    *,
    user_id: str,
    email: str,
    code_ciphertext: str,
    expires_at: str,
) -> None:
    """
    Отправляет письмо с одноразовым кодом подтверждения email.

    Временный сбой провайдера (``TemporaryError``) повторяется: до 3 повторов, экспоненциальный backoff
    от 10 сек; если провайдер назвал срок (до 5 мин) — через него. Постоянный падает сразу.
    Если к моменту отправки код истёк (повторы растянули доставку), письмо не уходит: вводить
    такой код бессмысленно.

    Scenarios:
        - фоновая отправка письма с кодом: после регистрации и по кнопке в диалоге «Подтвердите email»

    Args:
        context: Procrastinate JobContext с реестром компонентов воркера в
            ``additional_context``; из реестра берётся ``EmailTransportPort``
        user_id: ID пользователя; используется только для лога и lock'а
            (lock задаётся при defer'е в сервисе, не здесь)
        email: Адрес получателя; в лог не пишется
        code_ciphertext: Шифротекст кода; расшифровывается здесь, в аргументах задачи кода в открытом виде нет
        expires_at: Срок действия кода, ISO-8601 с часовым поясом
    """
    if dt.datetime.fromisoformat(expires_at) <= dt.datetime.now(tz=dt.UTC):
        logger.info("auth.verification_email.skipped_expired", user_id=user_id)
        return

    registry: ComponentRegistry = context.additional_context[WORKER_REGISTRY_KEY]
    transport = registry.get(EmailTransportPort)
    code = get_fernet_secret_cipher().decrypt(ciphertext=code_ciphertext)
    message = render_verification_email(email=email, code=code)
    await transport.send(message=message)
    logger.info("auth.verification_email.sent", user_id=user_id)
