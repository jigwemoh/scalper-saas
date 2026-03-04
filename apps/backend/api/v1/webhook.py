"""
Webhook endpoint that the MT5 bridge calls when trades are executed or closed.
Keeps the DB in sync with live MT5 state.
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from services.trade_service import close_trade, get_trade_by_ticket

logger = logging.getLogger("webhook")
router = APIRouter(prefix="/webhook", tags=["webhook"])
settings = get_settings()


class TradeClosedPayload(BaseModel):
    mt5_ticket: int
    exit_price: float
    profit_loss: float


@router.post("/trade-closed")
async def trade_closed(
    payload: TradeClosedPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Verify bridge secret
    secret = request.headers.get("X-Bridge-Secret", "")
    if secret != settings.mt5_bridge_secret:
        raise HTTPException(status_code=401, detail="Invalid bridge secret")

    trade = await get_trade_by_ticket(db, payload.mt5_ticket)
    if not trade:
        logger.warning(f"Trade ticket {payload.mt5_ticket} not found in DB")
        return {"status": "not_found"}

    updated = await close_trade(db, trade.id, payload.exit_price, payload.profit_loss)
    await db.commit()
    logger.info(f"Closed trade {payload.mt5_ticket} P&L={payload.profit_loss}")
    return {"status": "ok", "trade_id": str(updated.id) if updated else None}
