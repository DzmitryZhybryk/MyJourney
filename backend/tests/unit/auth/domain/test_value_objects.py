from app.auth.domain.value_objects import Password


def test_password_exposes_hash() -> None:
    """`Password.hash` возвращает переданный в конструктор хеш."""
    password = Password("argon2$abc")
    assert password.hash == "argon2$abc"
