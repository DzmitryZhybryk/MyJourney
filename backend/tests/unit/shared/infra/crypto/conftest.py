"""Фикстуры crypto-инфраструктуры: реальный Argon2-hasher для roundtrip-тестов."""

import pytest

from app.shared.infra.crypto.argon2 import Argon2SaltedHasher


@pytest.fixture
def argon2_salted_hasher() -> Argon2SaltedHasher:
    return Argon2SaltedHasher()
