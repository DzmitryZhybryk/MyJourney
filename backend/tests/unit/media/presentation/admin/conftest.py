import pytest

from app.shared.types import DictStrAny


@pytest.fixture
def update_media_config_body() -> DictStrAny:
    """Валидное тело правки конфига, как его шлёт экран администратора: camelCase, все виды."""
    return {
        "editedVersion": 1,
        "snapshot": {
            "avatar": {"maxSizeBytes": 1_000, "formats": ["image/jpeg"], "minSide": 512},
            "journeyPhoto": {"maxSizeBytes": 1_000, "formats": ["image/jpeg"], "minSide": 1280},
            "journeyVideo": {"maxSizeBytes": 1_000, "formats": ["video/mp4"]},
        },
    }
