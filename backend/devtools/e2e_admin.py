"""
Учётка администратора для одноразового e2e-стека: регистрация обычным ``POST /v1/auth/register/``.

Роль выдаёт следующим шагом боевой скрипт назначения первого админа — так e2e проходят тот же путь, что и
настоящий админ. Только для e2e. Запуск: ``python -m devtools.e2e_admin --api-url <адрес app> --username …
--email … --password …``.
"""

import argparse
import sys

import httpx

_ALREADY_REGISTERED = 409


def register_admin_account(*, api_url: str, username: str, email: str, password: str) -> None:
    """
    Регистрирует учётку будущего админа; уже существующая — не ошибка, стек мог подниматься повторно.

    Args:
        api_url: Адрес приложения внутри сети стека
        username: Логин
        email: Email
        password: Пароль

    Raises:
        httpx.HTTPStatusError: Регистрация отклонена не из-за занятого логина или email
    """
    response = httpx.post(
        f"{api_url}/v1/auth/register/",
        json={
            "username": username,
            "email": email,
            "password": password,
            "termsAccepted": True,
            "marketingEmailsConsent": False,
        },
        timeout=30,
    )
    if response.status_code == _ALREADY_REGISTERED:
        return

    response.raise_for_status()


def main() -> int:
    """
    Регистрирует учётку администратора e2e-стека.

    Returns:
        Код выхода процесса
    """
    parser = argparse.ArgumentParser(description="Учётка администратора e2e-стека")
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    register_admin_account(api_url=args.api_url, username=args.username, email=args.email, password=args.password)
    return 0


if __name__ == "__main__":
    sys.exit(main())
