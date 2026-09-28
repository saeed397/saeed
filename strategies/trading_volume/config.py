"""
config.py
Trading Volume Strategy — Configuration Layer (Phase 1 & 2)

Contains:
  * All UI-facing enums, mirroring the 18 documented Streamlit controls
    (selectbox / checkbox), each with the documented default value.
  * TradingVolumeUIConfig: the user-facing configuration dataclass.
  * TradingVolumeTechnicalConfig: the hidden/technical thresholds used by
    the VQS engine (strategy.py) — every numeric value here is taken
    verbatim from the supplied documentation.
  * SignalTitle: the four permitted narrative signal titles.

ASSUMPTIONS REQUIRING YOUR APPROVAL (flagged per the "No Hallucination"
policy — nothing below silently overrides documented behaviour, but two
items are not numerically defined in the supplied documentation):

  1. SENSITIVITY_PROFILES: the doc defines "Sensitivity" (Conservative /
     Balanced / Aggressive) as a UI control that should encapsulate
     technical nuance, but does not give the exact multipliers. The values
     below (±15% on Z / Efficiency thresholds, ±0.05 on the Taker-Buy
     neutral band) are a proposed default only.
  2. MinimumVolumeSlope -> numeric slope fraction mapping (in adapter.py)
     is likewise not given a number in the documentation and is a proposed
     default.

Everything else (Benford RMSE formula/thresholds, Z-Score windows and
whale/bot thresholds, Amihud efficiency formula/thresholds, Taker
Buy Ratio / Open-Interest thresholds, axis weights, Omega gate values,
Volume Concentration Index thresholds, Yale round-number 5% threshold) is
copied directly from the supplied documentation.
"""

from dataclasses import dataclass, field, replace
from enum import Enum


# ---------------------------------------------------------------------------
# Enums mirroring the 18 documented Streamlit UI controls
# ---------------------------------------------------------------------------

class MAType(str, Enum):
    SMA = "SMA"
    EMA = "EMA"


class MinimumRelativeVolume(str, Enum):
    BELOW_AVERAGE = "Below Average"
    GE_AVERAGE = "≥ Average"
    GE_1_2X = "≥ 1.2x"
    GE_1_5X = "≥ 1.5x"
    GE_2X = "≥ 2x"


class VolumeTrend(str, Enum):
    NONE = "None"
    INCREASING = "Increasing"
    DECREASING = "Decreasing"
    INCREASING_AND_DECREASING = "Increasing + Decreasing"


class SpikeThreshold(str, Enum):
    X1_5 = "1.5"
    X2 = "2"
    X2_5 = "2.5"
    X3 = "3"
    AVG_2X = "2x Average"
    AVG_4X = "4x Average"


class VolumeComparison(str, Enum):
    PREVIOUS = "Previous"
    LAST_3 = "3"
    LAST_5 = "5"
    LAST_10 = "10"


class VolumeConfirmation(str, Enum):
    OFF = "Off"
    ABOVE_AVERAGE = "Above Average"
    MULTIPLIER = "Multiplier"


class BuySellVolume(str, Enum):
    TOTAL = "Total"
    BUY_DOMINANT = "Buy Dominant"
    SELL_DOMINANT = "Sell Dominant"
    BUY_AND_SELL = "Buy + Sell"


class VolumeDivergence(str, Enum):
    OFF = "Off"
    BULLISH = "Bullish"
    BEARISH = "Bearish"
    BOTH = "Both"


class Sensitivity(str, Enum):
    CONSERVATIVE = "Conservative"
    BALANCED = "Balanced"
    AGGRESSIVE = "Aggressive"


class VolumeSlope(str, Enum):
    OFF = "Off"
    RISING = "Rising"
    FALLING = "Falling"
    BOTH = "Both"


class MinimumVolumeSlope(str, Enum):
    VERY_LOW = "Very Low"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    VERY_HIGH = "Very High"


class VolumeIncreaseCondition(str, Enum):
    VS_AVERAGE = "Volume > average volume"
    VS_PREVIOUS_CANDLE = "Volume > previous candle volume"
    VS_AVERAGE_TIMES_MULTIPLIER = "Volume > average x multiplier"


class PressureMode(str, Enum):
    BUY_ONLY = "Buy pressure only"
    SELL_ONLY = "Sell pressure only"
    BOTH = "Two-sided confirmation (Buy & Sell)"


# ---------------------------------------------------------------------------
# UI Config (Phase 1) — one field per documented control, documented defaults
# ---------------------------------------------------------------------------

@dataclass
class TradingVolumeUIConfig:
    volume_ema_length: int = 20                     # 9/10/20/21/30/50/100/200
    ma_type: MAType = MAType.SMA
    volume_multiplier: float = 1.5                  # 1.2/1.5/2/2.5/3
    minimum_relative_volume: MinimumRelativeVolume = MinimumRelativeVolume.GE_AVERAGE
    volume_trend: VolumeTrend = VolumeTrend.INCREASING
    volume_spike_enabled: bool = True
    spike_threshold: SpikeThreshold = SpikeThreshold.AVG_2X
    volume_comparison: VolumeComparison = VolumeComparison.LAST_3
    volume_confirmation: VolumeConfirmation = VolumeConfirmation.ABOVE_AVERAGE
    buy_sell_volume: BuySellVolume = BuySellVolume.TOTAL
    volume_divergence: VolumeDivergence = VolumeDivergence.BOTH
    volume_lookback: int = 30                       # 10/20/30/50/100
    sensitivity: Sensitivity = Sensitivity.BALANCED
    rvol_mode_candles: int = 5                      # 1/3/5/7/10/20
    volume_slope: VolumeSlope = VolumeSlope.BOTH
    minimum_volume_slope: MinimumVolumeSlope = MinimumVolumeSlope.MEDIUM
    volume_increase_condition: VolumeIncreaseCondition = (
        VolumeIncreaseCondition.VS_AVERAGE_TIMES_MULTIPLIER
    )
    pressure_mode: PressureMode = PressureMode.BOTH


# ---------------------------------------------------------------------------
# Technical / Hidden Config (Phase 2 — VQS engine), values from the spec
# ---------------------------------------------------------------------------

@dataclass
class BenfordAxisConfig:
    window_minutes: int = 5
    rmse_score_scale: float = 0.15          # S_Ben = 100*(1 - RMSE/0.15)
    red_flag_rmse: float = 0.12
    red_flag_round_trade_pct: float = 0.35  # >35% identical rounded sizes


@dataclass
class ZScoreAxisConfig:
    rolling_window_candles: int = 20
    z_vol_whale_threshold: float = 2.0
    z_size_whale_threshold: float = 2.0
    normal_market_abs_z_vol: float = 1.0
    normal_market_score: float = 70.0


@dataclass
class EfficiencyAxisConfig:
    baseline_window_candles: int = 50       # PER_50 moving average
    fake_spike_z_vol_threshold: float = 2.0
    fake_spike_efficiency_ratio: float = 0.15
    fake_spike_score: float = 10.0


@dataclass
class FlowAxisConfig:
    taker_buy_ratio_bull: float = 0.60
    taker_buy_ratio_bear: float = 0.40
    taker_buy_ratio_neutral_low: float = 0.48
    taker_buy_ratio_neutral_high: float = 0.52
    neutral_score: float = 15.0
    directional_score: float = 100.0


@dataclass
class OmegaGateConfig:
    fake_spike_z_vol_threshold: float = 2.5
    fake_spike_efficiency_threshold: float = 15.0
    fake_spike_omega: float = 0.2
    benford_red_flag_omega: float = 0.0
    normal_omega: float = 1.0


@dataclass
class VolumeConcentrationConfig:
    """Volume Concentration Index (documented extension)."""
    concentrated_threshold: float = 0.5     # Z_Vol - Z_Count > 0.5 -> whale
    dispersed_threshold: float = -1.5       # < -1.5 -> wash-trading bots


@dataclass
class RoundNumberClusteringConfig:
    """Yale Roundness & Clustering Filter (documented extension)."""
    round_bases: tuple = (10, 50, 100, 500, 1000)
    red_flag_round_ratio: float = 0.05      # <5% round trades -> red flag


@dataclass
class VQSWeights:
    w_benford: float = 0.25
    w_zscore: float = 0.25
    w_efficiency: float = 0.25
    w_flow: float = 0.25


@dataclass
class SensitivityAdjustment:
    """
    Proposed (NOT explicitly numerically documented) scaling applied on top
    of the documented base thresholds, per Sensitivity profile.
    Pending your review — see module docstring, item 1.
    """
    z_threshold_multiplier: float = 1.0
    efficiency_threshold_multiplier: float = 1.0
    taker_ratio_tightening: float = 0.0


SENSITIVITY_PROFILES = {
    Sensitivity.CONSERVATIVE: SensitivityAdjustment(
        z_threshold_multiplier=1.15,
        efficiency_threshold_multiplier=0.85,
        taker_ratio_tightening=0.05,
    ),
    Sensitivity.BALANCED: SensitivityAdjustment(
        z_threshold_multiplier=1.0,
        efficiency_threshold_multiplier=1.0,
        taker_ratio_tightening=0.0,
    ),
    Sensitivity.AGGRESSIVE: SensitivityAdjustment(
        z_threshold_multiplier=0.85,
        efficiency_threshold_multiplier=1.15,
        taker_ratio_tightening=-0.05,
    ),
}


@dataclass
class TradingVolumeTechnicalConfig:
    benford: BenfordAxisConfig = field(default_factory=BenfordAxisConfig)
    zscore: ZScoreAxisConfig = field(default_factory=ZScoreAxisConfig)
    efficiency: EfficiencyAxisConfig = field(default_factory=EfficiencyAxisConfig)
    flow: FlowAxisConfig = field(default_factory=FlowAxisConfig)
    omega: OmegaGateConfig = field(default_factory=OmegaGateConfig)
    concentration: VolumeConcentrationConfig = field(default_factory=VolumeConcentrationConfig)
    round_clustering: RoundNumberClusteringConfig = field(
        default_factory=RoundNumberClusteringConfig
    )
    weights: VQSWeights = field(default_factory=VQSWeights)


class SignalTitle(str, Enum):
    """Only these four titles may be used, per the spec's mobile-output rules."""
    BUY = "سیگنال خرید"
    SELL = "سیگنال فروش"
    RANGE = "بازار رنج"
    UNCERTAIN = "هشدار در عدم قطعیت بازار"


# ---------------------------------------------------------------------------
# Dynamic UI Parameter Schema (Architectural Exemption — "توضیح ۱")
# ---------------------------------------------------------------------------
# Pure data, no widgets: the UI_Renderer (core/ui_renderer.py) reads this to
# auto-render controls. Only "widget" values from the project's allowed set
# are used: selectbox, radio, checkbox. (No slider/toggle — forbidden by the
# project's UI rules.) Every entry gets a short "help" string, shown via
# st.popover("?") next to the control, per the concise-UI requirement.

PARAMS_SCHEMA = [
    {"key": "volume_ema_length", "label": "Vol EMA Length", "widget": "selectbox",
     "options": [9, 10, 20, 21, 30, 50, 100, 200], "default": 20,
     "help": "Lookback length of the volume moving average."},
    {"key": "ma_type", "label": "MA Type", "widget": "selectbox",
     "options": [e.value for e in MAType], "default": MAType.SMA.value,
     "help": "Moving-average type used for the volume baseline."},
    {"key": "volume_multiplier", "label": "Vol Multiplier", "widget": "selectbox",
     "options": [1.2, 1.5, 2, 2.5, 3], "default": 1.5,
     "help": "Multiplier applied to average volume for confirmation checks."},
    {"key": "minimum_relative_volume", "label": "Min Relative Vol", "widget": "selectbox",
     "options": [e.value for e in MinimumRelativeVolume], "default": MinimumRelativeVolume.GE_AVERAGE.value,
     "help": "Minimum volume required, relative to its moving average."},
    {"key": "volume_trend", "label": "Vol Trend", "widget": "selectbox",
     "options": [e.value for e in VolumeTrend], "default": VolumeTrend.INCREASING.value,
     "help": "Required trend direction of volume over recent candles."},
    {"key": "volume_spike_enabled", "label": "Vol Spike Filter", "widget": "checkbox",
     "options": None, "default": True,
     "help": "Enable/disable the volume-spike detector."},
    {"key": "spike_threshold", "label": "Spike Threshold", "widget": "selectbox",
     "options": [e.value for e in SpikeThreshold], "default": SpikeThreshold.AVG_2X.value,
     "help": "Multiplier that defines what counts as a volume spike."},
    {"key": "volume_comparison", "label": "Compare vs N Candles", "widget": "selectbox",
     "options": [e.value for e in VolumeComparison], "default": VolumeComparison.LAST_3.value,
     "help": "How many prior candles volume is compared against."},
    {"key": "volume_confirmation", "label": "Vol Confirmation", "widget": "selectbox",
     "options": [e.value for e in VolumeConfirmation], "default": VolumeConfirmation.ABOVE_AVERAGE.value,
     "help": "Extra confirmation rule required before a signal is valid."},
    {"key": "buy_sell_volume", "label": "Buy/Sell Vol Mode", "widget": "selectbox",
     "options": [e.value for e in BuySellVolume], "default": BuySellVolume.TOTAL.value,
     "help": "Which side of volume (buy/sell/total) drives the signal."},
    {"key": "volume_divergence", "label": "Vol Divergence", "widget": "selectbox",
     "options": [e.value for e in VolumeDivergence], "default": VolumeDivergence.BOTH.value,
     "help": "Detect divergence between price and volume."},
    {"key": "volume_lookback", "label": "Vol Lookback", "widget": "selectbox",
     "options": [10, 20, 30, 50, 100], "default": 30,
     "help": "Number of candles used for volume baseline statistics."},
    {"key": "sensitivity", "label": "Sensitivity", "widget": "radio",
     "options": [e.value for e in Sensitivity], "default": Sensitivity.BALANCED.value,
     "help": "Overall strictness profile: Conservative/Balanced/Aggressive."},
    {"key": "rvol_mode_candles", "label": "RVOL Candles", "widget": "selectbox",
     "options": [1, 3, 5, 7, 10, 20], "default": 5,
     "help": "Candle count used for the Relative Volume calculation."},
    {"key": "volume_slope", "label": "Vol Slope", "widget": "selectbox",
     "options": [e.value for e in VolumeSlope], "default": VolumeSlope.BOTH.value,
     "help": "Required slope direction of the volume curve."},
    {"key": "minimum_volume_slope", "label": "Min Vol Slope", "widget": "selectbox",
     "options": [e.value for e in MinimumVolumeSlope], "default": MinimumVolumeSlope.MEDIUM.value,
     "help": "Minimum required steepness of the volume slope."},
    {"key": "volume_increase_condition", "label": "Vol Increase Rule", "widget": "selectbox",
     "options": [e.value for e in VolumeIncreaseCondition],
     "default": VolumeIncreaseCondition.VS_AVERAGE_TIMES_MULTIPLIER.value,
     "help": "Rule that defines what counts as a volume increase."},
    {"key": "pressure_mode", "label": "Pressure Mode", "widget": "selectbox",
     "options": [e.value for e in PressureMode], "default": PressureMode.BOTH.value,
     "help": "Which side's pressure (buy/sell/both) must be confirmed."},
]


def ui_config_from_raw_dict(raw: dict) -> "TradingVolumeUIConfig":
    """
    Builds a TradingVolumeUIConfig from a plain dict of {param_key: value}
    as produced by the Dynamic UI_Renderer (values are raw strings/numbers
    from Streamlit widgets, matched back to their Enum by value).
    Missing keys fall back to the dataclass defaults.
    """
    enum_map = {
        "ma_type": MAType,
        "minimum_relative_volume": MinimumRelativeVolume,
        "volume_trend": VolumeTrend,
        "spike_threshold": SpikeThreshold,
        "volume_comparison": VolumeComparison,
        "volume_confirmation": VolumeConfirmation,
        "buy_sell_volume": BuySellVolume,
        "volume_divergence": VolumeDivergence,
        "sensitivity": Sensitivity,
        "volume_slope": VolumeSlope,
        "minimum_volume_slope": MinimumVolumeSlope,
        "volume_increase_condition": VolumeIncreaseCondition,
        "pressure_mode": PressureMode,
    }

    kwargs = {}
    defaults = TradingVolumeUIConfig()
    for field_name in defaults.__dataclass_fields__:
        if field_name not in raw:
            continue
        value = raw[field_name]
        if field_name in enum_map and not isinstance(value, enum_map[field_name]):
            value = enum_map[field_name](value)
        kwargs[field_name] = value

    return replace(defaults, **kwargs)
