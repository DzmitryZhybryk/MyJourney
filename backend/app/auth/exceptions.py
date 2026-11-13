from typing import ClassVar

from app.shared.exceptions import (
    ConflictError,
    GoneError,
    InvalidInputError,
    NotFoundError,
    RateLimitedError,
    UnauthenticatedError,
)
from app.shared.types import OptionalDict


class TermsNotAcceptedError(InvalidInputError):
    code = "auth.terms_not_accepted"
    message = "Необходимо принять пользовательское соглашение"
    default_details: ClassVar[OptionalDict] = {"field": "terms_accepted"}


class InvalidCredentialsError(UnauthenticatedError):
    code = "auth.invalid_credentials"
    message = "Неверный логин или пароль"


class InvalidRefreshTokenError(UnauthenticatedError):
    code = "auth.invalid_refresh_token"
    message = "Невалидный или истёкший refresh-токен"


class AccountNotFoundError(UnauthenticatedError):
    """Токен валиден, но учётной записи по его ``sub`` нет: токен никого не идентифицирует."""

    code = "auth.account_not_found"
    message = "Учётная запись не найдена"


class EmailAlreadyExistError(ConflictError):
    code = "auth.email_already_registered"
    message = "Пользователь с таким email уже существует"
    default_details: ClassVar[OptionalDict] = {"field": "email"}


class UsernameAlreadyExistError(ConflictError):
    code = "auth.username_already_taken"
    message = "Пользователь с таким username уже существует"
    default_details: ClassVar[OptionalDict] = {"field": "username"}


class EmailAlreadyVerifiedError(ConflictError):
    code = "auth.email_already_verified"
    message = "Email уже подтверждён"


class VerificationCodeInvalidError(InvalidInputError):
    code = "auth.verification_code_invalid"
    message = "Неверный код подтверждения"
    default_details: ClassVar[OptionalDict] = {"field": "code"}


class ChallengeNotFoundError(NotFoundError):
    code = "auth.challenge_not_found"
    message = "Код подтверждения не запрошен или больше недоступен"


class ChallengeExpiredError(GoneError):
    code = "auth.challenge_expired"
    message = "Срок действия кода подтверждения истёк"


class ChallengeAttemptsExceededError(RateLimitedError):
    code = "auth.challenge_attempts_exceeded"
    message = "Превышено количество попыток ввода кода"


class ChallengeResendCooldownError(RateLimitedError):
    code = "auth.challenge_resend_cooldown"
    message = "Слишком частая отправка кода, повторите попытку позже"
