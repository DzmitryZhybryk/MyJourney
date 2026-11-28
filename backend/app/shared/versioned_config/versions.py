from app.shared.versioned_config.exceptions import ConfigVersionConflictError


def next_config_version(*, latest_version: int, edited_version: int) -> int:
    """
    Номер версии, которой записывается правка конфига.

    Правка не последней версии — правка поверх устаревшего конфига или выдуманная версия: она
    отклоняется, иначе молча затёрла бы чужое изменение.

    Scenarios:
        - администратор сохраняет конфиг домена

    Args:
        latest_version: Последняя записанная версия
        edited_version: Версия, с которой правили

    Returns:
        Следующая версия

    Raises:
        ConfigVersionConflictError: Правили не последнюю версию
    """
    if edited_version != latest_version:
        raise ConfigVersionConflictError()

    return latest_version + 1
