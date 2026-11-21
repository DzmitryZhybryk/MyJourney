from dataclasses import dataclass

from app.media.application.ports.media_config_repository import MediaConfigSnapshot

__all__ = ["SeedMediaConfigCommand", "UpdateMediaConfigCommand"]


@dataclass(frozen=True, slots=True)
class SeedMediaConfigCommand:
    """Конфиг media из файла начальных значений."""

    snapshot: MediaConfigSnapshot


@dataclass(frozen=True, slots=True)
class UpdateMediaConfigCommand:
    """Новый конфиг media и версия, с которой его правили."""

    edited_version: int
    snapshot: MediaConfigSnapshot
