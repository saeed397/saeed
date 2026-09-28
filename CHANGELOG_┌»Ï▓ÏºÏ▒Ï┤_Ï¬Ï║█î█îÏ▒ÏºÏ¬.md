# گزارش دقیق تغییرات — برای بازبینی شما

## فایل‌هایی که ۱۰۰٪ منطق‌شان دست‌نخورده باقی مانده
(فقط ایندنت و `def __init__` اصلاح شد تا کد معتبر Python باشد — هیچ خط منطقی حذف/اضافه/جابه‌جا نشده)

- `core/strategy_manager.py`
- `core/orchestrator.py`
- `core/master_decision.py`
- `core/result_manager.py`
- `core/result.py`
- `core/coin_universe.py`
- `strategies/market_cap/adapter.py`
- `strategies/market_cap/strategy.py`
- `strategies/price/adapter.py`
- `strategies/price/strategy.py`
- `tests/test_strategies.py`
- `app.py` — **کاملاً بدون تغییر رفتاری**؛ همان دو استراتژی MC/PX هاردکد شده، همان چک‌باکس‌ها، همان CSS، همان منطق RUN. فقط ایندنت اصلاح شد.

## فایل‌های کاملاً جدید (اضافه‌شده، چیزی را جایگزین نکرده‌اند)

| فایل | هدف |
|---|---|
| `core/strategy_registry.py` | تنها منبع حقیقت برای «چه استراتژی‌هایی نصب‌اند» — پایه‌ی منوی خودکار هر ۴ ماژول جدید |
| `core/ui_components.py` | کامپوننت مشترک چک‌باکس انتخاب استراتژی، استفاده‌شده در هر ۴ صفحه |
| `core/market_data.py` | دریافت قیمت لحظه‌ای/تغییر ۲۴ساعته/تاریخچه از CoinGecko — مستقل از Adapterهای موجود |
| `core/backtest_engine.py` | متریک‌های مستند مالی (Sharpe، Sortino، CAGR، Max Drawdown) |
| `core/risk_profiles.py` | مدیریت ریسک بر پایه‌ی روش مستند Fixed Fractional Position Sizing |
| `core/notifier.py` | ارسال هشدار چندکاناله (تلگرام/ایمیل/داخل اپ) |
| `pages/1_Dashboard.py` | ماژول ۱ |
| `pages/2_Bot_Panel.py` | ماژول ۲ |
| `pages/3_Backtest.py` | ماژول ۳ |
| `pages/4_Alerts.py` | ماژول ۴ |

## نکات مهم که حتماً باید بدانید

۱. **منبع داده همه‌جا CoinGecko است** — هیچ Binance ای در پروژه نیست.

۲. **Backtest فعلاً فقط Buy & Hold است** — چون MC/PX سیگنال خرید/فروش تولید نمی‌کنند. هر وقت خواستید یک استراتژی سیگنال‌دهنده‌ی مستند (مثل RSI یا Moving Average Crossover) اضافه شود، طبق تعهدم، ابتدا با شما مطرح می‌کنم و بعد پیاده می‌کنم.

۳. **بات و Alert فقط با تعامل دستی کار می‌کنند** — نه ۲۴ساعته در پس‌زمینه (محدودیت ذاتی Streamlit، نه یک باگ).

۴. **افزودن استراتژی جدید در آینده:** فقط کافی است در `core/strategy_registry.py`، دیکشنری `AVAILABLE_STRATEGIES` یک ورودی جدید بگیرد؛ همان لحظه در منوی هر ۴ ماژول ظاهر می‌شود — بدون نیاز به دست‌زدن به ۴ صفحه‌ی دیگر یا هسته‌ی اصلی.

۵. تمام فایل‌ها با `python -m py_compile` از نظر نحوی (Syntax) تست شدند و بدون خطا هستند. برای تست کامل اجرایی، آن را روی Streamlit Cloud بالا بیاورید (چون در این محیط دسترسی اینترنت برای اجرای واقعی Streamlit وجود نداشت).
