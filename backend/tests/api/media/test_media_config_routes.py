"""Токены выпускает настоящий ``TokenIssuer`` (``issue_access_token``): право приходит из карты ролей, а не руками."""

from collections.abc import Callable
from typing import Final

from httpx import AsyncClient

from app.auth.domain.entities import UserCredentialsEntity
from app.auth.domain.enums import UserRoleEnum
from app.shared.types import DictStrAny
from tests.builders import ADMIN_ID, make_media_config_snapshot, make_user_credentials
from tests.fakes import FakeMediaConfigRepository

_PUBLIC_PATH: Final[str] = "/v1/media/config/"
_ADMIN_PATH: Final[str] = "/v1/admin/media/config/"

_EDIT_BODY: Final[DictStrAny] = {
    "editedVersion": 1,
    "snapshot": {
        "avatar": {"maxSizeBytes": 1_000, "formats": ["image/jpeg"], "minSide": 640},
        "journeyPhoto": {"maxSizeBytes": 2_000, "formats": ["image/png"], "minSide": 1280},
        "journeyVideo": {"maxSizeBytes": 3_000, "formats": ["video/mp4"]},
    },
}


async def test_get_upload_rules_without_token_returns_camelcase_rules(
    client: AsyncClient,
    fake_media_config_repository: FakeMediaConfigRepository,
) -> None:
    """Публичные правила отдаются без токена, с осью стороны и без версии и автора."""
    await fake_media_config_repository.insert_media_config(
        version=1, snapshot=make_media_config_snapshot(), created_by=ADMIN_ID
    )

    response = await client.get(_PUBLIC_PATH)

    assert response.status_code == 200
    body = response.json()
    assert body["avatar"]["minSideAxis"] == "short"
    assert body["journeyPhoto"]["minSideAxis"] == "long"
    assert set(body) == {"avatar", "journeyPhoto", "journeyVideo"}


async def test_get_media_config_admin_token_returns_version_and_author(
    client: AsyncClient,
    fake_media_config_repository: FakeMediaConfigRepository,
    issue_access_token: Callable[[UserCredentialsEntity], str],
) -> None:
    """Админ получает последнюю версию с номером и автором."""
    await fake_media_config_repository.insert_media_config(
        version=1, snapshot=make_media_config_snapshot(), created_by=ADMIN_ID
    )
    token = issue_access_token(make_user_credentials(role=UserRoleEnum.ADMIN))

    response = await client.get(_ADMIN_PATH, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert (body["version"], body["createdBy"]) == (1, str(ADMIN_ID))
    assert body["snapshot"]["avatar"]["minSide"] == 512


async def test_update_media_config_admin_token_writes_next_version_by_caller(
    client: AsyncClient,
    fake_media_config_repository: FakeMediaConfigRepository,
    issue_access_token: Callable[[UserCredentialsEntity], str],
) -> None:
    """204: новая версия записана с автором из токена и значениями из тела."""
    await fake_media_config_repository.insert_media_config(
        version=1, snapshot=make_media_config_snapshot(), created_by=None
    )
    admin = make_user_credentials(role=UserRoleEnum.ADMIN)

    response = await client.put(
        _ADMIN_PATH, json=_EDIT_BODY, headers={"Authorization": f"Bearer {issue_access_token(admin)}"}
    )

    assert response.status_code == 204
    stored = fake_media_config_repository.versions[2]
    assert stored.created_by == admin.user_id
    assert stored.snapshot.avatar.min_side == 640
    assert stored.snapshot.journey_video.max_size_bytes == 3_000


async def test_update_media_config_stale_version_returns_409(
    client: AsyncClient,
    fake_media_config_repository: FakeMediaConfigRepository,
    issue_access_token: Callable[[UserCredentialsEntity], str],
) -> None:
    """409 ``config_version_conflict``, когда правили не последнюю версию."""
    for version in (1, 2):
        await fake_media_config_repository.insert_media_config(
            version=version, snapshot=make_media_config_snapshot(), created_by=None
        )
    token = issue_access_token(make_user_credentials(role=UserRoleEnum.ADMIN))

    response = await client.put(_ADMIN_PATH, json=_EDIT_BODY, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 409
    assert response.json()["code"] == "config_version_conflict"
    assert list(fake_media_config_repository.versions) == [1, 2]


async def test_update_media_config_out_of_limits_returns_422(
    client: AsyncClient,
    fake_media_config_repository: FakeMediaConfigRepository,
    issue_access_token: Callable[[UserCredentialsEntity], str],
) -> None:
    """422 на значение вне пределов; ничего не записано."""
    await fake_media_config_repository.insert_media_config(
        version=1, snapshot=make_media_config_snapshot(), created_by=None
    )
    body = {**_EDIT_BODY, "snapshot": {**_EDIT_BODY["snapshot"], "journeyVideo": {"maxSizeBytes": 0, "formats": []}}}
    token = issue_access_token(make_user_credentials(role=UserRoleEnum.ADMIN))

    response = await client.put(_ADMIN_PATH, json=body, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 422
    assert list(fake_media_config_repository.versions) == [1]


async def test_admin_media_config_user_token_returns_403(
    client: AsyncClient,
    fake_media_config_repository: FakeMediaConfigRepository,
    issue_access_token: Callable[[UserCredentialsEntity], str],
) -> None:
    """403 ``permission_required`` у обычного пользователя — и на чтение, и на правку."""
    await fake_media_config_repository.insert_media_config(
        version=1, snapshot=make_media_config_snapshot(), created_by=None
    )
    headers = {"Authorization": f"Bearer {issue_access_token(make_user_credentials(role=UserRoleEnum.USER))}"}

    read = await client.get(_ADMIN_PATH, headers=headers)
    write = await client.put(_ADMIN_PATH, json=_EDIT_BODY, headers=headers)

    assert (read.status_code, read.json()["code"]) == (403, "permission_required")
    assert (write.status_code, write.json()["code"]) == (403, "permission_required")
    assert list(fake_media_config_repository.versions) == [1]


async def test_admin_media_config_without_token_returns_401(client: AsyncClient) -> None:
    """401 без Bearer — и на чтение, и на правку."""
    read = await client.get(_ADMIN_PATH)
    write = await client.put(_ADMIN_PATH, json=_EDIT_BODY)

    assert (read.status_code, write.status_code) == (401, 401)
