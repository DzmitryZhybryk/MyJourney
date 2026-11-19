from typing import Final

from procrastinate import Blueprint

from app.auth.infra import auth_blueprint

# Таски всех доменов: один список на API-процесс (он ставит задачи) и воркер (он их исполняет).
TASK_BLUEPRINTS: Final[tuple[Blueprint, ...]] = (auth_blueprint,)
