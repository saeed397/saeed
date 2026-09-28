import requests


def get_price(coin_ids):
    """
    دریافت قیمت فعلی رمزارزها از CoinGecko
    """

    url = "https://api.coingecko.com/api/v3/simple/price"

    params = {
        "ids": ",".join(coin_ids),
        "vs_currencies": "usd"
    }

    response = requests.get(
        url,
        params=params,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    results = []

    for coin_id in coin_ids:
        if coin_id in data:
            results.append({
                "id": coin_id,
                "price": data[coin_id]["usd"]
            })

    return results
