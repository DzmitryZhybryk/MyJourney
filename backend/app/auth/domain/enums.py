from enum import StrEnum


class UserRoleEnum(StrEnum):
    """Роль пользователя, определяющая уровень доступа и привилегии."""

    FREE = "free"
    PREMIUM = "premium"
    ADMIN = "admin"


class ChallengeTypeEnum(StrEnum):
    """
    Тип challenge'а — discriminator для одной записи `challenge` на разные сценарии.

    Поведение лайфсайкла одинаковое (TTL, попытки, использование, cooldown
    на resend), различается только домен использования.
    """

    EMAIL_VERIFICATION = "email_verification"
