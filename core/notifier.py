"""
core/notifier.py

ارسال هشدار به چند کانال: تلگرام، ایمیل، و نمایش داخل اپ.

محدودیت مهم (لطفاً حتماً بخوانید):
------------------------------------
Streamlit یک برنامه‌ی همیشه-در-حال-اجرا (Background Daemon) نیست؛
کد فقط زمانی اجرا می‌شود که کاربر صفحه را باز کرده و با آن تعامل
دارد (یا رفرش می‌شود). یعنی این ماژول هشدارها را فقط "در لحظه‌ی
بررسی" (وقتی کاربر روی دکمه‌ی بررسی کلیک می‌کند یا صفحه لود می‌شود)
چک و ارسال می‌کند، نه به‌صورت واقعی و ۲۴ساعته در پس‌زمینه.

برای هشدار واقعی ۲۴ساعته (بدون باز بودن اپ)، به یک فرآیند جداگانه
(مثلاً یک اسکریپت زمان‌بندی‌شده روی سرور یا GitHub Actions Cron)
نیاز است که خارج از دامنه‌ی این تحویل است و در صورت تمایل شما،
به‌عنوان گام بعدی می‌توان طراحی‌اش کرد.

توکن‌ها/رمزها هرگز نباید داخل کد قرار بگیرند؛ این ماژول آن‌ها را
از پارامتر ورودی (که خودِ صفحه از st.secrets یا فرم کاربر می‌گیرد)
دریافت می‌کند.
"""

import smtplib
from email.mime.text import MIMEText

import requests


def send_telegram_message(bot_token, chat_id, message):
    """
    ارسال پیام از طریق Telegram Bot API.
    مستندات رسمی: https://core.telegram.org/bots/api#sendmessage
    """

    if not bot_token or not chat_id:
        return False, "توکن یا Chat ID تلگرام تنظیم نشده است."

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": message,
    }

    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
        return True, "ارسال به تلگرام موفق بود."

    except Exception as e:
        return False, f"خطا در ارسال تلگرام: {e}"


def send_email_message(smtp_config, to_email, subject, message):
    """
    ارسال ایمیل ساده از طریق SMTP.

    smtp_config باید شامل این کلیدها باشد:
        host, port, username, password, use_tls (bool)
    """

    required_keys = ("host", "port", "username", "password")

    if not smtp_config or any(k not in smtp_config for k in required_keys):
        return False, "تنظیمات SMTP کامل نیست."

    try:
        msg = MIMEText(message, _charset="utf-8")
        msg["Subject"] = subject
        msg["From"] = smtp_config["username"]
        msg["To"] = to_email

        with smtplib.SMTP(smtp_config["host"], smtp_config["port"], timeout=10) as server:
            if smtp_config.get("use_tls", True):
                server.starttls()

            server.login(smtp_config["username"], smtp_config["password"])
            server.sendmail(smtp_config["username"], [to_email], msg.as_string())

        return True, "ارسال ایمیل موفق بود."

    except Exception as e:
        return False, f"خطا در ارسال ایمیل: {e}"


def dispatch_alert(message, channels, config):
    """
    ارسال یک پیام هشدار به چند کانال هم‌زمان.

    channels: لیستی از زیرمجموعه‌ی {"telegram", "email", "in_app"}
    config: دیکشنری تنظیمات هر کانال، مثال:
        {
            "telegram": {"bot_token": "...", "chat_id": "..."},
            "email": {
                "smtp": {...}, "to_email": "...", "subject": "..."
            }
        }

    خروجی: دیکشنری نتیجه‌ی هر کانال {channel: (success, detail)}
    """

    results = {}

    if "telegram" in channels:
        tg_config = config.get("telegram", {})

        results["telegram"] = send_telegram_message(
            tg_config.get("bot_token"),
            tg_config.get("chat_id"),
            message,
        )

    if "email" in channels:
        email_config = config.get("email", {})

        results["email"] = send_email_message(
            email_config.get("smtp"),
            email_config.get("to_email"),
            email_config.get("subject", "Crypto Master Alert"),
            message,
        )

    if "in_app" in channels:
        # نمایش داخل اپ توسط خود صفحه (st.toast/st.info) انجام می‌شود؛
        # اینجا فقط علامت موفقیت برمی‌گردانیم.
        results["in_app"] = (True, message)

    return results
