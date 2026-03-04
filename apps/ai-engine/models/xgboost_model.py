"""
XGBoost classifier for M1/M5 price direction prediction.
Input:  [n_samples, n_features] — latest feature row
Output: probability 0.0–1.0 that price goes up
"""
import os
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger("xgb_model")

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)
MODEL_PATH = ARTIFACTS_DIR / "xgb_latest.json"

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False
    logger.warning("xgboost not installed — XGB predictions will be neutral")


class ScalpingXGB:
    def __init__(self):
        self.model = None
        self._load()

    def _load(self) -> None:
        if not XGB_AVAILABLE:
            return
        if MODEL_PATH.exists():
            try:
                self.model = xgb.XGBClassifier()
                self.model.load_model(str(MODEL_PATH))
                logger.info("XGBoost model loaded from disk")
            except Exception as e:
                logger.warning(f"Could not load XGBoost model: {e}")
                self.model = None
        else:
            logger.info("No XGBoost model file found — running without XGB")

    def predict(self, feature_row: np.ndarray) -> float:
        """
        feature_row: shape [1, n_features] — latest candle features
        Returns probability 0.0–1.0 of price going up.
        """
        if self.model is None or not XGB_AVAILABLE:
            return 0.5

        try:
            prob = self.model.predict_proba(feature_row)[0][1]
            return float(prob)
        except Exception as e:
            logger.error(f"XGB predict error: {e}")
            return 0.5

    def save(self) -> None:
        if self.model:
            self.model.save_model(str(MODEL_PATH))
            logger.info("XGBoost model saved")

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """
        Train XGBoost on historical features.
        X: [n_samples, n_features]
        y: [n_samples] binary labels
        """
        if not XGB_AVAILABLE:
            logger.error("xgboost not installed")
            return

        self.model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=3,
            gamma=0.1,
            reg_alpha=0.1,
            reg_lambda=1.0,
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1,
        )
        self.model.fit(X, y, verbose=False)
        logger.info(f"XGBoost trained on {len(X)} samples")
        self.save()
