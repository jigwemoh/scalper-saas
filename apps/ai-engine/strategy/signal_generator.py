"""
Core signal generation logic.
Combines rule-based filters with AI ensemble prediction.
Only emits signals when ALL conditions pass.
"""
import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import numpy as np

from features.pipeline import build_feature_matrix, get_latest_feature_row, FEATURE_COLUMNS
from models.ensemble import EnsemblePredictor
from strategy.liquidity_sweep import detect_bullish_sweep, detect_bearish_sweep
from strategy.regime_detector import classify_regime, is_tradeable_regime

logger = logging.getLogger("signal_generator")

# Tunable thresholds
MIN_AI_CONFIDENCE = 0.68
MAX_SPREAD_PIPS = 3.0
MIN_ATR_MULTIPLE = 0.8   # ATR must be >= 80% of session average

# TP:SL ratio
REWARD_RISK_RATIO = 1.5

SYMBOLS = ["EURUSD", "GBPUSD", "XAUUSD"]


@dataclass
class TradingSignal:
    symbol: str
    timeframe: str
    direction: str        # BUY | SELL
    probability: float
    entry_price: float
    stop_loss: float
    take_profit: float
    sl_pips: float
    regime: str
    session: str
    spread: float
    atr: float
    expected_move_pips: float
    liquidity_sweep: bool


def _get_session(hour: int) -> str:
    if 7 <= hour < 16:
        return "london"
    if 13 <= hour < 22:
        return "new_york"
    if 0 <= hour < 8:
        return "asia"
    return "off_hours"


def _calc_sl_tp(
    direction: str,
    entry: float,
    atr: float,
    symbol: str,
    rr: float = REWARD_RISK_RATIO,
) -> tuple[float, float, float]:
    """Returns (stop_loss, take_profit, sl_pips)."""
    pip_size = 0.0001 if "JPY" not in symbol else 0.01
    if symbol == "XAUUSD":
        pip_size = 0.1

    sl_distance = atr * 1.0  # 1× ATR for SL
    tp_distance = sl_distance * rr

    if direction == "BUY":
        sl = entry - sl_distance
        tp = entry + tp_distance
    else:
        sl = entry + sl_distance
        tp = entry - tp_distance

    sl_pips = sl_distance / pip_size
    return round(sl, 5), round(tp, 5), round(sl_pips, 1)


def evaluate_setup(
    df_m1: pd.DataFrame,
    df_m5: pd.DataFrame,
    symbol: str,
    predictor: EnsemblePredictor,
) -> Optional[TradingSignal]:
    """
    Evaluates M1+M5 data for a trade setup.
    Returns TradingSignal if all conditions pass, else None.
    """
    if len(df_m1) < 60 or len(df_m5) < 20:
        return None

    last = df_m1.iloc[-1]
    hour = last.name.hour if hasattr(last.name, "hour") else 12

    # === RULE FILTER 1: Session ===
    session = _get_session(hour)
    if session == "off_hours":
        return None

    # === RULE FILTER 2: Spread ===
    spread = float(last.get("spread", 0))
    spread_pips = spread  # Already in pips if spread column is pips
    if spread_pips > MAX_SPREAD_PIPS:
        logger.debug(f"{symbol}: spread {spread_pips} > {MAX_SPREAD_PIPS}")
        return None

    # Build feature matrix
    features = build_feature_matrix(df_m1)
    if features.empty or len(features) < 60:
        return None

    latest = features.iloc[-1]

    # === RULE FILTER 3: EMA alignment ===
    ema20 = latest.get("ema20", 0)
    ema50 = latest.get("ema50", 0)
    close = float(last["close"])
    vwap = latest.get("vwap", close)

    ema_bull = ema20 > ema50
    ema_bear = ema20 < ema50

    # === RULE FILTER 4: RSI pullback zone ===
    rsi = latest.get("rsi14", 50)
    rsi_bull_zone = 40 <= rsi <= 58   # Pullback in uptrend
    rsi_bear_zone = 42 <= rsi <= 62   # Pullback in downtrend

    # === RULE FILTER 5: ATR above session average ===
    atr = float(latest.get("atr14", 0))
    atr_avg = float(features["atr14"].iloc[-20:].mean()) if "atr14" in features.columns else atr
    atr_ok = atr >= atr_avg * MIN_ATR_MULTIPLE

    # === RULE FILTER 6: Regime ===
    regime = classify_regime(features)
    if not is_tradeable_regime(regime):
        logger.debug(f"{symbol}: regime {regime} not tradeable")
        return None

    # Determine candidate direction
    if ema_bull and close > vwap and rsi_bull_zone:
        candidate = "BUY"
        liquidity_sweep = detect_bullish_sweep(df_m1)
    elif ema_bear and close < vwap and rsi_bear_zone:
        candidate = "SELL"
        liquidity_sweep = detect_bearish_sweep(df_m1)
    else:
        return None

    if not atr_ok:
        return None

    # === AI GATE: Ensemble prediction ===
    feature_matrix = features[FEATURE_COLUMNS].values  # [N, 55]
    feature_row = features[FEATURE_COLUMNS].iloc[[-1]].values  # [1, 55]

    prediction = predictor.predict(feature_row, feature_matrix)

    if prediction["direction"] == "HOLD":
        return None
    if prediction["direction"] != candidate:
        return None  # AI disagrees with rule filter
    if prediction["probability"] < MIN_AI_CONFIDENCE:
        return None

    # Liquidity sweep bonus: lower threshold slightly
    effective_threshold = MIN_AI_CONFIDENCE - (0.03 if liquidity_sweep else 0)
    if prediction["probability"] < effective_threshold:
        return None

    # === CALCULATE SL/TP ===
    sl, tp, sl_pips = _calc_sl_tp(candidate, close, atr, symbol)
    expected_move = atr * REWARD_RISK_RATIO / 0.0001  # In pips (for 4-digit pairs)

    return TradingSignal(
        symbol=symbol,
        timeframe="M1",
        direction=candidate,
        probability=prediction["probability"],
        entry_price=round(close, 5),
        stop_loss=sl,
        take_profit=tp,
        sl_pips=sl_pips,
        regime=regime,
        session=session,
        spread=spread_pips,
        atr=atr,
        expected_move_pips=round(expected_move, 1),
        liquidity_sweep=liquidity_sweep,
    )
