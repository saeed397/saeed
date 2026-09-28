"""
core/ui_components.py

کامپوننت‌های رابط کاربری مشترک بین ۴ ماژول جدید
(داشبورد / بات / بک‌تست / الرت) تا کد در هر صفحه تکرار نشود
و رفتار در همه‌جا یکسان بماند.

هیچ‌کدام از این توابع به core/strategy_manager.py یا
core/orchestrator.py دست نمی‌زنند.
"""

import streamlit as st

from core.strategy_registry import list_available_strategies


def render_strategy_selector(key_prefix, default_checked=True):
    """
    یک Expander با چک‌باکس برای هر استراتژی نصب‌شده رندر می‌کند.

    key_prefix:
        رشته‌ی یکتا برای هر صفحه (مثلاً "dashboard", "bot", "backtest",
        "alerts") تا session_state چک‌باکس‌های هر صفحه با بقیه
        تداخل نکند و انتخاب هر صفحه مستقل از صفحات دیگر باشد.

    خروجی:
        لیستی از کلید استراتژی‌های فعال‌شده توسط کاربر، مثل ["MC", "PX"]
    """

    strategies = list_available_strategies()

    selected = []

    with st.expander("\u200eSTRATEGIES", expanded=True):

        if not strategies:
            st.caption(
                "هیچ استراتژی‌ای در core/strategy_registry.py ثبت نشده است."
            )

            return selected

        for strategy in strategies:

            checkbox_key = f"{key_prefix}_strategy_{strategy['key']}"

            is_checked = st.checkbox(
                f"\u200e{strategy['label']}",
                value=default_checked,
                key=checkbox_key,
            )

            if is_checked:
                selected.append(strategy["key"])

    if not selected:
        st.warning(
            "هیچ استراتژی‌ای فعال نیست — حداقل یکی را انتخاب کنید."
        )

    return selected
