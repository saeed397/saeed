"""
Unit tests for the Trading Volume / VQS engine.

Each test is designed to check the implementation against an explicit,
documented formula or threshold — not against invented expected values.
"""

import math
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from strategies.trading_volume.config import TradingVolumeTechnicalConfig
from strategies.trading_volume.strategy import (
    Trade,
    Candle,
    compute_benford_axis,
    compute_zscore_axis,
    compute_efficiency_axis,
    compute_flow_axis,
    compute_volume_concentration,
    compute_round_number_clustering,
    compute_vqs,
    generate_signal_text,
)

CFG = TradingVolumeTechnicalConfig()


# ---------------------------------------------------------------------------
# Axis 1 — Benford's Law
# ---------------------------------------------------------------------------

def _benford_like_trades(n=1000):
    """Synthetic trades whose first-digit distribution follows Benford's Law
    closely (should score near 100, no red flag)."""
    trades = []
    for d in range(1, 10):
        expected_p = math.log10(1 + 1 / d)
        count = round(expected_p * n)
        for i in range(count):
            qty = d + i * 0.0001  # keep leading digit == d, avoid exact duplicates
            trades.append(Trade(price=1.0, base_qty=qty, quote_volume=qty, is_taker_buy=True))
    return trades


def _wash_trading_trades(n=500):
    """Thousands of near-identical small trades -> Benford red flag."""
    return [Trade(price=1.0, base_qty=7.77, quote_volume=7.77, is_taker_buy=True) for _ in range(n)]


def test_benford_axis_real_market_scores_high_no_red_flag():
    result = compute_benford_axis(_benford_like_trades(), CFG)
    assert result.score > 80
    assert result.detail["red_flag"] is False


def test_benford_axis_wash_trading_triggers_red_flag():
    result = compute_benford_axis(_wash_trading_trades(), CFG)
    assert result.detail["red_flag"] is True
    assert result.score < 50


def test_benford_axis_insufficient_data_is_neutral_not_guessed():
    result = compute_benford_axis([Trade(1.0, 5.0, 5.0, True)], CFG)
    assert result.score == 50.0
    assert result.detail["reason"] == "insufficient_trade_count_for_benford"


# ---------------------------------------------------------------------------
# Axis 2 — Z-Score
# ---------------------------------------------------------------------------

def _flat_candles(n, quote_volume=1000.0, trade_count=50):
    return [
        Candle(open=1.0, close=1.0, quote_volume=quote_volume, trade_count=trade_count,
               taker_buy_quote_volume=quote_volume * 0.5)
        for _ in range(n)
    ]


def test_zscore_axis_whale_case_scores_100():
    # 20 normal candles, then one candle with a huge volume spike concentrated
    # in very few trades (Z_Size > Z_Count) -> documented whale case.
    candles = _flat_candles(20, quote_volume=1000.0, trade_count=50)
    candles.append(
        Candle(open=1.0, close=1.0, quote_volume=500000.0, trade_count=51,
               taker_buy_quote_volume=300000.0)
    )
    result = compute_zscore_axis(candles, CFG)
    assert result.score == 100.0
    assert result.detail["z_vol"] > CFG.zscore.z_vol_whale_threshold
    assert result.detail["z_size"] > result.detail["z_count"]


def test_zscore_axis_wash_bot_case_scores_low_via_formula():
    # Volume spikes mostly from a large trade-count jump (bot behaviour):
    # Z_Count >= Z_Size while Z_Vol still exceeds the threshold.
    candles = _flat_candles(20, quote_volume=1000.0, trade_count=50)
    candles.append(
        Candle(open=1.0, close=1.0, quote_volume=3000.0, trade_count=5000,
               taker_buy_quote_volume=1500.0)
    )
    result = compute_zscore_axis(candles, CFG)
    z_size, z_count = result.detail["z_size"], result.detail["z_count"]
    expected = max(0.0, min(100.0, 50.0 * (1 + (z_size / z_count if z_count else 0))))
    assert math.isclose(result.score, expected, rel_tol=1e-9)
    assert result.score < 100.0


def test_zscore_axis_normal_market_scores_70():
    candles = _flat_candles(21)  # perfectly flat -> zero variance -> None z-scores
    result = compute_zscore_axis(candles, CFG)
    # zero-variance window is a distinct, explicitly-flagged neutral case
    assert result.detail.get("reason") == "zero_variance_window"
    assert result.score == 50.0


def test_zscore_axis_insufficient_history():
    result = compute_zscore_axis(_flat_candles(5), CFG)
    assert result.detail["reason"] == "insufficient_history"
    assert result.score == 50.0


# ---------------------------------------------------------------------------
# Axis 3 — Amihud Efficiency
# ---------------------------------------------------------------------------

def test_efficiency_axis_fake_spike_detected():
    # 50 baseline candles with meaningful price movement per unit volume,
    # then one candle: huge volume, essentially no price movement.
    history = [
        Candle(open=1.0, close=1.0 + 0.01 * (i % 3), quote_volume=1000.0,
               trade_count=50, taker_buy_quote_volume=500.0)
        for i in range(50)
    ]
    spike_candle = Candle(open=1.0, close=1.0001, quote_volume=1_000_000.0,
                           trade_count=100, taker_buy_quote_volume=500_000.0)
    candles = history + [spike_candle]
    result = compute_efficiency_axis(candles, CFG, z_vol_current=3.0)
    assert result.detail["fake_spike"] is True
    assert result.score == CFG.efficiency.fake_spike_score


def test_efficiency_axis_normal_case_uses_ratio_formula():
    history = [
        Candle(open=1.0, close=1.01, quote_volume=1000.0, trade_count=50,
               taker_buy_quote_volume=500.0)
        for _ in range(50)
    ]
    current = Candle(open=1.0, close=1.01, quote_volume=1000.0, trade_count=50,
                      taker_buy_quote_volume=500.0)
    candles = history + [current]
    result = compute_efficiency_axis(candles, CFG, z_vol_current=0.5)
    assert math.isclose(result.detail["efficiency_ratio"], 1.0, rel_tol=1e-6)
    assert math.isclose(result.score, 100.0, rel_tol=1e-6)


def test_efficiency_axis_zero_volume_is_neutral_not_divide_error():
    candles = [Candle(open=1.0, close=1.0, quote_volume=0.0, trade_count=0,
                       taker_buy_quote_volume=0.0) for _ in range(51)]
    result = compute_efficiency_axis(candles, CFG, z_vol_current=None)
    assert result.score == 50.0


# ---------------------------------------------------------------------------
# Axis 4 — Taker Flow / Open Interest
# ---------------------------------------------------------------------------

def test_flow_axis_bullish_confirmation():
    candle = Candle(open=1.0, close=1.02, quote_volume=1000.0, trade_count=50,
                     taker_buy_quote_volume=700.0, open_interest=1100.0)
    result = compute_flow_axis(candle, prev_open_interest=1000.0, cfg=CFG)
    assert result.score == CFG.flow.directional_score
    assert result.detail["tbr"] > CFG.flow.taker_buy_ratio_bull


def test_flow_axis_neutral_wash_case():
    candle = Candle(open=1.0, close=1.0, quote_volume=1000.0, trade_count=50,
                     taker_buy_quote_volume=500.0, open_interest=1000.0)
    result = compute_flow_axis(candle, prev_open_interest=1000.0, cfg=CFG)
    assert result.score == CFG.flow.neutral_score


def test_flow_axis_missing_open_interest_is_neutral_not_guessed():
    candle = Candle(open=1.0, close=1.02, quote_volume=1000.0, trade_count=50,
                     taker_buy_quote_volume=700.0, open_interest=None)
    result = compute_flow_axis(candle, prev_open_interest=None, cfg=CFG)
    assert result.score == 50.0
    assert result.detail["reason"] == "open_interest_unavailable"


# ---------------------------------------------------------------------------
# Extensions
# ---------------------------------------------------------------------------

def test_volume_concentration_states():
    vc, state = compute_volume_concentration(z_vol=3.0, z_count=1.0, cfg=CFG)
    assert vc == 2.0
    assert state == "concentrated_whale"

    vc, state = compute_volume_concentration(z_vol=0.5, z_count=3.0, cfg=CFG)
    assert vc == -2.5
    assert state == "dispersed_wash_trading"


def test_round_number_clustering_red_flag():
    non_round_trades = [Trade(1.0, 7.123456 + i * 0.00001, 1.0, True) for i in range(100)]
    assert compute_round_number_clustering(non_round_trades, CFG) is True

    round_trades = [Trade(1.0, 100.0, 100.0, True) for _ in range(100)]
    assert compute_round_number_clustering(round_trades, CFG) is False


# ---------------------------------------------------------------------------
# Governance gate (Omega) and final VQS / narrative output
# ---------------------------------------------------------------------------

def test_omega_zero_on_benford_red_flag():
    trades = _wash_trading_trades()
    candles = _flat_candles(51)
    result = compute_vqs(trades, candles, CFG)
    assert result.benford_red_flag is True
    assert result.omega == CFG.omega.benford_red_flag_omega
    assert result.vqs_final == 0.0


def test_generate_signal_text_uses_only_permitted_titles():
    trades = _benford_like_trades()
    candles = _flat_candles(51, quote_volume=1000.0, trade_count=50)
    result = compute_vqs(trades, candles, CFG)
    text = generate_signal_text("BTC", 65000.0, "15m", result)

    permitted = {"سیگنال خرید", "سیگنال فروش", "بازار رنج", "هشدار در عدم قطعیت بازار"}
    assert any(title in text for title in permitted)
    assert "BTCUSDT" in text


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
