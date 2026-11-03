from fastapi import Request, Response

from app.auth.application.schemas.results import TokenPairResult

_REFRESH_COOKIE_NAME = "refresh_token"
_COOKIE_PATH = "/"
_COOKIE_SAMESITE = "lax"


def set_refresh_token_cookie(*, response: Response, token_pair: TokenPairResult) -> None:
    """
    Устанавливает refresh-токен в HttpOnly Secure cookie.

    HttpOnly защищает токен от XSS (недоступен из JavaScript), Secure
    передаёт cookie только по HTTPS, SameSite=lax ограничивает отправку
    при cross-site запросах. Значение — plaintext-секрет; в БД лежит
    только его детерминированный hash.

    Scenarios:
        - регистрация
        - вход
        - обновление сессии

    Args:
        response: HTTP-ответ FastAPI, в который добавляется cookie
        token_pair: Пара токенов, из которой берётся refresh-секрет и его срок жизни
    """
    response.set_cookie(
        key=_REFRESH_COOKIE_NAME,
        value=token_pair.refresh_token.secret.get_secret_value(),
        httponly=True,
        secure=True,
        samesite=_COOKIE_SAMESITE,
        path=_COOKIE_PATH,
        expires=int(token_pair.refresh_token.expires_at.timestamp()),
    )


def read_refresh_token_cookie(request: Request) -> str | None:
    """
    Возвращает plaintext-значение refresh-cookie или ``None``, если cookie нет.

    Scenarios:
        - выход из аккаунта
        - обновление сессии

    Args:
        request: HTTP-запрос FastAPI

    Returns:
        Plaintext-секрет refresh-токена либо ``None``
    """
    return request.cookies.get(_REFRESH_COOKIE_NAME)


def clear_refresh_token_cookie(response: Response) -> None:
    """
    Очищает refresh-cookie у клиента.

    Атрибуты ``path``/``samesite`` дублируют параметры ``set_refresh_token_cookie``:
    браузер удаляет cookie только при совпадающем (name, path, domain), а
    SameSite/Secure не должны конфликтовать с ранее установленным значением.

    Scenarios:
        - выход из аккаунта

    Args:
        response: HTTP-ответ FastAPI, в который добавляется ``Set-Cookie: ...; Max-Age=0``
    """
    response.delete_cookie(
        key=_REFRESH_COOKIE_NAME,
        path=_COOKIE_PATH,
        samesite=_COOKIE_SAMESITE,
        secure=True,
        httponly=True,
    )
