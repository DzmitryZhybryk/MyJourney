from app.auth.domain.value_objects import Password


def test_hash_returns_given_hash() -> None:
    """Отдаёт хеш, переданный в конструктор."""
    password = Password("argon2$abc")
    assert password.hash == "argon2$abc"
