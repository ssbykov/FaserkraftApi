import asyncio
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any

from jinja2 import Template

from app.core import settings

TEMPLATE_DICT = {
    "verification": {
        "template": "verification_template.html",
        "subject": "Запрос на верификацию",
    },
    "verify_confirmation": {
        "template": "verify_confirmation_template.html",
        "subject": "Подтверждение верификации",
    },
    "check_update": {
        "template": "check_update_template.html",
        "subject": "Проверка обновления календаря",
    },
    "forgot_password": {
        "template": "reset_password_template.html",
        "subject": "Подтверждение изменения пароля",
    },
    "send_qr": {
        "template": "send_qr_template.html",
        "subject": "Ваш QR-код",
    },
    "backup_failed": {
        "template": "backup_failed_template.html",
        "subject": "Ошибка резервного копирования базы данных",
    },
}

TEMPLATES_DIR = os.path.dirname(__file__) + "/email_templates/"


async def send_email(
    context: dict[str, Any],
    action: str | None = None,
) -> None:
    if not action or not (action_dict := TEMPLATE_DICT.get(action)):
        raise ValueError(f"Неизвестное действие отправки письма: {action}")

    if not (user_email := context.get("user_email")):
        raise ValueError("Не указан получатель письма: user_email")

    mail_params = settings.email

    msg = EmailMessage()
    msg["From"] = mail_params.admin_email
    msg["To"] = (
        mail_params.admin_email
        if action in ("verification", "backup_failed")
        else user_email
    )
    msg["Subject"] = action_dict["subject"]

    template_path = os.path.join(
        TEMPLATES_DIR,
        action_dict["template"],
    )

    with open(template_path, "r", encoding="utf-8") as file:
        template_content = file.read()

    # Экранируем данные, подставляемые в HTML письма.
    template = Template(template_content, autoescape=True)
    rendered_html_content = template.render(**context)

    msg.set_content(
        "Это письмо содержит HTML-версию. "
        "Откройте его в почтовом клиенте с поддержкой HTML."
    )
    msg.add_alternative(
        rendered_html_content,
        subtype="html",
    )

    if "qr_code_bytes" in context:
        msg.get_payload()[-1].add_related(
            context["qr_code_bytes"],
            maintype="image",
            subtype="png",
            cid="<qr_code>",
            filename="qr.png",
        )

    def send_via_smtp() -> None:
        tls_context = ssl.create_default_context()

        with smtplib.SMTP(
            mail_params.host,
            mail_params.port,
            timeout=30,
        ) as server:
            server.ehlo()
            server.starttls(context=tls_context)
            server.ehlo()

            server.login(
                mail_params.admin_email,
                password=mail_params.password,
            )

            refused = server.send_message(msg)
            if refused:
                raise smtplib.SMTPRecipientsRefused(refused)

    try:
        await asyncio.to_thread(send_via_smtp)
    except Exception:
        logging.exception(
            "Ошибка отправки письма: action=%s, recipient=%s",
            action,
            msg["To"],
        )
        raise

    logging.info(
        "Письмо передано SMTP-серверу: action=%s, recipient=%s",
        action,
        msg["To"],
    )
