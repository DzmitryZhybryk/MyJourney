"""Unit-тесты клиента Wikidata Query Service."""

import json
from urllib.parse import parse_qs

import httpx
import pytest

from app.geo.infra.datasets.wikidata.sparql import USER_AGENT, fetch_sparql_bindings

_BINDINGS = [{"gn": {"value": "1"}, "label": {"value": "Москва"}}]
_BODY = json.dumps({"results": {"bindings": _BINDINGS}})


def test_fetch_sparql_bindings_sends_query_and_returns_bindings() -> None:
    """fetch_sparql_bindings: запрос уходит с User-Agent владельца, строки ответа возвращаются как есть."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=_BODY)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        bindings = fetch_sparql_bindings(query="SELECT ?gn ?label WHERE {}", http_client=http_client)

    assert bindings == tuple(_BINDINGS)
    [request] = requests
    assert request.headers["User-Agent"] == USER_AGENT
    assert parse_qs(request.content.decode())["query"] == ["SELECT ?gn ?label WHERE {}"]


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_fetch_sparql_bindings_retries_transient_error(status: int) -> None:
    """fetch_sparql_bindings: сервис перегружен или ограничил частоту → запрос повторяется, результат приходит."""
    statuses = iter([status, 200])
    transport = httpx.MockTransport(lambda request: httpx.Response(next(statuses), content=_BODY))

    with httpx.Client(transport=transport) as http_client:
        bindings = fetch_sparql_bindings(query="SELECT", http_client=http_client, retry_delays=(0.0,))

    assert bindings == tuple(_BINDINGS)


def test_fetch_sparql_bindings_raises_after_retries_run_out() -> None:
    """fetch_sparql_bindings: временная ошибка не проходит за все повторы → исключение, а не пустой результат."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(503)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client, pytest.raises(httpx.HTTPStatusError):
        fetch_sparql_bindings(query="SELECT", http_client=http_client, retry_delays=(0.0, 0.0))

    assert len(requests) == 3


def test_fetch_sparql_bindings_does_not_retry_permanent_error() -> None:
    """fetch_sparql_bindings: ошибка запроса (400) повтором не лечится → исключение сразу, без повторов."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(400)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client, pytest.raises(httpx.HTTPStatusError):
        fetch_sparql_bindings(query="SELECT", http_client=http_client, retry_delays=(0.0, 0.0))

    assert len(requests) == 1
