"""
Polls the MT5 bridge every second for account + position updates.
Broadcasts changes over WebSocket and syncs open positions to DB.
"""
import asyncio
import logging
from typing import Any

from services.mt5_bridge_client import get_account_info, get_positions

logger = logging.getLogger("bridge_poller")


async def start_bridge_poller(ws_manager: Any) -> None:
    previous_account: dict | None = None
    previous_positions: list | None = None

    while True:
        try:
            account = await get_account_info()
            if account and account != previous_account:
                await ws_manager.broadcast({"type": "account_update", "data": account})
                previous_account = account

            positions = await get_positions()
            if positions != previous_positions:
                await ws_manager.broadcast({"type": "positions_update", "data": positions})
                previous_positions = positions

        except Exception as e:
            logger.error(f"Bridge poller error: {e}")

        await asyncio.sleep(2)
