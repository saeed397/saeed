"""
behavioral_fingerprint.py
Trading Volume Strategy — Behavioral Fingerprint / Contextual Backtest Layer
(Phase 2 addition — "توضیح ۲")

Implements the project-wide "Asset-Specific Behavior Calibration" rule for
this strategy:
  1. MANDATORY PRE-SIGNAL STEP — a historical (Contextual Backtest) pass over
     the specific asset's own candles must run before any live signal.
  2. DYNAMIC CALIBRATION — VQS thresholds are personalized to that asset's
     own historical behaviour instead of using the fixed universal constants
     from config.py directly.
  3. The documented VQS formulas themselves (Benford, Z-Score, Amihud, Flow)
     are left completely unchanged — this module only recalibrates their
     thresholds. This keeps "Calculation Reuse ≠ Strategy Merge": the axis
     math is reused as-is (per the project's redundant-calculation rule),
     only the threshold *inputs* to that math change per asset.

ASSUMPTION FLAGGED FOR APPROVAL: the source instruction defines the
requirement conceptually but gives no formula for converting historical
data into a threshold. The percentile-based calibration below is a
proposed default:
  - Z-Score whale threshold  -> asset's OWN 95th percentile of |Z_Vol|,
    floor-clamped to the documented base (2.0): calibration can only
    TIGHTEN (raise) the threshold, never loosen it below the documented
    minimum.
  - Efficiency fake-spike ratio -> asset's OWN 10th percentile of its
    historical Efficiency Ratio, ceiling-clamped to the documented base
    (0.15): can only tighten, never loosen.
  - Taker Buy Ratio neutral band -> widened/narrowed by the asset's own
    historical TBR standard deviation, clamped to stay strictly inside the
    documented bull/bear thresholds (0.40 / 0.60) so those are never
    crossed by calibration.
Tell me if a different calibration formula is preferred; only this module
would need to change.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, replace
from typing import List, Optional, Sequence

from .config import TradingVolumeTechnicalConfig
from .strategy import Candle, compute_zscore_axis, compute_efficiency_axis


MIN_HISTORICAL_CANDLES = 60  # must exceed the largest base window (50) with margin


class InsufficientHistoryError(Exception):
    """Raised when there isn't enough historical data to run the mandatory
    Contextual Backtest for an asset. No live signal may be generated
    without it — callers must handle this explicitly (see adapter.py),
    never silently fall back to a guessed threshold."""


@dataclass
class AssetBehavioralProfile:
    symbol: str
    n_candles_analyzed: int
    z_vol_p95: Optional[float]
    efficiency_ratio_p10: Optional[float]
    tbr_mean: Optional[float]
    tbr_std: Optional[float]


def _percentile(values: List[float], pct: float) -> Optional[float]:
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * pct
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def build_asset_behavioral_profile(
    symbol: str,
    historical_candles: Sequence[Candle],
    base_cfg: TradingVolumeTechnicalConfig,
) -> AssetBehavioralProfile:
    """
    MANDATORY PRE-SIGNAL STEP ("Contextual Backtest"): walks-forward over the
    asset's own historical candles (no look-ahead — each step only uses data
    up to that point) and records how ITS OWN Z-Vol, Efficiency Ratio and
    Taker Buy Ratio behaved historically.

    Raises InsufficientHistoryError if there isn't enough history to do this
    meaningfully — this is intentional: the project rule requires the
    fingerprint to run before any signal, so "not enough data" must be
    surfaced, not silently ignored.
    """
    if len(historical_candles) < MIN_HISTORICAL_CANDLES:
        raise InsufficientHistoryError(
            f"{symbol}: needs >= {MIN_HISTORICAL_CANDLES} historical candles for "
            f"the mandatory Behavioral Fingerprint, got {len(historical_candles)}."
        )

    z_vols: List[float] = []
    eff_ratios: List[float] = []
    tbrs: List[float] = []

    w = base_cfg.zscore.rolling_window_candles
    eff_n = base_cfg.efficiency.baseline_window_candles
    start = max(w, eff_n) + 1

    for i in range(start, len(historical_candles) + 1):
        window = historical_candles[:i]  # no look-ahead: only data up to i

        z_result = compute_zscore_axis(window, base_cfg)
        if "z_vol" in z_result.detail:
            z_vols.append(abs(z_result.detail["z_vol"]))

        eff_result = compute_efficiency_axis(window, base_cfg, z_result.detail.get("z_vol"))
        if "efficiency_ratio" in eff_result.detail:
            eff_ratios.append(eff_result.detail["efficiency_ratio"])

        c = window[-1]
        if c.quote_volume > 0:
            tbrs.append(c.taker_buy_quote_volume / c.quote_volume)

    return AssetBehavioralProfile(
        symbol=symbol,
        n_candles_analyzed=len(historical_candles),
        z_vol_p95=_percentile(z_vols, 0.95),
        efficiency_ratio_p10=_percentile(eff_ratios, 0.10),
        tbr_mean=statistics.fmean(tbrs) if tbrs else None,
        tbr_std=statistics.pstdev(tbrs) if len(tbrs) >= 2 else None,
    )


def calibrate_config_for_asset(
    base_cfg: TradingVolumeTechnicalConfig,
    profile: AssetBehavioralProfile,
) -> TradingVolumeTechnicalConfig:
    """
    DYNAMIC CALIBRATION: personalizes thresholds to the asset's own
    historical behaviour. Calibration is one-directional (can only tighten
    relative to the documented base values), so the documented VQS spec's
    minimum strictness is always preserved regardless of the asset.
    """
    zscore = base_cfg.zscore
    if profile.z_vol_p95 is not None:
        calibrated_z = max(base_cfg.zscore.z_vol_whale_threshold, profile.z_vol_p95)
        zscore = replace(
            zscore,
            z_vol_whale_threshold=calibrated_z,
            z_size_whale_threshold=calibrated_z,
        )

    efficiency = base_cfg.efficiency
    if profile.efficiency_ratio_p10 is not None:
        calibrated_eff = min(
            base_cfg.efficiency.fake_spike_efficiency_ratio, profile.efficiency_ratio_p10
        )
        efficiency = replace(efficiency, fake_spike_efficiency_ratio=calibrated_eff)

    flow = base_cfg.flow
    if profile.tbr_std is not None and profile.tbr_mean is not None:
        half_band = min(0.10, max(0.02, profile.tbr_std))
        low = max(base_cfg.flow.taker_buy_ratio_bear + 0.01, 0.5 - half_band)
        high = min(base_cfg.flow.taker_buy_ratio_bull - 0.01, 0.5 + half_band)
        if low < high:
            flow = replace(flow, taker_buy_ratio_neutral_low=low, taker_buy_ratio_neutral_high=high)

    return replace(base_cfg, zscore=zscore, efficiency=efficiency, flow=flow)
