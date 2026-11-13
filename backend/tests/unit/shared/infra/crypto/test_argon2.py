from app.shared.infra.crypto.argon2 import Argon2SaltedHasher


def test_hash_then_verify_roundtrip(argon2_salted_hasher: Argon2SaltedHasher) -> None:
    """verify() истинно для секрета, проверяемого против его же hash()."""
    secret = "correct horse battery staple"

    hashed = argon2_salted_hasher.hash(secret=secret)

    assert argon2_salted_hasher.verify(secret=secret, hashed=hashed) is True


def test_verify_wrong_secret_returns_false(argon2_salted_hasher: Argon2SaltedHasher) -> None:
    """verify() ложно для секрета, не соответствующего hash()."""
    hashed = argon2_salted_hasher.hash(secret="correct-secret")

    assert argon2_salted_hasher.verify(secret="wrong-secret", hashed=hashed) is False


def test_hash_is_salted_unique_per_call(argon2_salted_hasher: Argon2SaltedHasher) -> None:
    """Argon2 солит каждый вызов: один секрет → разные хеши, оба валидны."""
    secret = "same-secret"

    first = argon2_salted_hasher.hash(secret=secret)
    second = argon2_salted_hasher.hash(secret=secret)

    assert first != second
    assert argon2_salted_hasher.verify(secret=secret, hashed=first) is True
    assert argon2_salted_hasher.verify(secret=secret, hashed=second) is True
