"""
core/backtest_engine.py

موتور Backtest عمومی و مستقل از هر استراتژی خاص.

نکته‌ی بسیار مهم (لطفاً حتماً بخوانید):
------------------------------------------
استراتژی‌های فعلی پروژه‌ی شما (MarketCapAdapter و PriceAdapter)
فقط داده‌ی خام برمی‌گردانند (قیمت فعلی / مارکت‌کپ فعلی) و هیچ‌کدام
یک قانون تصمیم‌گیری خرید/فروش (Signal Logic) ندارند.

Backtest به‌معنای واقعی نیاز به یک تابع "سیگنال" دارد که مشخص کند
در هر نقطه از زمان باید Long باشیم، Short باشیم یا خارج از بازار.
چون چنین قانونی در استراتژی‌های فعلی شما تعریف نشده، این فایل
هیچ قانون اختراعی برای شما نمی‌سازد (طبق درخواست صریح شما مبنی بر
عدم استفاده از فرضیات بدون مستند علمی).

این ماژول فقط "زیرساخت اندازه‌گیری" را آماده می‌کند: به‌محض این‌که
یک استراتژی سیگنال‌دهنده‌ی واقعی (مثلاً بر پایه‌ی یک اندیکاتور مستند
مثل RSI، MACD یا Moving Average Crossover) به پروژه اضافه شد، همین
موتور بلافاصله قابل استفاده خواهد بود.

فرمول‌های استفاده‌شده (همگی استاندارد و مرجع‌دار):
----------------------------------------------------
- Total Return / CAGR:
    Investopedia, "Compound Annual Growth Rate (CAGR)"
    https://www.investopedia.com/terms/c/cagr.asp

- Max Drawdown:
    Investopedia, "Maximum Drawdown (MDD)"
    https://www.investopedia.com/terms/m/maximum-drawdown-mdd.asp

- Sharpe Ratio:
    Sharpe, W. F. (1994). "The Sharpe Ratio". Journal of Portfolio
    Management.
    https://web.stanford.edu/~wfsharpe/art/sr/sr.htm

- Sortino Ratio:
    Sortino, F. A., & Price, L. N. (1994). "Performance Measurement
    in a Downside Risk Framework". Journal of Investing.

- Win Rate:
    نسبت ساده‌ی معاملات سودده به کل معاملات (تعریف عمومی صنعت).
"""

import math


def compute_equity_curve(returns, initial_capital=1.0):
    """
    از روی یک لیست بازده‌ی دوره‌ای (returns، مثلاً [0.01, -0.02, ...])
    منحنی سرمایه (Equity Curve) می‌سازد.
    """

    equity = [initial_capital]

    for r in returns:
        equity.append(equity[-1] * (1 + r))

    return equity


def total_return(equity_curve):
    if len(equity_curve) < 2 or equity_curve[0] == 0:
        return 0.0

    return (equity_curve[-1] / equity_curve[0]) - 1.0


def cagr(equity_curve, periods_per_year):
    """
    Compound Annual Growth Rate.
    periods_per_year: تعداد دوره‌ها در یک سال (مثلاً 365 برای روزانه).
    """

    n_periods = len(equity_curve) - 1

    if n_periods <= 0 or equity_curve[0] <= 0:
        return 0.0

    years = n_periods / periods_per_year

    if years <= 0:
        return 0.0

    growth = equity_curve[-1] / equity_curve[0]

    if growth <= 0:
        return -1.0

    return growth ** (1 / years) - 1.0


def max_drawdown(equity_curve):
    """
    بزرگ‌ترین افت از قله‌ی قبلی تا کف بعدی روی منحنی سرمایه.
    خروجی به‌صورت عدد منفی (مثلاً -0.35 یعنی ۳۵٪ افت).
    """

    if not equity_curve:
        return 0.0

    peak = equity_curve[0]
    max_dd = 0.0

    for value in equity_curve:
        if value > peak:
            peak = value

        if peak > 0:
            drawdown = (value - peak) / peak

            if drawdown < max_dd:
                max_dd = drawdown

    return max_dd


def sharpe_ratio(returns, risk_free_rate=0.0, periods_per_year=365):
    """
    Sharpe Ratio = (میانگین بازده مازاد / انحراف معیار بازده) * ریشه‌ی دوره‌ها
    """

    if not returns or len(returns) < 2:
        return 0.0

    period_rf = risk_free_rate / periods_per_year

    excess_returns = [r - period_rf for r in returns]

    mean_excess = sum(excess_returns) / len(excess_returns)

    variance = sum(
        (r - mean_excess) ** 2 for r in excess_returns
    ) / (len(excess_returns) - 1)

    std_dev = math.sqrt(variance)

    if std_dev == 0:
        return 0.0

    return (mean_excess / std_dev) * math.sqrt(periods_per_year)


def sortino_ratio(returns, risk_free_rate=0.0, periods_per_year=365):
    """
    مثل Sharpe Ratio اما فقط نوسانِ سمت منفی (Downside Deviation) را
    در مخرج در نظر می‌گیرد، نه کل انحراف معیار.
    """

    if not returns or len(returns) < 2:
        return 0.0

    period_rf = risk_free_rate / periods_per_year

    excess_returns = [r - period_rf for r in returns]

    mean_excess = sum(excess_returns) / len(excess_returns)

    downside_returns = [r for r in excess_returns if r < 0]

    if not downside_returns:
        return 0.0

    downside_variance = sum(
        r ** 2 for r in downside_returns
    ) / len(downside_returns)

    downside_deviation = math.sqrt(downside_variance)

    if downside_deviation == 0:
        return 0.0

    return (mean_excess / downside_deviation) * math.sqrt(periods_per_year)


def win_rate(trade_returns):
    """
    trade_returns: بازده‌ی هر معامله‌ی بسته‌شده (نه هر دوره‌ی زمانی).
    """

    if not trade_returns:
        return 0.0

    wins = sum(1 for r in trade_returns if r > 0)

    return wins / len(trade_returns)


def run_backtest_report(returns, periods_per_year=365, trade_returns=None):
    """
    گزارش کامل Backtest از روی یک لیست بازده‌ی دوره‌ای.

    returns:
        لیستی از بازده‌ی هر دوره (مثلاً بازده‌ی روزانه بر اساس
        سیگنال یک استراتژی واقعی). این تابع خودش سیگنال تولید نمی‌کند.

    trade_returns:
        اختیاری. اگر بازده‌ی هر معامله‌ی جداگانه در دسترس باشد،
        Win Rate هم محاسبه می‌شود.
    """

    equity_curve = compute_equity_curve(returns)

    report = {
        "total_return": total_return(equity_curve),
        "cagr": cagr(equity_curve, periods_per_year),
        "max_drawdown": max_drawdown(equity_curve),
        "sharpe_ratio": sharpe_ratio(
            returns, periods_per_year=periods_per_year
        ),
        "sortino_ratio": sortino_ratio(
            returns, periods_per_year=periods_per_year
        ),
        "equity_curve": equity_curve,
    }

    if trade_returns:
        report["win_rate"] = win_rate(trade_returns)
    else:
        report["win_rate"] = None

    return report
