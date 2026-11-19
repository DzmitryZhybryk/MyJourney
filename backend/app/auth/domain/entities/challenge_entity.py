import datetime as dt
import math
import secrets
import string
from typing import Final, Self
from uuid import UUID, uuid4

from app.auth.domain.enums import ChallengeTypeEnum
from app.auth.exceptions import (
    ChallengeAttemptsExceededError,
    ChallengeExpiredError,
    ChallengeResendCooldownError,
)
from app.shared.domain.domain_mixins import TimestampedEntityMixin

_VERIFICATION_CODE_LENGTH: Final[int] = 6


class ChallengeEntity(TimestampedEntityMixin):
    """
    Challenge — одноразовый код, выдаваемый под конкретный сценарий
    (см. ``ChallengeTypeEnum``): подтверждение email, восстановление пароля и т.п.

    Термин ``challenge`` выбран сознательно, чтобы не путать с access/refresh
    токенами авторизации. Здесь речь о challenge-response верификации:
    backend генерирует «вопрос» (код), пользователь должен ответить тем же
    кодом из письма/SMS.

    Лайфсайкл (TTL, счётчик попыток, использование, cooldown на resend)
    одинаков для всех типов; различается только домен использования —
    откуда `challenge_type` как discriminator.

    Хранит код **зашифрованным**, а не хешем: код нужно уметь отправить ещё раз.
    Шифрование и расшифровка делаются на стороне application через ``SecretCipherPort``:
    сущность об алгоритме не знает.
    """

    def __init__(
        self,
        *,
        challenge_id: UUID,
        user_id: UUID,
        challenge_type: ChallengeTypeEnum,
        code_ciphertext: str,
        expires_at: dt.datetime,
        last_sent_at: dt.datetime,
        attempts: int = 0,
        used_at: dt.datetime | None = None,
        **timestamp_kwargs: dt.datetime | None,
    ) -> None:
        super().__init__(**timestamp_kwargs)
        self.challenge_id = challenge_id
        self.user_id = user_id
        self.challenge_type = challenge_type
        self.code_ciphertext = code_ciphertext
        self.expires_at = expires_at
        self.last_sent_at = last_sent_at
        self.attempts = attempts
        self.used_at = used_at

    @staticmethod
    def generate_code() -> str:
        """
        Генерирует криптостойкий 6-значный числовой код.

        Scenarios:
            - отправка кода подтверждения email: после регистрации и из диалога «Подтвердите email»

        Returns:
            Строка из 6 цифр, равномерно распределённая по `secrets.choice`
        """
        return "".join(secrets.choice(string.digits) for _ in range(_VERIFICATION_CODE_LENGTH))

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        challenge_type: ChallengeTypeEnum,
        code_ciphertext: str,
        ttl_minutes: int,
    ) -> Self:
        """
        Создаёт новый challenge с истечением через ``ttl_minutes`` минут.

        Scenarios:
            - отправка кода подтверждения email: после регистрации и из диалога «Подтвердите email»

        Args:
            user_id: ID пользователя, которому принадлежит challenge
            challenge_type: Сценарий, для которого выпускается challenge
            code_ciphertext: Шифротекст кода, полученный из ``SecretCipherPort.encrypt``
            ttl_minutes: Срок жизни challenge'а в минутах

        Returns:
            Новая доменная сущность со свежим UUID, `expires_at = now + ttl` и `last_sent_at = now`
        """
        now = dt.datetime.now(tz=dt.UTC)
        return cls(
            challenge_id=uuid4(),
            user_id=user_id,
            challenge_type=challenge_type,
            code_ciphertext=code_ciphertext,
            expires_at=now + dt.timedelta(minutes=ttl_minutes),
            last_sent_at=now,
        )

    def is_expired(self) -> bool:
        """
        Проверяет, что срок действия кода прошёл.

        Scenarios:
            - кнопка «Отправить код повторно»: истёкший код заменяется новым, живой отправляется снова
            - ввод кода в диалоге «Подтвердите email»

        Returns:
            ``True``, если срок действия прошёл
        """
        return self.expires_at <= dt.datetime.now(tz=dt.UTC)

    def is_active(self) -> bool:
        """
        Проверяет, что challenge не использован и не истёк.

        Scenarios:
            - ввод кода в диалоге «Подтвердите email»

        Returns:
            ``True`` если challenge ещё можно использовать, иначе ``False``
        """
        return self.used_at is None and not self.is_expired()

    def seconds_until_expiry(self) -> int:
        """
        Считает, сколько целых секунд осталось до истечения кода, с округлением вверх.

        Scenarios:
            - исчерпаны попытки ввода: сколько ждать до нового кода

        Returns:
            Число секунд, не меньше нуля
        """
        remaining_seconds = (self.expires_at - dt.datetime.now(tz=dt.UTC)).total_seconds()
        return max(0, math.ceil(remaining_seconds))

    def ensure_resend_cooldown_passed(self, *, cooldown_seconds: int) -> None:
        """
        Проверяет, что с последней отправки кода прошло достаточно времени, чтобы отправить его снова.

        Scenarios:
            - кнопка «Отправить код повторно» в диалоге «Подтвердите email»

        Args:
            cooldown_seconds: Минимальное число секунд между отправками кода одному пользователю

        Raises:
            ChallengeResendCooldownError: Cooldown ещё не истёк
        """
        elapsed_seconds = (dt.datetime.now(tz=dt.UTC) - self.last_sent_at).total_seconds()
        if elapsed_seconds < cooldown_seconds:
            raise ChallengeResendCooldownError()

    def ensure_not_exhausted(self, *, max_attempts: int) -> None:
        """
        Проверяет, что лимит попыток ввода не выбран.

        Исчерпанный код не заменяется новым, пока не истечёт: иначе повторная отправка
        выдавала бы свежие попытки и обходила лимит.

        Scenarios:
            - кнопка «Отправить код повторно» в диалоге «Подтвердите email»
            - ввод кода в диалоге «Подтвердите email»

        Args:
            max_attempts: Максимально разрешённое число попыток ввода кода

        Raises:
            ChallengeAttemptsExceededError: Лимит выбран; в ``details`` — секунды до нового кода
        """
        if self.attempts >= max_attempts:
            raise ChallengeAttemptsExceededError(details={"retry_after_seconds": self.seconds_until_expiry()})

    def resend(self, *, ttl_minutes: int) -> None:
        """
        Отмечает повторную отправку того же кода и продлевает его срок.

        Scenarios:
            - кнопка «Отправить код повторно», пока код жив

        Args:
            ttl_minutes: Срок жизни кода в минутах, отсчитывается от этой отправки
        """
        now = dt.datetime.now(tz=dt.UTC)
        self.last_sent_at = now
        self.expires_at = now + dt.timedelta(minutes=ttl_minutes)
        self._mark_updated()

    def ensure_can_attempt(self, *, max_attempts: int) -> None:
        """
        Проверяет, что challenge пригоден к очередной попытке ввода кода.

        Консолидирует две связанных проверки в один доменный инвариант: challenge
        активен (не истёк и не использован) и лимит попыток не выбран. Любое
        нарушение — это переход, который нельзя совершить, и ответственность
        за защиту лежит на entity, а не на каждом сервисе-вызывающем.

        Scenarios:
            - ввод кода в диалоге «Подтвердите email»

        Args:
            max_attempts: Максимально разрешённое число попыток ввода кода

        Raises:
            ChallengeExpiredError: Challenge истёк или уже использован
            ChallengeAttemptsExceededError: Превышен лимит попыток
        """
        if not self.is_active():
            raise ChallengeExpiredError()

        self.ensure_not_exhausted(max_attempts=max_attempts)

    def register_failed_attempt(self) -> None:
        """
        Увеличивает счётчик неудачных попыток ввода кода на 1.

        Scenarios:
            - неверный код в диалоге «Подтвердите email»
        """
        self.attempts += 1
        self._mark_updated()

    def mark_used(self) -> None:
        """
        Помечает challenge как использованный.

        Scenarios:
            - верный код в диалоге «Подтвердите email»
            - повторный запрос кода, когда прежний истёк: он гасится, выдаётся новый
        """
        self.used_at = dt.datetime.now(tz=dt.UTC)
        self._mark_updated()
