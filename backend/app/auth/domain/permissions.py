from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from app.auth.domain.enums import UserPlanEnum, UserRoleEnum
from app.shared.infra.jwt import PermissionEnum

ROLE_PERMISSIONS: Final[Mapping[UserRoleEnum, frozenset[PermissionEnum]]] = MappingProxyType(
    {
        UserRoleEnum.USER: frozenset(),
        UserRoleEnum.ADMIN: frozenset({PermissionEnum.MEDIA_CONFIG_EDIT}),
    },
)

PLAN_PERMISSIONS: Final[Mapping[UserPlanEnum, frozenset[PermissionEnum]]] = MappingProxyType(
    {
        UserPlanEnum.FREE: frozenset(),
        UserPlanEnum.PREMIUM: frozenset(),
    },
)


def expand_permissions(*, role: UserRoleEnum, plan: UserPlanEnum) -> frozenset[PermissionEnum]:
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
