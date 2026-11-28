from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager

from app.shared.infra.di.base import BaseComponent
from app.shared.infra.di.registry import ComponentRegistry
from app.shared.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def run_components(
    *,
    components: Sequence[BaseComponent],
    registry: ComponentRegistry,
) -> AsyncGenerator[None]:
    """
    Поднимает компоненты по порядку и гарантированно останавливает поднятые — в обратном.

    Обратный порядок — потому что компонент читает нужное ему из реестра в своём ``startup``:
    остановка в прямом порядке отняла бы ресурс у того, кто им ещё пользуется. Если ``startup``
    очередного компонента падает (или старт отменён), останавливаются только уже поднятые, а
    исходная ошибка летит дальше. Упавший компонент сам освобождает то, что успел открыть.
    Сбой старта пишется в лог с именем компонента — трейсбек сам по себе его не называет.

    Scenarios:
        - старт и остановка API-процесса
        - старт и остановка воркера фоновых задач
        - разовый CLI-шаг, которому нужен компонент на время работы

    Args:
        components: Компоненты в порядке зависимостей: тот, кого читают из реестра, раньше читающего
        registry: Реестр, в который компоненты публикуют свои ресурсы

    Raises:
        Exception: Первая ошибка ``shutdown``, если тело и старт завершились без ошибки
    """
    started: list[BaseComponent] = []
    try:
        for component in components:
            try:
                await component.startup(registry)
            except Exception:
                logger.exception("component.startup_failed", component=type(component).__name__)
                raise

            started.append(component)

        yield
    except BaseException:
        # Исходная ошибка важнее ошибок остановки: они только логируются.
        await _shutdown_in_reverse(started)
        raise

    shutdown_errors = await _shutdown_in_reverse(started)
    if shutdown_errors:
        raise shutdown_errors[0]


async def _shutdown_in_reverse(started: Sequence[BaseComponent]) -> tuple[Exception, ...]:
    """
    Останавливает компоненты в обратном порядке; сбой одного не отменяет остановку остальных.

    Каждый сбой логируется здесь с именем компонента — трейсбек сам по себе его не называет.

    Scenarios:
        - остановка процесса: штатная и после упавшего старта

    Args:
        started: Успешно поднятые компоненты в порядке старта

    Returns:
        Ошибки ``shutdown`` в порядке, в котором они случились
    """
    errors: list[Exception] = []
    for component in reversed(started):
        try:
            await component.shutdown()
        except Exception as exc:
            logger.exception("component.shutdown_failed", component=type(component).__name__)
            errors.append(exc)

    return tuple(errors)
