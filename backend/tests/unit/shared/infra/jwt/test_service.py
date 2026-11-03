import datetime as dt
from uuid import uuid4

import jwt
import pytest

from app.shared.infra.jwt import JWTDecodeError
from app.shared.infra.jwt.service import JWTService


def test_decode_access_token_roundtrips_user_id(jwt_service: JWTService) -> None:
    """Токен, выпущенный сервисом, декодируется обратно в тот же user_id."""
    user_id = uuid4()

    token = jwt_service.create_access_token(user_id=user_id, role="free", email_verified=True)

    assert jwt_service.decode_access_token(token) == user_id


def test_decode_access_token_invalid_signature_raises(jwt_service: JWTService, jwt_algorithm: str) -> None:
    """Токен, подписанный чужим секретом, → JWTDecodeError (неверная подпись)."""
    token = jwt.encode({"sub": str(uuid4())}, "another-secret-at-least-32-bytes-long", algorithm=jwt_algorithm)

    with pytest.raises(JWTDecodeError):
        jwt_service.decode_access_token(token)


def test_decode_access_token_expired_raises(jwt_service: JWTService, jwt_secret: str, jwt_algorithm: str) -> None:
    """Истёкший токен (exp в прошлом) → JWTDecodeError."""
    expired_at = dt.datetime.now(tz=dt.UTC) - dt.timedelta(minutes=1)
    token = jwt.encode({"sub": str(uuid4()), "exp": expired_at}, jwt_secret, algorithm=jwt_algorithm)

    with pytest.raises(JWTDecodeError):
        jwt_service.decode_access_token(token)


def test_decode_access_token_malformed_raises(jwt_service: JWTService) -> None:
    """Строка, не являющаяся JWT, → JWTDecodeError."""
    with pytest.raises(JWTDecodeError):
        jwt_service.decode_access_token("not-a-jwt")


def test_decode_access_token_missing_sub_raises(
    jwt_service: JWTService,
    jwt_secret: str,
    jwt_algorithm: str,
) -> None:
    """Валидная подпись, но claim sub отсутствует → JWTDecodeError."""
    token = jwt.encode({"role": "free"}, jwt_secret, algorithm=jwt_algorithm)

    with pytest.raises(JWTDecodeError):
        jwt_service.decode_access_token(token)


def test_decode_access_token_non_uuid_sub_raises(jwt_service: JWTService, jwt_secret: str, jwt_algorithm: str) -> None:
    """Валидная подпись, sub-строка, но не UUID → JWTDecodeError."""
    token = jwt.encode({"sub": "not-a-uuid"}, jwt_secret, algorithm=jwt_algorithm)

    with pytest.raises(JWTDecodeError):
        jwt_service.decode_access_token(token)
