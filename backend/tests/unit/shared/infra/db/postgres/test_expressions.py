import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.shared.enums import SortDirectionEnum
from app.shared.infra.db.postgres.expressions import directed_order


class _Base(DeclarativeBase):
    pass


class _Row(_Base):
    __tablename__ = "rows"

    row_id: Mapped[int] = mapped_column(primary_key=True)


@pytest.mark.parametrize(("direction", "keyword"), [(SortDirectionEnum.ASC, "ASC"), (SortDirectionEnum.DESC, "DESC")])
def test_directed_order_sorts_column_in_given_direction(direction: SortDirectionEnum, keyword: str) -> None:
    """``directed_order`` сортирует колонку в переданном направлении."""
    query = select(_Row.row_id).order_by(directed_order(column=_Row.row_id, direction=direction))

    compiled = str(query.compile(dialect=postgresql.dialect()))

    assert compiled.endswith(f"ORDER BY rows.row_id {keyword}")
