"""
Market regime classification: trending | ranging | volatile
Used to adjust AI thresholds and risk sizing.
"""
import pandas as pd


def classify_regime(df: pd.DataFrame) -> str:
    """
    Simple regime detection:
    - trending: EMA20 slope > threshold, consistent directional moves
    - volatile: ATR significantly above average (news, spikes)
    - ranging: otherwise
    """
    if len(df) < 50:
        return "unknown"

    last = df.iloc[-1]
    atr = df["atr14"].iloc[-1] if "atr14" in df.columns else 0
    atr_avg = df["atr14"].rolling(50).mean().iloc[-1] if "atr14" in df.columns else 0

    # Volatile: ATR > 2× average
    if atr_avg > 0 and atr > atr_avg * 2.0:
        return "volatile"

    # Trending: EMA20 consistently above/below EMA50
    if "ema20" in df.columns and "ema50" in df.columns:
        ema_diff = df["ema20"].iloc[-5:] - df["ema50"].iloc[-5:]
        if (ema_diff > 0).all():
            return "trending_up"
        if (ema_diff < 0).all():
            return "trending_down"

    return "ranging"


def is_tradeable_regime(regime: str) -> bool:
    """Only trade in trending or ranging — not during volatile spikes."""
    return regime in ("trending_up", "trending_down", "ranging")
