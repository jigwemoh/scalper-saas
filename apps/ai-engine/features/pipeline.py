"""
Full feature pipeline: OHLCV DataFrame → 55 feature matrix.
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

# Final ordered feature columns used by ML models (52 base + 3 M5 context = 55 total)
FEATURE_COLUMNS = [
    # Trend (10)
    "ema5", "ema10", "ema20", "ema50", "sma20",
    "ema20_slope", "ema50_slope",
    "price_vs_ema20", "price_vs_ema50", "ema20_vs_ema50",
    # Momentum (9)
    "rsi7", "rsi14", "macd", "macd_signal", "macd_hist",
    "stoch_k", "stoch_d", "cci14", "mom10",
    # Volatility (9)
    "atr14", "atr20", "std20",
    "bb_upper", "bb_lower", "bb_mid", "bb_width", "bb_pct", "atr_pct",
    # Volume (6)
    "vol_ratio", "obv", "obv_sma10",
    "vol_spike_2x", "vol_spike_3x", "vol_z_score",
    # Price action (6)
    "body_ratio", "upper_wick", "lower_wick", "candle_direction",
    "price_change", "high_low_ratio",
    # VWAP (2)
    "price_vs_vwap", "above_vwap",
    # Session (9)
    "hour_sin", "hour_cos", "dow_sin", "dow_cos",
    "is_london", "is_new_york", "is_overlap", "is_asia", "is_high_liquidity",
    # Spread (1)
    "spread",
    # M5 context (3) — filled by get_latest_feature_row; 0 if M5 unavailable
    "m5_ema20_slope", "m5_above_vwap", "m5_vol_ratio",
]

assert len(FEATURE_COLUMNS) == 55, f"Expected 55 features, got {len(FEATURE_COLUMNS)}"


def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Takes raw OHLCV DataFrame and returns a DataFrame of engineered features.
    Input df must have: open, high, low, close, tick_volume (or real_volume), spread
    M5 context columns (m5_*) default to 0; caller should populate via get_latest_feature_row.
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

    # Convert spread from MT5 points (1 point = 0.1 pip for 5-digit brokers) to pips
    if "spread" in df.columns:
        df["spread"] = df["spread"] / 10.0
    else:
        df["spread"] = 0.0

    # Ensure all FEATURE_COLUMNS exist (missing ones → 0)
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
    Builds feature matrix from M1 data, populates M5 context columns from df_m5.
    Returns the last row as a 1-row DataFrame with all 55 features.
    """
    features = build_feature_matrix(df_m1)

    if df_m5 is not None and not df_m5.empty:
        m5_features = build_feature_matrix(df_m5)
        if not m5_features.empty:
            last_m5 = m5_features.iloc[-1]
            features["m5_ema20_slope"] = float(last_m5["ema20_slope"])
            features["m5_above_vwap"] = float(last_m5["above_vwap"])
            features["m5_vol_ratio"] = float(last_m5["vol_ratio"])

    return features.iloc[[-1]]  # Return last row
