from core.strategy_manager import StrategyManager
from core.orchestrator import Orchestrator

from strategies.market_cap.adapter import MarketCapAdapter
from strategies.price.adapter import PriceAdapter


def test_market_cap_strategy():
    manager = StrategyManager()

    manager.register(
        "Market Cap",
        MarketCapAdapter()
    )

    orchestrator = Orchestrator(
        manager
    )

    result = orchestrator.run_strategy(
        "Market Cap",
        ["bitcoin"]
    )

    assert result.strategy_name == "Market Cap"

    assert isinstance(
        result.data,
        list
    )

    assert len(result.data) > 0


def test_price_strategy():
    manager = StrategyManager()

    manager.register(
        "Price",
        PriceAdapter()
    )

    orchestrator = Orchestrator(
        manager
    )

    result = orchestrator.run_strategy(
        "Price",
        ["bitcoin"]
    )

    assert result.strategy_name == "Price"

    assert isinstance(
        result.data,
        list
    )

    assert len(result.data) > 0
