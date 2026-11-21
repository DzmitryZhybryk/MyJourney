from pydantic import BaseModel
from sqlalchemy import literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.models.pydantic_jsonb import PydanticJSONB


class _Limits(BaseModel):
    size: int


class _Other(BaseModel):
    size: int


async def test_pydantic_jsonb_same_sql_with_other_model_parsed_by_that_model(db_session: AsyncSession) -> None:
    """Один и тот же SQL, прочитанный другой моделью, разбирается ею, а не моделью из кэша первого запроса."""
    config_sql = """'{"size": 5}'::jsonb"""

    first = await db_session.scalar(select(literal_column(config_sql, type_=PydanticJSONB(_Limits))))
    second = await db_session.scalar(select(literal_column(config_sql, type_=PydanticJSONB(_Other))))

    assert (type(first), type(second)) == (_Limits, _Other)
