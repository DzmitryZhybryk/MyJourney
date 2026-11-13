from httpx import AsyncClient


async def test_healthz_returns_200_empty_body(client: AsyncClient) -> None:
    """/healthz/ отвечает 200 с пустым телом — liveness-проба смонтирована в корне."""
    response = await client.get("/healthz/")

    assert response.status_code == 200
    assert response.content == b""
