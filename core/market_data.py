"""
core/market_data.py

منبع داده: CoinGecko Public API (همان منبعی که در
core/coin_universe.py و strategies/*/strategy.py استفاده شده است).

این فایل به‌عمد جدا از strategies/price و strategies/market_cap
نگه داشته شده تا:
    ۱. منطق آن دو Adapter موجود (که بخشی از معماری Plugin شما هستند)
       دست‌نخورده بماند.
    ۲. داده‌ی نمایشی داشبورد (قیمت لحظه‌ای، تغییر ۲۴ساعته) و
       داده‌ی تاریخی لازم برای Backtest، از یک نقطه‌ی مستقل و
       قابل نگهداری تامین شود.

منبع مستندات رسمی CoinGecko:
    https://docs.coingecko.com/reference/coins-markets
    https://docs.coingecko.com/reference/coins-id-market-chart
"""

import requests

COINGECKO_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"
COINGECKO_CHART_URL = "https://api.coingecko.com/api/v3/coins/{id}/market_chart"


def get_market_snapshot(coin_ids):
    """
    قیمت لحظه‌ای + تغییر ۲۴ساعته + مارکت‌کپ برای یک یا چند رمزارز.

    خروجی هر آیتم:
        {
            "id": ...,
            "symbol": ...,
            "name": ...,
            "current_price": ...,
            "price_change_percentage_24h": ...,
            "market_cap": ...,
        }
    """

    if not coin_ids:
        return []

    params = {
        "vs_currency": "usd",
        "ids": ",".join(coin_ids),
        "order": "market_cap_desc",
        "per_page": len(coin_ids),
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h",
    }

    response = requests.get(
        COINGECKO_MARKETS_URL,
        params=params,
        timeout=20,
    )

    response.raise_for_status()

    data = response.json()

    results = []

    for coin in data:
        results.append({
            "id": coin.get("id"),
            "symbol": (coin.get("symbol") or "").upper(),
            "name": coin.get("name"),
            "current_price": coin.get("current_price"),
            "price_change_percentage_24h": coin.get(
                "price_change_percentage_24h"
            ),
            "market_cap": coin.get("market_cap"),
        })

    return results


def get_historical_prices(coin_id, days):
    """
    قیمت‌های تاریخی روزانه‌ی یک رمزارز برای Backtest.

    days: تعداد روزهای گذشته (مثلاً 30, 90, 365)

    خروجی: لیستی از [timestamp_ms, price] طبق مستندات رسمی CoinGecko.
    """

    url = COINGECKO_CHART_URL.format(id=coin_id)

    params = {
        "vs_currency": "usd",
        "days": days,
    }

    response = requests.get(url, params=params, timeout=20)

    response.raise_for_status()

    data = response.json()

    return data.get("prices", [])
