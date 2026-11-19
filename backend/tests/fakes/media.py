"""Фейк сырого потока ответа S3: тело ``GetObject`` для ``StreamingBody`` aiobotocore без сети."""


class FakeS3ResponseContent:
    """
    Поток содержимого ответа: отдаёт заданные байты или падает заданной ошибкой.

    ``error`` моделирует обрыв соединения посреди тела.
    """

    def __init__(self, *, body: bytes, error: Exception | None) -> None:
        self._body = body
        self._error = error

    async def read(self, amount: int = -1) -> bytes:
        if self._error is not None:
            raise self._error

        if amount < 0:
            chunk, self._body = self._body, b""
        else:
            chunk, self._body = self._body[:amount], self._body[amount:]

        return chunk


class FakeS3ResponseStream:
    """
    Сырой ответ, который ``StreamingBody`` читает через ``content`` и закрывает через ``close``.

    ``is_closed`` показывает, закрыл ли читатель поток.
    """

    def __init__(self, *, body: bytes, error: Exception | None = None) -> None:
        self.content = FakeS3ResponseContent(body=body, error=error)
        self.url = "http://s3.localhost:9050"
        self.is_closed = False

    def close(self) -> None:
        self.is_closed = True
