import pytest

from app.shared.versioned_config import ConfigVersionConflictError, next_config_version


def test_next_config_version_latest_edited_returns_following_number() -> None:
    """Правка последней версии записывается следующим номером."""
    assert next_config_version(latest_version=4, edited_version=4) == 5


@pytest.mark.parametrize("edited_version", [3, 5], ids=["stale", "future"])
def test_next_config_version_other_edited_raises_conflict(edited_version: int) -> None:
    """Версия, отличная от последней, — конфликт, а не запись поверх."""
    with pytest.raises(ConfigVersionConflictError):
        next_config_version(latest_version=4, edited_version=edited_version)
