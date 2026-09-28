import requests

COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/coins/markets"
)


def get_top_500_coins():
    coins = []

    for page in (1, 2):
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 250,
            "page": page,
            "sparkline": "false"
        }

        response = requests.get(
            COINGECKO_URL,
            params=params,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        coins.extend(data)

    return coins[:500]
