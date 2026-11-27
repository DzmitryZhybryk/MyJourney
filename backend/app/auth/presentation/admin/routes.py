from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.application.schemas.commands import FindAccountsByIdsCommand
from app.auth.application.services.account import AccountService
from app.auth.presentation.admin.responses import ACCOUNT_OPTIONS_RESPONSES, FIND_ACCOUNTS_BY_IDS_RESPONSES
from app.auth.presentation.admin.schemas import AccountOptionsResponse, AccountsResponse, FindAccountsByIdsRequest
from app.auth.presentation.dependencies import account_service_dependency
from app.shared.infra.jwt import PermissionEnum
from app.shared.infra.jwt.permission_checker import PermissionChecker

auth_admin_router = APIRouter()


@auth_admin_router.get(
    "/accounts/",
    response_model=AccountsResponse,
    responses=FIND_ACCOUNTS_BY_IDS_RESPONSES,
    dependencies=[Depends(PermissionChecker(PermissionEnum.AUTH_ACCOUNTS_READ))],
)
async def find_accounts_by_ids(
    *,
    query: Annotated[FindAccountsByIdsRequest, Query()],
    account_service: Annotated[AccountService, Depends(account_service_dependency)],
) -> AccountsResponse:
    """Учётные записи по id, удалённые с `isDeleted: true`; id без записи пропускается. Право `auth.accounts.read`."""
    result = await account_service.find_accounts_by_ids(FindAccountsByIdsCommand(user_ids=query.ids))
    return AccountsResponse.model_validate(result, from_attributes=True)


@auth_admin_router.get(
    "/account-options/",
    response_model=AccountOptionsResponse,
    responses=ACCOUNT_OPTIONS_RESPONSES,
    dependencies=[Depends(PermissionChecker(PermissionEnum.AUTH_ACCOUNTS_READ))],
)
async def get_account_options(
    account_service: Annotated[AccountService, Depends(account_service_dependency)],
) -> AccountOptionsResponse:
    """Все роли и тарифы учётной записи в порядке объявления. Право `auth.accounts.read`."""
    result = account_service.get_account_options()
    return AccountOptionsResponse.model_validate(result, from_attributes=True)
