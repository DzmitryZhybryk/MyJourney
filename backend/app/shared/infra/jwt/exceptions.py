from app.shared.exceptions import UnauthenticatedError


class InvalidAccessTokenError(UnauthenticatedError):
    """
    Bearer access-токен отсутствует или не прошёл валидацию.

    Код сохраняет исторический префикс ``auth.`` — это стабильный внешний контракт
    (фронт маппит его в текст, api-тесты пиннят), и менять его вместе с переездом
    класса из домена auth в shared нельзя.
    """

    code = "auth.invalid_access_token"
    message = "Невалидный или истёкший access-токен"
