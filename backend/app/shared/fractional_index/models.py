from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import BaseDBModel


class SortKeyModel(BaseDBModel):
    """
    База для модели с ручным порядком строк: колонка ``sort_key`` — дробный ключ.

    Коллация ``"C"``: ключи сравниваются побайтно, как их строит ``generate_key_between``;
    языковая коллация (``a < B``) разошлась бы с ним (``B < a``). Уникальный индекс по области
    и ``sort_key`` модель объявляет сама — область у каждой сущности своя.
    """

    __abstract__ = True

    sort_key: Mapped[str] = mapped_column(Text(collation="C"))
