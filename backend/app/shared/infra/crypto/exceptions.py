"""Исключения шифрования секретов."""

from app.shared.exceptions.base import InvariantViolationError


class UndecryptableSecretError(InvariantViolationError):
    """Шифротекст не расшифровывается текущим ключом: он испорчен или ключ сменили без ротации."""

    message = "Шифротекст не расшифровывается текущим ключом"
