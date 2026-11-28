from app.shared.exceptions import GoneError, NotFoundError


class UserNotFoundError(NotFoundError):
    code = "users.user_not_found"
    message = "Пользователь не найден"


class UserDeletedError(GoneError):
    code = "users.user_deleted"
    message = "Пользователь удалён"
