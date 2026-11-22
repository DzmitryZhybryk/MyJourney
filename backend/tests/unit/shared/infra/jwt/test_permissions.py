import pytest

from app.shared.infra.jwt import PermissionEnum


@pytest.mark.parametrize("permission", list(PermissionEnum))
def test_permission_enum_member_named_as_domain_resource_action(permission: PermissionEnum) -> None:
    """Значение права — ``<домен>.<ресурс>.<действие>``, имя члена — то же значение заглавными через подчёркивание."""
    assert len(permission.value.split(".")) == 3
    assert permission.name == permission.value.upper().replace(".", "_")
