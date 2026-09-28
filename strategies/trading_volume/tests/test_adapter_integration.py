"""
Integration tests: validates TradingVolumeAdapter.run(inputs) against the
exact contract read from the real core/orchestrator.py and
core/strategy_registry.py (Adapter built with no args; orchestrator calls
`strategy.run(inputs)`).
"""

import os
import sys
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from strategies.trading_volume.adapter import TradingVolumeAdapter
from strategies.trading_volume.strategy import Candle, Trade
from strategies.trading_volume.behavioral_fingerprint import MIN_HISTORICAL_CANDLES


def _historical_candles(n, seed=3):
    rnd = random.Random(seed)
    out = []
    for _ in range(n):
        qv = 1000.0 + rnd.uniform(-100, 100)
        out.append(Candle(
            open=1.0, close=1.0 + rnd.uniform(-0.01, 0.01), quote_volume=qv,
            trade_count=50 + rnd.randint(-5, 5), taker_buy_quote_volume=qv * 0.5,
        ))
    return out


def _live_candles(n=51):
    return [
        Candle(open=1.0, close=1.01, quote_volume=1000.0, trade_count=50,
               taker_buy_quote_volume=500.0)
        for _ in range(n)
    ]


def _live_trades(n=500):
    return [Trade(price=1.0, base_qty=1.0 + (i % 9), quote_volume=1.0 + (i % 9), is_taker_buy=True)
            for i in range(n)]


def test_adapter_constructed_with_no_args_like_core_pattern():
    # Matches strategy_registry.build_strategy_manager(): adapter_cls()
    adapter = TradingVolumeAdapter()
    assert adapter.name == "Trading Volume Strategy"


def test_run_returns_uncertain_signal_when_history_insufficient():
    adapter = TradingVolumeAdapter()
    result = adapter.run({
        "symbol": "BTC",
        "price": 65000.0,
        "timeframe": "15m",
        "live_trades": _live_trades(),
        "live_candles": _live_candles(),
        "historical_candles": _historical_candles(10),  # too little
    })
    assert result["vqs_final"] is None
    assert "هشدار در عدم قطعیت بازار" in result["signal_text"]
    assert result["calibration_note"] is not None


def test_run_full_pipeline_with_sufficient_history():
    adapter = TradingVolumeAdapter()
    result = adapter.run({
        "symbol": "ETH",
        "price": 3200.0,
        "timeframe": "1h",
        "live_trades": _live_trades(),
        "live_candles": _live_candles(),
        "historical_candles": _historical_candles(MIN_HISTORICAL_CANDLES + 20),
    })
    assert result["vqs_final"] is not None
    assert "ETHUSDT" in result["signal_text"]
    assert result["asset_profile"] is not None
    assert result["asset_profile"].symbol == "ETH"


def test_get_params_schema_is_data_only():
    schema = TradingVolumeAdapter.get_params_schema()
    assert isinstance(schema, list)
    assert all("key" in f and "widget" in f and "label" in f for f in schema)
    allowed_widgets = {"selectbox", "radio", "checkbox"}
    assert all(f["widget"] in allowed_widgets for f in schema)


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
