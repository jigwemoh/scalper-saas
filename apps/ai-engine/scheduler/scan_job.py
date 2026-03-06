"""
Main scan job: runs every 60 seconds.
For each symbol, fetches M1+M5 data, evaluates setup, pushes signals to Redis.
"""
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis

from data.fetcher import fetch_multi_tf
from models.ensemble import EnsemblePredictor
from strategy.signal_generator import evaluate_setup, SYMBOLS

logger = logging.getLogger("scan_job")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
AI_ENGINE_SECRET = os.getenv("AI_ENGINE_SECRET", "dev-engine-secret")
SIGNAL_QUEUE_KEY = "signals:pending"

# Singleton predictor — loaded once at startup
_predictor: EnsemblePredictor | None = None


def get_predictor() -> EnsemblePredictor:
    global _predictor
    if _predictor is None:
        _predictor = EnsemblePredictor()
    return _predictor


async def _persist_signal_to_backend(signal_payload: dict) -> str | None:
    """POST signal to backend API to persist in DB. Returns signal ID."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{BACKEND_URL}/api/v1/signals/internal",
                json=signal_payload,
                headers={"X-AI-Engine-Secret": AI_ENGINE_SECRET},
            )
            if r.status_code == 201:
                return r.json().get("id")
    except Exception as e:
        logger.error(f"Failed to persist signal: {e}")
    return None


async def scan_symbol(symbol: str, redis: aioredis.Redis) -> None:
    try:
        data = await fetch_multi_tf(symbol)
        df_m1 = data.get("M1")
        df_m5 = data.get("M5")

        if df_m1 is None or df_m1.empty:
            return

        predictor = get_predictor()
        signal = evaluate_setup(df_m1, df_m5 or df_m1, symbol, predictor)

        if signal is None:
            return

        logger.info(
            f"SIGNAL: {signal.direction} {symbol} "
            f"prob={signal.probability:.3f} "
            f"regime={signal.regime} session={signal.session}"
            f"{' [SWEEP]' if signal.liquidity_sweep else ''}"
        )

        # Build Redis payload
        payload = {
            "signal_id": str(uuid.uuid4()),
            "symbol": signal.symbol,
            "timeframe": signal.timeframe,
            "direction": signal.direction,
            "probability": signal.probability,
            "entry_price": signal.entry_price,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "sl_pips": signal.sl_pips,
            "regime": signal.regime,
            "session": signal.session,
            "spread": signal.spread,
            "atr": signal.atr,
            "expected_move_pips": signal.expected_move_pips,
            "liquidity_sweep": signal.liquidity_sweep,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Push to Redis for signal_dispatcher to consume
        await redis.rpush(SIGNAL_QUEUE_KEY, json.dumps(payload))
        logger.info(f"Signal pushed to Redis queue: {signal.direction} {symbol}")

    except Exception as e:
        logger.error(f"Error scanning {symbol}: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def run_scan() -> None:
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    logger.info(f"Scanning {len(SYMBOLS)} symbols...")
    await asyncio.gather(*[scan_symbol(sym, r) for sym in SYMBOLS])
    await r.aclose()


async def start_scan_loop() -> None:
    logger.info("Scan loop started — interval: 60s")
    while True:
        await run_scan()
        await asyncio.sleep(60)
