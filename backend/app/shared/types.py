from typing import Any

type OptionalDict = dict[str, Any] | None
type DictStrAny = dict[str, Any]
type OpenAPIResponses = dict[int | str, DictStrAny]


__all__ = [
    "DictStrAny",
    "OpenAPIResponses",
    "OptionalDict",
]
