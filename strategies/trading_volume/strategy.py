"""
strategy.py
Trading Volume Strategy — Volume Quality Score (VQS) Engine (Phase 2)

Implements, using only the formulas specified in the supplied documentation:
  * Axis 1: Benford's Law conformity test              (S_Ben, weight 25%)
  * Axis 2: Multi-variable rolling Z-Score divergence   (S_Z,   weight 25%)
  * Axis 3: Amihud-style Price Efficiency Ratio         (S_Eff, weight 25%)
  * Axis 4: Taker flow / Open Interest confirmation     (S_Flow,weight 25%)
  * Governance gate (Omega) and Final VQS
  * Documented extensions: Volume Concentration Index, Yale round-number
    clustering filter
  * Narrative (Persian) mobile-first signal-as-text output, restricted to
    the four permitted signal titles.

Design notes:
  - Only the Python standard library (statistics, math) is used, so every
    number is directly traceable to the documented formula rather than to
    a third-party library's internal implementation.
  - No look-ahead: every function only reads data up to and including the
    current (last) element of the input sequence.
  - Division-by-zero / insufficient-history / missing-data cases return an
    explicit neutral score (never an invented directional signal) and are
    reported in `detail` so callers/tests can distinguish "neutral because
    of insufficient data" from "neutral because the market is calm".

ASSUMPTION REQUIRING APPROVAL: within the 80-100 VQS band, the documentation
confirms the volume is real but does not itself specify how to choose
"سیگنال خرید" vs "سیگنال فروش" vs a range/uncertain title. `generate_signal_text`
below uses the already-documented Taker Buy Ratio thresholds (>0.60 / <0.40)
from the Flow axis to disambiguate direction. If you'd rather this be decided
differently (e.g. by price change over the candle instead of TBR), tell me
and I will change only this branch.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .config import TradingVolumeTechnicalConfig, SignalTitle


# ---------------------------------------------------------------------------
# Input data contracts
# ---------------------------------------------------------------------------

@dataclass
class Trade:
    price: float
    base_qty: float            # quantity in base asset
    quote_volume: float        # notional value in quote currency (USD/USDT)
    is_taker_buy: bool
    timestamp: float = 0.0


@dataclass
class Candle:
    open: float
    close: float
    quote_volume: float             # V_USD for the candle
    trade_count: int                # N_Trades
    taker_buy_quote_volume: float   # V_Taker_Buy
    open_interest: Optional[float] = None  # OI_t (None if spot / unavailable)
    timestamp: float = 0.0


@dataclass
class AxisResult:
    score: float
    detail: dict


@dataclass
class VQSResult:
    vqs_raw: float
    omega: float
    vqs_final: float
    benford: AxisResult
    zscore: AxisResult
    efficiency: AxisResult
    flow: AxisResult
    benford_red_flag: bool
    round_clustering_red_flag: bool
    volume_concentration: Optional[float]
    volume_concentration_state: Optional[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_zscore(series: Sequence[float]) -> Optional[float]:
    """Z = (X_t - mu) / sigma, mu/sigma over the whole given window.
    Returns None on insufficient history or zero variance (never fabricates
    a signal by dividing by zero)."""
    if len(series) < 2:
        return None
    mu = statistics.fmean(series)
    sigma = statistics.pstdev(series)
    if sigma == 0:
        return None
    return (series[-1] - mu) / sigma


def _first_digit(x: float) -> Optional[int]:
    x = abs(x)
    if x == 0 or math.isnan(x) or math.isinf(x):
        return None
    while x < 1:
        x *= 10
    while x >= 10:
        x /= 10
    return int(x)


def _benford_expected(d: int) -> float:
    return math.log10(1 + 1 / d)


# ---------------------------------------------------------------------------
# Axis 1 — Benford's Law (S_Ben)
# ---------------------------------------------------------------------------

def compute_benford_axis(
    trades: Sequence[Trade], cfg: TradingVolumeTechnicalConfig
) -> AxisResult:
    """S_Ben = max(0, 100 * (1 - RMSE / 0.15)).
    Red flag if RMSE > 0.12 OR >35% of trades share an identical rounded size."""
    digits = [d for d in (_first_digit(t.base_qty) for t in trades) if d is not None]

    if len(digits) < 10:
        return AxisResult(
            score=50.0,
            detail={"reason": "insufficient_trade_count_for_benford", "n": len(digits)},
        )

    n = len(digits)
    freq = {d: 0 for d in range(1, 10)}
    for d in digits:
        freq[d] += 1
    f = {d: freq[d] / n for d in range(1, 10)}
    p = {d: _benford_expected(d) for d in range(1, 10)}

    rmse = math.sqrt(sum((f[d] - p[d]) ** 2 for d in range(1, 10)) / 9)
    score = max(0.0, 100.0 * (1 - rmse / cfg.benford.rmse_score_scale))

    rounded_counts: dict = {}
    for t in trades:
        r = round(t.base_qty, 2)
        rounded_counts[r] = rounded_counts.get(r, 0) + 1
    most_common_pct = (max(rounded_counts.values()) / n) if rounded_counts else 0.0

    red_flag = (rmse > cfg.benford.red_flag_rmse) or (
        most_common_pct > cfg.benford.red_flag_round_trade_pct
    )

    return AxisResult(
        score=score,
        detail={"rmse": rmse, "red_flag": red_flag, "most_common_size_pct": most_common_pct, "n_trades": n},
    )


# ---------------------------------------------------------------------------
# Axis 2 — Rolling multi-variable Z-Score (S_Z)
# ---------------------------------------------------------------------------

def compute_zscore_axis(
    candles: Sequence[Candle], cfg: TradingVolumeTechnicalConfig
) -> AxisResult:
    """
    Z_Vol, Z_Count, Z_Size over the trailing `rolling_window_candles` (doc: 20).
    Documented piecewise scoring:
        100                       if Z_Vol>threshold and Z_Size>Z_Count
        50*(1 + Z_Size/Z_Count)   if Z_Vol>threshold and Z_Count>=Z_Size
        70                        if |Z_Vol|<=1.0 (normal market)
    Any other combination is not covered by the documentation; a neutral 50
    is returned rather than an invented rule.
    """
    w = cfg.zscore.rolling_window_candles
    if len(candles) < w + 1:
        return AxisResult(score=50.0, detail={"reason": "insufficient_history", "n": len(candles)})

    window = candles[-(w + 1):]
    vol_series = [c.quote_volume for c in window]
    count_series = [c.trade_count for c in window]
    size_series = [
        (c.quote_volume / c.trade_count) if c.trade_count > 0 else 0.0 for c in window
    ]

    z_vol = _safe_zscore(vol_series)
    z_count = _safe_zscore(count_series)
    z_size = _safe_zscore(size_series)

    if z_vol is None or z_count is None or z_size is None:
        return AxisResult(score=50.0, detail={"reason": "zero_variance_window"})

    z_vol_th = cfg.zscore.z_vol_whale_threshold

    if z_vol > z_vol_th and z_size > z_count:
        score = 100.0
    elif z_vol > z_vol_th and z_count >= z_size:
        ratio = (z_size / z_count) if z_count != 0 else 0.0
        score = max(0.0, min(100.0, 50.0 * (1 + ratio)))
    elif abs(z_vol) <= cfg.zscore.normal_market_abs_z_vol:
        score = cfg.zscore.normal_market_score
    else:
        score = 50.0  # not covered by documentation — neutral, not invented

    return AxisResult(score=score, detail={"z_vol": z_vol, "z_count": z_count, "z_size": z_size})


# ---------------------------------------------------------------------------
# Axis 3 — Amihud Price Efficiency Ratio (S_Eff)
# ---------------------------------------------------------------------------

def compute_efficiency_axis(
    candles: Sequence[Candle],
    cfg: TradingVolumeTechnicalConfig,
    z_vol_current: Optional[float],
) -> AxisResult:
    """
    PER_t = |Close - Open| / V_USD
    Efficiency_Ratio = PER_t / mean(PER over trailing baseline window, doc: 50)
    S_Eff = 10 if (Z_Vol > 2.0 and Efficiency_Ratio < 0.15) else min(100, 100*Efficiency_Ratio)
    """
    n = cfg.efficiency.baseline_window_candles
    if len(candles) < n + 1:
        return AxisResult(score=50.0, detail={"reason": "insufficient_history", "n": len(candles)})

    def per(c: Candle) -> Optional[float]:
        if c.quote_volume == 0:
            return None
        return abs(c.close - c.open) / c.quote_volume

    history = candles[-(n + 1):-1]
    per_hist = [p for p in (per(c) for c in history) if p is not None]
    per_t = per(candles[-1])

    if per_t is None or not per_hist:
        return AxisResult(score=50.0, detail={"reason": "zero_volume_or_no_history"})

    per_avg = statistics.fmean(per_hist)
    if per_avg == 0:
        return AxisResult(score=50.0, detail={"reason": "zero_baseline_per"})

    efficiency_ratio = per_t / per_avg

    fake_spike = (
        z_vol_current is not None
        and z_vol_current > cfg.efficiency.fake_spike_z_vol_threshold
        and efficiency_ratio < cfg.efficiency.fake_spike_efficiency_ratio
    )

    score = cfg.efficiency.fake_spike_score if fake_spike else min(100.0, 100.0 * efficiency_ratio)

    return AxisResult(
        score=score,
        detail={"per_t": per_t, "per_avg_baseline": per_avg, "efficiency_ratio": efficiency_ratio, "fake_spike": fake_spike},
    )


# ---------------------------------------------------------------------------
# Axis 4 — Taker flow & Open Interest (S_Flow)
# ---------------------------------------------------------------------------

def compute_flow_axis(
    candle: Candle, prev_open_interest: Optional[float], cfg: TradingVolumeTechnicalConfig
) -> AxisResult:
    """
    TBR = V_Taker_Buy / V_Total
    delta_OI = (OI_t - OI_t-1) / OI_t-1
    If OI data is unavailable (spot market), delta_OI cannot be computed;
    the documentation does not define a spot-market fallback, so a neutral
    score is returned rather than guessing directional confirmation.
    """
    if candle.quote_volume == 0:
        return AxisResult(score=50.0, detail={"reason": "zero_volume"})

    tbr = candle.taker_buy_quote_volume / candle.quote_volume

    if candle.open_interest is None or not prev_open_interest:
        return AxisResult(score=50.0, detail={"reason": "open_interest_unavailable", "tbr": tbr})

    delta_oi = (candle.open_interest - prev_open_interest) / prev_open_interest

    f = cfg.flow
    if tbr > f.taker_buy_ratio_bull and delta_oi > 0:
        score = f.directional_score
    elif tbr < f.taker_buy_ratio_bear and delta_oi > 0:
        score = f.directional_score
    elif f.taker_buy_ratio_neutral_low <= tbr <= f.taker_buy_ratio_neutral_high and abs(delta_oi) < 1e-9:
        score = f.neutral_score
    else:
        score = 50.0  # not covered by documentation — neutral, not invented

    return AxisResult(score=score, detail={"tbr": tbr, "delta_oi": delta_oi})


# ---------------------------------------------------------------------------
# Extensions — Volume Concentration Index & Yale Round-Number Clustering
# ---------------------------------------------------------------------------

def compute_volume_concentration(
    z_vol: Optional[float], z_count: Optional[float], cfg: TradingVolumeTechnicalConfig
) -> Tuple[Optional[float], Optional[str]]:
    """Volume Concentration = Z_Vol - Z_Count."""
    if z_vol is None or z_count is None:
        return None, None
    vc = z_vol - z_count
    if vc > cfg.concentration.concentrated_threshold:
        state = "concentrated_whale"
    elif vc < cfg.concentration.dispersed_threshold:
        state = "dispersed_wash_trading"
    else:
        state = "normal"
    return vc, state


def compute_round_number_clustering(
    trades: Sequence[Trade], cfg: TradingVolumeTechnicalConfig
) -> bool:
    """Red flag if the share of trades whose size is a multiple of one of the
    documented round bases falls below 5%."""
    if not trades:
        return False
    bases = cfg.round_clustering.round_bases

    def is_round(qty: float) -> bool:
        for b in bases:
            remainder = qty % b
            if remainder < 1e-6 or (b - remainder) < 1e-6:
                return True
        return False

    round_count = sum(1 for t in trades if is_round(t.base_qty))
    ratio = round_count / len(trades)
    return ratio < cfg.round_clustering.red_flag_round_ratio


# ---------------------------------------------------------------------------
# Final VQS assembly
# ---------------------------------------------------------------------------

def compute_vqs(
    trades: Sequence[Trade],
    candles: Sequence[Candle],
    cfg: Optional[TradingVolumeTechnicalConfig] = None,
) -> VQSResult:
    cfg = cfg or TradingVolumeTechnicalConfig()

    benford = compute_benford_axis(trades, cfg)
    zscore = compute_zscore_axis(candles, cfg)
    z_vol_current = zscore.detail.get("z_vol")
    efficiency = compute_efficiency_axis(candles, cfg, z_vol_current)

    prev_oi = candles[-2].open_interest if len(candles) >= 2 else None
    flow = compute_flow_axis(candles[-1], prev_oi, cfg)

    vqs_raw = (
        cfg.weights.w_benford * benford.score
        + cfg.weights.w_zscore * zscore.score
        + cfg.weights.w_efficiency * efficiency.score
        + cfg.weights.w_flow * flow.score
    )

    benford_red_flag = bool(benford.detail.get("red_flag", False))
    round_red_flag = compute_round_number_clustering(trades, cfg)

    z_count_current = zscore.detail.get("z_count")
    vc, vc_state = compute_volume_concentration(z_vol_current, z_count_current, cfg)

    if benford_red_flag or round_red_flag:
        omega = cfg.omega.benford_red_flag_omega
    elif (
        z_vol_current is not None
        and z_vol_current > cfg.omega.fake_spike_z_vol_threshold
        and efficiency.score < cfg.omega.fake_spike_efficiency_threshold
    ):
        omega = cfg.omega.fake_spike_omega
    else:
        omega = cfg.omega.normal_omega

    vqs_final = vqs_raw * omega

    return VQSResult(
        vqs_raw=vqs_raw,
        omega=omega,
        vqs_final=vqs_final,
        benford=benford,
        zscore=zscore,
        efficiency=efficiency,
        flow=flow,
        benford_red_flag=benford_red_flag,
        round_clustering_red_flag=round_red_flag,
        volume_concentration=vc,
        volume_concentration_state=vc_state,
    )


# ---------------------------------------------------------------------------
# Narrative Signal Engine (Persian, mobile-first, text-only)
# ---------------------------------------------------------------------------

def generate_signal_text(symbol: str, price: float, timeframe: str, result: VQSResult) -> str:
    """
    Compact Persian text output. Only the four documented signal titles are
    used. Classification follows the documented VQS score bands
    (80-100 / 50-79 / 0-49); see module docstring for the one inferred
    disambiguation rule (Taker Buy Ratio -> buy/sell direction).
    """
    vqs = result.vqs_final
    symbol_disp = symbol if symbol.upper().endswith("USDT") else f"{symbol}USDT"

    if result.omega == 0.0:
        title = SignalTitle.UNCERTAIN
        body = "کیفیت حجم رد شد (پرچم قرمز بنفورد یا خوشه اعداد گرد) — حجم غیرقابل اتکا."
    elif vqs >= 80:
        tbr = result.flow.detail.get("tbr")
        if tbr is not None and tbr > 0.60:
            title = SignalTitle.BUY
        elif tbr is not None and tbr < 0.40:
            title = SignalTitle.SELL
        else:
            title = SignalTitle.UNCERTAIN
        body = f"حجم اصیل و تاییدشده (VQS={vqs:.0f})."
    elif vqs >= 50:
        title = SignalTitle.RANGE
        body = f"حجم عادی بازار، بدون آنومالی خاص (VQS={vqs:.0f})."
    else:
        title = SignalTitle.UNCERTAIN
        body = f"حجم مشکوک به Wash Trading یا فعالیت ربات (VQS={vqs:.0f}) — ورود قدغن."

    return f"{symbol_disp} | {timeframe}\nقیمت: {price}\n{title.value}\n{body}"
