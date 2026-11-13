from app.auth.application.ports.unit_of_work import AuthUnitOfWorkPort
from app.auth.application.ports.users_client import CreateUserRequest, UsersClientPort
from app.auth.application.schemas.commands import LoginCommand, RegistrationCommand
from app.auth.application.schemas.metadata import ClientMetadata
from app.auth.application.schemas.results import TokenPairResult
from app.auth.application.services.email_verification import EmailVerificationService
from app.auth.application.services.token_issuer import TokenIssuer
from app.auth.domain.entities import UserCredentialsEntity
from app.auth.domain.value_objects import Password
from app.auth.exceptions import (
    EmailAlreadyExistError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    UsernameAlreadyExistError,
)
from app.shared.infra.crypto import SaltedHasherPort


class AuthService:
    def __init__(
        self,
        *,
        uow: AuthUnitOfWorkPort,
        users_client: UsersClientPort,
        salted_hasher: SaltedHasherPort,
        token_issuer: TokenIssuer,
        email_verification_service: EmailVerificationService,
    ) -> None:
        self._uow = uow
        self._users_client = users_client
        self._salted_hasher = salted_hasher
        self._token_issuer = token_issuer
        self._email_verification_service = email_verification_service

    async def register(
        self,
        *,
        command: RegistrationCommand,
        client_metadata: ClientMetadata,
    ) -> TokenPairResult:
        """
        Регистрирует пользователя.

        Учётные данные, профиль пользователя и refresh-токен сохраняются одной транзакцией; после
        неё запрашивается код подтверждения email.

        Scenarios:
            - регистрация на странице «Создать аккаунт»

        Args:
            command: Username, email, пароль и согласие на рассылку
            client_metadata: IP/user-agent для аудита refresh-токена

        Returns:
            Пара access + refresh для presentation-слоя

        Raises:
            EmailAlreadyExistError: email уже занят
            UsernameAlreadyExistError: username уже занят
        """
        async with self._uow.transaction():
            await self._ensure_credentials_unique(email=command.email, username=command.username)
            password = Password(hash=self._salted_hasher.hash(secret=command.password.get_secret_value()))
            user_credentials_entity = UserCredentialsEntity.create(
                email=command.email,
                username=command.username,
                password=password,
            )
            await self._uow.user_credentials_repository.insert_user_credentials(
                user_credentials_entity=user_credentials_entity
            )
            # Материализуем родителя до зависимого refresh_token: INSERT user_credentials
            # должен уйти в БД раньше INSERT refresh_tokens (FK refresh_tokens.user_id →
            # user_credentials.user_id). Порядок INSERT'ов между мапперами в одном flush на
            # commit'е не гарантирован, поэтому фиксируем его явным flush'ем здесь.
            await self._uow.flush()
            await self._users_client.create_user(
                request=CreateUserRequest(
                    user_id=user_credentials_entity.user_id,
                    display_name=command.username,
                    marketing_emails_consent=command.marketing_emails_consent,
                    terms_accepted_at=user_credentials_entity.created_at,
                ),
            )

            refresh_secret, refresh_token_entity = self._token_issuer.issue_refresh_token(
                user_id=user_credentials_entity.user_id,
                client_metadata=client_metadata,
            )
            await self._uow.refresh_token_repository.insert_refresh_token(refresh_token_entity=refresh_token_entity)
            await self._uow.commit()

        # Вне транзакции register'а: own transaction()/commit (atomic-defer письма) — поэтому ПОСЛЕ блока.
        await self._email_verification_service.request_email_verification(user_id=user_credentials_entity.user_id)

        return self._token_issuer.build_token_pair(
            user_credentials_entity=user_credentials_entity,
            refresh_secret=refresh_secret,
            refresh_token_entity=refresh_token_entity,
        )

    async def _ensure_credentials_unique(self, *, email: str, username: str) -> None:
        """
        Гарантирует, что email и username ещё не заняты другой учётной записью.

        Scenarios:
            - регистрация

        Args:
            email: Email новой учётной записи
            username: Username новой учётной записи

        Raises:
            EmailAlreadyExistError: email уже занят
            UsernameAlreadyExistError: username уже занят
        """
        email_owner_entity = await self._uow.user_credentials_repository.find_user_credentials_by_email(email=email)
        if email_owner_entity is not None:
            raise EmailAlreadyExistError()

        username_owner_entity = await self._uow.user_credentials_repository.find_user_credentials_by_username(
            username=username,
        )
        if username_owner_entity is not None:
            raise UsernameAlreadyExistError()

    async def login(self, *, command: LoginCommand, client_metadata: ClientMetadata) -> TokenPairResult:
        """
        Аутентифицирует пользователя по email/username и паролю.

        Любая ошибка (нет такого пользователя, неверный пароль) превращается
        в один и тот же ``InvalidCredentialsError`` — это не даёт атакующему
        отличить "несуществующий логин" от "неверный пароль" по коду ответа.

        Timing-attack mitigation: если по логину никого не найдено, введённый пароль
        всё равно хешируется — столько же работы, сколько у проверки найденного. Без
        этого юзер-enumeration был бы тривиален по разнице во времени ответа.

        Scenarios:
            - вход

        Args:
            command: Введённые логин и пароль
            client_metadata: IP/user-agent для аудита refresh-токена

        Returns:
            Пара access + refresh для presentation-слоя

        Raises:
            InvalidCredentialsError: Логин не найден или пароль не совпал
        """
        async with self._uow.transaction():
            user_credentials_entity = await self._uow.user_credentials_repository.find_user_credentials_by_login(
                login=command.login,
            )
            if user_credentials_entity is None:
                # Результат не нужен: хеш стоит столько же, сколько verify ниже, и ответ по
                # несуществующему логину не приходит заметно быстрее, чем по существующему.
                self._salted_hasher.hash(secret=command.password.get_secret_value())
                raise InvalidCredentialsError()

            if not self._salted_hasher.verify(
                secret=command.password.get_secret_value(),
                hashed=user_credentials_entity.password.hash,
            ):
                raise InvalidCredentialsError()

            refresh_secret, refresh_token_entity = self._token_issuer.issue_refresh_token(
                user_id=user_credentials_entity.user_id,
                client_metadata=client_metadata,
            )
            await self._uow.refresh_token_repository.insert_refresh_token(refresh_token_entity=refresh_token_entity)
            await self._uow.commit()

        return self._token_issuer.build_token_pair(
            user_credentials_entity=user_credentials_entity,
            refresh_secret=refresh_secret,
            refresh_token_entity=refresh_token_entity,
        )

    async def logout(self, refresh_secret: str | None) -> None:
        """
        Отзывает текущий refresh-токен по секрету из cookie.

        Идемпотентная операция: отсутствие cookie / неизвестный секрет /
        уже revoked-токен — все три случая завершаются молча, без ошибки.
        Это позволяет фронту звать /logout без предварительной проверки
        состояния и без боязни race с другим табом.

        Scenarios:
            - выход из аккаунта кнопкой в шапке

        Args:
            refresh_secret: Plaintext-секрет из cookie или ``None``, если cookie не пришла
        """
        if refresh_secret is None:
            return

        async with self._uow.transaction():
            token_hash = self._token_issuer.hash_refresh_secret(refresh_secret=refresh_secret)
            refresh_token_entity = await self._uow.refresh_token_repository.find_refresh_token_by_hash_for_update(
                token_hash=token_hash,
            )
            if refresh_token_entity is None or refresh_token_entity.is_revoked:
                return

            refresh_token_entity.revoke()
            await self._uow.refresh_token_repository.update_refresh_token_by_id(
                refresh_token_entity=refresh_token_entity
            )
            await self._uow.commit()

    async def refresh(self, *, refresh_secret: str, client_metadata: ClientMetadata) -> TokenPairResult:
        """
        Ротация refresh-токена с reuse detection (OAuth 2.1).

        Поток:
          1. По hash'у секрета берём строку под ``FOR UPDATE`` — параллельные
             /refresh с одним секретом сериализуются.
          2. Если токен уже revoked — это reuse: либо двойной /refresh, либо
             утечка cookie. Защитная реакция — отозвать все активные refresh-токены
             пользователя и вернуть 401, чтобы вынудить полный re-login.
          3. Если истёк — 401 без побочных эффектов.
          4. Подгружаем credentials по ``user_id`` (нужно для нового access-token'а).
             Если их нет — race с удалением аккаунта, 401.
          5. Старый токен помечаем revoked, выпускаем новый, всё одной транзакцией.

        Scenarios:
            - восстановление сессии при открытии приложения
            - повтор запроса, получившего 401 из-за истёкшего access-токена
            - новый access-токен после подтверждения email

        Args:
            refresh_secret: Plaintext-секрет из cookie
            client_metadata: IP/user-agent для аудита нового refresh-токена

        Returns:
            Новая пара access + refresh

        Raises:
            InvalidRefreshTokenError: Секрет не найден / уже revoked / истёк / связанный аккаунт не существует
        """
        async with self._uow.transaction():
            token_hash = self._token_issuer.hash_refresh_secret(refresh_secret=refresh_secret)
            refresh_token_entity = await self._uow.refresh_token_repository.find_refresh_token_by_hash_for_update(
                token_hash=token_hash,
            )
            if refresh_token_entity is None:
                raise InvalidRefreshTokenError()

            if refresh_token_entity.is_revoked:
                await self._uow.refresh_token_repository.revoke_all_active_refresh_tokens_by_user_id(
                    user_id=refresh_token_entity.user_id,
                )
                await self._uow.commit()
                raise InvalidRefreshTokenError()

            if refresh_token_entity.is_expired:
                raise InvalidRefreshTokenError()

            user_credentials_entity = await self._uow.user_credentials_repository.find_user_credentials_by_user_id(
                user_id=refresh_token_entity.user_id,
            )
            if user_credentials_entity is None:
                raise InvalidRefreshTokenError()

            refresh_token_entity.revoke()
            await self._uow.refresh_token_repository.update_refresh_token_by_id(
                refresh_token_entity=refresh_token_entity
            )

            new_refresh_secret, new_refresh_token_entity = self._token_issuer.issue_refresh_token(
                user_id=refresh_token_entity.user_id,
                client_metadata=client_metadata,
            )
            await self._uow.refresh_token_repository.insert_refresh_token(refresh_token_entity=new_refresh_token_entity)
            await self._uow.commit()

        return self._token_issuer.build_token_pair(
            user_credentials_entity=user_credentials_entity,
            refresh_secret=new_refresh_secret,
            refresh_token_entity=new_refresh_token_entity,
        )
