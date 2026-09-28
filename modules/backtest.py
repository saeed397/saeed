"""
ماژول ۳ — پلتفرم Backtesting

نکته‌ی مهم و صادقانه (لطفاً حتماً بخوانید):
----------------------------------------------
استراتژی‌های فعلی پروژه (MC و PX) فقط داده‌ی خام برمی‌گردانند و
هیچ قانون خرید/فروش (Signal) ندارند. بنابراین در حال حاضر
نمی‌توان "استراتژی" واقعی شما را Backtest کرد — چیزی برای تست
کردن (به‌معنای یک قانون تصمیم‌گیری) وجود ندارد.

آنچه این صفحه ارائه می‌دهد:
    ۱. بنچمارک استاندارد و کاملاً مستند "Buy & Hold" (خرید و نگهداری)
       که در تمام ادبیات مالی به‌عنوان خط پایه‌ی مقایسه استفاده
       می‌شود.
    ۲. موتور اندازه‌گیری (core/backtest_engine.py) با متریک‌های
       علمی استاندارد (CAGR, Max Drawdown, Sharpe, Sortino) که
       به‌محض افزوده‌شدن یک استراتژی سیگنال‌دهنده‌ی واقعی
       (مثلاً بر پایه‌ی RSI یا Moving Average — با تایید قبلی شما)
       بلافاصله قابل استفاده برای آن هم خواهد بود.

هیچ قانون معاملاتی اختراعی در این فایل پیاده‌سازی نشده است.
"""

import streamlit as st

from core.coin_universe import get_top_500_coins
from core.market_data import get_historical_prices
from core.backtest_engine import run_backtest_report

st.set_page_config(page_title="پلتفرم Backtest", page_icon="📈")

st.title("📈 پلتفرم Backtesting")

st.warning(
    "در حال حاضر استراتژی‌های نصب‌شده (MC/PX) فاقد قانون خرید/فروش "
    "هستند؛ این صفحه فعلاً فقط بنچمارک استاندارد **Buy & Hold** را "
    "محاسبه می‌کند. به‌محض افزودن یک استراتژی سیگنال‌دهنده (با تایید "
    "قبلی شما)، همین موتور برای آن هم فعال می‌شود."
)


@st.cache_data(ttl=300, show_spinner=False)
def load_top_500():
    return get_top_500_coins()


try:
    top_500 = load_top_500()

except Exception as e:
    st.error(f"خطا در دریافت لیست رمزارزها: {e}")
    st.stop()

coin_labels = []
coin_map = {}

for coin in top_500:
    symbol = (coin.get("symbol") or "").upper()
    name = coin.get("name", coin.get("id", ""))
    coin_id = coin.get("id")

    label = f"{symbol} — {name}"
    coin_labels.append(label)
    coin_map[label] = coin_id

selected_label = st.selectbox("انتخاب رمزارز", coin_labels)
selected_coin_id = coin_map[selected_label]

days_options = {
    "۳۰ روز گذشته": 30,
    "۹۰ روز گذشته": 90,
    "۱۸۰ روز گذشته": 180,
    "۳۶۵ روز گذشته": 365,
}

selected_days_label = st.selectbox(
    "بازه‌ی زمانی Backtest",
    list(days_options.keys()),
)

selected_days = days_options[selected_days_label]

if st.button("اجرای Backtest (Buy & Hold)", use_container_width=True):

    try:
        prices = get_historical_prices(selected_coin_id, selected_days)

        if len(prices) < 2:
            st.warning("داده‌ی تاریخی کافی برای این بازه دریافت نشد.")
            st.stop()

        # فقط قیمت‌ها را استخراج می‌کنیم؛ prices شکل [timestamp, price] دارد.
        price_series = [p[1] for p in prices]

        daily_returns = [
            (price_series[i] / price_series[i - 1]) - 1
            for i in range(1, len(price_series))
        ]

        report = run_backtest_report(
            daily_returns,
            periods_per_year=365,
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "بازده کل (Buy & Hold)",
                f"{report['total_return'] * 100:+.2f}%",
            )

        with col2:
            st.metric("CAGR", f"{report['cagr'] * 100:+.2f}%")

        with col3:
            st.metric(
                "بیشترین افت (Max Drawdown)",
                f"{report['max_drawdown'] * 100:.2f}%",
            )

        col4, col5 = st.columns(2)

        with col4:
            st.metric("Sharpe Ratio", f"{report['sharpe_ratio']:.2f}")

        with col5:
            st.metric("Sortino Ratio", f"{report['sortino_ratio']:.2f}")

        st.markdown("#### منحنی سرمایه (Equity Curve)")
        st.line_chart(report["equity_curve"])

        st.caption(
            "فرمول‌ها: Sharpe (Sharpe 1994) | Sortino (Sortino & Price 1994) "
            "| CAGR و Max Drawdown طبق تعریف استاندارد Investopedia."
        )

    except Exception as e:
        st.error(f"خطا: {e}")
