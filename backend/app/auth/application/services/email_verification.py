import hmac
from uuid import UUID

from app.auth.application.config import EmailVerificationConfig
from app.auth.application.ports.tasks import SEND_VERIFICATION_EMAIL_TASK
from app.auth.application.ports.unit_of_work import AuthUnitOfWorkPort
from app.auth.application.schemas.commands import VerifyEmailCommand
from app.auth.domain.entities import ChallengeEntity
from app.auth.domain.enums import ChallengeTypeEnum
from app.auth.exceptions import (
    AccountNotFoundError,
    ChallengeNotFoundError,
    VerificationCodeInvalidError,
)
from app.shared.infra.crypto import SecretCipherPort
from app.shared.infra.procrastinate import TaskBusPort


class EmailVerificationService:
    def __init__(
        self,
        *,
        uow: AuthUnitOfWorkPort,
        secret_cipher: SecretCipherPort,
        task_bus: TaskBusPort,
        config: EmailVerificationConfig,
    ) -> None:
        self._uow = uow
        self._secret_cipher = secret_cipher
        self._task_bus = task_bus
        self._config = config

    async def request_email_verification(self, user_id: UUID) -> None:
        """
        Отправляет код подтверждения email: тот же, пока он жив, или новый.

        Живой код с невыбранными попытками отправляется снова, и его срок продлевается: любое
        письмо, дошедшее позже, несёт действующий код. Пока код исчерпан и не истёк, нового нет —
        иначе повторная отправка обходила бы лимит попыток. Истёкший код гасится
        (``used_at = now()``, чтобы партиальный unique-индекс пропустил новый), и выдаётся новый.

        Запись challenge'а и defer таски коммитятся одной транзакцией — невозможно состояние
        «в БД challenge есть, в очереди job'а нет» (или наоборот).

        Scenarios:
            - регистрация: код уходит на почту сразу
            - кнопки «Отправить код» и «Отправить код повторно» в диалоге «Подтвердите email»

        Args:
            user_id: ID пользователя, которому нужен код

        Raises:
            AccountNotFoundError: Если учётной записи с таким ``user_id`` не существует
            EmailAlreadyVerifiedError: Если email уже подтверждён
            ChallengeResendCooldownError: Если код отправлялся позже, чем cooldown назад
            ChallengeAttemptsExceededError: Если попытки ввода живого кода исчерпаны
        """
        async with self._uow.transaction():
            user_credentials_entity = await self._uow.user_credentials_repository.find_user_credentials_by_user_id(
                user_id=user_id
            )
            if user_credentials_entity is None:
                raise AccountNotFoundError()

            user_credentials_entity.ensure_not_verified()

            existing_challenge_entity = await self._uow.challenge_repository.find_active_challenge_for_update(
                user_id=user_id,
                challenge_type=ChallengeTypeEnum.EMAIL_VERIFICATION,
            )
            if existing_challenge_entity is not None and not existing_challenge_entity.is_expired():
                existing_challenge_entity.ensure_not_exhausted(max_attempts=self._config.max_attempts)
                existing_challenge_entity.ensure_resend_cooldown_passed(
                    cooldown_seconds=self._config.resend_cooldown_seconds,
                )
                existing_challenge_entity.resend(ttl_minutes=self._config.ttl_minutes)
                await self._uow.challenge_repository.update_challenge_by_id(challenge_entity=existing_challenge_entity)
                challenge_entity = existing_challenge_entity
            else:
                if existing_challenge_entity is not None:
                    existing_challenge_entity.mark_used()
                    await self._uow.challenge_repository.update_challenge_by_id(
                        challenge_entity=existing_challenge_entity
                    )

                code = ChallengeEntity.generate_code()
                challenge_entity = ChallengeEntity.create(
                    user_id=user_id,
                    challenge_type=ChallengeTypeEnum.EMAIL_VERIFICATION,
                    code_ciphertext=self._secret_cipher.encrypt(secret=code),
                    ttl_minutes=self._config.ttl_minutes,
                )
                await self._uow.challenge_repository.insert_challenge(challenge_entity=challenge_entity)

            await self._task_bus.bind_to(self._uow.session).defer(
                task_name=SEND_VERIFICATION_EMAIL_TASK,
                lock=f"email_verification:user:{user_id}",
                user_id=str(user_id),
                email=user_credentials_entity.email,
                code_ciphertext=challenge_entity.code_ciphertext,
                expires_at=challenge_entity.expires_at.isoformat(),
            )
            await self._uow.commit()

    async def verify_email(self, *, user_id: UUID, command: VerifyEmailCommand) -> None:
        """
        Проверяет одноразовый код и помечает email пользователя подтверждённым.

        Активный challenge берётся под ``SELECT ... FOR UPDATE`` — параллельные
        попытки ввода кода сериализуются и не теряют инкремент счётчика. На
        неверном коде счётчик неудачных попыток увеличивается; при превышении
        лимита challenge дальше не принимается до выпуска нового.

        Scenarios:
            - ввод кода в диалоге «Подтвердите email»

        Args:
            user_id: ID пользователя
            command: Команда с кодом, который ввёл пользователь

        Raises:
            AccountNotFoundError: Если учётной записи с таким ``user_id`` не существует
            EmailAlreadyVerifiedError: Если email уже подтверждён
            ChallengeNotFoundError: У пользователя нет активного challenge'а для верификации
            VerificationCodeInvalidError: Код не совпал с активным challenge'ом
            ChallengeExpiredError: Срок действия challenge'а истёк
            ChallengeAttemptsExceededError: Превышен лимит попыток
        """
        async with self._uow.transaction():
            user_credentials_entity = await self._uow.user_credentials_repository.find_user_credentials_by_user_id(
                user_id=user_id
            )
            if user_credentials_entity is None:
                raise AccountNotFoundError()

            user_credentials_entity.ensure_not_verified()

            challenge_entity = await self._uow.challenge_repository.find_active_challenge_for_update(
                user_id=user_id,
                challenge_type=ChallengeTypeEnum.EMAIL_VERIFICATION,
            )
            if challenge_entity is None:
                raise ChallengeNotFoundError()

            challenge_entity.ensure_can_attempt(max_attempts=self._config.max_attempts)

            stored_code = self._secret_cipher.decrypt(ciphertext=challenge_entity.code_ciphertext)
            # Байты, а не str: схема пропускает не-ASCII цифры, а compare_digest на таких str бросает TypeError.
            if not hmac.compare_digest(stored_code.encode(), command.code.get_secret_value().encode()):
                challenge_entity.register_failed_attempt()
                await self._uow.challenge_repository.update_challenge_by_id(challenge_entity=challenge_entity)
                await self._uow.commit()
                raise VerificationCodeInvalidError()

            challenge_entity.mark_used()
            user_credentials_entity.mark_email_verified()
            await self._uow.challenge_repository.update_challenge_by_id(challenge_entity=challenge_entity)
            await self._uow.user_credentials_repository.update_user_credentials_by_user_id(
                user_credentials_entity=user_credentials_entity
            )
            await self._uow.commit()
