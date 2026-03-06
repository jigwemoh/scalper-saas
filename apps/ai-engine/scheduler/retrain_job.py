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

# Must match SYMBOLS in strategy/signal_generator.py
RETRAIN_SYMBOLS = ["EURUSD", "GBPUSD", "XAUUSD"]
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


async def retrain_models(predictor: EnsemblePredictor | None = None) -> None:
    logger.info("Starting weekly model retraining...")
    all_X_xgb, all_y_xgb = [], []
    all_X_lstm, all_y_lstm = [], []

    for symbol in RETRAIN_SYMBOLS:
        try:
            logger.info(f"Fetching training data for {symbol}...")
            # Use M1 data for training to match inference timeframe
            df = await fetch_candles(symbol, "M1", count=2000)

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
            if len(lstm_X) > 0:
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
        lstm_predictor = LSTMPredictor()
        lstm_predictor.save(lstm_model)
        logger.info(f"LSTM retrained on {len(X_lstm)} sequences")

    # Reload the live ensemble predictor so new models take effect immediately
    if predictor is not None:
        predictor.reload()
        logger.info("Live ensemble predictor reloaded with new models")
    else:
        logger.warning("No predictor reference passed — live predictor not reloaded; restart to use new models")


async def start_retrain_loop(predictor: EnsemblePredictor | None = None) -> None:
    """Run retraining once weekly (every 7 days). First run immediately."""
    WEEK_SECONDS = 7 * 24 * 3600
    logger.info("Retraining loop started — running initial training now")

    # Train immediately on startup
    await retrain_models(predictor)

    while True:
        await asyncio.sleep(WEEK_SECONDS)
        await retrain_models(predictor)
