import pytest

from app.shared.infra.jwt import PermissionEnum


@pytest.mark.parametrize("permission", list(PermissionEnum))
def test_permission_enum_member_named_as_domain_resource_action(permission: PermissionEnum) -> None:
    """Значение права — ``<домен>.<ресурс>.<действие>``, имя члена — то же значение заглавными через подчёркивание."""
    assert len(permission.value.split(".")) == 3
    assert permission.name == permission.value.upper().replace(".", "_")


def test_permission_enum_values_pinned_as_token_contract() -> None:
    """Строка права уходит в выданные токены: её переименование — смена контракта, а не рефакторинг."""
    assert {permission.value for permission in PermissionEnum} == {"media.config.edit", "auth.accounts.read"}
