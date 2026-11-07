from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.shared.infra.jwt.dependency import current_user_id_dependency
from app.shared.schemas.missing import none_if_missing
from app.users.application.schemas.commands import UpdateCurrentUserCommand
from app.users.application.services.user import UserService
from app.users.presentation.dependencies import user_service_dependency
from app.users.presentation.responses import GET_CURRENT_USER_RESPONSES, UPDATE_CURRENT_USER_RESPONSES
from app.users.presentation.schemas import CurrentUserResponse, UpdateCurrentUserRequest

users_router = APIRouter()


@users_router.get(
    "/me/",
    response_model=CurrentUserResponse,
    responses=GET_CURRENT_USER_RESPONSES,
)
async def get_current_user(
    *,
    user_id: Annotated[UUID, Depends(current_user_id_dependency)],
    user_service: Annotated[UserService, Depends(user_service_dependency)],
) -> CurrentUserResponse:
    result = await user_service.get_current_user(user_id=user_id)
    return CurrentUserResponse.model_validate(result, from_attributes=True)


@users_router.patch(
    "/me/",
    response_model=CurrentUserResponse,
    responses=UPDATE_CURRENT_USER_RESPONSES,
)
async def update_current_user(
    *,
    request: UpdateCurrentUserRequest,
    user_id: Annotated[UUID, Depends(current_user_id_dependency)],
    user_service: Annotated[UserService, Depends(user_service_dependency)],
) -> CurrentUserResponse:
    command = UpdateCurrentUserCommand(
        display_name=none_if_missing(request.display_name),
        marketing_emails_consent=none_if_missing(request.marketing_emails_consent),
    )
    result = await user_service.update_current_user(user_id=user_id, command=command)
    return CurrentUserResponse.model_validate(result, from_attributes=True)
