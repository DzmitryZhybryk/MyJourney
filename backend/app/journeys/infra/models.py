import uuid

from sqlalchemy import REAL, Index, SmallInteger, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.fractional_index.models import SortKeyModel
from app.shared.models.base_model import DateTimeMixin


class Journey(DateTimeMixin, SortKeyModel):
    """
    Поездка пользователя: откуда, куда, на чём и когда.

    Города — ссылки на справочник geo плюс страна и координаты, названий здесь нет. Внешних
    ключей на geo и users нет: это другие домены. Когда — только год.

    ``sort_key`` — ручной порядок внутри года: уникален среди неудалённых поездок пользователя
    за год, индекс заодно обслуживает ленту.
    """

    __tablename__ = "journeys"
    __table_args__ = (
        # Должен совпадать с миграцией.
        Index(
            "ix_journeys_active_user_id_year_sort_key",
            "user_id",
            text("traveled_year DESC"),
            "sort_key",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column()

    origin_city_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    origin_country_code: Mapped[str] = mapped_column(String(2))
    origin_latitude: Mapped[float] = mapped_column(REAL)
    origin_longitude: Mapped[float] = mapped_column(REAL)

    destination_city_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    destination_country_code: Mapped[str] = mapped_column(String(2))
    destination_latitude: Mapped[float] = mapped_column(REAL)
    destination_longitude: Mapped[float] = mapped_column(REAL)

    transport_type: Mapped[str] = mapped_column(String(20))
    distance_km: Mapped[int] = mapped_column(SmallInteger)
    traveled_year: Mapped[int] = mapped_column(SmallInteger)
