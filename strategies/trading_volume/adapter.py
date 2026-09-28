"""
adapter.py
Trading Volume Strategy — Translation / Abstraction Layer (Phase 1)

Pure mapping layer: converts TradingVolumeUIConfig (what the user picks in
Streamlit) into the technical parameters strategy.py needs, and applies the
Sensitivity profile's adjustments on top of the documented base
TradingVolumeTechnicalConfig. Contains NO signal-generation logic.
"""

from dataclasses import replace
from typing import Optional

from .config import (
    TradingVolumeUIConfig,
    TradingVolumeTechnicalConfig,
    SENSITIVITY_PROFILES,
    MinimumRelativeVolume,
    SpikeThreshold,
    VolumeComparison,
    MinimumVolumeSlope,
    PARAMS_SCHEMA,
    ui_config_from_raw_dict,
    SignalTitle,
)
from .strategy import compute_vqs, generate_signal_text
from .behavioral_fingerprint import (
    build_asset_behavioral_profile,
    calibrate_config_for_asset,
    InsufficientHistoryError,
)


# Minimum Relative Volume -> float multiplier of the moving average
_MIN_REL_VOLUME_MAP = {
    MinimumRelativeVolume.BELOW_AVERAGE: 0.0,  # explicitly allows < average
    MinimumRelativeVolume.GE_AVERAGE: 1.0,
    MinimumRelativeVolume.GE_1_2X: 1.2,
    MinimumRelativeVolume.GE_1_5X: 1.5,
    MinimumRelativeVolume.GE_2X: 2.0,
}

# Spike Threshold -> float multiplier ("x Average" variants share the same
# multiplier semantics as the literal numeric options)
_SPIKE_THRESHOLD_MAP = {
    SpikeThreshold.X1_5: 1.5,
    SpikeThreshold.X2: 2.0,
    SpikeThreshold.X2_5: 2.5,
    SpikeThreshold.X3: 3.0,
    SpikeThreshold.AVG_2X: 2.0,
    SpikeThreshold.AVG_4X: 4.0,
}

# Volume Comparison -> number of prior candles to compare against
_VOLUME_COMPARISON_MAP = {
    VolumeComparison.PREVIOUS: 1,
    VolumeComparison.LAST_3: 3,
    VolumeComparison.LAST_5: 5,
    VolumeComparison.LAST_10: 10,
}

# Minimum Volume Slope -> required slope magnitude as a fraction of the
# rolling volume's standard deviation.
# NOT given a number in the documentation — proposed default, pending approval.
_MIN_VOLUME_SLOPE_MAP = {
    MinimumVolumeSlope.VERY_LOW: 0.10,
    MinimumVolumeSlope.LOW: 0.25,
    MinimumVolumeSlope.MEDIUM: 0.50,
    MinimumVolumeSlope.HIGH: 0.75,
    MinimumVolumeSlope.VERY_HIGH: 1.00,
}


class TradingVolumeAdapter:
    """
    Translation layer + orchestrator entry point.

    Registration contract (core/strategy_registry.py): built with NO
    arguments — `adapter_cls()` — matching the existing PriceAdapter /
    MarketCapAdapter pattern, so no change to build_strategy_manager() is
    needed. Per-request UI parameter selections (e.g. from the Dynamic
    UI_Renderer) are instead passed at call time via `run(inputs)`.
    """

    name = "Trading Volume Strategy"

    def __init__(self, ui_config: Optional[TradingVolumeUIConfig] = None):
        self.ui_config = ui_config or TradingVolumeUIConfig()

    @classmethod
    def get_params_schema(cls):
        """Data-only parameter metadata for the Dynamic UI_Renderer."""
        return PARAMS_SCHEMA

    def get_minimum_relative_volume_multiplier(self) -> float:
        return _MIN_REL_VOLUME_MAP[self.ui_config.minimum_relative_volume]

    def get_spike_threshold_multiplier(self) -> float:
        return _SPIKE_THRESHOLD_MAP[self.ui_config.spike_threshold]

    def get_volume_comparison_candles(self) -> int:
        return _VOLUME_COMPARISON_MAP[self.ui_config.volume_comparison]

    def get_minimum_volume_slope_fraction(self) -> float:
        return _MIN_VOLUME_SLOPE_MAP[self.ui_config.minimum_volume_slope]

    def build_technical_config(
        self,
        base_config: Optional[TradingVolumeTechnicalConfig] = None,
    ) -> TradingVolumeTechnicalConfig:
        """
        Produces the final TradingVolumeTechnicalConfig for strategy.py:
        starts from the documented base VQS thresholds and applies the
        Sensitivity profile's adjustment multipliers on top.
        """
        base = base_config or TradingVolumeTechnicalConfig()
        adj = SENSITIVITY_PROFILES[self.ui_config.sensitivity]

        zscore = replace(
            base.zscore,
            z_vol_whale_threshold=base.zscore.z_vol_whale_threshold * adj.z_threshold_multiplier,
            z_size_whale_threshold=base.zscore.z_size_whale_threshold * adj.z_threshold_multiplier,
        )
        efficiency = replace(
            base.efficiency,
            fake_spike_efficiency_ratio=(
                base.efficiency.fake_spike_efficiency_ratio
                * adj.efficiency_threshold_multiplier
            ),
        )
        flow = replace(
            base.flow,
            taker_buy_ratio_bull=base.flow.taker_buy_ratio_bull + adj.taker_ratio_tightening,
            taker_buy_ratio_bear=base.flow.taker_buy_ratio_bear - adj.taker_ratio_tightening,
        )

        return replace(base, zscore=zscore, efficiency=efficiency, flow=flow)

    def as_dict(self) -> dict:
        """Flat technical summary of current UI selections (logging / UI display)."""
        return {
            "volume_ema_length": self.ui_config.volume_ema_length,
            "ma_type": self.ui_config.ma_type.value,
            "volume_multiplier": self.ui_config.volume_multiplier,
            "minimum_relative_volume_x": self.get_minimum_relative_volume_multiplier(),
            "volume_trend": self.ui_config.volume_trend.value,
            "volume_spike_enabled": self.ui_config.volume_spike_enabled,
            "spike_threshold_x": self.get_spike_threshold_multiplier(),
            "volume_comparison_candles": self.get_volume_comparison_candles(),
            "volume_confirmation": self.ui_config.volume_confirmation.value,
            "buy_sell_volume": self.ui_config.buy_sell_volume.value,
            "volume_divergence": self.ui_config.volume_divergence.value,
            "volume_lookback": self.ui_config.volume_lookback,
            "sensitivity": self.ui_config.sensitivity.value,
            "rvol_mode_candles": self.ui_config.rvol_mode_candles,
            "volume_slope": self.ui_config.volume_slope.value,
            "minimum_volume_slope_fraction": self.get_minimum_volume_slope_fraction(),
            "volume_increase_condition": self.ui_config.volume_increase_condition.value,
            "pressure_mode": self.ui_config.pressure_mode.value,
        }

    def run(self, inputs: dict) -> dict:
        """
        Contract expected by core/orchestrator.py:
            result = strategy.run(inputs)   # `strategy` is this Adapter

        Required keys in `inputs`:
            symbol             : str  (e.g. "BTC")
            price              : float (current price, for the text output)
            timeframe          : str  (e.g. "15m")
            live_trades        : Sequence[Trade]     (recent trades)
            live_candles       : Sequence[Candle]    (recent candles, VQS window)
            historical_candles : Sequence[Candle]    (long history for the
                                                       mandatory Behavioral
                                                       Fingerprint)
        Optional:
            ui_params          : dict  (raw selections from the Dynamic
                                         UI_Renderer; overrides self.ui_config
                                         for this call only)

        Returns a plain dict (MasterDecisionEngine stores it as-is in
        `result.data`, so no fixed schema is imposed by core/).
        """
        if "ui_params" in inputs and inputs["ui_params"]:
            self.ui_config = ui_config_from_raw_dict(inputs["ui_params"])

        symbol = inputs["symbol"]
        price = inputs["price"]
        timeframe = inputs["timeframe"]
        live_trades = inputs["live_trades"]
        live_candles = inputs["live_candles"]
        historical_candles = inputs["historical_candles"]

        base_cfg = self.build_technical_config()

        # MANDATORY PRE-SIGNAL STEP: Behavioral Fingerprint / Contextual Backtest.
        # No signal may be produced without this running first.
        try:
            profile = build_asset_behavioral_profile(symbol, historical_candles, base_cfg)
            calibrated_cfg = calibrate_config_for_asset(base_cfg, profile)
            calibration_note = None
        except InsufficientHistoryError as exc:
            # Fail safe, not silent: report uncertainty rather than fabricate
            # a signal without the mandatory calibration step.
            profile = None
            calibrated_cfg = base_cfg
            calibration_note = str(exc)

        if calibration_note:
            symbol_disp = symbol if symbol.upper().endswith("USDT") else f"{symbol}USDT"
            return {
                "symbol": symbol,
                "signal_text": (
                    f"{symbol_disp} | {timeframe}\nقیمت: {price}\n"
                    f"{SignalTitle.UNCERTAIN.value}\n"
                    f"دادهٔ تاریخی کافی برای Behavioral Fingerprint موجود نیست؛ "
                    f"سیگنال صادر نشد."
                ),
                "vqs_final": None,
                "omega": None,
                "asset_profile": None,
                "calibration_note": calibration_note,
            }

        vqs_result = compute_vqs(live_trades, live_candles, calibrated_cfg)
        signal_text = generate_signal_text(symbol, price, timeframe, vqs_result)

        return {
            "symbol": symbol,
            "signal_text": signal_text,
            "vqs_final": vqs_result.vqs_final,
            "omega": vqs_result.omega,
            "asset_profile": profile,
            "calibration_note": None,
        }
