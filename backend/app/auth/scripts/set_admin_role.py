"""Назначение первого админа: ``python -m app.auth.scripts.set_admin_role --email <email>``."""

import argparse
import logging
import sys
from typing import Final

import psycopg

from app.shared.settings import settings

_ADMIN_ROLE: Final[str] = "admin"

logger = logging.getLogger(__name__)


def _set_admin_role(*, connection: psycopg.Connection, email: str) -> int:
    """
    Делает аккаунт админом в одной транзакции, только если админа в системе ещё нет.

    Scenarios:
        - назначение первого админа

    Args:
        connection: Соединение с базой
        email: Email аккаунта

    Returns:
        Код выхода процесса
    """
    with connection.transaction():
        existing_admin = connection.execute(
            "SELECT email FROM user_credentials WHERE role = %(role)s LIMIT 1",
            {"role": _ADMIN_ROLE},
        ).fetchone()
        if existing_admin is not None:
            logger.error("Админ уже есть: %s. Скрипт только для назначения первого админа", existing_admin[0])
            return 1

        row = connection.execute(
            "SELECT user_id, role FROM user_credentials WHERE lower(email) = lower(%(email)s) FOR UPDATE",
            {"email": email},
        ).fetchone()
        if row is None:
            logger.error("Аккаунт %s не найден", email)
            return 1

        user_id, current_role = row
        connection.execute(
            "UPDATE user_credentials SET role = %(role)s, updated_at = now() WHERE user_id = %(user_id)s",
            {"role": _ADMIN_ROLE, "user_id": user_id},
        )
        logger.info("%s: %s → %s", email, current_role, _ADMIN_ROLE)
        return 0


def main() -> int:
    """
    Делает аккаунт с указанным email первым админом.

    Scenarios:
        - назначение первого админа

    Returns:
        Код выхода процесса: 0 — роль назначена, 1 — админ уже есть или аккаунт не найден
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Сделать аккаунт первым админом")
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    with psycopg.connect(settings.postgres_libpq_dsn) as connection:
        return _set_admin_role(connection=connection, email=args.email)


if __name__ == "__main__":
    sys.exit(main())
