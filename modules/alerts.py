"""
ماژول ۴ — سیستم Alert و نوتیفیکیشن

محدودیت مهم (لطفاً حتماً بخوانید):
------------------------------------
این صفحه هشدارها را فقط "در لحظه‌ی بررسی" چک می‌کند - یعنی وقتی
صفحه باز است و شما دکمه‌ی «بررسی هشدارها» را می‌زنید (یا صفحه را
رفرش می‌کنید). به‌دلیل ماهیت Streamlit، بررسی واقعی و مداوم
۲۴ساعته بدون باز بودن این صفحه ممکن نیست و به یک فرآیند جداگانه
(Scheduler خارج از Streamlit) نیاز دارد که خارج از دامنه‌ی این
تحویل است.

کانال‌ها: تلگرام + ایمیل + نمایش داخل اپ (طبق تصمیم شما: «ترکیبی
از چند کانال»).
"""

import streamlit as st

from core.market_data import get_market_snapshot
from core.notifier import dispatch_alert
from core.ui_components import render_strategy_selector

st.set_page_config(page_title="سیستم Alert", page_icon="🔔")

st.title("🔔 سیستم Alert و نوتیفیکیشن")

st.info(
    "⚠️ هشدارها فقط در لحظه‌ای که این صفحه باز است و دکمه‌ی «بررسی "
    "هشدارها» زده می‌شود، چک می‌شوند — نه به‌صورت ۲۴ساعته در پس‌زمینه."
)

# ------------------------------------------------------------
# انتخاب استراتژی‌های فعال (برای آماده‌سازی الرت‌های مبتنی بر سیگنال
# در آینده - در حال حاضر فقط نمایشی است چون استراتژی‌ها سیگنال
# تولید نمی‌کنند)
# ------------------------------------------------------------

active_strategy_keys = render_strategy_selector(
    key_prefix="alerts", default_checked=False
)

st.caption(
    "این انتخاب فعلاً فقط برای آماده‌سازی الرت‌های آینده مبتنی بر "
    "سیگنال استراتژی‌هاست؛ الرت‌های فعال فعلی بر پایه‌ی قیمت هستند."
)

# ------------------------------------------------------------
# تنظیمات کانال‌ها
# ------------------------------------------------------------

st.markdown("### تنظیمات کانال‌های ارسال")

channels = st.multiselect(
    "کانال‌های فعال برای ارسال هشدار",
    ["telegram", "email", "in_app"],
    default=["in_app"],
)

telegram_bot_token = ""
telegram_chat_id = ""

if "telegram" in channels:
    st.markdown("**تلگرام**")
    telegram_bot_token = st.text_input("Bot Token", type="password")
    telegram_chat_id = st.text_input("Chat ID")

smtp_host = smtp_port = smtp_user = smtp_pass = to_email = ""

if "email" in channels:
    st.markdown("**ایمیل**")
    smtp_host = st.text_input("SMTP Host", value="smtp.gmail.com")
    smtp_port = st.number_input("SMTP Port", value=587, step=1)
    smtp_user = st.text_input("ایمیل فرستنده")
    smtp_pass = st.text_input("رمز عبور / App Password", type="password")
    to_email = st.text_input("ایمیل گیرنده هشدار")

# ------------------------------------------------------------
# افزودن هشدار جدید (بر پایه قیمت)
# ------------------------------------------------------------

st.markdown("### افزودن هشدار قیمتی")

if "price_alerts" not in st.session_state:
    st.session_state["price_alerts"] = []

col1, col2, col3 = st.columns(3)

with col1:
    alert_coin_id = st.text_input(
        "شناسه‌ی رمزارز (CoinGecko)", value="bitcoin", key="alert_coin_id"
    )

with col2:
    alert_condition = st.selectbox(
        "شرط", ["بالاتر از", "پایین‌تر از"], key="alert_condition"
    )

with col3:
    alert_target_price = st.number_input(
        "قیمت هدف (دلار)", min_value=0.0, value=0.0, format="%.6f",
        key="alert_target_price",
    )

if st.button("افزودن این هشدار به لیست"):
    if alert_target_price <= 0:
        st.warning("قیمت هدف باید بزرگ‌تر از صفر باشد.")
    else:
        st.session_state["price_alerts"].append({
            "coin_id": alert_coin_id.strip(),
            "condition": alert_condition,
            "target_price": alert_target_price,
        })
        st.success("هشدار اضافه شد.")

# ------------------------------------------------------------
# نمایش لیست هشدارهای تعریف‌شده (فقط برای همین Session)
# ------------------------------------------------------------

st.markdown("### هشدارهای تعریف‌شده (فقط برای همین Session)")

if not st.session_state["price_alerts"]:
    st.caption("هنوز هشداری اضافه نکرده‌اید.")

else:
    for i, alert in enumerate(st.session_state["price_alerts"]):
        col_a, col_b = st.columns([4, 1])

        with col_a:
            st.write(
                f"{alert['coin_id']} — {alert['condition']} "
                f"${alert['target_price']:,.6f}"
            )

        with col_b:
            if st.button("حذف", key=f"delete_alert_{i}"):
                st.session_state["price_alerts"].pop(i)
                st.rerun()

# ------------------------------------------------------------
# بررسی هشدارها الان
# ------------------------------------------------------------

if st.button("🔍 بررسی هشدارها الان", use_container_width=True):

    if not st.session_state["price_alerts"]:
        st.warning("هیچ هشداری برای بررسی وجود ندارد.")
        st.stop()

    config = {
        "telegram": {
            "bot_token": telegram_bot_token,
            "chat_id": telegram_chat_id,
        },
        "email": {
            "smtp": {
                "host": smtp_host,
                "port": int(smtp_port) if smtp_port else 587,
                "username": smtp_user,
                "password": smtp_pass,
                "use_tls": True,
            },
            "to_email": to_email,
            "subject": "Crypto Master — هشدار قیمت",
        },
    }

    for alert in st.session_state["price_alerts"]:
        try:
            snapshot = get_market_snapshot([alert["coin_id"]])

            if not snapshot:
                st.warning(f"قیمت {alert['coin_id']} دریافت نشد.")
                continue

            current_price = snapshot[0]["current_price"]

            triggered = (
                (alert["condition"] == "بالاتر از" and current_price >= alert["target_price"])
                or
                (alert["condition"] == "پایین‌تر از" and current_price <= alert["target_price"])
            )

            if triggered:
                message = (
                    f"هشدار قیمت: {alert['coin_id']} به "
                    f"${current_price:,.6f} رسید "
                    f"(شرط: {alert['condition']} ${alert['target_price']:,.6f})"
                )

                results = dispatch_alert(message, channels, config)

                st.success(f"✅ هشدار {alert['coin_id']} فعال شد.")

                for channel, (success, detail) in results.items():
                    if success:
                        st.write(f"✔️ {channel}: {detail}")
                    else:
                        st.error(f"❌ {channel}: {detail}")

            else:
                st.caption(
                    f"⏳ {alert['coin_id']}: قیمت فعلی "
                    f"${current_price:,.6f} — شرط هنوز برقرار نشده."
                )

        except Exception as e:
            st.error(f"خطا در بررسی {alert['coin_id']}: {e}")
