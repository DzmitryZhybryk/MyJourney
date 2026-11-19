from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EmailVerificationConfig:
    """Настройки подтверждения email: срок жизни кода, лимит попыток, пауза между отправками."""

    ttl_minutes: int
    max_attempts: int
    resend_cooldown_seconds: int
