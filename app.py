import streamlit as st

from core.orchestrator import Orchestrator
from core.strategy_manager import StrategyManager
from core.coin_universe import get_top_500_coins

from strategies.market_cap.adapter import MarketCapAdapter
from strategies.price.adapter import PriceAdapter

# ==================================================
# PAGE
# ==================================================

st.set_page_config(
    page_title="Crypto Master",
    page_icon="₿",
    layout="centered"
)

# ==================================================
# CUSTOM UI / RTL / LTR / COLORS
# ==================================================

st.markdown(
    """
    <style>

    /* ==============================================
    GLOBAL TEXT DIRECTION PRINCIPLE
    ============================================== */

    /*
    English = LTR
    Persian = RTL

    نکته‌ی مهم:
    قبلاً "direction: rtl" روی کل .stApp گذاشته شده بود که باعث
    می‌شد هدر و سایدبار Streamlit (که برای چیدمان LTR طراحی
    شده‌اند) به‌هم بریزند و دکمه‌ی جمع/بازکردن سایدبار گیر کند.

    راه‌حل: RTL را فقط روی محتوای اصلی صفحه (block-container)
    اعمال می‌کنیم، نه روی هدر/سایدبار. به این ترتیب هیچ تداخلی
    با مکانیزم داخلی Streamlit پیش نمی‌آید.
    */

    section.main .block-container {
    direction: rtl;
    }

    /* ==============================================
    GLOBAL FONT
    ============================================== */

    html, body, [class*="css"] {
    font-family: "Noto Sans Arabic",
    "Vazirmatn",
    "Tahoma",
    sans-serif;
    }

    /* ==============================================
    PERSIAN TEXT
    ============================================== */

    .stMarkdown,
    .stText,
    .stCaption,
    .stAlert {
    direction: rtl;
    text-align: right;
    }

    /* ==============================================
    ENGLISH EXPANDER TITLES
    STR / CRYPTO
    LTR + LEFT
    ============================================== */

    div[data-testid="stExpander"] > details > summary {
    direction: ltr !important;
    text-align: left !important;
    }

    div[data-testid="stExpander"] > details > summary span {
    direction: ltr !important;
    text-align: left !important;
    unicode-bidi: isolate !important;
    }

    /* ==============================================
    EXPANDER - PURPLE
    STR / CRYPTO
    ============================================== */

    div[data-testid="stExpander"] {
    border: 1px solid #8b5cf6;
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 10px;
    }

    div[data-testid="stExpander"] > details > summary {
    background: linear-gradient(
    135deg,
    #6d28d9,
    #7c3aed
    );

    color: #ffffff !important;
    font-weight: 700;
    border-radius: 10px;
    }

    div[data-testid="stExpander"] > details > summary span {
    color: #ffffff !important;
    }

    /* ==============================================
    TF / SIGNAL / R:R
    DARKER LIGHT-CREAM
    ============================================== */

    div[data-testid="stSelectbox"] {
    background: #f1e4c8;
    border: 1px solid #d8c59e;
    border-radius: 12px;
    padding: 8px 10px;
    margin-bottom: 8px;
    }

    /* ==============================================
    SELECTBOX FIELD
    ============================================== */

    div[data-testid="stSelectbox"]
    div[data-baseweb="select"] > div {
    background: #f8efd9;
    border: 1px solid #d8c59e;
    border-radius: 9px;
    }

    /* ==============================================
    SELECTBOX VALUE - LTR
    ============================================== */

    div[data-testid="stSelectbox"]
    div[data-baseweb="select"] {
    direction: ltr !important;
    text-align: left !important;
    }

    div[data-testid="stSelectbox"]
    div[data-baseweb="select"] span {
    direction: ltr !important;
    text-align: left !important;
    unicode-bidi: isolate;
    }

    /* ==============================================
    DROPDOWN OPTIONS - LTR
    ============================================== */

    ul[role="listbox"] {
    direction: ltr !important;
    text-align: left !important;
    }

    li[role="option"] {
    direction: ltr !important;
    text-align: left !important;
    }

    /* ==============================================
    ENGLISH SELECTBOX TITLES
    LTR + LEFT
    ============================================== */

    div[data-testid="stSelectbox"] > label {
    direction: ltr !important;
    text-align: left !important;
    unicode-bidi: isolate !important;
    }

    div[data-testid="stSelectbox"] > label p {
    direction: ltr !important;
    text-align: left !important;
    unicode-bidi: isolate !important;
    }

    /* ==============================================
    HTF CONFIRM
    ENGLISH LTR + LEFT
    ============================================== */

    div[data-testid="stCheckbox"] label {
    direction: ltr !important;
    text-align: left !important;
    display: flex !important;
    flex-direction: row !important;
    justify-content: flex-start !important;
    align-items: center !important;
    }

    div[data-testid="stCheckbox"] label p {
    direction: ltr !important;
    text-align: left !important;
    unicode-bidi: isolate !important;
    }

    /* ==============================================
    STR CHECKBOXES - ENGLISH LTR
    ============================================== */

    div[data-testid="stExpander"]
    div[data-testid="stCheckbox"] label {
    direction: ltr !important;
    text-align: left !important;
    flex-direction: row !important;
    justify-content: flex-start !important;
    }

    /* ==============================================
    RUN BUTTON
    ============================================== */

    div.stButton > button {
    background: linear-gradient(
    135deg,
    #6d28d9,
    #7c3aed
    );

    color: #ffffff;
    border: none;
    border-radius: 10px;
    font-weight: 700;
    }

    div.stButton > button:hover {
    background: linear-gradient(
    135deg,
    #7c3aed,
    #8b5cf6
    );

    color: #ffffff;
    }

    /* ==============================================
    OUTPUT
    ============================================== */

    .buy-box {
    direction: ltr;
    text-align: left;
    border-left: 5px solid #22c55e;
    padding: 8px 12px;
    border-radius: 8px;
    background: rgba(34, 197, 94, 0.08);
    }

    .sell-box {
    direction: ltr;
    text-align: left;
    border-left: 5px solid #ef4444;
    padding: 8px 12px;
    border-radius: 8px;
    background: rgba(239, 68, 68, 0.08);
    }

    .info-box {
    direction: ltr;
    text-align: left;
    border-left: 5px solid #3b82f6;
    padding: 8px 12px;
    border-radius: 8px;
    background: rgba(59, 130, 246, 0.08);
    }

    .warning-box {
    direction: ltr;
    text-align: left;
    border-left: 5px solid #f59e0b;
    padding: 8px 12px;
    border-radius: 8px;
    background: rgba(245, 158, 11, 0.08);
    }

    /* ==============================================
    CONFIG / STATUS - LTR
    ============================================== */

    div[data-testid="stCaptionContainer"] {
    direction: ltr !important;
    text-align: left !important;
    unicode-bidi: isolate;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# ==================================================
# TOP 500 DATA
# ==================================================

@st.cache_data(ttl=300, show_spinner=False)
def load_top_500():
    return get_top_500_coins()

# ==================================================
# STRATEGY MANAGER
# ==================================================

strategy_manager = StrategyManager()

strategy_manager.register(
    "MC",
    MarketCapAdapter()
)

strategy_manager.register(
    "PX",
    PriceAdapter()
)

# ==================================================
# ORCHESTRATOR
# ==================================================

orchestrator = Orchestrator(
    strategy_manager
)

# ==================================================
# HEADER
# ==================================================

st.title("Crypto Master")

# ==================================================
# STRATEGY
# ==================================================

with st.expander("\u200eSTR"):

    selected_strategies = []

    if st.checkbox(
        "MC",
        value=True
    ):
        selected_strategies.append("MC")

    if st.checkbox(
        "PX",
        value=True
    ):
        selected_strategies.append("PX")

# ==================================================
# LOAD TOP 500
# ==================================================

try:
    top_500 = load_top_500()

except Exception as e:
    st.error(
        f"ERR: {e}"
    )

    st.stop()

# ==================================================
# CRYPTO
# ==================================================

with st.expander("\u200eCRYPTO"):

    mode = st.selectbox(
        "",
        [
            "انتخاب رمزارز",
            "انتخاب چند رمزارز"
        ],
        label_visibility="collapsed"
    )

    # ------------------------------------------------
    # SINGLE COIN
    # ------------------------------------------------

    if mode == "انتخاب رمزارز":

        coin_labels = []

        coin_map = {}

        for coin in top_500:

            symbol = coin.get(
                "symbol",
                ""
            ).upper()

            name = coin.get(
                "name",
                coin.get("id", "")
            )

            coin_id = coin.get(
                "id"
            )

            label = f"{symbol} — {name}"

            coin_labels.append(
                label
            )

            coin_map[label] = coin_id

        selected_label = st.selectbox(
            "انتخاب رمزارز",
            coin_labels
        )

        selected_coins = [
            coin_map[selected_label]
        ]

        single_coin_mode = True

    # ------------------------------------------------
    # MULTIPLE COINS
    # ------------------------------------------------

    else:

        rank_ranges = [
            "رتبه ۱ تا ۵۰",
            "رتبه ۵۱ تا ۱۰۰",
            "رتبه ۱۰۱ تا ۱۵۰",
            "رتبه ۱۵۱ تا ۲۰۰",
            "رتبه ۲۰۱ تا ۲۵۰",
            "رتبه ۲۵۱ تا ۳۰۰",
            "رتبه ۳۰۱ تا ۳۵۰",
            "رتبه ۳۵۱ تا ۴۰۰",
            "رتبه ۴۰۱ تا ۴۵۰",
            "رتبه ۴۵۱ تا ۵۰۰"
        ]

        selected_ranges = st.multiselect(
            "انتخاب چند رمزارز",
            rank_ranges
        )

        selected_coins = []

        range_map = {

            "رتبه ۱ تا ۵۰": (1, 50),

            "رتبه ۵۱ تا ۱۰۰": (51, 100),

            "رتبه ۱۰۱ تا ۱۵۰": (101, 150),

            "رتبه ۱۵۱ تا ۲۰۰": (151, 200),

            "رتبه ۲۰۱ تا ۲۵۰": (201, 250),

            "رتبه ۲۵۱ تا ۳۰۰": (251, 300),

            "رتبه ۳۰۱ تا ۳۵۰": (301, 350),

            "رتبه ۳۵۱ تا ۴۰۰": (351, 400),

            "رتبه ۴۰۱ تا ۴۵۰": (401, 450),

            "رتبه ۴۵۱ تا ۵۰۰": (451, 500)
        }

        for selected_range in selected_ranges:

            start_rank, end_rank = range_map[
                selected_range
            ]

            for index in range(
                start_rank - 1,
                min(
                    end_rank,
                    len(top_500)
                )
            ):

                coin_id = top_500[
                    index
                ].get("id")

                if coin_id not in selected_coins:

                    selected_coins.append(
                        coin_id
                    )

        single_coin_mode = False

# ==================================================
# TIMEFRAME
# ==================================================

timeframes = [
    "5m",
    "15m",
    "30m",
    "1h",
    "4h",
    "6h",
    "12h",
    "1D",
    "1W",
    "1M",
    "1Y"
]

selected_timeframe = st.selectbox(
    "\u200eTF",
    timeframes
)

# ==================================================
# HTF CONFIRM (نسبت ۱:۴ تایم‌فریم بالاتر)
# ==================================================

HTF_MAP = {
    "5m": "15m",
    "15m": "1h",
    "30m": "1h",
    "1h": "4h",
    "4h": "12h",
    "6h": "1D",
    "12h": "1D",
    "1D": "1W",
    "1W": "1M",
    "1M": "1Y",
    "1Y": None,
}

selected_htf = HTF_MAP.get(selected_timeframe)

if single_coin_mode:

    if selected_htf is None:

        htf_confirm = False

        st.checkbox(
            "\u200eHTF CONFIRM",
            value=False,
            disabled=True
        )

        st.caption("این تایم‌فریم بالاترین سطح است؛ HTF بالاتری وجود ندارد.")

    else:

        htf_confirm = st.checkbox(
            f"\u200eHTF CONFIRM ({selected_htf})"
        )

else:

    htf_confirm = False

    st.checkbox(
        "\u200eHTF CONFIRM",
        value=False,
        disabled=True
    )

# ==================================================
# SIGNAL
# ==================================================

signal_options = [
    "🟢 SELL",
    "🔴 BUY",
    "🔵 BOTH"
]

selected_signal = st.selectbox(
    "\u200eSIGNAL",
    signal_options
)

# ==================================================
# R:R
# ==================================================
#
# قرارداد این پروژه برای R:R (Risk : Reward):
#   عدد سمت چپ = ضریب حدسود (Take Profit / Reward)
#   عدد سمت راست (همیشه 1) = ضریب حدضرر (Stop Loss / Risk)
#
# یعنی مثلاً "2 : 1" یعنی حدسود ۲ برابر حدضرر است.
# در هر منطق محاسباتی که بعداً از selected_rr استفاده شود،
# همیشه باید عدد بزرگ‌تر به‌عنوان حدسود و عدد کوچک‌تر (1)
# به‌عنوان حدضرر در نظر گرفته شود - نه برعکس.
#
# نکته: مشکل قبلی (نمایش برعکس مثل "1 : 1.5" در رابط کاربری)
# صرفاً یک اثر بصری Unicode Bidi بود (چون این عدد وسط یک
# صفحه‌ی RTL رندر می‌شد)، نه اشتباه در مقدار واقعی متغیر.
# افزودن نویسه‌ی نامرئی LRM (\u200e) به ابتدای هر گزینه باعث
# می‌شود مرورگر این اعداد را همیشه از چپ‌به‌راست رندر کند -
# مطابق تعریف استاندارد Unicode Bidirectional Algorithm
# (Unicode Standard Annex #9) برای رفع تداخل RTL/LTR در اعداد.
# مقدار واقعی selected_rr (برای هرگونه مقایسه یا محاسبه در
# آینده) تغییری نکرده، فقط یک نویسه‌ی نامرئی اضافه شده است.

rr_options = [
    "\u200e1.5 : 1",
    "\u200e2 : 1",
    "\u200e2.5 : 1",
    "\u200e3 : 1"
]

selected_rr = st.selectbox(
    "\u200eR:R",
    rr_options
)

# ==================================================
# RUN
# ==================================================

if st.button(
    "RUN",
    use_container_width=True
):

    if not selected_strategies:

        st.warning(
            "ERR: STR"
        )

        st.stop()

    if not selected_coins:

        st.warning(
            "ERR: CRYPTO"
        )

        st.stop()

    try:

        # ------------------------------------------
        # RUN STRATEGIES
        # ------------------------------------------

        results = orchestrator.run_strategies(
            selected_strategies,
            selected_coins
        )

        # ------------------------------------------
        # ORGANIZE BY COIN
        # ------------------------------------------

        coin_results = {}

        for result in results:

            for coin in result.data:

                coin_id = coin["id"]

                if coin_id not in coin_results:

                    coin_results[coin_id] = {
                        "name": coin.get(
                            "name",
                            coin_id
                        ),
                        "mc": None,
                        "px": None
                    }

                if "market_cap" in coin:

                    coin_results[
                        coin_id
                    ]["mc"] = coin[
                        "market_cap"
                    ]

                if "price" in coin:

                    coin_results[
                        coin_id
                    ]["px"] = coin[
                        "price"
                    ]

        # ------------------------------------------
        # OUTPUT
        # ------------------------------------------

        for coin_id in selected_coins:

            if coin_id not in coin_results:

                continue

            coin = coin_results[
                coin_id
            ]

            st.markdown(
                f"### {coin['name']}"
            )

            values = []

            if coin["mc"] is not None:

                values.append(
                    f"MC: $`{coin['mc']:,.0f}"
                )

            if coin["px"] is not None:

                values.append(
                    f"PX: `${coin['px']:,.6f}"
                )

            if values:

                st.write(
                    " | ".join(values)
                )

        # ------------------------------------------
        # CURRENT CONFIG
        # ------------------------------------------

        config_items = [
            f"TF: {selected_timeframe}",
            f"R:R: {selected_rr}",
            f"SIGNAL: {selected_signal}"
        ]

        if single_coin_mode and htf_confirm and selected_htf:

            config_items.append(
                f"HTF: ON ({selected_htf})"
            )

        elif single_coin_mode:

            config_items.append(
                "HTF: OFF"
            )

        else:

            config_items.append(
                "HTF: OFF"
            )

        st.caption(
            " | ".join(config_items)
        )

        # ------------------------------------------
        # MASTER ENGINE
        # ------------------------------------------

        master_decision = (
            orchestrator.make_master_decision()
        )

        if master_decision:

            st.caption(
                f"MASTER: "
                f"{master_decision['status']}"
            )

    except Exception as e:
        st.error(
            f"ERR: {e}"
        )
