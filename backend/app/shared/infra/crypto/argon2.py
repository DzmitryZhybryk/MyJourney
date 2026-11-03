"""Реализация ``SaltedHasherPort`` через Argon2."""

from functools import cache

from argon2 import PasswordHasher as Argon2Hasher
from argon2.exceptions import VerifyMismatchError


class Argon2SaltedHasher:
    """
    Реализация ``SaltedHasherPort`` через Argon2.

    Argon2 — победитель Password Hashing Competition (PHC), рекомендован
    OWASP для хеширования паролей и других чувствительных секретов.
    """

    def __init__(self) -> None:
        self._hasher = Argon2Hasher()

    def hash(self, secret: str) -> str:
        """
        Хеширует секрет используя Argon2.

        Args:
            secret: Секрет в открытом виде

        Returns:
            Хешированный секрет в формате Argon2
        """
        return self._hasher.hash(secret)

    def verify(self, *, secret: str, hashed: str) -> bool:
        """
        Проверяет соответствие секрета хешу.

        Args:
            secret: Секрет в открытом виде
            hashed: Хешированный секрет

        Returns:
            ``True`` если секрет соответствует хешу. Иначе ``False``.
        """
        try:
            self._hasher.verify(hashed, secret)
        except VerifyMismatchError:
            return False
        else:
            return True


@cache
def get_argon2_salted_hasher() -> Argon2SaltedHasher:
    """
    Возвращает singleton ``Argon2SaltedHasher`` на процесс.

    Hasher stateless и thread-safe, пересоздавать на каждый запрос
    бессмысленно. Тестируемость сохраняется через ``app.dependency_overrides``
    на presentation-обёртке.

    Scenarios:
        - домен, который хранит пароли
    """
    return Argon2SaltedHasher()
