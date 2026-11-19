import uuid

from sqlalchemy import ARRAY, REAL, CheckConstraint, Index, Integer, String, Uuid, column, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import BaseDBModel


class GeoPlace(BaseDBModel):
    """
    Место газеттира: озеро, гора, хребет, национальный парк.

    ``latitude``/``longitude`` — опорная точка места (подпись, маркер), а не его форма.
    ``notability`` — известность объекта в мире, порядок в поиске; сейчас это число сайтов
    Wikimedia со статьёй о нём.

    Индексы:
        ix_geo_places_name_en_prefix: btree ``lower(name_en) text_pattern_ops`` — префиксный поиск
            по английскому имени (``LIKE 'q%'``).
        ix_geo_places_name_ru_prefix: то же по ``lower(name_ru)`` — поиск по русскому.
    """

    __tablename__ = "geo_places"

    __table_args__ = (
        CheckConstraint("cardinality(country_codes) >= 1", name="ck_geo_places_country_codes_not_empty"),
        Index(
            "ix_geo_places_name_en_prefix",
            func.lower(column("name_en")).label("name_en_lower"),
            postgresql_ops={"name_en_lower": "text_pattern_ops"},
        ),
        Index(
            "ix_geo_places_name_ru_prefix",
            func.lower(column("name_ru")).label("name_ru_lower"),
            postgresql_ops={"name_ru_lower": "text_pattern_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(255), unique=True)
    kind: Mapped[str] = mapped_column(String(30))
    name_en: Mapped[str] = mapped_column(String(200))
    name_ru: Mapped[str | None] = mapped_column(String(200))
    country_codes: Mapped[list[str]] = mapped_column(ARRAY(String(2)))
    latitude: Mapped[float] = mapped_column(REAL)
    longitude: Mapped[float] = mapped_column(REAL)
    notability: Mapped[int] = mapped_column(Integer)
