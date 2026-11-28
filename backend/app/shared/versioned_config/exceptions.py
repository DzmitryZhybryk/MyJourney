from app.shared.exceptions.base import ConflictError, InvariantViolationError


class ConfigMissingError(InvariantViolationError):
    """В таблице конфига домена нет ни одной версии: начальное значение не записано при развёртывании."""

    message = "Нет ни одной версии конфига — запустите запись начального значения"


class ConfigVersionConflictError(ConflictError):
    """Версию конфига с таким номером уже записали: конфиг изменили, пока его правили."""

    code = "config_version_conflict"
    message = "Конфиг уже изменили — перечитайте его"
