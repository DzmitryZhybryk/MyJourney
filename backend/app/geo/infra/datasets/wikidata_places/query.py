from typing import Final

import httpx

from app.geo.domain.enums import PlaceKindEnum
from app.geo.infra.datasets.wikidata.sparql import fetch_sparql_bindings
from app.shared.types import DictStrAny

# Классы Wikidata от узкого к широкому: место получает тип первого класса, в который попало
# (водохранилище — подкласс озера, вулкан — подкласс горы).
PLACE_CLASSES: Final[tuple[tuple[PlaceKindEnum, tuple[str, ...]], ...]] = (
    (PlaceKindEnum.RESERVOIR, ("Q131681",)),
    (PlaceKindEnum.LAKE, ("Q23397", "Q5926864")),
    (PlaceKindEnum.VOLCANO, ("Q8072",)),
    (PlaceKindEnum.MOUNTAIN, ("Q8502",)),
    (PlaceKindEnum.MOUNTAIN_RANGE, ("Q46831",)),
    (PlaceKindEnum.WATERFALL, ("Q34038",)),
    (PlaceKindEnum.GLACIER, ("Q35666",)),
    (PlaceKindEnum.MOUNTAIN_PASS, ("Q133056",)),
    (PlaceKindEnum.NATIONAL_PARK, ("Q46169",)),
    (PlaceKindEnum.NATURE_RESERVE, ("Q179049",)),
)

# P31/P279* — экземпляр класса или его подклассов; P625 — координаты; P17 — страна, P297 — её код
# ISO 3166-1 alpha-2, P576 — дата упразднения (у СССР, Югославии и т.п.).
_QUERY_TEMPLATE: Final[str] = """
SELECT ?item ?links ?coord ?en ?ru ?iso WHERE {{
  ?item wdt:P31/wdt:P279* wd:{class_qid} ; wikibase:sitelinks ?links .
  FILTER(?links >= {min_sitelinks})
  ?item wdt:P625 ?coord .
  OPTIONAL {{ ?item rdfs:label ?en FILTER(lang(?en) = "en") }}
  OPTIONAL {{ ?item rdfs:label ?ru FILTER(lang(?ru) = "ru") }}
  OPTIONAL {{
    ?item wdt:P17 ?country .
    ?country wdt:P297 ?iso .
    FILTER NOT EXISTS {{ ?country wdt:P576 [] }}
  }}
}}
"""


def fetch_class_bindings(*, class_qid: str, min_sitelinks: int, http_client: httpx.Client) -> tuple[DictStrAny, ...]:
    """
    Запрашивает у Wikidata объекты класса с координатами, метками и странами.

    У объекта с несколькими точками или странами в ответе несколько строк — их сводит сборка мест.

    Scenarios:
        - сборка новой версии датасета мест из Wikidata

    Args:
        class_qid: Класс Wikidata (``Q23397`` — озеро)
        min_sitelinks: Нижняя граница числа сайтов Wikimedia со статьёй об объекте
        http_client: HTTP-клиент

    Returns:
        Строки ответа SPARQL как есть

    Raises:
        httpx.HTTPError: запрос к Wikidata не удался, в том числе после всех повторов
    """
    query = _QUERY_TEMPLATE.format(class_qid=class_qid, min_sitelinks=min_sitelinks)
    return fetch_sparql_bindings(query=query, http_client=http_client)
