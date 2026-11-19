from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from app.auth.domain.enums import UserPlanEnum, UserRoleEnum

MEDIA_CONFIG_EDIT: Final[str] = "media.config.edit"

ROLE_PERMISSIONS: Final[Mapping[UserRoleEnum, frozenset[str]]] = MappingProxyType(
    {
        UserRoleEnum.USER: frozenset(),
        UserRoleEnum.ADMIN: frozenset({MEDIA_CONFIG_EDIT}),
    },
)

PLAN_PERMISSIONS: Final[Mapping[UserPlanEnum, frozenset[str]]] = MappingProxyType(
    {
        UserPlanEnum.FREE: frozenset(),
        UserPlanEnum.PREMIUM: frozenset(),
    },
)


def expand_permissions(*, role: UserRoleEnum, plan: UserPlanEnum) -> frozenset[str]:
    """
    Раскрывает роль и тариф в итоговый набор прав: права роли плюс права тарифа.

    Scenarios:
        - регистрация, вход и обновление сессии: набор уходит в access-токен

    Args:
        role: Роль пользователя
        plan: Тариф пользователя

    Returns:
        Объединение прав роли и тарифа
    """
    return ROLE_PERMISSIONS[role] | PLAN_PERMISSIONS[plan]
