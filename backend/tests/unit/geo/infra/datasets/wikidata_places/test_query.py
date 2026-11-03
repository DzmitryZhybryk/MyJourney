"""Unit-тесты запроса мест одного класса у Wikidata."""

import json
from urllib.parse import parse_qs

import httpx

from app.geo.infra.datasets.wikidata_places.query import fetch_class_bindings


def test_fetch_class_bindings_queries_class_above_sitelinks_threshold() -> None:
    """fetch_class_bindings: в запрос подставлены класс и порог sitelinks, строки ответа возвращаются как есть."""
    queries: list[str] = []
    bindings = [{"item": {"value": "http://www.wikidata.org/entity/Q724367"}}]

    def handler(request: httpx.Request) -> httpx.Response:
        queries.append(parse_qs(request.content.decode())["query"][0])
        return httpx.Response(200, content=json.dumps({"results": {"bindings": bindings}}))

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        result = fetch_class_bindings(class_qid="Q8502", min_sitelinks=4, http_client=http_client)

    assert result == tuple(bindings)
    [query] = queries
    assert "wdt:P279* wd:Q8502 ;" in query
    assert "FILTER(?links >= 4)" in query
