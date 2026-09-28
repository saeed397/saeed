"""
modules/bot_panel.py

ماژول ۲ — پنل مدیریت بات معاملاتی (نسخه‌ی درون‌صفحه‌ای)

تبدیل‌شده از pages/2_Bot_Panel.py به تابع render()، دقیقاً با
همان توضیحات و منطق قبلی (اجرای دستی، بدون پس‌زمینه‌ی واقعی).
"""

import streamlit as st

from core.orchestrator import Orchestrator
from core.strategy_registry import build_strategy_manager
from core.ui_components import render_strategy_selector
from core.risk_profiles import list_risk_profiles, calculate_position_size


def render():

    st.header("🤖 پنل مدیریت بات معاملاتی")

    st.info(
        "⚠️ این پنل به‌صورت **دستی** اجرا می‌شود. به‌دلیل محدودیت‌های "
        "زیرساخت Streamlit، اجرای خودکار و واقعی ۲۴ساعته بدون باز بودن "
        "این صفحه ممکن نیست."
    )

    # --------------------------------------------------------
    # وضعیت روشن/خاموش (Session-based)
    # --------------------------------------------------------

    if "bot_enabled" not in st.session_state:
        st.session_state["bot_enabled"] = False

    st.session_state["bot_enabled"] = st.toggle(
        "فعال‌سازی امکان اجرای بات در این Session",
        value=st.session_state["bot_enabled"],
        key="bot_panel_enable_toggle",
    )

    if not st.session_state["bot_enabled"]:
        st.warning("بات غیرفعال است. برای اجرا، ابتدا آن را فعال کنید.")
        return

    # --------------------------------------------------------
    # انتخاب استراتژی‌های فعال (منوی خودکار)
    # --------------------------------------------------------

    active_strategy_keys = render_strategy_selector(key_prefix="bot")

    # --------------------------------------------------------
    # تنظیمات ریسک (Fixed Fractional Position Sizing)
    # --------------------------------------------------------

    st.markdown("#### تنظیمات ریسک")

    risk_profiles = list_risk_profiles()

    risk_labels = {
        f"{p['label_fa']} ({p['risk_per_trade_pct']}٪ سرمایه)": p["key"]
        for p in risk_profiles
    }

    selected_risk_label = st.selectbox(
        "سطح ریسک هر معامله",
        list(risk_labels.keys()),
        key="bot_panel_risk_select",
    )

    selected_risk_key = risk_labels[selected_risk_label]

    col1, col2, col3 = st.columns(3)

    with col1:
        account_balance = st.number_input(
            "سرمایه کل (دلار)",
            min_value=0.0,
            value=1000.0,
            key="bot_panel_account_balance",
        )

    with col2:
        entry_price = st.number_input(
            "قیمت ورود فرضی",
            min_value=0.0,
            value=0.0,
            format="%.6f",
            key="bot_panel_entry_price",
        )

    with col3:
        stop_loss_price = st.number_input(
            "قیمت حد ضرر فرضی",
            min_value=0.0,
            value=0.0,
            format="%.6f",
            key="bot_panel_stop_loss_price",
        )

    if st.button(
        "محاسبه‌ی حجم پوزیشن پیشنهادی",
        key="bot_panel_sizing_button",
    ):

        sizing = calculate_position_size(
            account_balance,
            selected_risk_key,
            entry_price,
            stop_loss_price,
        )

        if sizing is None:
            st.warning(
                "برای محاسبه، قیمت ورود و حد ضرر باید متفاوت و سرمایه "
                "بزرگ‌تر از صفر باشد."
            )

        else:
            st.success(
                f"با ریسک {sizing['risk_pct']}٪ سرمایه "
                f"(${sizing['risk_amount_usd']:,.2f})، حجم پیشنهادی پوزیشن: "
                f"{sizing['position_size_units']:,.6f} واحد."
            )

    st.caption(
        "روش محاسبه: Fixed Fractional Position Sizing "
        "(Van K. Tharp — Trade Your Way to Financial Freedom)."
    )

    # --------------------------------------------------------
    # اجرای دستی استراتژی‌های فعال روی یک رمزارز
    # --------------------------------------------------------

    st.markdown("#### اجرای دستی")

    coin_id_input = st.text_input(
        "شناسه‌ی رمزارز در CoinGecko (مثل bitcoin, ethereum)",
        value="bitcoin",
        key="bot_panel_coin_id_input",
    )

    if st.button(
        "اجرای بات (دستی)",
        use_container_width=True,
        key="bot_panel_run_button",
    ):

        if not active_strategy_keys:
            st.warning("حداقل یک استراتژی را فعال کنید.")
            return

        if not coin_id_input.strip():
            st.warning("شناسه‌ی رمزارز را وارد کنید.")
            return

        try:
            manager = build_strategy_manager(active_strategy_keys)
            orchestrator = Orchestrator(manager)

            results = orchestrator.run_strategies(
                active_strategy_keys,
                [coin_id_input.strip()],
            )

            for result in results:
                st.write(f"**{result.strategy_name}**")
                st.json(result.data)

            master_decision = orchestrator.make_master_decision()

            if master_decision:
                st.caption(f"MASTER: {master_decision['status']}")

        except Exception as e:
            st.error(f"خطا: {e}")
