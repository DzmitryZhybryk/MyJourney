from enum import StrEnum


class UserRoleEnum(StrEnum):
    """Роль пользователя: что ему разрешено делать в системе."""

    USER = "user"
    ADMIN = "admin"


class UserPlanEnum(StrEnum):
    """Тариф пользователя: за что он платит. Независим от роли."""

    FREE = "free"
    PREMIUM = "premium"


class ChallengeTypeEnum(StrEnum):
    """
    Тип challenge'а — discriminator для одной записи `challenge` на разные сценарии.

    Поведение лайфсайкла одинаковое (TTL, попытки, использование, cooldown
    на resend), различается только домен использования.
    """

    EMAIL_VERIFICATION = "email_verification"
