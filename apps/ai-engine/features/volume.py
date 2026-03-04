"""Volume spike and liquidity detection features."""
import pandas as pd
import numpy as np


def detect_volume_spike(df: pd.DataFrame, threshold: float = 2.0) -> pd.Series:
    """Returns 1 where volume is > threshold × 20-bar average."""
    vol_col = "tick_volume" if "tick_volume" in df.columns else "volume"
    if vol_col not in df.columns:
        return pd.Series(0, index=df.index)
    avg = df[vol_col].rolling(20).mean()
    spike = (df[vol_col] > avg * threshold).astype(int)
    return spike


def add_volume_spike_features(df: pd.DataFrame) -> pd.DataFrame:
    df["vol_spike_2x"] = detect_volume_spike(df, threshold=2.0)
    df["vol_spike_3x"] = detect_volume_spike(df, threshold=3.0)

    vol_col = "tick_volume" if "tick_volume" in df.columns else "volume"
    if vol_col in df.columns:
        df["vol_change"] = df[vol_col].pct_change().fillna(0)
        df["vol_z_score"] = (
            (df[vol_col] - df[vol_col].rolling(20).mean())
            / df[vol_col].rolling(20).std().replace(0, 1)
        )
    return df
