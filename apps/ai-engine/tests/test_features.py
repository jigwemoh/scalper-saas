"""Feature pipeline tests."""
import pytest
import pandas as pd
import numpy as np
from features.pipeline import build_feature_matrix, FEATURE_COLUMNS


def _make_df(n=100) -> pd.DataFrame:
    """Create synthetic OHLCV data."""
    import datetime
    idx = pd.date_range("2024-01-01", periods=n, freq="1min", tz="UTC")
    close = 1.1000 + np.cumsum(np.random.randn(n) * 0.0001)
    high = close + np.abs(np.random.randn(n) * 0.0002)
    low = close - np.abs(np.random.randn(n) * 0.0002)
    open_ = close + np.random.randn(n) * 0.0001
    volume = np.random.randint(100, 1000, n)
    spread = np.random.uniform(0.5, 2.0, n)
    return pd.DataFrame({
        "open": open_, "high": high, "low": low, "close": close,
        "tick_volume": volume, "spread": spread,
    }, index=idx)


def test_feature_matrix_shape():
    df = _make_df(100)
    features = build_feature_matrix(df)
    assert not features.empty
    assert len(features.columns) == len(FEATURE_COLUMNS)


def test_no_inf_values():
    df = _make_df(100)
    features = build_feature_matrix(df)
    assert not np.isinf(features.values).any(), "Feature matrix contains inf values"


def test_no_nan_values():
    df = _make_df(100)
    features = build_feature_matrix(df)
    assert not features.isna().any().any(), "Feature matrix contains NaN values"
