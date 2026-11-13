"""Реализация ``SecretCipherPort`` через Fernet."""

from functools import cache

from cryptography.fernet import Fernet, InvalidToken
from pydantic import SecretStr

from app.shared.infra.crypto.exceptions import UndecryptableSecretError
from app.shared.settings import settings


class FernetSecretCipher:
    """
    Реализация ``SecretCipherPort`` через Fernet из ``cryptography``.

    Fernet — готовый рецепт аутентифицированного шифрования (AES-128-CBC + HMAC-SHA256): нонс
    генерируется сам, подделанный или чужой шифротекст не расшифровывается.
    """

    def __init__(self, key: SecretStr) -> None:
        self._fernet = Fernet(key.get_secret_value())

    def encrypt(self, secret: str) -> str:
        """
        Шифрует секрет ключом Fernet.

        Args:
            secret: Секрет в открытом виде

        Returns:
            Fernet-токен (url-safe base64)
        """
        return self._fernet.encrypt(secret.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """
        Расшифровывает Fernet-токен.

        Args:
            ciphertext: Fernet-токен из ``encrypt``

        Returns:
            Секрет в открытом виде

        Raises:
            UndecryptableSecretError: Токен испорчен или зашифрован другим ключом
        """
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as error:
            raise UndecryptableSecretError() from error


@cache
def get_fernet_secret_cipher() -> FernetSecretCipher:
    """
    Возвращает singleton ``FernetSecretCipher`` на процесс с ключом из настроек.

    Scenarios:
        - домен, который хранит одноразовые коды и отправляет их в письме
    """
    return FernetSecretCipher(key=settings.CHALLENGE_CODE_ENCRYPTION_KEY)
