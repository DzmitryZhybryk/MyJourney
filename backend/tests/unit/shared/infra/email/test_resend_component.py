"""
Unit-тест lifecycle ``ResendComponent``.

Компонент собирает ``ResendClient`` из настроек и регистрирует его в registry под
ключом-Protocol'ом ``EmailTransportPort`` (доменный код зависит от Protocol, не от
провайдера); shutdown закрывает httpx-пул. Сети нет — httpx-клиент коннектится
только на запрос, а ``aclose`` лишь освобождает пул.
"""

from pydantic import SecretStr

from app.shared.infra.di.registry import ComponentRegistry
from app.shared.infra.email import EmailTransportPort
from app.shared.infra.email.component import ResendComponent
from app.shared.infra.email.resend_client import ResendClient
from app.shared.settings import ResendSettings


async def test_startup_registers_resend_client_and_shutdown_closes_it() -> None:
    """startup регистрирует ``ResendClient`` под ``EmailTransportPort``; shutdown закрывает его без ошибок."""
    component = ResendComponent(
        settings=ResendSettings(RESEND_API_KEY=SecretStr("test-key"), RESEND_FROM_EMAIL="noreply@app.test"),
    )
    registry = ComponentRegistry()

    await component.startup(registry)
    assert isinstance(registry.get(EmailTransportPort), ResendClient)

    await component.shutdown()
