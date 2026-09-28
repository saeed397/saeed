"""
modules/dashboard.py

ماژول ۱ — داشبورد تحلیل کریپتو (نسخه‌ی درون‌صفحه‌ای)

این فایل قبلاً یک صفحه‌ی جدای Streamlit بود (pages/1_Dashboard.py)
و اکنون طبق درخواست شما، به یک تابع render() تبدیل شده تا از
داخل app.py، همان‌جا در صفحه‌ی اصلی نمایش داده شود.

هیچ منطقی نسبت به نسخه‌ی قبلی تغییر نکرده؛ فقط:
    - همه‌چیز داخل تابع render() قرار گرفته
    - st.set_page_config حذف شد (چون فقط app.py مجاز به فراخوانی
      آن است)
    - st.stop() به return تبدیل شد (تا فقط همین ماژول متوقف شود،
      نه کل صفحه)
    - به هر ویجت یک key یکتا اضافه شد تا با ماژول‌های دیگری که
      هم‌زمان فعال هستند تداخل نکند
"""

import streamlit as st

from core.coin_universe import get_top_500_coins
from core.market_data import get_market_snapshot
from core.orchestrator import Orchestrator
from core.strategy_registry import build_strategy_manager
from core.ui_components import render_strategy_selector


@st.cache_data(ttl=300, show_spinner=False)
def _load_top_500():
    return get_top_500_coins()


def render():

    st.header("📊 داشبورد تحلیل کریپتو")

    st.caption(
        "منبع داده: CoinGecko Public API — بدون استفاده از Binance."
    )

    # --------------------------------------------------------
    # انتخاب استراتژی‌های فعال (منوی خودکار)
    # --------------------------------------------------------

    active_strategy_keys = render_strategy_selector(key_prefix="dashboard")

    # --------------------------------------------------------
    # انتخاب رمزارز
    # --------------------------------------------------------

    try:
        top_500 = _load_top_500()

    except Exception as e:
        st.error(f"خطا در دریافت لیست رمزارزها: {e}")
        return

    coin_labels = []
    coin_map = {}

    for coin in top_500:
        symbol = (coin.get("symbol") or "").upper()
        name = coin.get("name", coin.get("id", ""))
        coin_id = coin.get("id")

        label = f"{symbol} — {name}"
        coin_labels.append(label)
        coin_map[label] = coin_id

    selected_label = st.selectbox(
        "انتخاب رمزارز",
        coin_labels,
        key="dashboard_coin_select",
    )

    selected_coin_id = coin_map[selected_label]

    # --------------------------------------------------------
    # دکمه‌ی به‌روزرسانی
    # --------------------------------------------------------

    if st.button(
        "به‌روزرسانی داشبورد",
        use_container_width=True,
        key="dashboard_update_button",
    ):

        if not active_strategy_keys:
            st.warning("حداقل یک استراتژی را از بخش STRATEGIES فعال کنید.")
            return

        try:
            # ----------------------------------------------
            # داده‌ی بازار (قیمت لحظه‌ای + تغییر ۲۴ساعته)
            # ----------------------------------------------

            snapshot = get_market_snapshot([selected_coin_id])

            if snapshot:
                coin_info = snapshot[0]

                price = coin_info["current_price"]
                change_24h = coin_info["price_change_percentage_24h"]

                col1, col2 = st.columns(2)

                with col1:
                    st.metric(
                        label=f"قیمت {coin_info['symbol']}",
                        value=f"${price:,.4f}" if price is not None else "—",
                    )

                with col2:
                    if change_24h is not None:
                        st.metric(
                            label="تغییر ۲۴ ساعته",
                            value=f"{change_24h:+.2f}%",
                            delta=f"{change_24h:+.2f}%",
                        )
                    else:
                        st.metric(label="تغییر ۲۴ ساعته", value="—")

            else:
                st.warning("داده‌ای برای این رمزارز از CoinGecko دریافت نشد.")

            # ----------------------------------------------
            # اجرای استراتژی‌های فعال (از طریق Orchestrator موجود)
            # ----------------------------------------------

            manager = build_strategy_manager(active_strategy_keys)
            orchestrator = Orchestrator(manager)

            results = orchestrator.run_strategies(
                active_strategy_keys,
                [selected_coin_id],
            )

            st.markdown("#### خروجی استراتژی‌های فعال")

            for result in results:
                st.write(f"**{result.strategy_name}**")
                st.json(result.data)

            master_decision = orchestrator.make_master_decision()

            if master_decision:
                st.caption(f"MASTER: {master_decision['status']}")

        except Exception as e:
            st.error(f"خطا: {e}")

    # --------------------------------------------------------
    # محاسبه‌گر ساده PnL (دستی، بدون اتصال به صرافی)
    # --------------------------------------------------------

    st.markdown("---")
    st.subheader("💰 محاسبه‌گر PnL (دستی)")

    st.caption(
        "این بخش به هیچ صرافی متصل نیست؛ فقط بر اساس قیمت ورودی که "
        "خودتان وارد می‌کنید، سود/زیان لحظه‌ای را محاسبه می‌کند."
    )

    pnl_col1, pnl_col2 = st.columns(2)

    with pnl_col1:
        entry_price = st.number_input(
            "قیمت خرید (Entry) به دلار",
            min_value=0.0,
            value=0.0,
            format="%.6f",
            key="dashboard_pnl_entry_price",
        )

    with pnl_col2:
        quantity = st.number_input(
            "تعداد",
            min_value=0.0,
            value=0.0,
            format="%.6f",
            key="dashboard_pnl_quantity",
        )

    if st.button("محاسبه PnL", key="dashboard_pnl_button"):

        try:
            snapshot = get_market_snapshot([selected_coin_id])

            if not snapshot:
                st.warning("قیمت لحظه‌ای دریافت نشد.")

            elif entry_price <= 0 or quantity <= 0:
                st.warning("قیمت خرید و تعداد باید بزرگ‌تر از صفر باشند.")

            else:
                current_price = snapshot[0]["current_price"]

                pnl_usd = (current_price - entry_price) * quantity
                pnl_pct = ((current_price / entry_price) - 1) * 100

                pnl_col_a, pnl_col_b = st.columns(2)

                with pnl_col_a:
                    st.metric("PnL (دلار)", f"${pnl_usd:,.2f}")

                with pnl_col_b:
                    st.metric("PnL (درصد)", f"{pnl_pct:+.2f}%")

        except Exception as e:
            st.error(f"خطا: {e}")
