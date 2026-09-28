"""
core/strategy_registry.py

هدف این فایل:
--------------
تنها منبع حقیقت (Single Source of Truth) برای لیست استراتژی‌های
نصب‌شده در پروژه، مخصوص ۴ ماژول جدید:
    - داشبورد تحلیل کریپتو
    - پنل مدیریت بات
    - پلتفرم Backtest
    - سیستم Alert

این فایل به core/strategy_manager.py یا core/orchestrator.py
هیچ تغییری نمی‌دهد. فقط یک لایه‌ی نازک روی روی آن‌هاست.

نکته‌ی مهم برای توسعه‌ی آینده:
------------------------------
وقتی یک استراتژی جدید به پوشه‌ی strategies/ اضافه کردید،
کافی است یک ورودی جدید به دیکشنری AVAILABLE_STRATEGIES زیر
اضافه کنید. همین یک تغییر باعث می‌شود استراتژی جدید به‌صورت
خودکار در منوی هر ۴ ماژول (داشبورد، بات، بک‌تست، الرت) ظاهر شود
- بدون نیاز به ویرایش دستی هر صفحه.

app.py اصلی (صفحه‌ی فعلی شما) دست‌نخورده باقی مانده و از این
Registry استفاده نمی‌کند، تا رفتار فعلی آن دقیقاً همان‌طور که
هست حفظ شود.
"""

from core.strategy_manager import StrategyManager

from strategies.market_cap.adapter import MarketCapAdapter
from strategies.price.adapter import PriceAdapter


# ------------------------------------------------------------
# لیست استراتژی‌های نصب‌شده
# ------------------------------------------------------------
# هر ورودی شامل:
#   label     : نامی که در چک‌باکس منوی هر ۴ ماژول نمایش داده می‌شود
#   adapter   : کلاس Adapter همان استراتژی (باید متد run() داشته باشد)
#
# برای افزودن استراتژی جدید در آینده، فقط یک خط اینجا اضافه کنید.
# ------------------------------------------------------------

AVAILABLE_STRATEGIES = {
    "MC": {
        "label": "Market Cap Strategy",
        "adapter": MarketCapAdapter,
    },
    "PX": {
        "label": "Price Strategy",
        "adapter": PriceAdapter,
    },
}


def list_available_strategies():
    """
    خروجی: لیستی از دیکشنری‌های {"key": ..., "label": ...}
    برای رندر شدن در منوهای چک‌باکسی ۴ ماژول جدید.
    """

    return [
        {"key": key, "label": info["label"]}
        for key, info in AVAILABLE_STRATEGIES.items()
    ]


def build_strategy_manager(active_keys=None):
    """
    یک StrategyManager تازه می‌سازد و فقط استراتژی‌های
    active_keys را در آن ثبت می‌کند.

    اگر active_keys داده نشود، همه‌ی استراتژی‌های ثبت‌شده
    در AVAILABLE_STRATEGIES فعال در نظر گرفته می‌شوند.

    این تابع از StrategyManager.register() موجود استفاده می‌کند
    و هیچ منطق جدیدی به آن اضافه نمی‌کند.
    """

    manager = StrategyManager()

    keys = (
        active_keys
        if active_keys is not None
        else list(AVAILABLE_STRATEGIES.keys())
    )

    for key in keys:
        if key not in AVAILABLE_STRATEGIES:
            continue

        adapter_cls = AVAILABLE_STRATEGIES[key]["adapter"]
        manager.register(key, adapter_cls())

    return manager
