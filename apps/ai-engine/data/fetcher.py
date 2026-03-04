"""Fetches OHLCV candle data from the MT5 bridge."""
import os
import logging
from typing import Any

import httpx
import pandas as pd

logger = logging.getLogger("fetcher")

BRIDGE_URL = os.getenv("MT5_BRIDGE_URL", "http://localhost:9000")
BRIDGE_SECRET = os.getenv("MT5_BRIDGE_SECRET", "dev-bridge-secret")

HEADERS = {"X-Bridge-Secret": BRIDGE_SECRET}


async def fetch_candles(symbol: str, timeframe: str, count: int = 200) -> pd.DataFrame:
    """Fetch OHLCV candles from the bridge and return as DataFrame."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{BRIDGE_URL}/api/mt5/candles",
                params={"symbol": symbol, "tf": timeframe, "count": count},
                headers=HEADERS,
            )
            r.raise_for_status()
            data: list[dict[str, Any]] = r.json()

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df = df.set_index("time").sort_index()
        df.columns = [c.lower() for c in df.columns]
        return df

    except Exception as e:
        logger.error(f"Failed to fetch candles for {symbol}/{timeframe}: {e}")
        return pd.DataFrame()


async def fetch_multi_tf(symbol: str) -> dict[str, pd.DataFrame]:
    """Fetch M1 and M5 data simultaneously."""
    import asyncio
    m1, m5 = await asyncio.gather(
        fetch_candles(symbol, "M1", count=200),
        fetch_candles(symbol, "M5", count=100),
    )
    return {"M1": m1, "M5": m5}
