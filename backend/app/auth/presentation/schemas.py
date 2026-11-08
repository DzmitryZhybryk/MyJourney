from typing import Annotated, Self

from pydantic import ConfigDict, EmailStr, Field, SecretStr, StringConstraints, model_validator

from app.auth.exceptions import TermsNotAcceptedError
from app.shared.schemas.base import CamelModel


class RegisterRequest(CamelModel):
    username: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$"),
    ]
    email: Annotated[EmailStr, Field(max_length=254)]
    password: Annotated[SecretStr, Field(min_length=8, max_length=50)]
    terms_accepted: bool
    marketing_emails_consent: bool

    @model_validator(mode="after")
    def validate_terms(self) -> Self:
        """
        Проверяет, что пользователь принял условия использования.

        Запускается на границе HTTP-слоя сразу после парсинга тела запроса.
        Если флаг не выставлен, регистрация останавливается ещё до выхода в
        application-слой. Момент принятия условий — время создания учётной
        записи, его берёт сервис регистрации.

        Pydantic v2 оборачивает в ``ValidationError`` только ``ValueError``/
        ``AssertionError``/``PydanticCustomError``; ``TermsNotAcceptedError``
        (наследник ``AppError`` с категорией ``INVALID_INPUT``)
        пробрасывается наружу как есть и ловится глобальным exception handler'ом →
        HTTP 400 с правильным ``code`` по категории, а не 422 от FastAPI.

        Scenarios:
            - регистрация

        Returns:
            Сам валидируемый объект (контракт ``model_validator(mode="after")``)

        Raises:
            TermsNotAcceptedError: Если ``terms_accepted`` равен ``False``
        """
        if not self.terms_accepted:
            raise TermsNotAcceptedError()

        return self


class LoginRequest(CamelModel):
    # На login пароль/логин на длину/политику не валидируем — проверяем лишь, что
    # они непустые и в пределах max. Иначе юзер со «старым» коротким паролем
    # залочится на входе; неверные креды и так дадут 401, а не 422.
    # Пробелы по краям срезаются, как у username на регистрации: иначе « neo» не найдёт «neo».
    login: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=254, pattern=r"^[^\x00-\x1F\x7F-\x9F]*$"),
    ]
    password: Annotated[SecretStr, Field(min_length=1, max_length=50)]


class TokenResponse(CamelModel):
    model_config = ConfigDict(frozen=True)

    access_token: str
    token_type: str = "bearer"  # noqa: S105


class CurrentAccountResponse(CamelModel):
    model_config = ConfigDict(frozen=True)

    email: str
    username: str
    email_verified: bool


class VerifyEmailRequest(CamelModel):
    code: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\d{6}$")]
