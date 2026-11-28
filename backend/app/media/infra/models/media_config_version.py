from sqlalchemy.orm import Mapped, mapped_column

from app.media.application.ports.media_config_repository import MediaConfigSnapshot
from app.shared.infra.db.postgres.jsonb import PydanticJSONB
from app.shared.versioned_config.models import VersionedConfigModel


class MediaConfigVersion(VersionedConfigModel):
    """Версия конфига media: правила загрузки всех видов файлов."""

    __tablename__ = "media_config"

    config: Mapped[MediaConfigSnapshot] = mapped_column(PydanticJSONB(MediaConfigSnapshot))
