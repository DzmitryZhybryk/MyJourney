from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.media.application.ports.media_config_repository import ImageKindRules, MediaConfigSnapshot, VideoKindRules
from app.media.application.schemas.commands import UpdateMediaConfigCommand
from app.media.application.services.media_config import MediaConfigService
from app.media.presentation.admin.responses import GET_MEDIA_CONFIG_RESPONSES, UPDATE_MEDIA_CONFIG_RESPONSES
from app.media.presentation.admin.schemas import AdminMediaConfigResponse, AdminUpdateMediaConfigRequest
from app.media.presentation.dependencies import media_config_service_dependency
from app.shared.infra.jwt import AccessTokenClaims, PermissionEnum
from app.shared.infra.jwt.permission_checker import PermissionChecker

media_admin_router = APIRouter()


@media_admin_router.get(
    "/config/",
    response_model=AdminMediaConfigResponse,
    responses=GET_MEDIA_CONFIG_RESPONSES,
    dependencies=[Depends(PermissionChecker(PermissionEnum.MEDIA_CONFIG_EDIT))],
)
async def get_media_config(
    media_config_service: Annotated[MediaConfigService, Depends(media_config_service_dependency)],
) -> AdminMediaConfigResponse:
    """Последняя версия конфига для правки. Нужно право `media.config.edit`."""
    result = await media_config_service.get_media_config()
    return AdminMediaConfigResponse.model_validate(result, from_attributes=True)


@media_admin_router.put(
    "/config/",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=UPDATE_MEDIA_CONFIG_RESPONSES,
)
async def update_media_config(
    *,
    body: AdminUpdateMediaConfigRequest,
    claims: Annotated[AccessTokenClaims, Depends(PermissionChecker(PermissionEnum.MEDIA_CONFIG_EDIT))],
    media_config_service: Annotated[MediaConfigService, Depends(media_config_service_dependency)],
) -> Response:
    """Записывает конфиг новой версией. `editedVersion` не последняя — 409. Нужно право `media.config.edit`."""
    snapshot = body.snapshot
    command = UpdateMediaConfigCommand(
        edited_version=body.edited_version,
        snapshot=MediaConfigSnapshot(
            avatar=ImageKindRules(
                max_size_bytes=snapshot.avatar.max_size_bytes,
                formats=snapshot.avatar.formats,
                min_side=snapshot.avatar.min_side,
            ),
            journey_photo=ImageKindRules(
                max_size_bytes=snapshot.journey_photo.max_size_bytes,
                formats=snapshot.journey_photo.formats,
                min_side=snapshot.journey_photo.min_side,
            ),
            journey_video=VideoKindRules(
                max_size_bytes=snapshot.journey_video.max_size_bytes,
                formats=snapshot.journey_video.formats,
            ),
        ),
    )
    await media_config_service.update_media_config(user_id=claims.user_id, command=command)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
