from typing import Protocol
from uuid import UUID

from app.auth.domain.entities import ChallengeEntity
from app.auth.domain.enums import ChallengeTypeEnum

__all__ = ["ChallengeRepositoryPort"]


class ChallengeRepositoryPort(Protocol):
    """Контракт хранилища challenge'ей, на который опирается application-слой."""

    async def insert_challenge(self, challenge_entity: ChallengeEntity) -> None:
        """
        Добавляет challenge; у пользователя не бывает двух активных challenge'ей одного типа.

        Scenarios:
            - отправка кода подтверждения email: после регистрации и из диалога «Подтвердите email»

        Args:
            challenge_entity: Новый challenge
        """
        ...

    async def find_active_challenge_for_update(
        self,
        *,
        user_id: UUID,
        challenge_type: ChallengeTypeEnum,
    ) -> ChallengeEntity | None:
        """
        Находит активный challenge пользователя заданного типа и блокирует строку до конца транзакции.

        Scenarios:
            - повторный запрос кода в диалоге «Подтвердите email»: прежний код гасится
            - ввод кода в диалоге «Подтвердите email»

        Args:
            user_id: Владелец challenge'а
            challenge_type: Тип challenge'а

        Returns:
            Challenge; ``None``, если активного нет
        """
        ...

    async def update_challenge_by_id(self, challenge_entity: ChallengeEntity) -> None:
        """
        Записывает изменённое состояние challenge'а.

        Scenarios:
            - повторный запрос кода в диалоге «Подтвердите email»: прежний код гасится
            - ввод кода в диалоге «Подтвердите email»: неверная попытка или верный код

        Args:
            challenge_entity: Challenge с уже изменённым состоянием
        """
        ...
