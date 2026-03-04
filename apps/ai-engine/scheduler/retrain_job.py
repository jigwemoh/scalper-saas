"""
Weekly retraining job.
Fetches historical candle data, engineers features, labels,
and retrains both LSTM and XGBoost models.
"""
import asyncio
import logging
import numpy as np
import pandas as pd

from data.fetcher import fetch_candles
from features.pipeline import build_feature_matrix, FEATURE_COLUMNS
from models.lstm_model import train_lstm, LSTMPredictor, SEQ_LEN
from models.xgboost_model import ScalpingXGB
from models.ensemble import EnsemblePredictor

logger = logging.getLogger("retrain_job")

RETRAIN_SYMBOLS = ["EURUSD", "GBPUSD"]
LABEL_LOOKAHEAD = 5  # Predict if price up 5 candles later


def create_labels(close_prices: pd.Series, lookahead: int = LABEL_LOOKAHEAD) -> np.ndarray:
    """1 if close[t+lookahead] > close[t], else 0."""
    future = close_prices.shift(-lookahead)
    labels = (future > close_prices).astype(int)
    return labels.values


def prepare_sequences(features: pd.DataFrame, labels: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Prepare [N, SEQ_LEN, n_features] sequences for LSTM."""
    feat_array = features[FEATURE_COLUMNS].values
    X, y = [], []
    for i in range(SEQ_LEN, len(feat_array) - LABEL_LOOKAHEAD):
        X.append(feat_array[i - SEQ_LEN:i])
        y.append(labels[i])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


async def retrain_models() -> None:
    logger.info("Starting weekly model retraining...")
    all_X_xgb, all_y_xgb = [], []
    all_X_lstm, all_y_lstm = [], []

    for symbol in RETRAIN_SYMBOLS:
        try:
            logger.info(f"Fetching training data for {symbol}...")
            df = await fetch_candles(symbol, "M5", count=1000)  # ~3 days of M5 data

            if df.empty or len(df) < 100:
                logger.warning(f"Insufficient data for {symbol}")
                continue

            features = build_feature_matrix(df)
            labels = create_labels(df["close"])

            # Align lengths
            min_len = min(len(features), len(labels))
            features = features.iloc[:min_len]
            labels = labels[:min_len]

            # Remove rows where labels are NaN (last LABEL_LOOKAHEAD rows)
            valid_mask = ~pd.isna(pd.Series(labels))
            features = features[valid_mask]
            labels = labels[valid_mask.values]

            # XGBoost: flat feature matrix
            xgb_X = features[FEATURE_COLUMNS].values.astype(np.float32)
            all_X_xgb.append(xgb_X)
            all_y_xgb.append(labels)

            # LSTM: sequences
            lstm_X, lstm_y = prepare_sequences(features, labels)
            all_X_lstm.append(lstm_X)
            all_y_lstm.append(lstm_y)

        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")

    if not all_X_xgb:
        logger.error("No training data collected — skipping retraining")
        return

    # Train XGBoost
    X_xgb = np.vstack(all_X_xgb)
    y_xgb = np.concatenate(all_y_xgb)
    xgb = ScalpingXGB()
    xgb.train(X_xgb, y_xgb)
    logger.info(f"XGBoost retrained on {len(X_xgb)} samples")

    # Train LSTM
    if all_X_lstm:
        X_lstm = np.vstack(all_X_lstm)
        y_lstm = np.concatenate(all_y_lstm)
        lstm_model = train_lstm(X_lstm, y_lstm, epochs=20)
        predictor = LSTMPredictor()
        predictor.save(lstm_model)
        logger.info(f"LSTM retrained on {len(X_lstm)} sequences")

    logger.info("Retraining complete — reloading ensemble predictor")


async def start_retrain_loop() -> None:
    """Run retraining once weekly (every 7 days)."""
    WEEK_SECONDS = 7 * 24 * 3600
    logger.info("Retraining loop started — first run in 24h")
    await asyncio.sleep(24 * 3600)  # Wait 24h before first retrain

    while True:
        await retrain_models()
        await asyncio.sleep(WEEK_SECONDS)
