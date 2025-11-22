import logging
import os
import smtplib
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
}

TEMPLATES_DIR = os.path.dirname(__file__) + "/email_templates/"


async def send_email(context: dict[str, Any], action: str | None = None) -> None:
    if not action or not (action_dict := TEMPLATE_DICT.get(action)):
        return
    if not (user_email := context.get("user_email")):
        return
    # Создаем объект сообщения
    mail_params = settings.email
    msg = EmailMessage()
    msg["From"] = mail_params.admin_email
    msg["To"] = mail_params.admin_email if action == "verification" else user_email
    msg["Subject"] = action_dict.get("subject", "")

    with open(
        TEMPLATES_DIR + action_dict.get("template", ""), "r", encoding="utf-8"
    ) as file:
        template_content = file.read()

    template = Template(template_content)

    rendered_html_content = template.render(**context)

    msg.add_alternative(rendered_html_content, subtype="html")

    # Настройка SMTP сервера и отправка сообщения
    try:
        with smtplib.SMTP(mail_params.host, mail_params.port) as server:
            server.starttls()  # Запускаем шифрование TLS
            server.login(
                mail_params.admin_email, password=mail_params.password
            )  # Логинимся на сервере
            server.send_message(msg)  # Отправляем сообщение
    except Exception as e:
        logging.error(f"Ошибка при отправке письма: {e}")
