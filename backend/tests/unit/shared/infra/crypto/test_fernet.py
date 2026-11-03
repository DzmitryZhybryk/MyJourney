import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from app.shared.infra.crypto import UndecryptableSecretError
from app.shared.infra.crypto.fernet import FernetSecretCipher


def test_encrypt_then_decrypt_roundtrip(secret_cipher: FernetSecretCipher) -> None:
    """decrypt() возвращает секрет, зашифрованный encrypt(); в шифротексте его не видно."""
    ciphertext = secret_cipher.encrypt(secret="123456")

    assert "123456" not in ciphertext
    assert secret_cipher.decrypt(ciphertext=ciphertext) == "123456"


def test_encrypt_is_randomized_per_call(secret_cipher: FernetSecretCipher) -> None:
    """Один секрет → разные шифротексты, оба расшифровываются в него же."""
    first = secret_cipher.encrypt(secret="123456")
    second = secret_cipher.encrypt(secret="123456")

    assert first != second
    assert secret_cipher.decrypt(ciphertext=first) == "123456"
    assert secret_cipher.decrypt(ciphertext=second) == "123456"


def test_decrypt_ciphertext_of_another_key_raises(secret_cipher: FernetSecretCipher) -> None:
    """Шифротекст чужого ключа не расшифровывается → UndecryptableSecretError."""
    other_cipher = FernetSecretCipher(key=SecretStr(Fernet.generate_key().decode()))
    ciphertext = other_cipher.encrypt(secret="123456")

    with pytest.raises(UndecryptableSecretError):
        secret_cipher.decrypt(ciphertext=ciphertext)


def test_decrypt_tampered_ciphertext_raises(secret_cipher: FernetSecretCipher) -> None:
    """Испорченный шифротекст не расшифровывается → UndecryptableSecretError."""
    ciphertext = secret_cipher.encrypt(secret="123456")
    middle = len(ciphertext) // 2
    replacement = "B" if ciphertext[middle] == "A" else "A"
    tampered = ciphertext[:middle] + replacement + ciphertext[middle + 1 :]

    with pytest.raises(UndecryptableSecretError):
        secret_cipher.decrypt(ciphertext=tampered)
