import uuid

from sqlalchemy import REAL, Index, Integer, String, Uuid, column, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import BaseDBModel


class GeoCity(BaseDBModel):
    """
    Город газеттира.

    Индексы:
        ix_geo_cities_name_en_prefix: btree ``lower(name_en) text_pattern_ops`` — автокомплит
            по английскому имени (``LIKE 'q%'``).
        ix_geo_cities_name_ru_prefix: то же по ``lower(name_ru)`` — автокомплит по русскому.
    """

    __tablename__ = "geo_cities"

    __table_args__ = (
        Index(
            "ix_geo_cities_name_en_prefix",
            func.lower(column("name_en")).label("name_en_lower"),
            postgresql_ops={"name_en_lower": "text_pattern_ops"},
        ),
        Index(
            "ix_geo_cities_name_ru_prefix",
            func.lower(column("name_ru")).label("name_ru_lower"),
            postgresql_ops={"name_ru_lower": "text_pattern_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(255), unique=True)
    name_en: Mapped[str] = mapped_column(String(200))
    name_ru: Mapped[str | None] = mapped_column(String(200))
    country_code: Mapped[str] = mapped_column(String(2))
    latitude: Mapped[float] = mapped_column(REAL)
    longitude: Mapped[float] = mapped_column(REAL)
    population: Mapped[int | None] = mapped_column(Integer)
