"""Trading session and temporal feature encoding."""
import numpy as np
import pandas as pd


SESSION_HOURS = {
    "asia": (0, 8),       # 00:00–08:00 UTC
    "london": (7, 16),    # 07:00–16:00 UTC
    "new_york": (13, 22), # 13:00–22:00 UTC
}


def get_session(hour_utc: int) -> str:
    """Return the dominant session for a given UTC hour."""
    if 13 <= hour_utc < 16:
        return "london_ny_overlap"
    if 7 <= hour_utc < 16:
        return "london"
    if 13 <= hour_utc < 22:
        return "new_york"
    if 0 <= hour_utc < 8:
        return "asia"
    return "off_hours"


def add_session_features(df: pd.DataFrame) -> pd.DataFrame:
    hours = df.index.hour if hasattr(df.index, "hour") else pd.to_datetime(df.index).hour

    # Cyclical encoding of hour (avoids discontinuity at midnight)
    df["hour_sin"] = np.sin(2 * np.pi * hours / 24)
    df["hour_cos"] = np.cos(2 * np.pi * hours / 24)

    # Day of week cyclical
    dow = df.index.dayofweek if hasattr(df.index, "dayofweek") else pd.to_datetime(df.index).dayofweek
    df["dow_sin"] = np.sin(2 * np.pi * dow / 5)
    df["dow_cos"] = np.cos(2 * np.pi * dow / 5)

    # Session binary flags
    df["is_london"] = ((hours >= 7) & (hours < 16)).astype(int)
    df["is_new_york"] = ((hours >= 13) & (hours < 22)).astype(int)
    df["is_overlap"] = ((hours >= 13) & (hours < 16)).astype(int)
    df["is_asia"] = ((hours >= 0) & (hours < 8)).astype(int)
    df["is_high_liquidity"] = ((hours >= 7) & (hours < 22)).astype(int)

    return df
