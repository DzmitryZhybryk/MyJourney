import time
from collections.abc import Sequence
from typing import Final

import httpx

from app.shared.types import DictStrAny

WIKIDATA_SPARQL_URL: Final[str] = "https://query.wikidata.org/sparql"

# Политика Wikidata Query Service требует User-Agent с контактом владельца клиента.
USER_AGENT: Final[str] = "MyJourney-gazetteer/1.0 (https://github.com/DzmitryZhybryk/MyJourney)"

# Сервис под нагрузкой отвечает этими кодами; запрос стоит повторить, а не ронять всю сборку.
_TRANSIENT_STATUSES: Final[frozenset[int]] = frozenset({429, 500, 502, 503, 504})
RETRY_DELAYS_SECONDS: Final[tuple[float, ...]] = (10.0, 30.0, 60.0, 120.0)


def fetch_sparql_bindings(
    *,
    query: str,
    http_client: httpx.Client,
    retry_delays: Sequence[float] = RETRY_DELAYS_SECONDS,
) -> tuple[DictStrAny, ...]:
    """
    Выполняет SPARQL-запрос к Wikidata, повторяя его после пауз, пока сервис отвечает временной ошибкой.

    Scenarios:
        - сборка новой версии датасета с русскими названиями из Wikidata
        - сборка новой версии датасета мест из Wikidata

    Args:
        query: SPARQL-запрос
        http_client: HTTP-клиент
        retry_delays: Паузы перед повторами запроса, который сервис отклонил временно

    Returns:
        Строки ответа SPARQL как есть

    Raises:
        httpx.HTTPError: запрос к Wikidata не удался, в том числе после всех повторов
    """
    for delay in retry_delays:
        response = _send_query(http_client=http_client, query=query)
        if response.status_code not in _TRANSIENT_STATUSES:
            return tuple(response.raise_for_status().json()["results"]["bindings"])

        time.sleep(delay)

    response = _send_query(http_client=http_client, query=query).raise_for_status()
    return tuple(response.json()["results"]["bindings"])


def _send_query(*, http_client: httpx.Client, query: str) -> httpx.Response:
    return http_client.post(
        WIKIDATA_SPARQL_URL,
        data={"query": query, "format": "json"},
        headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
    )
