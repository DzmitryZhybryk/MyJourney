from app.shared.exceptions import InvalidInputError


class InvalidCursorError(InvalidInputError):
    """Курсор страницы не удалось разобрать: он испорчен или выдан не этим списком."""

    code = "invalid_cursor"
    message = "Некорректный курсор страницы"
