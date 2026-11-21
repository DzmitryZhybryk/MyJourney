from pydantic import BaseModel
from sqlalchemy.dialects import postgresql

from app.shared.models.pydantic_jsonb import PydanticJSONB


class _Limits(BaseModel):
    size: int
    tags: frozenset[str]


class _Other(BaseModel):
    size: int


_DIALECT = postgresql.dialect()


def test_pydantic_jsonb_roundtrip_returns_equal_model() -> None:
    """Модель уходит в JSON-совместимый dict и читается обратно той же моделью."""
    column_type = PydanticJSONB(_Limits)
    limits = _Limits(size=5, tags=frozenset({"a"}))

    stored = column_type.process_bind_param(limits, _DIALECT)

    assert stored == {"size": 5, "tags": ["a"]}
    assert column_type.process_result_value(stored, _DIALECT) == limits


def test_pydantic_jsonb_none_passes_through_both_ways() -> None:
    """``None`` остаётся ``None`` — в базе это SQL NULL, а не JSON null."""
    column_type = PydanticJSONB(_Limits)

    assert column_type.process_bind_param(None, _DIALECT) is None
    assert column_type.process_result_value(None, _DIALECT) is None


def test_pydantic_jsonb_equality_follows_model_class() -> None:
    """Колонки с разными моделями различаются, иначе кэш SQLAlchemy разобрал бы одну чужой моделью."""
    assert PydanticJSONB(_Limits) == PydanticJSONB(_Limits)
    assert hash(PydanticJSONB(_Limits)) == hash(PydanticJSONB(_Limits))
    assert PydanticJSONB(_Limits) != PydanticJSONB(_Other)
