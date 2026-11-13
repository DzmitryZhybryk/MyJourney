class Password:
    """Value Object для пароля пользователя."""

    def __init__(self, hash: str) -> None:
        """
        Создаёт Value Object из готового argon2-хеша.

        Хеширование raw-пароля — ответственность application-слоя: он вызывает
        ``SaltedHasherPort.hash`` и передаёт сюда уже готовое значение. Так домен
        не зависит от инфраструктурного протокола хеширования.

        Args:
            hash: Готовый argon2-хеш пароля
        """
        self._hash = hash

    @property
    def hash(self) -> str:
        """
        Возвращает хеш пароля для сохранения в БД.

        Scenarios:
            - регистрация: хеш сохраняется
            - вход: введённый пароль сверяется с хешем

        Returns:
            Argon2-хеш пароля
        """
        return self._hash
