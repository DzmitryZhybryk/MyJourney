from typing import Final
from uuid import NAMESPACE_URL, UUID, uuid5

# Строку не менять: у всех объектов газеттира сменятся id, а их уже хранят те, кто на них ссылается.
GAZETTEER_NAMESPACE: Final[UUID] = uuid5(NAMESPACE_URL, "urn:myjourney:geo-place")


def gazetteer_id_for(*, external_id: str) -> UUID:
    """
    Выводит id объекта газеттира из ключа поставщика (uuid5): одинаковый на любом окружении.

    Scenarios:
        - загрузка газеттира в базу: при развёртывании до старта приложения и в дев-стеке

    Args:
        external_id: Ключ объекта с префиксом источника (``"GeoNames:524901"``)

    Returns:
        Наш id объекта
    """
    return uuid5(GAZETTEER_NAMESPACE, external_id)
