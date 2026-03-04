"""
Ensemble combiner: 0.7 × XGBoost + 0.3 × LSTM
Threshold: > 0.68 = BUY signal, < 0.32 = SELL signal, else HOLD
"""
import logging
import numpy as np

from models.xgboost_model import ScalpingXGB
from models.lstm_model import LSTMPredictor

logger = logging.getLogger("ensemble")

BUY_THRESHOLD = 0.68
SELL_THRESHOLD = 0.32
XGB_WEIGHT = 0.7
LSTM_WEIGHT = 0.3


class EnsemblePredictor:
    def __init__(self):
        self.xgb = ScalpingXGB()
        self.lstm = LSTMPredictor()

    def predict(
        self,
        feature_row: np.ndarray,      # [1, n_features] — latest candle
        feature_matrix: np.ndarray,   # [seq_len, n_features] — last 60 candles
    ) -> dict:
        """
        Returns:
            {
              "direction": "BUY" | "SELL" | "HOLD",
              "probability": float,   # 0.5 = neutral, >0.68 = strong buy
              "xgb_prob": float,
              "lstm_prob": float,
            }
        """
        xgb_prob = self.xgb.predict(feature_row)
        lstm_prob = self.lstm.predict(feature_matrix)

        ensemble_score = XGB_WEIGHT * xgb_prob + LSTM_WEIGHT * lstm_prob

        if ensemble_score > BUY_THRESHOLD:
            direction = "BUY"
        elif ensemble_score < SELL_THRESHOLD:
            direction = "SELL"
        else:
            direction = "HOLD"

        return {
            "direction": direction,
            "probability": ensemble_score,
            "xgb_prob": xgb_prob,
            "lstm_prob": lstm_prob,
        }

    def reload(self) -> None:
        """Reload models from disk after retraining."""
        self.xgb = ScalpingXGB()
        self.lstm = LSTMPredictor()
        logger.info("Ensemble models reloaded")
