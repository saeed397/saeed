from .strategy import get_market_cap


class MarketCapAdapter:

    name = "Market Cap Strategy"

    def run(self, coin_ids):
        data = get_market_cap(coin_ids)

        return data
