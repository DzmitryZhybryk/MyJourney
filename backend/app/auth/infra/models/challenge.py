import datetime as dt
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import BaseDBModel
from app.shared.models.base_model import DateTimeMixin


class Challenge(DateTimeMixin, BaseDBModel):
    __tablename__ = "challenges"
    __table_args__ = (
        # Один активный challenge данного типа на пользователя; обеспечивается
        # композитным партиальным unique-индексом. Должен совпадать с миграцией.
        Index(
            "ix_challenges_active_user_id_type",
            "user_id",
            "challenge_type",
            unique=True,
            postgresql_where=text("used_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_credentials.user_id", ondelete="CASCADE"),
    )
    challenge_type: Mapped[str] = mapped_column(String(32))
    code_ciphertext: Mapped[str] = mapped_column(Text())
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    last_sent_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(default=0)
    used_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), default=None)
