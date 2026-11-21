import datetime as dt
from uuid import UUID

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import BaseDBModel


class VersionedConfigModel(BaseDBModel):
    """
    База таблицы конфига домена: строка — весь конфиг одной версии, строки только добавляются.

    Текущий конфиг — строка с наибольшей ``version``. Колонку ``config`` наследник объявляет сам —
    через ``PydanticJSONB`` со схемой своего домена. ``created_by`` — аккаунт, правивший конфиг; у правки
    человека он есть всегда, а ``NULL`` значит «записано развёртыванием»: начальное значение или миграция.
    """

    __abstract__ = True

    version: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: dt.datetime.now(tz=dt.UTC),
    )
    created_by: Mapped[UUID | None]
