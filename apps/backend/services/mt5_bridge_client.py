"""
HTTP client to the Windows VPS MT5 bridge.
The bridge runs mt5_executor_fastapi.py on the Windows machine.
"""
from typing import Any
import httpx

from config import get_settings

settings = get_settings()


def _headers() -> dict[str, str]:
    return {"X-Bridge-Secret": settings.mt5_bridge_secret}


async def get_account_info() -> dict[str, Any] | None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{settings.mt5_bridge_url}/api/mt5/account", headers=_headers())
            r.raise_for_status()
            return r.json()
    except Exception:
        return None


async def get_positions() -> list[dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{settings.mt5_bridge_url}/api/mt5/positions", headers=_headers())
            r.raise_for_status()
            return r.json()
    except Exception:
        return []


async def execute_order(
    symbol: str,
    direction: str,
    volume: float,
    entry_price: float | None = None,
    stop_loss: float | None = None,
    take_profit: float | None = None,
    comment: str = "SCALPER_SAAS",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "symbol": symbol,
        "direction": direction,
        "volume": volume,
        "comment": comment,
    }
    if entry_price is not None:
        payload["entry_price"] = entry_price
    if stop_loss is not None:
        payload["stop_loss"] = stop_loss
    if take_profit is not None:
        payload["take_profit"] = take_profit

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{settings.mt5_bridge_url}/execute",
                json=payload,
                headers=_headers(),
            )
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        return {"status": "error", "error": str(e)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def get_candles(symbol: str, timeframe: str, count: int = 100) -> list[dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{settings.mt5_bridge_url}/api/mt5/candles",
                params={"symbol": symbol, "tf": timeframe, "count": count},
                headers=_headers(),
            )
            r.raise_for_status()
            return r.json()
    except Exception:
        return []


async def get_history_stats(days: int = 365) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{settings.mt5_bridge_url}/api/mt5/history_stats",
                params={"days": days},
                headers=_headers(),
            )
            r.raise_for_status()
            return r.json()
    except Exception:
        return {}
