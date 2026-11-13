from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from pydantic import SecretStr

from app.auth.application.schemas.commands import LoginCommand, RegistrationCommand, VerifyEmailCommand
from app.auth.application.schemas.metadata import ClientMetadata
from app.auth.application.services.account import AccountService
from app.auth.application.services.auth import AuthService
from app.auth.application.services.email_verification import EmailVerificationService
from app.auth.presentation.cookies import clear_refresh_token_cookie, set_refresh_token_cookie
from app.auth.presentation.dependencies import (
    account_service_dependency,
    auth_service_dependency,
    client_metadata_dependency,
    email_verification_service_dependency,
    optional_refresh_secret_dependency,
    required_refresh_secret_dependency,
)
from app.auth.presentation.responses import (
    GET_CURRENT_ACCOUNT_RESPONSES,
    LOGIN_RESPONSES,
    LOGOUT_RESPONSES,
    REFRESH_RESPONSES,
    REGISTER_RESPONSES,
    SEND_EMAIL_VERIFICATION_RESPONSES,
    VERIFY_EMAIL_RESPONSES,
)
from app.auth.presentation.schemas import (
    CurrentAccountResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.shared.infra.jwt.dependency import current_user_id_dependency

auth_router = APIRouter()


@auth_router.post(
    "/register/",
    status_code=status.HTTP_201_CREATED,
    response_model=TokenResponse,
    responses=REGISTER_RESPONSES,
)
async def register(
    *,
    response: Response,
    body: RegisterRequest,
    client_metadata: Annotated[ClientMetadata, Depends(client_metadata_dependency)],
    auth_service: Annotated[AuthService, Depends(auth_service_dependency)],
) -> TokenResponse:
    command = RegistrationCommand(
        username=body.username,
        email=body.email,
        password=body.password,
        marketing_emails_consent=body.marketing_emails_consent,
    )
    token_pair = await auth_service.register(command=command, client_metadata=client_metadata)
    set_refresh_token_cookie(response=response, token_pair=token_pair)
    return TokenResponse(access_token=token_pair.access_token.get_secret_value())


@auth_router.post(
    "/login/",
    status_code=status.HTTP_200_OK,
    response_model=TokenResponse,
    responses=LOGIN_RESPONSES,
)
async def login(
    *,
    response: Response,
    body: LoginRequest,
    client_metadata: Annotated[ClientMetadata, Depends(client_metadata_dependency)],
    auth_service: Annotated[AuthService, Depends(auth_service_dependency)],
) -> TokenResponse:
    command = LoginCommand(login=body.login, password=body.password)
    token_pair = await auth_service.login(command=command, client_metadata=client_metadata)
    set_refresh_token_cookie(response=response, token_pair=token_pair)
    return TokenResponse(access_token=token_pair.access_token.get_secret_value())


@auth_router.post(
    "/logout/",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=LOGOUT_RESPONSES,
)
async def logout(
    *,
    response: Response,
    refresh_secret: Annotated[str | None, Depends(optional_refresh_secret_dependency)],
    auth_service: Annotated[AuthService, Depends(auth_service_dependency)],
) -> None:
    await auth_service.logout(refresh_secret=refresh_secret)
    clear_refresh_token_cookie(response=response)


@auth_router.post(
    "/refresh/",
    status_code=status.HTTP_200_OK,
    response_model=TokenResponse,
    responses=REFRESH_RESPONSES,
)
async def refresh(
    *,
    response: Response,
    refresh_secret: Annotated[str, Depends(required_refresh_secret_dependency)],
    client_metadata: Annotated[ClientMetadata, Depends(client_metadata_dependency)],
    auth_service: Annotated[AuthService, Depends(auth_service_dependency)],
) -> TokenResponse:
    token_pair = await auth_service.refresh(refresh_secret=refresh_secret, client_metadata=client_metadata)
    set_refresh_token_cookie(response=response, token_pair=token_pair)
    return TokenResponse(access_token=token_pair.access_token.get_secret_value())


@auth_router.get(
    "/me/",
    response_model=CurrentAccountResponse,
    responses=GET_CURRENT_ACCOUNT_RESPONSES,
)
async def get_current_account(
    *,
    user_id: Annotated[UUID, Depends(current_user_id_dependency)],
    account_service: Annotated[AccountService, Depends(account_service_dependency)],
) -> CurrentAccountResponse:
    result = await account_service.get_current_account(user_id=user_id)
    return CurrentAccountResponse.model_validate(result, from_attributes=True)


@auth_router.post(
    "/email/send-verification/",
    status_code=status.HTTP_202_ACCEPTED,
    responses=SEND_EMAIL_VERIFICATION_RESPONSES,
)
async def send_email_verification(
    *,
    user_id: Annotated[UUID, Depends(current_user_id_dependency)],
    email_verification_service: Annotated[EmailVerificationService, Depends(email_verification_service_dependency)],
) -> Response:
    await email_verification_service.request_email_verification(user_id=user_id)
    # Явно пустое тело: 202 = «принято в асинхронную обработку» (письмо ставится в
    # очередь воркеру), клиенту нечего возвращать. Без этого FastAPI сериализовал бы
    # None в JSON `null` — не пустой, но и бессмысленный payload.
    return Response(status_code=status.HTTP_202_ACCEPTED)


@auth_router.post(
    "/email/verify/",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=VERIFY_EMAIL_RESPONSES,
)
async def verify_email(
    *,
    body: VerifyEmailRequest,
    user_id: Annotated[UUID, Depends(current_user_id_dependency)],
    email_verification_service: Annotated[EmailVerificationService, Depends(email_verification_service_dependency)],
) -> None:
    await email_verification_service.verify_email(
        user_id=user_id, command=VerifyEmailCommand(code=SecretStr(body.code))
    )
