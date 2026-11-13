from app.auth.application.ports.users_client import CreateUserRequest, UsersClientPort
from app.users.application.schemas.commands import CreateUserCommand
from app.users.application.services.user import UserService


class InternalUsersClient(UsersClientPort):
    """Адаптер ``UsersClientPort``: переводит ``CreateUserRequest`` в команду users и зовёт ``UserService``."""

    def __init__(self, user_service: UserService) -> None:
        self._user_service = user_service

    async def create_user(self, request: CreateUserRequest) -> None:
        await self._user_service.create_user(
            command=CreateUserCommand(
                user_id=request.user_id,
                display_name=request.display_name,
                marketing_emails_consent=request.marketing_emails_consent,
                terms_accepted_at=request.terms_accepted_at,
            ),
        )
