from app.shared.exceptions import InvariantViolationError


class InvalidFractionalKeyError(InvariantViolationError):
    """Дробный ключ не соответствует формату ключа порядка."""

    message = "Некорректный дробный ключ"


class FractionalBoundsOrderError(InvariantViolationError):
    """Границы для нового ключа переданы не по возрастанию."""

    message = "Границы дробного ключа не по возрастанию"
