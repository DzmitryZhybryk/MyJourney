"""
Migration name: initial schema — users, user_credentials, refresh_tokens, challenges, geo_cities,
geo_places, geo_dataset_loads, journeys

Revision ID: e00067cc5c0e
Revises: None
Create Date: 2025-12-20 13:44:53.248832
"""

# pylint: disable=no-member,invalid-name

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e00067cc5c0e"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=50), nullable=False),
        sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("marketing_emails_consent", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "user_credentials",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("user_id"),
    )
    # Уникальность email и username без учёта регистра.
    op.create_index(
        "ix_user_credentials_email_lower",
        "user_credentials",
        [sa.text("lower(email)")],
        unique=True,
    )
    op.create_index(
        "ix_user_credentials_username_lower",
        "user_credentials",
        [sa.text("lower(username)")],
        unique=True,
    )
    op.create_table(
        "refresh_tokens",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user_credentials.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])
    op.create_table(
        "challenges",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("challenge_type", sa.String(length=32), nullable=False),
        sa.Column("code_ciphertext", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user_credentials.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Один активный challenge данного типа на пользователя: композитный
    # партиальный unique-индекс по неиспользованным записям.
    op.create_index(
        "ix_challenges_active_user_id_type",
        "challenges",
        ["user_id", "challenge_type"],
        unique=True,
        postgresql_where=sa.text("used_at IS NULL"),
    )

    # Газеттир городов: id выводит из external_id загрузчик датасетов (uuid5), база его не генерирует.
    op.create_table(
        "geo_cities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("name_en", sa.String(length=200), nullable=False),
        sa.Column("name_ru", sa.String(length=200), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("latitude", sa.REAL(), nullable=False),
        sa.Column("longitude", sa.REAL(), nullable=False),
        sa.Column("population", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id", name="uq_geo_cities_external_id"),
    )
    # Префиксный автокомплит lower(name) LIKE 'q%' — btree text_pattern_ops по lower(name_*)
    # берётся range-scan'ом для запроса любой длины (даже 1 символ).
    op.create_index(
        "ix_geo_cities_name_en_prefix",
        "geo_cities",
        [sa.text("lower(name_en) text_pattern_ops")],
    )
    op.create_index(
        "ix_geo_cities_name_ru_prefix",
        "geo_cities",
        [sa.text("lower(name_ru) text_pattern_ops")],
    )

    op.create_table(
        "geo_places",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("name_en", sa.String(length=200), nullable=False),
        sa.Column("name_ru", sa.String(length=200), nullable=True),
        sa.Column("country_codes", sa.ARRAY(sa.String(length=2)), nullable=False),
        sa.Column("latitude", sa.REAL(), nullable=False),
        sa.Column("longitude", sa.REAL(), nullable=False),
        sa.Column("notability", sa.Integer(), nullable=False),
        sa.CheckConstraint("cardinality(country_codes) >= 1", name="ck_geo_places_country_codes_not_empty"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id", name="uq_geo_places_external_id"),
    )
    op.create_index(
        "ix_geo_places_name_en_prefix",
        "geo_places",
        [sa.text("lower(name_en) text_pattern_ops")],
    )
    op.create_index(
        "ix_geo_places_name_ru_prefix",
        "geo_places",
        [sa.text("lower(name_ru) text_pattern_ops")],
    )

    # Журнал загрузок датасетов газеттира.
    op.create_table(
        "geo_dataset_loads",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("name"),
    )

    # Поездки пользователей. Города — ссылки на справочник geo, без внешних ключей на geo и users:
    # это другие домены.
    op.create_table(
        "journeys",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("origin_city_id", sa.Uuid(), nullable=False),
        sa.Column("origin_country_code", sa.String(length=2), nullable=False),
        sa.Column("origin_latitude", sa.REAL(), nullable=False),
        sa.Column("origin_longitude", sa.REAL(), nullable=False),
        sa.Column("destination_city_id", sa.Uuid(), nullable=False),
        sa.Column("destination_country_code", sa.String(length=2), nullable=False),
        sa.Column("destination_latitude", sa.REAL(), nullable=False),
        sa.Column("destination_longitude", sa.REAL(), nullable=False),
        sa.Column("transport_type", sa.String(length=20), nullable=False),
        sa.Column("distance_km", sa.SmallInteger(), nullable=False),
        sa.Column("traveled_year", sa.SmallInteger(), nullable=False),
        sa.Column("sort_key", sa.Text(collation="C"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # Порядок поездок внутри года: ключ уникален среди неудалённых, индекс обслуживает и ленту.
    op.create_index(
        "ix_journeys_active_user_id_year_sort_key",
        "journeys",
        ["user_id", sa.text("traveled_year DESC"), "sort_key"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    # journeys и таблицы geo создаются последними в upgrade — дропаются первыми.
    op.drop_index("ix_journeys_active_user_id_year_sort_key", table_name="journeys")
    op.drop_table("journeys")
    op.drop_table("geo_dataset_loads")
    op.drop_index("ix_geo_places_name_ru_prefix", table_name="geo_places")
    op.drop_index("ix_geo_places_name_en_prefix", table_name="geo_places")
    op.drop_table("geo_places")
    op.drop_index("ix_geo_cities_name_ru_prefix", table_name="geo_cities")
    op.drop_index("ix_geo_cities_name_en_prefix", table_name="geo_cities")
    op.drop_table("geo_cities")
    op.drop_index(
        "ix_challenges_active_user_id_type",
        table_name="challenges",
        postgresql_where=sa.text("used_at IS NULL"),
    )
    op.drop_table("challenges")
    op.drop_index("ix_refresh_tokens_expires_at", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index("ix_user_credentials_username_lower", table_name="user_credentials")
    op.drop_index("ix_user_credentials_email_lower", table_name="user_credentials")
    op.drop_table("user_credentials")
    op.drop_table("users")
