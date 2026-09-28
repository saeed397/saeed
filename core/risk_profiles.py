"""
core/risk_profiles.py

روش استفاده‌شده: Fixed Fractional Position Sizing
یکی از پرکاربردترین و مستندترین روش‌های مدیریت ریسک در معاملات،
که در آن درصد مشخصی از کل سرمایه در هر معامله به خطر انداخته می‌شود
(نه یک مقدار ثابت دلاری).

مرجع:
    Van K. Tharp, "Trade Your Way to Financial Freedom"
    (McGraw-Hill) — فصل مربوط به Position Sizing.

    همچنین به‌عنوان یک قاعده‌ی عمومی صنعت شناخته می‌شود که
    ریسک هر معامله را بین ۱٪ تا ۲٪ از کل سرمایه نگه دارند تا
    احتمال از دست دادن کامل سرمایه در یک رشته ضررهای متوالی
    به‌شدت کاهش یابد.

این فایل هیچ سیگنال خرید/فروشی تولید نمی‌کند؛ فقط "اندازه‌ی
پوزیشن" را بر اساس ریسک انتخابی کاربر و فاصله‌ی حد ضرر محاسبه
می‌کند.
"""

RISK_PROFILES = {
    "Low": {
        "label_fa": "کم (محافظه‌کارانه)",
        "risk_per_trade_pct": 0.5,
    },
    "Medium": {
        "label_fa": "متوسط",
        "risk_per_trade_pct": 1.0,
    },
    "High": {
        "label_fa": "بالا (تهاجمی)",
        "risk_per_trade_pct": 2.0,
    },
}


def list_risk_profiles():
    return [
        {
            "key": key,
            "label_fa": info["label_fa"],
            "risk_per_trade_pct": info["risk_per_trade_pct"],
        }
        for key, info in RISK_PROFILES.items()
    ]


def calculate_position_size(
    account_balance,
    risk_profile_key,
    entry_price,
    stop_loss_price,
):
    """
    Fixed Fractional Position Sizing:

        risk_amount = account_balance * (risk_pct / 100)
        position_size (به واحد کوین) = risk_amount / |entry_price - stop_loss_price|

    اگر entry_price برابر stop_loss_price باشد (فاصله صفر)،
    محاسبه ممکن نیست و None برگردانده می‌شود.
    """

    if risk_profile_key not in RISK_PROFILES:
        raise ValueError(f"Unknown risk profile: {risk_profile_key}")

    if account_balance is None or account_balance <= 0:
        return None

    price_distance = abs(entry_price - stop_loss_price)

    if price_distance == 0:
        return None

    risk_pct = RISK_PROFILES[risk_profile_key]["risk_per_trade_pct"]

    risk_amount = account_balance * (risk_pct / 100)

    position_size_units = risk_amount / price_distance

    return {
        "risk_amount_usd": risk_amount,
        "position_size_units": position_size_units,
        "risk_pct": risk_pct,
    }
