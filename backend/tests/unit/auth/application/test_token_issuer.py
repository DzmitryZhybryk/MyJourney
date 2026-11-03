import datetime as dt
from uuid import uuid4

from app.auth.application.schemas.metadata import ClientMetadata
from app.auth.application.services.token_issuer import TokenIssuer
from app.shared.infra.crypto.sha256 import Sha256DeterministicHasher
from app.shared.infra.jwt.service import JWTService
from tests.builders import make_user_credentials


def test_hash_refresh_secret_is_deterministic(
    token_issuer: TokenIssuer,
    deterministic_hasher: Sha256DeterministicHasher,
) -> None:
    """`hash_refresh_secret` детерминирован и равен digest'у используемого hasher'а."""
    secret = "refresh-secret"

    first = token_issuer.hash_refresh_secret(refresh_secret=secret)
    second = token_issuer.hash_refresh_secret(refresh_secret=secret)

    assert first == second
    assert first == deterministic_hasher.digest(secret=secret)


def test_issue_refresh_token_stores_digest_and_propagates_metadata(
    token_issuer: TokenIssuer,
    deterministic_hasher: Sha256DeterministicHasher,
) -> None:
    """`issue_refresh_token`: в БД ложится digest plaintext-секрета, метаданные пробрасываются, expiry в будущем."""
    user_id = uuid4()
    metadata = ClientMetadata(ip_address="10.0.0.1", user_agent="UA/1.0")

    plaintext, refresh_token_entity = token_issuer.issue_refresh_token(user_id=user_id, client_metadata=metadata)

    assert refresh_token_entity.token_hash == deterministic_hasher.digest(secret=plaintext)
    assert refresh_token_entity.user_id == user_id
    assert refresh_token_entity.ip_address == "10.0.0.1"
    assert refresh_token_entity.user_agent == "UA/1.0"
    assert refresh_token_entity.expires_at > dt.datetime.now(tz=dt.UTC)


def test_issue_refresh_token_secret_is_unpredictable(token_issuer: TokenIssuer) -> None:
    """Plaintext-секрет каждый раз новый (high-entropy), а не предсказуемый."""
    first_secret, _ = token_issuer.issue_refresh_token(user_id=uuid4(), client_metadata=ClientMetadata())
    second_secret, _ = token_issuer.issue_refresh_token(user_id=uuid4(), client_metadata=ClientMetadata())

    assert first_secret != second_secret


def test_build_token_pair_access_token_decodes_back_to_user(
    token_issuer: TokenIssuer,
    jwt_service: JWTService,
) -> None:
    """`build_token_pair`: access-token декодируется обратно в user_id, refresh-секрет и expiry пробрасываются."""
    user_credentials_entity = make_user_credentials()
    refresh_secret, refresh_token_entity = token_issuer.issue_refresh_token(
        user_id=user_credentials_entity.user_id,
        client_metadata=ClientMetadata(),
    )

    pair = token_issuer.build_token_pair(
        user_credentials_entity=user_credentials_entity,
        refresh_secret=refresh_secret,
        refresh_token_entity=refresh_token_entity,
    )

    assert jwt_service.decode_access_token(pair.access_token.get_secret_value()) == user_credentials_entity.user_id
    assert pair.refresh_token.secret.get_secret_value() == refresh_secret
    assert pair.refresh_token.expires_at == refresh_token_entity.expires_at
