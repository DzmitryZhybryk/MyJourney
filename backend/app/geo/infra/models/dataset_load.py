import datetime as dt

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import BaseDBModel


class GeoDatasetLoad(BaseDBModel):
    """
    Журнал загрузок датасетов газеттира.

    Перед загрузкой загрузчик ищет здесь строку с именем, версией и sha256 датасета из
    ``manifest.toml``: нашёл — пропускает датасет, нет — загружает и записывает строку.
    Так повторный запуск ничего не скачивает, а новая версия в манифесте подхватывается.
    """

    __tablename__ = "geo_dataset_loads"

    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    version: Mapped[str] = mapped_column(String(50))
    sha256: Mapped[str] = mapped_column(String(64))
    loaded_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
