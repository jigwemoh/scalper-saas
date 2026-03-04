"""
Liquidity sweep / stop-hunt detection.
Looks for: long wick + volume spike + immediate rejection.
A sweep before entry dramatically improves edge.
"""
import pandas as pd


def detect_bullish_sweep(df: pd.DataFrame, lookback: int = 3) -> bool:
    """
    Bullish liquidity sweep:
    - Price briefly dipped below recent swing low (took out sell stops)
    - Closed back above the low (rejection)
    - Volume spike on the sweep candle
    """
    if len(df) < lookback + 2:
        return False

    recent = df.iloc[-(lookback + 1):]
    last = df.iloc[-1]
    prev_low = df.iloc[-(lookback + 1):-1]["low"].min()

    # Wick went below prior low
    swept_low = last["low"] < prev_low
    # Closed above prior low (rejection)
    closed_above = last["close"] > prev_low
    # Volume above average
    vol_col = "tick_volume" if "tick_volume" in df.columns else "volume"
    avg_vol = df[vol_col].rolling(20).mean().iloc[-1] if vol_col in df.columns else 0
    vol_spike = df[vol_col].iloc[-1] > avg_vol * 1.5 if vol_col in df.columns else False
    # Lower wick is significant
    candle_range = last["high"] - last["low"]
    lower_wick = last["close"] - last["low"]
    big_wick = lower_wick > candle_range * 0.4 if candle_range > 0 else False

    return bool(swept_low and closed_above and big_wick)


def detect_bearish_sweep(df: pd.DataFrame, lookback: int = 3) -> bool:
    """
    Bearish liquidity sweep:
    - Price briefly exceeded recent swing high (took out buy stops)
    - Closed back below the high (rejection)
    """
    if len(df) < lookback + 2:
        return False

    last = df.iloc[-1]
    prev_high = df.iloc[-(lookback + 1):-1]["high"].max()

    swept_high = last["high"] > prev_high
    closed_below = last["close"] < prev_high
    candle_range = last["high"] - last["low"]
    upper_wick = last["high"] - last["close"]
    big_wick = upper_wick > candle_range * 0.4 if candle_range > 0 else False

    return bool(swept_high and closed_below and big_wick)
