import requests


def get_market_cap(coin_ids):
    """
    دریافت Market Cap رمزارزها از CoinGecko

    coin_ids:
    لیستی از شناسه رمزارزها در CoinGecko
    مثال:
    ["bitcoin", "ethereum", "solana"]
    """

    url = "https://api.coingecko.com/api/v3/coins/markets"

    params = {
        "vs_currency": "usd",
        "ids": ",".join(coin_ids),
        "order": "market_cap_desc",
        "per_page": len(coin_ids),
        "page": 1,
        "sparkline": "false"
    }

    response = requests.get(url, params=params, timeout=20)

    response.raise_for_status()

    data = response.json()

    results = []

    for coin in data:
        results.append({
            "id": coin["id"],
            "symbol": coin["symbol"].upper(),
            "name": coin["name"],
            "market_cap": coin["market_cap"]
        })

    return results
