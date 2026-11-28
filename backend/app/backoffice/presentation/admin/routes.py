from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.backoffice.application.ports.account_repository import AccountFilters
from app.backoffice.application.schemas.commands import ListAccountsCommand
from app.backoffice.application.services.account import AccountService
from app.backoffice.presentation.admin.responses import ACCOUNTS_LIST_RESPONSES
from app.backoffice.presentation.admin.schemas import AdminAccountsListRequest, AdminAccountsListResponse
from app.backoffice.presentation.dependencies import account_service_dependency
from app.shared.infra.jwt import PermissionEnum
from app.shared.infra.jwt.permission_checker import PermissionChecker
from app.shared.pagination.offset import OffsetPageQuery

backoffice_admin_router = APIRouter()


@backoffice_admin_router.get(
    "/accounts/",
    response_model=AdminAccountsListResponse,
    responses=ACCOUNTS_LIST_RESPONSES,
    dependencies=[Depends(PermissionChecker(PermissionEnum.BACKOFFICE_ACCOUNTS_READ))],
)
async def list_accounts(
    *,
    query: Annotated[AdminAccountsListRequest, Query()],
    account_service: Annotated[AccountService, Depends(account_service_dependency)],
) -> AdminAccountsListResponse:
    """Страница списка аккаунтов под фильтром и число всех аккаунтов под ним. Право `backoffice.accounts.read`."""
    result = await account_service.list_accounts(
        ListAccountsCommand(
            page=OffsetPageQuery(page=query.page, limit=query.limit),
            filters=AccountFilters(
                email_contains=query.email,
                display_name_contains=query.display_name,
                role=query.role,
                marketing_emails_consent=query.marketing_emails_consent,
                include_deleted=query.include_deleted,
            ),
            sort_direction=query.sort_direction,
        ),
    )
    return AdminAccountsListResponse.model_validate(result, from_attributes=True)
