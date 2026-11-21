"""
Пределы конфига media живут в request-схеме правки администратором; тип хранения несёт только форму.

Файл начальных значений пишет конфиг в обход HTTP, поэтому его прогоняет через ту же request-схему тест.
"""

from pathlib import Path
from typing import Final

import pytest
from pydantic import ValidationError

from app.media.application.ports.media_config_repository import MediaConfigSnapshot as StoredSnapshot
from app.media.presentation.admin.schemas import MediaConfigSnapshot, UpdateMediaConfigRequest
from app.shared.types import DictStrAny

_DEFAULTS_PATH: Final[Path] = Path(__file__).resolve().parents[5] / "app" / "media" / "scripts" / "config_defaults.json"


def test_config_defaults_file_passes_admin_request_schema() -> None:
    """Начальные значения деплоя подчиняются тем же пределам, что и правка администратором."""
    MediaConfigSnapshot.model_validate_json(_DEFAULTS_PATH.read_text(encoding="utf-8"))


def test_update_media_config_request_valid_body_accepted(update_media_config_body: DictStrAny) -> None:
    """Тело со всеми видами и разумными значениями проходит схему."""
    request = UpdateMediaConfigRequest.model_validate(update_media_config_body)

    assert request.snapshot.avatar.min_side == 512


@pytest.mark.parametrize(
    ("kind", "field", "value"),
    [
        ("avatar", "maxSizeBytes", 0),
        ("avatar", "minSide", 0),
        ("avatar", "formats", []),
        ("journeyVideo", "maxSizeBytes", -1),
        ("journeyVideo", "formats", []),
        ("avatar", "formats", ["video/mp4"]),
        ("journeyVideo", "formats", ["image/jpeg"]),
    ],
    ids=[
        "zero-size",
        "zero-side",
        "no-image-formats",
        "negative-video-size",
        "no-video-formats",
        "video-format-for-image",
        "image-format-for-video",
    ],
)
def test_update_media_config_request_out_of_limits_rejected(
    update_media_config_body: DictStrAny, kind: str, field: str, value: object
) -> None:
    """Каждый предел правки проверяется схемой запроса."""
    update_media_config_body["snapshot"][kind][field] = value

    with pytest.raises(ValidationError):
        UpdateMediaConfigRequest.model_validate(update_media_config_body)


@pytest.mark.parametrize(
    "path",
    [(), ("snapshot",), ("snapshot", "avatar")],
    ids=["body", "snapshot", "kind"],
)
def test_update_media_config_request_extra_key_rejected(
    update_media_config_body: DictStrAny, path: tuple[str, ...]
) -> None:
    """Лишний ключ на любом уровне — опечатка администратора, а не молча проигнорированное поле."""
    target = update_media_config_body
    for key in path:
        target = target[key]
    target["typo"] = 1

    with pytest.raises(ValidationError):
        UpdateMediaConfigRequest.model_validate(update_media_config_body)


def test_update_media_config_request_missing_kind_rejected(update_media_config_body: DictStrAny) -> None:
    """Конфиг сохраняется только целиком: без одного вида запрос не проходит."""
    del update_media_config_body["snapshot"]["journeyVideo"]

    with pytest.raises(ValidationError):
        UpdateMediaConfigRequest.model_validate(update_media_config_body)


def test_stored_snapshot_extra_key_ignored_on_read() -> None:
    """Тип хранения читает строку с полем, которого код уже не знает: форма, а не пределы."""
    image_rules = {"max_size_bytes": 1, "formats": ["image/png"], "min_side": 1, "retired_field": True}

    snapshot = StoredSnapshot.model_validate(
        {
            "avatar": image_rules,
            "journey_photo": image_rules,
            "journey_video": {"max_size_bytes": 1, "formats": ["video/mp4"]},
        }
    )

    assert snapshot.avatar.max_size_bytes == 1
