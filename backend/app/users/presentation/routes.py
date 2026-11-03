from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.shared.infra.jwt.dependency import current_user_id_dependency
from app.users.application.services.user import UserService
from app.users.presentation.dependencies import user_service_dependency
from app.users.presentation.responses import GET_CURRENT_USER_RESPONSES
from app.users.presentation.schemas import CurrentUserResponse

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
