import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr, ValidationError

from app.shared.settings import ChallengeSettings, JWTSettings, PostgresSettings


def test_postgres_settings_password_hidden_in_repr_but_present_in_dsn() -> None:
    """Пароль БД не попадает в repr, но развёрнут в обоих DSN."""
    postgres_settings = PostgresSettings(
        POSTGRES_USER="user",
        POSTGRES_PASSWORD=SecretStr("s3cret-pw"),
        POSTGRES_DB="db",
    )

    assert "s3cret-pw" not in repr(postgres_settings)
    assert postgres_settings.postgres_dsn == "postgresql+psycopg://user:s3cret-pw@localhost:5432/db"
    assert postgres_settings.postgres_libpq_dsn == "postgresql://user:s3cret-pw@localhost:5432/db"


def test_jwt_settings_secret_key_hidden_in_repr() -> None:
    """Ключ подписи JWT не попадает в repr настроек."""
    jwt_settings = JWTSettings(JWT_SECRET_KEY=SecretStr("signing-key"))

    assert "signing-key" not in repr(jwt_settings)


def test_challenge_settings_accepts_fernet_key_and_hides_it_in_repr() -> None:
    """Валидный ключ Fernet принимается и не попадает в repr настроек."""
    key = Fernet.generate_key().decode()

    challenge_settings = ChallengeSettings(CHALLENGE_CODE_ENCRYPTION_KEY=SecretStr(key))

    assert challenge_settings.CHALLENGE_CODE_ENCRYPTION_KEY.get_secret_value() == key
    assert key not in repr(challenge_settings)


@pytest.mark.parametrize("key", ["", "not-a-fernet-key", "c2hvcnQ="])
def test_challenge_settings_rejects_malformed_key(key: str) -> None:
    """Ключ не формата Fernet (пустой, не base64, не 32 байта) останавливает сборку настроек."""
    with pytest.raises(ValidationError, match="CHALLENGE_CODE_ENCRYPTION_KEY должен быть ключом Fernet"):
        ChallengeSettings(CHALLENGE_CODE_ENCRYPTION_KEY=SecretStr(key))
