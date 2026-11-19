"""Реализация ``DeterministicHasherPort`` через SHA-256."""

import hashlib
from functools import cache


class Sha256DeterministicHasher:
    """
    Реализация ``DeterministicHasherPort`` через SHA-256.

    Возвращает hex-представление SHA-256 от UTF-8 байт plaintext'а:
    один и тот же вход всегда даёт один и тот же 64-символьный hex,
    что и нужно для index lookup'а в БД.
    """

    def digest(self, secret: str) -> str:
        """
        Считает SHA-256 от plaintext'а и возвращает hex-строку.

        Args:
            secret: Plaintext в открытом виде

        Returns:
            64-символьная hex-строка SHA-256-дайджеста
        """
        return hashlib.sha256(secret.encode()).hexdigest()


@cache
def get_sha256_deterministic_hasher() -> Sha256DeterministicHasher:
    """
    Возвращает singleton ``Sha256DeterministicHasher`` на процесс.

    Hasher не имеет состояния, плодить инстансы бессмысленно. Тестируемость
    сохраняется через ``app.dependency_overrides`` на presentation-обёртке.

    Scenarios:
        - домен, который ищет запись по секрету от клиента
    """
    return Sha256DeterministicHasher()
