import pytest

from app.auth.domain.enums import UserPlanEnum, UserRoleEnum
from app.auth.domain.permissions import MEDIA_CONFIG_EDIT, PLAN_PERMISSIONS, ROLE_PERMISSIONS, expand_permissions


@pytest.mark.parametrize(
    ("role", "plan", "expected"),
    [
        (UserRoleEnum.USER, UserPlanEnum.FREE, frozenset()),
        (UserRoleEnum.USER, UserPlanEnum.PREMIUM, frozenset()),
        (UserRoleEnum.ADMIN, UserPlanEnum.FREE, frozenset({MEDIA_CONFIG_EDIT})),
        (UserRoleEnum.ADMIN, UserPlanEnum.PREMIUM, frozenset({MEDIA_CONFIG_EDIT})),
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
