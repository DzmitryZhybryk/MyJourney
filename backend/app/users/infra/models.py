import datetime as dt
import uuid

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import BaseDBModel
from app.shared.models.base_model import DateTimeMixin


class User(DateTimeMixin, BaseDBModel):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(50))
    terms_accepted_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    marketing_emails_consent: Mapped[bool] = mapped_column(default=False)
