"""
Unit tests for behavioral_fingerprint.py — validates the mandatory
Contextual Backtest and the one-directional (tighten-only) calibration
rule against the documented base thresholds.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import random

from strategies.trading_volume.config import TradingVolumeTechnicalConfig
from strategies.trading_volume.strategy import Candle
from strategies.trading_volume.behavioral_fingerprint import (
    build_asset_behavioral_profile,
    calibrate_config_for_asset,
    InsufficientHistoryError,
    MIN_HISTORICAL_CANDLES,
)

CFG = TradingVolumeTechnicalConfig()


def _stable_candles(n, seed=1):
    rnd = random.Random(seed)
    candles = []
    for i in range(n):
        qv = 1000.0 + rnd.uniform(-50, 50)
        candles.append(
            Candle(
                open=1.0,
                close=1.0 + rnd.uniform(-0.005, 0.005),
                quote_volume=qv,
                trade_count=50 + rnd.randint(-3, 3),
                taker_buy_quote_volume=qv * (0.5 + rnd.uniform(-0.02, 0.02)),
            )
        )
    return candles


def _volatile_candles(n, seed=2):
    rnd = random.Random(seed)
    candles = []
    for i in range(n):
        qv = 1000.0 * rnd.uniform(0.3, 4.0)  # much wider historical spread
        candles.append(
            Candle(
                open=1.0,
                close=1.0 + rnd.uniform(-0.05, 0.05),
                quote_volume=qv,
                trade_count=50 + rnd.randint(-20, 20),
                taker_buy_quote_volume=qv * (0.5 + rnd.uniform(-0.3, 0.3)),
            )
        )
    return candles


def test_insufficient_history_raises():
    try:
        build_asset_behavioral_profile("BTC", _stable_candles(10), CFG)
        assert False, "expected InsufficientHistoryError"
    except InsufficientHistoryError:
        pass


def test_profile_builds_with_enough_history():
    candles = _stable_candles(MIN_HISTORICAL_CANDLES + 20)
    profile = build_asset_behavioral_profile("BTC", candles, CFG)
    assert profile.symbol == "BTC"
    assert profile.n_candles_analyzed == len(candles)
    # Enough data should produce real statistics, not None
    assert profile.tbr_mean is not None


def test_calibration_never_loosens_below_documented_base():
    # A very "quiet" historical asset (tiny z-vol percentile) must NOT push
    # the whale threshold below the documented base of 2.0.
    candles = _stable_candles(MIN_HISTORICAL_CANDLES + 20)
    profile = build_asset_behavioral_profile("QUIET", candles, CFG)
    calibrated = calibrate_config_for_asset(CFG, profile)
    assert calibrated.zscore.z_vol_whale_threshold >= CFG.zscore.z_vol_whale_threshold
    assert calibrated.efficiency.fake_spike_efficiency_ratio <= CFG.efficiency.fake_spike_efficiency_ratio


def test_calibration_tightens_for_historically_volatile_asset():
    # A historically volatile asset should raise (tighten) the whale
    # threshold above the documented base, since its own 95th percentile of
    # |Z_Vol| will be well above 2.0.
    candles = _volatile_candles(MIN_HISTORICAL_CANDLES + 40)
    profile = build_asset_behavioral_profile("VOLATILE", candles, CFG)
    calibrated = calibrate_config_for_asset(CFG, profile)
    assert calibrated.zscore.z_vol_whale_threshold >= CFG.zscore.z_vol_whale_threshold


def test_calibration_never_crosses_documented_bull_bear_bounds():
    candles = _volatile_candles(MIN_HISTORICAL_CANDLES + 40)
    profile = build_asset_behavioral_profile("VOLATILE", candles, CFG)
    calibrated = calibrate_config_for_asset(CFG, profile)
    assert calibrated.flow.taker_buy_ratio_neutral_low > CFG.flow.taker_buy_ratio_bear
    assert calibrated.flow.taker_buy_ratio_neutral_high < CFG.flow.taker_buy_ratio_bull


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
