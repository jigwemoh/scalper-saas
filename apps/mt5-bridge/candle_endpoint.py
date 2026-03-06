"""
Adds OHLCV candle data endpoint to the MT5 bridge.
GET /api/mt5/candles?symbol=EURUSD&tf=M1&count=100
Returns list of OHLCV dicts for the AI engine to consume.
"""
from typing import Any
from fastapi import APIRouter, HTTPException, Query

try:
    import MetaTrader5 as mt5  # type: ignore
    mt5_available = True
except ImportError:
    mt5 = None  # type: ignore
    mt5_available = False

TIMEFRAME_MAP = {
    "M1": 1,    # mt5.TIMEFRAME_M1
    "M5": 5,    # mt5.TIMEFRAME_M5
    "M15": 15,
    "M30": 30,
    "H1": 16385,
    "H4": 16388,
    "D1": 16408,
}

router = APIRouter()


def _get_tf_constant(tf_str: str) -> int:
    if mt5 is None:
        return 1
    tf_map = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }
    return tf_map.get(tf_str.upper(), mt5.TIMEFRAME_M5)


@router.get("/api/mt5/candles")
def get_candles(
    symbol: str = Query(..., description="Trading symbol e.g. EURUSD"),
    tf: str = Query(default="M5", description="Timeframe: M1, M5, M15, H1, etc."),
    count: int = Query(default=100, ge=10, le=1000),
) -> list[dict[str, Any]]:
    if not mt5_available or mt5 is None:
        raise HTTPException(status_code=503, detail="MT5 not available")

    timeframe = _get_tf_constant(tf)
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)  # type: ignore

    if rates is None:
        raise HTTPException(status_code=500, detail=f"Failed to fetch candles for {symbol}")

    return [
        {
            "time": int(r["time"]),
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
            "tick_volume": int(r["tick_volume"]),
            "real_volume": int(r["real_volume"]) if "real_volume" in r.dtype.names else 0,
            "spread": int(r["spread"]) if "spread" in r.dtype.names else 0,
        }
        for r in rates
    ]
