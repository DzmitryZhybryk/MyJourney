from typing import Annotated

from fastapi import APIRouter, Depends

from app.media.application.services.media_config import MediaConfigService
from app.media.presentation.dependencies import media_config_service_dependency
from app.media.presentation.responses import GET_UPLOAD_RULES_RESPONSES
from app.media.presentation.schemas import UploadRulesResponse

media_router = APIRouter()


@media_router.get(
    "/config/",
    response_model=UploadRulesResponse,
    responses=GET_UPLOAD_RULES_RESPONSES,
)
async def get_upload_rules(
    media_config_service: Annotated[MediaConfigService, Depends(media_config_service_dependency)],
) -> UploadRulesResponse:
    """Текущие правила загрузки каждого вида файла: размер, форматы, минимальная сторона. Без авторизации."""
    result = await media_config_service.get_upload_rules()
    return UploadRulesResponse.model_validate(result, from_attributes=True)
