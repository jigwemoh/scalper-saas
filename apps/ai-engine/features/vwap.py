"""VWAP calculation for intraday sessions."""
import pandas as pd


def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Calculate rolling VWAP from session start (UTC midnight).
    Typical price = (H + L + C) / 3
    """
    if "tick_volume" in df.columns:
        vol = df["tick_volume"]
    elif "real_volume" in df.columns:
        vol = df["real_volume"]
    else:
        return pd.Series(index=df.index, dtype=float)

    typical = (df["high"] + df["low"] + df["close"]) / 3
    cum_tpv = (typical * vol).groupby(df.index.date).cumsum()
    cum_vol = vol.groupby(df.index.date).cumsum()
    vwap = cum_tpv / cum_vol.replace(0, 1)
    return vwap


def add_vwap_features(df: pd.DataFrame) -> pd.DataFrame:
    df["vwap"] = calculate_vwap(df)
    df["price_vs_vwap"] = (df["close"] - df["vwap"]) / df["vwap"]
    df["above_vwap"] = (df["close"] > df["vwap"]).astype(int)
    return df
