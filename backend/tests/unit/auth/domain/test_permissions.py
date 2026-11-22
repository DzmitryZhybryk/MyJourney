from typing import Final

import pytest

from app.auth.domain.enums import UserPlanEnum, UserRoleEnum
from app.auth.domain.permissions import PLAN_PERMISSIONS, ROLE_PERMISSIONS, expand_permissions
from app.shared.infra.jwt import PermissionEnum

_ADMIN_PERMISSIONS: Final[frozenset[PermissionEnum]] = frozenset(
    {PermissionEnum.MEDIA_CONFIG_EDIT, PermissionEnum.AUTH_ACCOUNTS_READ},
)


@pytest.mark.parametrize(
    ("role", "plan", "expected"),
    [
        (UserRoleEnum.USER, UserPlanEnum.FREE, frozenset()),
        (UserRoleEnum.USER, UserPlanEnum.PREMIUM, frozenset()),
        (UserRoleEnum.ADMIN, UserPlanEnum.FREE, _ADMIN_PERMISSIONS),
        (UserRoleEnum.ADMIN, UserPlanEnum.PREMIUM, _ADMIN_PERMISSIONS),
    ],
)
def test_expand_permissions_by_role_and_plan(
    role: UserRoleEnum,
    plan: UserPlanEnum,
    expected: frozenset[str],
) -> None:
    """Права пользователя — объединение прав роли и прав тарифа."""
    assert expand_permissions(role=role, plan=plan) == expected


def test_permission_maps_cover_every_role_and_plan() -> None:
    """У каждой роли и каждого тарифа есть запись в карте прав: новая роль без записи не уронит выпуск токена."""
    assert set(ROLE_PERMISSIONS) == set(UserRoleEnum)
    assert set(PLAN_PERMISSIONS) == set(UserPlanEnum)
