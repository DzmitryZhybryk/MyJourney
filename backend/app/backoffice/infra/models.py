import datetime as dt
import uuid

from sqlalchemy import DateTime, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infra.db.postgres.models import BaseDBModel


class Account(BaseDBModel):
    __tablename__ = "accounts"
    __table_args__ = (
        Index("ix_accounts_registered_at_user_id", text("registered_at DESC NULLS LAST"), text("user_id DESC")),
        Index("ix_accounts_email_trgm", "email", postgresql_using="gin", postgresql_ops={"email": "gin_trgm_ops"}),
        Index(
            "ix_accounts_display_name_trgm",
            "display_name",
            postgresql_using="gin",
            postgresql_ops={"display_name": "gin_trgm_ops"},
        ),
        {"schema": "backoffice"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)

    email: Mapped[str | None]
    username: Mapped[str | None]
    role: Mapped[str | None]
    plan: Mapped[str | None]
    email_verified_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    registered_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    auth_version: Mapped[int | None]

    display_name: Mapped[str | None]
    marketing_emails_consent: Mapped[bool | None]
    terms_accepted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    users_version: Mapped[int | None]
