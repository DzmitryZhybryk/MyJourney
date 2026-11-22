import datetime as dt

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BaseDBModel(DeclarativeBase):
    """Базовый класс декларативных моделей. Используется в миграциях Alembic."""


class DateTimeMixin:
    """
    Mixin для добавления полей дат создания, обновления и удаления.
    """

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: dt.datetime.now(tz=dt.UTC),
    )
    updated_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), default=None)
