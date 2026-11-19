from typing import Annotated

from fastapi import Depends

from app.shared.infra.jwt.dependency import current_user_claims_dependency
from app.shared.infra.jwt.exceptions import PermissionRequiredError
from app.shared.infra.jwt.ports import AccessTokenClaims


class PermissionChecker:
    """Зависимость маршрута: пропускает запрос, только если в access-токене есть право ``permission``."""

    def __init__(self, permission: str) -> None:
        self.permission = permission

    async def __call__(
        self,
        claims: Annotated[AccessTokenClaims, Depends(current_user_claims_dependency)],
    ) -> AccessTokenClaims:
        """
        Пропускает запрос с правом и отдаёт содержимое токена.

        Scenarios:
            - эндпоинт, доступный только обладателю права

        Args:
            claims: Содержимое токена

        Returns:
            То же содержимое токена

        Raises:
            PermissionRequiredError: Права нет в токене
        """
        if self.permission not in claims.permissions:
            raise PermissionRequiredError()

        return claims
