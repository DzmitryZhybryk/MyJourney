from uuid import UUID

from psycopg.errors import UniqueViolation
from pydantic import BaseModel
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError

from app.shared.infra.db.postgres.repository import BaseDBRepository
from app.shared.versioned_config.exceptions import ConfigVersionConflictError
from app.shared.versioned_config.models import VersionedConfigModel


class BaseVersionedConfigRepository[ModelT: VersionedConfigModel](BaseDBRepository[ModelT]):
    """
    Чтение и запись таблицы конфига домена — одна реализация на все такие таблицы.

    Методы защищённые: наружу доменный репозиторий отдаёт их под именами со своей сущностью.
    """

    async def _find_latest_config(self) -> ModelT | None:
        """
        Находит строку последней версии конфига.

        Scenarios:
            - чтение текущего конфига домена
            - начальное значение при развёртывании: есть ли уже конфиг

        Returns:
            Строка с наибольшей версией; ``None``, если таблица пуста
        """
        query = select(self._model).order_by(self._model.version.desc()).limit(1)
        return await self._fetch_one(query)

    async def _insert_config(self, *, version: int, config: BaseModel, created_by: UUID | None) -> None:
        """
        Вставляет новую версию конфига сразу, а не на commit — чтобы конфликт номера всплыл здесь.

        Единственное ограничение уникальности таблицы — ключ ``version``, поэтому любое нарушение
        уникальности здесь и есть «эту версию уже записали». Транзакция после конфликта прервана:
        вызывающий её откатывает.

        Scenarios:
            - начальное значение конфига домена при развёртывании
            - правка конфига администратором

        Args:
            version: Номер новой версии
            config: Конфиг по схеме домена
            created_by: Аккаунт, правивший конфиг; ``None`` — запись развёртыванием

        Raises:
            ConfigVersionConflictError: Версия с таким номером уже есть
        """
        query = insert(self._model).values({"version": version, "config": config, "created_by": created_by})
        try:
            await self._session.execute(query)
        except IntegrityError as err:
            if isinstance(err.orig, UniqueViolation):
                raise ConfigVersionConflictError() from err

            raise
