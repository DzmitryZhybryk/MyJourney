from functools import cache
from pathlib import Path
from typing import Final

from cryptography.fernet import Fernet
from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.shared.enums import AppEnvEnum
from app.shared.types import DictStrAny

_APP_DIR: Final[Path] = Path(__file__).resolve().parent
_ROOT_DIR: Final[Path] = _APP_DIR.parent.parent


class PostgresSettings(BaseModel):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_POOL_PRE_PING: bool = True  # ВКЛЮЧЕНО: Проверка соединений перед использованием
    POSTGRES_POOL_RECYCLE: int = 3600  # Переустановка соединений старше 1 часа
    POSTGRES_POOL_TIMEOUT: int = 30
    POSTGRES_POOL_SIZE: int = 5
    POSTGRES_MAX_OVERFLOW: int = 10
    POSTGRES_ISOLATION_LEVEL: str = "READ COMMITTED"
    POSTGRES_ECHO: bool = False
    POSTGRES_CONNECTION_TIMEOUT: int = 5  # Таймаут для установки нового соединения
    POSTGRES_STATEMENT_TIMEOUT_MS: int = 10_000  # statement_timeout сервера в миллисекундах

    @property
    def postgres_dsn(self) -> str:
        """
        Собирает SQLAlchemy DSN.

        Драйвер — psycopg3 (async). Выбран сознательно вместо asyncpg, чтобы
        procrastinate.PsycopgConnector мог делить connection с SQLAlchemy
        для атомарного defer_async() в одной транзакции.

        Scenarios:
            - подключение приложения, воркера и миграций к базе
        """
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD.get_secret_value()}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def postgres_libpq_dsn(self) -> str:
        """
        Plain libpq DSN (без +driver-префикса) для прямых psycopg-соединений мимо SQLAlchemy.

        Scenarios:
            - очередь фоновых задач
            - массовая загрузка справочных данных в базу
        """
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD.get_secret_value()}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def engine_kwargs(self) -> DictStrAny:
        return {
            "pool_size": self.POSTGRES_POOL_SIZE,
            "max_overflow": self.POSTGRES_MAX_OVERFLOW,
            "echo": self.POSTGRES_ECHO,
            "pool_pre_ping": self.POSTGRES_POOL_PRE_PING,
            "pool_recycle": self.POSTGRES_POOL_RECYCLE,
            "pool_timeout": self.POSTGRES_POOL_TIMEOUT,
            "isolation_level": self.POSTGRES_ISOLATION_LEVEL,
            "connect_args": {
                "connect_timeout": self.POSTGRES_CONNECTION_TIMEOUT,
                "options": f"-c statement_timeout={self.POSTGRES_STATEMENT_TIMEOUT_MS}",
            },
        }

    @property
    def sessionmaker_kwargs(self) -> DictStrAny:
        return {"expire_on_commit": False}


class WebSettings(BaseModel):
    PORT: int
    HOST: str
    ENVIRONMENT: AppEnvEnum
    RELOAD: bool = False


class JWTSettings(BaseModel):
    JWT_SECRET_KEY: SecretStr
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30


class ResendSettings(BaseModel):
    RESEND_API_KEY: SecretStr
    RESEND_FROM_EMAIL: str
    RESEND_BASE_URL: str = "https://api.resend.com"
    RESEND_TIMEOUT_SECONDS: float = 10.0


class EmailVerificationSettings(BaseModel):
    EMAIL_VERIFICATION_TTL_MINUTES: int = 15
    EMAIL_VERIFICATION_MAX_ATTEMPTS: int = 5
    EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS: int = 60


class ChallengeSettings(BaseModel):
    CHALLENGE_CODE_ENCRYPTION_KEY: SecretStr

    @field_validator("CHALLENGE_CODE_ENCRYPTION_KEY")
    @classmethod
    def _ensure_fernet_key(cls, value: SecretStr) -> SecretStr:
        """
        Проверяет, что ключ шифрования одноразовых кодов — валидный ключ Fernet.

        Scenarios:
            - запуск API и воркера: неверный ключ останавливает старт, а не первую отправку кода

        Args:
            value: Ключ из окружения

        Returns:
            Тот же ключ

        Raises:
            ValueError: Ключ не 32 байта в url-safe base64
        """
        try:
            Fernet(value.get_secret_value())
        except ValueError as error:
            message = "CHALLENGE_CODE_ENCRYPTION_KEY должен быть ключом Fernet: 32 байта в url-safe base64"
            raise ValueError(message) from error

        return value


class GeoDatasetsSettings(BaseModel):
    GEO_DATASETS_CACHE_DIR: Path = _ROOT_DIR / ".geo-cache"


class MediaStorageSettings(BaseModel):
    MEDIA_S3_ENDPOINT_URL: str
    MEDIA_S3_ACCESS_KEY_ID: SecretStr
    MEDIA_S3_SECRET_ACCESS_KEY: SecretStr
    MEDIA_S3_REGION: str = "auto"
    MEDIA_S3_PRIVATE_BUCKET: str = Field(default="media-private", min_length=3, max_length=63)
    MEDIA_S3_PUBLIC_BUCKET: str = Field(default="media-public", min_length=3, max_length=63)
    MEDIA_S3_MAX_ATTEMPTS: int = 3
    MEDIA_S3_CONNECT_TIMEOUT_SECONDS: float = 5.0
    MEDIA_S3_READ_TIMEOUT_SECONDS: float = 30.0


class ProcrastinateSettings(PostgresSettings):
    """
    Procrastinate шарит БД с приложением — наследует PG-конфиг для DSN.

    Procrastinate-специфичны только пул и concurrency; connection info
    приходит через ``postgres_libpq_dsn`` из ``PostgresSettings``.
    """

    PROCRASTINATE_POOL_MIN_SIZE: int = 2
    PROCRASTINATE_POOL_MAX_SIZE: int = 5
    PROCRASTINATE_WORKER_CONCURRENCY: int = 10


class Settings(
    BaseSettings,
    WebSettings,
    JWTSettings,
    ResendSettings,
    EmailVerificationSettings,
    ChallengeSettings,
    GeoDatasetsSettings,
    MediaStorageSettings,
    ProcrastinateSettings,
):
    model_config = SettingsConfigDict(frozen=True, env_file=".env", extra="ignore")


@cache
def get_app_settings() -> Settings:
    """
    Возвращает настройки приложения, один экземпляр на процесс.

    Scenarios:
        - запуск API, воркера, миграций и CLI-скриптов
    """
    return Settings()


settings = get_app_settings()
