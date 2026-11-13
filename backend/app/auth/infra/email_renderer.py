"""
Рендеринг писем подтверждения email через Jinja2.

Шаблоны лежат рядом с auth-доменом и подгружаются ``PackageLoader``.
Рендерер собирает subject/html/text в ``EmailMessage`` — транспорт-агностичную
структуру, которая дальше уходит в ``EmailTransportPort`` (Resend и т.п.).
"""

from jinja2 import Environment, PackageLoader, select_autoescape

from app.shared.infra.email import EmailMessage

_environment = Environment(
    loader=PackageLoader(package_name="app.auth.infra", package_path="email_templates"),
    autoescape=select_autoescape(enabled_extensions=("html",)),
)


def render_verification_email(*, email: str, code: str) -> EmailMessage:
    """
    Рендерит письмо с одноразовым кодом подтверждения email.

    Scenarios:
        - фоновая отправка письма с кодом: после регистрации и по кнопке в диалоге «Подтвердите email»

    Args:
        email: Email-адрес получателя
        code: Plaintext-код подтверждения, который покажем пользователю

    Returns:
        EmailMessage с заполненными subject/html/text, готовый к отправке
    """
    context = {"email": email, "code": code}
    subject = _environment.get_template(name="verification_code.subject.txt").render(context).strip()
    html = _environment.get_template(name="verification_code.html").render(context)
    text = _environment.get_template(name="verification_code.txt").render(context)
    return EmailMessage(to=email, subject=subject, html=html, text=text)
