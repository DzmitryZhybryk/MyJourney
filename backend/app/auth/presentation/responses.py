from typing import Final

from app.auth.exceptions import (
    AccountNotFoundError,
    ChallengeAttemptsExceededError,
    ChallengeExpiredError,
    ChallengeNotFoundError,
    ChallengeResendCooldownError,
    EmailAlreadyExistError,
    EmailAlreadyVerifiedError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    TermsNotAcceptedError,
    UsernameAlreadyExistError,
    VerificationCodeInvalidError,
)
from app.shared.exceptions import InternalError
from app.shared.exceptions.examples import error_response_example
from app.shared.exceptions.schemas import ErrorResponse
from app.shared.infra.jwt import InvalidAccessTokenError
from app.shared.types import DictStrAny

_ATTEMPTS_EXCEEDED_EXAMPLE: Final[DictStrAny] = {
    **error_response_example(ChallengeAttemptsExceededError),
    "details": {"retry_after_seconds": 540},
}

REGISTER_RESPONSES: Final[dict[int | str, DictStrAny]] = {
    400: {
        "description": "Ошибка валидации",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(TermsNotAcceptedError),
            }
        },
    },
    409: {
        "description": "Email или username уже заняты",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "examples": {
                    "auth.email_already_registered": {
                        "summary": "Email уже зарегистрирован",
                        "value": error_response_example(EmailAlreadyExistError),
                    },
                    "auth.username_already_taken": {
                        "summary": "Username уже занят",
                        "value": error_response_example(UsernameAlreadyExistError),
                    },
                },
            }
        },
    },
    500: {
        "description": "Внутренняя ошибка сервера",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(InternalError),
            }
        },
    },
}


LOGIN_RESPONSES: Final[dict[int | str, DictStrAny]] = {
    401: {
        "description": "Неверные учётные данные",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(InvalidCredentialsError),
            }
        },
    },
    500: {
        "description": "Внутренняя ошибка сервера",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(InternalError),
            }
        },
    },
}


LOGOUT_RESPONSES: Final[dict[int | str, DictStrAny]] = {
    500: {
        "description": "Внутренняя ошибка сервера",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(InternalError),
            }
        },
    },
}


REFRESH_RESPONSES: Final[dict[int | str, DictStrAny]] = {
    401: {
        "description": "Невалидный или истёкший refresh-токен",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(InvalidRefreshTokenError),
            }
        },
    },
    500: {
        "description": "Внутренняя ошибка сервера",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(InternalError),
            }
        },
    },
}


_ACCOUNT_UNAUTHENTICATED_RESPONSE: Final[DictStrAny] = {
    "description": "Невалидный или истёкший access-токен, либо учётной записи по токену нет",
    "model": ErrorResponse,
    "content": {
        "application/json": {
            "examples": {
                "auth.invalid_access_token": {
                    "summary": "Невалидный или истёкший access-токен",
                    "value": error_response_example(InvalidAccessTokenError),
                },
                "auth.account_not_found": {
                    "summary": "Учётная запись не найдена",
                    "value": error_response_example(AccountNotFoundError),
                },
            },
        }
    },
}


GET_CURRENT_ACCOUNT_RESPONSES: Final[dict[int | str, DictStrAny]] = {
    401: _ACCOUNT_UNAUTHENTICATED_RESPONSE,
    500: {
        "description": "Внутренняя ошибка сервера",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(InternalError),
            }
        },
    },
}


SEND_EMAIL_VERIFICATION_RESPONSES: Final[dict[int | str, DictStrAny]] = {
    401: _ACCOUNT_UNAUTHENTICATED_RESPONSE,
    409: {
        "description": "Email уже подтверждён",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(EmailAlreadyVerifiedError),
            }
        },
    },
    429: {
        "description": "Cooldown повторной отправки ещё не истёк или попытки ввода живого кода исчерпаны",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "examples": {
                    "auth.challenge_resend_cooldown": {
                        "summary": "Cooldown повторной отправки кода ещё не истёк",
                        "value": error_response_example(ChallengeResendCooldownError),
                    },
                    "auth.challenge_attempts_exceeded": {
                        "summary": "Попытки исчерпаны; новый код — через retry_after_seconds",
                        "value": _ATTEMPTS_EXCEEDED_EXAMPLE,
                    },
                },
            }
        },
    },
    500: {
        "description": "Внутренняя ошибка сервера",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(InternalError),
            }
        },
    },
}


VERIFY_EMAIL_RESPONSES: Final[dict[int | str, DictStrAny]] = {
    400: {
        "description": "Неверный код подтверждения",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(VerificationCodeInvalidError),
            }
        },
    },
    401: _ACCOUNT_UNAUTHENTICATED_RESPONSE,
    404: {
        "description": "Активный challenge отсутствует",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(ChallengeNotFoundError),
            }
        },
    },
    409: {
        "description": "Email уже подтверждён",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(EmailAlreadyVerifiedError),
            }
        },
    },
    410: {
        "description": "Срок действия кода истёк",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(ChallengeExpiredError),
            }
        },
    },
    429: {
        "description": "Превышено количество попыток ввода кода",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": _ATTEMPTS_EXCEEDED_EXAMPLE,
            }
        },
    },
    500: {
        "description": "Внутренняя ошибка сервера",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(InternalError),
            }
        },
    },
}
