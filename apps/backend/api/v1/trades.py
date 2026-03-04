from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from dependencies import get_current_user
from services.trade_service import get_trade_history, get_open_trades
from models.user import User
from models.mt5_account import MT5Account

router = APIRouter(prefix="/trades", tags=["trades"])


async def _get_user_account(db: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID) -> MT5Account:
    result = await db.execute(
        select(MT5Account).where(
            MT5Account.id == account_id,
            MT5Account.user_id == user_id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.get("/open")
async def open_trades(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    await _get_user_account(db, current_user.id, account_id)
    trades = await get_open_trades(db, account_id)
    return [_trade_dict(t) for t in trades]


@router.get("/history")
async def trade_history(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
) -> dict:
    await _get_user_account(db, current_user.id, account_id)
    trades = await get_trade_history(db, account_id, limit=limit, offset=offset)
    return {"trades": [_trade_dict(t) for t in trades], "count": len(trades)}


def _trade_dict(t) -> dict:
    return {
        "id": str(t.id),
        "mt5_ticket": t.mt5_ticket,
        "symbol": t.symbol,
        "direction": t.direction,
        "lot_size": float(t.lot_size),
        "entry_price": float(t.entry_price) if t.entry_price else None,
        "stop_loss": float(t.stop_loss) if t.stop_loss else None,
        "take_profit": float(t.take_profit) if t.take_profit else None,
        "exit_price": float(t.exit_price) if t.exit_price else None,
        "profit_loss": float(t.profit_loss) if t.profit_loss else None,
        "status": t.status,
        "opened_at": t.opened_at.isoformat() if t.opened_at else None,
        "closed_at": t.closed_at.isoformat() if t.closed_at else None,
    }
