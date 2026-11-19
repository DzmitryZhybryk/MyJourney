"""Фейк ``SaltedHasherPort`` без argon2 — детерминированный и быстрый."""

from app.shared.infra.crypto import SaltedHasherPort


class FakeSaltedHasher(SaltedHasherPort):
    """
    Детерминированный фейк: ``hash(secret) == f"hashed::{secret}"``, ``verify`` сравнивает с ним.

    Каждый захешированный секрет записывается в ``hashed_secrets`` — так тест видит хеширование,
    результат которого сервис выбрасывает.
    """

    def __init__(self) -> None:
        self.hashed_secrets: list[str] = []

    def hash(self, secret: str) -> str:
        self.hashed_secrets.append(secret)
        return f"hashed::{secret}"

    def verify(self, *, secret: str, hashed: str) -> bool:
        return hashed == f"hashed::{secret}"
