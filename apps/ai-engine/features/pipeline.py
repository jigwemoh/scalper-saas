"""
Full feature pipeline: OHLCV DataFrame → 55+ feature matrix.
"""
import logging
import pandas as pd
import numpy as np

from features.technical import (
    add_trend_features,
    add_momentum_features,
    add_volatility_features,
    add_volume_features,
    add_price_action_features,
)
from features.vwap import add_vwap_features
from features.session import add_session_features
from features.volume import add_volume_spike_features

logger = logging.getLogger("pipeline")

# Final ordered feature columns used by ML models
FEATURE_COLUMNS = [
    # Trend
    "ema5", "ema10", "ema20", "ema50", "sma20",
    "ema20_slope", "ema50_slope",
    "price_vs_ema20", "price_vs_ema50", "ema20_vs_ema50",
    # Momentum
    "rsi7", "rsi14", "macd", "macd_signal", "macd_hist",
    "stoch_k", "stoch_d", "cci14", "mom10",
    # Volatility
    "atr14", "atr20", "std20",
    "bb_upper", "bb_lower", "bb_mid", "bb_width", "bb_pct", "atr_pct",
    # Volume
    "vol_ratio", "obv", "obv_sma10",
    "vol_spike_2x", "vol_spike_3x", "vol_z_score",
    # Price action
    "body_ratio", "upper_wick", "lower_wick", "candle_direction",
    "price_change", "high_low_ratio",
    # VWAP
    "price_vs_vwap", "above_vwap",
    # Session
    "hour_sin", "hour_cos", "dow_sin", "dow_cos",
    "is_london", "is_new_york", "is_overlap", "is_asia", "is_high_liquidity",
    # Spread
    "spread",
]


def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Takes raw OHLCV DataFrame and returns a DataFrame of engineered features.
    Input df must have: open, high, low, close, tick_volume (or real_volume), spread
    """
    df = df.copy()

    df = add_trend_features(df)
    df = add_momentum_features(df)
    df = add_volatility_features(df)
    df = add_volume_features(df)
    df = add_price_action_features(df)
    df = add_vwap_features(df)
    df = add_session_features(df)
    df = add_volume_spike_features(df)

    # Normalize spread to pips
    if "spread" not in df.columns:
        df["spread"] = 0.0

    # Select and order final features
    available = [c for c in FEATURE_COLUMNS if c in df.columns]
    missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing:
        logger.debug(f"Missing features (will be 0): {missing}")
        for col in missing:
            df[col] = 0.0

    features = df[FEATURE_COLUMNS].copy()

    # Replace inf with nan, then fill nan with forward fill + 0
    features = features.replace([np.inf, -np.inf], np.nan)
    features = features.ffill().fillna(0.0)

    return features


def get_latest_feature_row(df_m1: pd.DataFrame, df_m5: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Builds feature matrix from M1 data, optionally adds M5 EMA slope context.
    Returns the last row as a 1-row DataFrame.
    """
    features = build_feature_matrix(df_m1)

    if df_m5 is not None and not df_m5.empty:
        m5_features = build_feature_matrix(df_m5)
        if not m5_features.empty:
            features["m5_ema20_slope"] = m5_features["ema20_slope"].iloc[-1]
            features["m5_above_vwap"] = m5_features["above_vwap"].iloc[-1]
            features["m5_vol_ratio"] = m5_features["vol_ratio"].iloc[-1]

    return features.iloc[[-1]]  # Return last row
