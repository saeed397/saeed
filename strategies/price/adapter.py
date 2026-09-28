from .strategy import get_price


class PriceAdapter:

    name = "Price Strategy"

    def run(self, coin_ids):
        return get_price(coin_ids)
