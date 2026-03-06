"""
Technical indicator features using the `ta` library.
"""
import pandas as pd
import ta


def add_trend_features(df: pd.DataFrame) -> pd.DataFrame:
    df["ema5"] = ta.trend.ema_indicator(df["close"], window=5)
    df["ema10"] = ta.trend.ema_indicator(df["close"], window=10)
    df["ema20"] = ta.trend.ema_indicator(df["close"], window=20)
    df["ema50"] = ta.trend.ema_indicator(df["close"], window=50)
    df["sma20"] = ta.trend.sma_indicator(df["close"], window=20)

    # EMA slopes (rate of change)
    df["ema20_slope"] = df["ema20"].diff(3) / df["ema20"].shift(3)
    df["ema50_slope"] = df["ema50"].diff(5) / df["ema50"].shift(5)

    # Price position relative to EMAs
    df["price_vs_ema20"] = (df["close"] - df["ema20"]) / df["ema20"]
    df["price_vs_ema50"] = (df["close"] - df["ema50"]) / df["ema50"]
    df["ema20_vs_ema50"] = (df["ema20"] - df["ema50"]) / df["ema50"]
    return df


def add_momentum_features(df: pd.DataFrame) -> pd.DataFrame:
    df["rsi7"] = ta.momentum.rsi(df["close"], window=7)
    df["rsi14"] = ta.momentum.rsi(df["close"], window=14)

    macd_result = ta.trend.macd(df["close"], window_slow=26, window_fast=12)
    df["macd"] = macd_result.iloc[:, 0] if isinstance(macd_result, pd.DataFrame) else macd_result
    macd_signal_result = ta.trend.macd_signal(df["close"], window_slow=26, window_fast=12, window_sign=9)
    df["macd_signal"] = macd_signal_result.iloc[:, 0] if isinstance(macd_signal_result, pd.DataFrame) else macd_signal_result
    macd_diff_result = ta.trend.macd_diff(df["close"], window_slow=26, window_fast=12, window_sign=9)
    df["macd_hist"] = macd_diff_result.iloc[:, 0] if isinstance(macd_diff_result, pd.DataFrame) else macd_diff_result

    df["stoch_k"] = ta.momentum.stoch(df["high"], df["low"], df["close"], window=14, smooth_window=3)
    df["stoch_d"] = ta.momentum.stoch_signal(df["high"], df["low"], df["close"], window=14, smooth_window=3)

    df["cci14"] = ta.trend.cci(df["high"], df["low"], df["close"], window=14)
    df["mom10"] = ta.momentum.roc(df["close"], window=10)
    return df


def add_volatility_features(df: pd.DataFrame) -> pd.DataFrame:
    df["atr14"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
    df["atr20"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=20)
    df["std20"] = df["close"].rolling(20).std()

    df["bb_upper"] = ta.volatility.bollinger_hband(df["close"], window=20, window_dev=2)
    df["bb_lower"] = ta.volatility.bollinger_lband(df["close"], window=20, window_dev=2)
    df["bb_mid"] = ta.volatility.bollinger_mavg(df["close"], window=20)
    df["bb_width"] = ta.volatility.bollinger_wband(df["close"], window=20, window_dev=2)
    df["bb_pct"] = ta.volatility.bollinger_pband(df["close"], window=20, window_dev=2)

    # Normalized ATR (ATR as % of price)
    df["atr_pct"] = df["atr14"] / df["close"]
    return df


def add_volume_features(df: pd.DataFrame) -> pd.DataFrame:
    if "tick_volume" in df.columns:
        vol_col = "tick_volume"
    elif "real_volume" in df.columns:
        vol_col = "real_volume"
    else:
        return df

    df["volume"] = df[vol_col]
    df["vol_sma20"] = df["volume"].rolling(20).mean()
    df["vol_ratio"] = df["volume"] / df["vol_sma20"].replace(0, 1)

    df["obv"] = ta.volume.on_balance_volume(df["close"], df["volume"])
    df["obv_sma10"] = df["obv"].rolling(10).mean()
    return df


def add_price_action_features(df: pd.DataFrame) -> pd.DataFrame:
    body = (df["close"] - df["open"]).abs()
    candle_range = df["high"] - df["low"]

    df["body_ratio"] = body / candle_range.replace(0, 1e-8)
    df["upper_wick"] = (df["high"] - df[["close", "open"]].max(axis=1)) / candle_range.replace(0, 1e-8)
    df["lower_wick"] = (df[["close", "open"]].min(axis=1) - df["low"]) / candle_range.replace(0, 1e-8)
    df["candle_direction"] = (df["close"] > df["open"]).astype(int)
    df["price_change"] = df["close"].pct_change()
    df["high_low_ratio"] = candle_range / df["close"]
    return df
