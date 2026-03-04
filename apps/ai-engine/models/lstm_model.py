"""
Scalping LSTM model for price direction prediction.
Input:  [batch_size, seq_len=60, n_features=55]
Output: [batch_size, 1]  →  P(price up in next 3–5 candles)
"""
import os
import logging
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger("lstm_model")

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)
MODEL_PATH = ARTIFACTS_DIR / "lstm_latest.pt"

SEQ_LEN = 60
N_FEATURES = 55  # 52 base + 3 M5 context — must match len(FEATURE_COLUMNS) in pipeline.py


class ScalpingLSTM(nn.Module):
    def __init__(self, input_size: int = N_FEATURES, hidden_size: int = 128, num_layers: int = 2):
        super().__init__()
        self.lstm1 = nn.LSTM(input_size, hidden_size, num_layers=1, batch_first=True, dropout=0.0)
        self.lstm2 = nn.LSTM(hidden_size, 64, num_layers=1, batch_first=True)
        self.dropout = nn.Dropout(0.3)
        self.fc1 = nn.Linear(64, 32)
        self.fc2 = nn.Linear(32, 1)
        self.relu = nn.ReLU()
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm1(x)
        out = self.dropout(out)
        out, _ = self.lstm2(out)
        last = out[:, -1, :]          # Take last timestep
        out = self.relu(self.fc1(last))
        out = self.dropout(out)
        out = self.sigmoid(self.fc2(out))
        return out                    # Shape: [B, 1]


class LSTMPredictor:
    def __init__(self):
        self.model: ScalpingLSTM | None = None
        self._load()

    def _load(self) -> None:
        if MODEL_PATH.exists():
            try:
                self.model = ScalpingLSTM()
                self.model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
                self.model.eval()
                logger.info("LSTM model loaded from disk")
            except Exception as e:
                logger.warning(f"Could not load LSTM model: {e}")
                self.model = None
        else:
            logger.info("No LSTM model file found — running without LSTM")
            self.model = None

    def predict(self, feature_matrix: np.ndarray) -> float:
        """
        feature_matrix: shape [seq_len, n_features] — last 60 candles
        Returns probability 0.0–1.0 that next 3–5 candles go up.
        """
        if self.model is None:
            return 0.5  # Neutral if no model loaded

        if len(feature_matrix) < SEQ_LEN:
            return 0.5

        seq = feature_matrix[-SEQ_LEN:]  # Last 60 rows
        if seq.shape[1] != N_FEATURES:
            logger.warning(f"Feature dimension mismatch: expected {N_FEATURES}, got {seq.shape[1]}. Returning neutral.")
            return 0.5

        x = torch.FloatTensor(seq).unsqueeze(0)  # [1, 60, F]
        with torch.no_grad():
            prob = self.model(x).item()
        return float(prob)

    def save(self, model: ScalpingLSTM) -> None:
        torch.save(model.state_dict(), MODEL_PATH)
        self.model = model
        self.model.eval()
        logger.info("LSTM model saved")


def train_lstm(X: np.ndarray, y: np.ndarray, epochs: int = 30) -> ScalpingLSTM:
    """
    Train LSTM on historical data.
    X: [N, SEQ_LEN, N_FEATURES]
    y: [N] binary labels — 1 if price rose 3+ candles later
    """
    model = ScalpingLSTM()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-5)
    criterion = nn.BCELoss()
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5)

    X_t = torch.FloatTensor(X)
    y_t = torch.FloatTensor(y).unsqueeze(1)

    dataset = torch.utils.data.TensorDataset(X_t, y_t)
    loader = torch.utils.data.DataLoader(dataset, batch_size=64, shuffle=True)

    model.train()
    for epoch in range(epochs):
        total_loss = 0.0
        for xb, yb in loader:
            optimizer.zero_grad()
            pred = model(xb)
            loss = criterion(pred, yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += loss.item()
        avg_loss = total_loss / len(loader)
        scheduler.step(avg_loss)
        if (epoch + 1) % 10 == 0:
            logger.info(f"Epoch {epoch+1}/{epochs} — Loss: {avg_loss:.4f}")

    return model
