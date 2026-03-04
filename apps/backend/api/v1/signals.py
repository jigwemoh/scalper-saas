from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import get_current_user, verify_api_key
from services.signal_service import get_latest_signals, get_signal_by_id, get_recent_signals
from models.user import User

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("/latest")
async def latest_signals(
    api_user: Annotated[User, Depends(verify_api_key)],
    db: Annotated[AsyncSession, Depends(get_db)],
    symbol: str | None = Query(default=None),
    limit: int = Query(default=10, le=50),
) -> list[dict]:
    signals = await get_latest_signals(db, symbol=symbol, limit=limit)
    return [
        {
            "id": str(s.id),
            "symbol": s.symbol,
            "timeframe": s.timeframe,
            "direction": s.direction,
            "probability": float(s.probability),
            "entry_price": float(s.entry_price) if s.entry_price else None,
            "stop_loss": float(s.stop_loss) if s.stop_loss else None,
            "take_profit": float(s.take_profit) if s.take_profit else None,
            "regime": s.regime,
            "session": s.session,
            "atr": float(s.atr) if s.atr else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in signals
    ]


@router.get("/recent")
async def recent_signals(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    minutes: int = Query(default=60, le=1440),
    symbol: str | None = Query(default=None),
) -> list[dict]:
    signals = await get_recent_signals(db, since_minutes=minutes, symbol=symbol)
    return [
        {
            "id": str(s.id),
            "symbol": s.symbol,
            "timeframe": s.timeframe,
            "direction": s.direction,
            "probability": float(s.probability),
            "expected_move_pips": float(s.expected_move_pips) if s.expected_move_pips else None,
            "entry_price": float(s.entry_price) if s.entry_price else None,
            "stop_loss": float(s.stop_loss) if s.stop_loss else None,
            "take_profit": float(s.take_profit) if s.take_profit else None,
            "regime": s.regime,
            "session": s.session,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in signals
    ]


@router.get("/{signal_id}")
async def get_signal(
    signal_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    from fastapi import HTTPException
    signal = await get_signal_by_id(db, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return {
        "id": str(signal.id),
        "symbol": signal.symbol,
        "timeframe": signal.timeframe,
        "direction": signal.direction,
        "probability": float(signal.probability),
        "expected_move_pips": float(signal.expected_move_pips) if signal.expected_move_pips else None,
        "entry_price": float(signal.entry_price) if signal.entry_price else None,
        "stop_loss": float(signal.stop_loss) if signal.stop_loss else None,
        "take_profit": float(signal.take_profit) if signal.take_profit else None,
        "regime": signal.regime,
        "session": signal.session,
        "spread": float(signal.spread) if signal.spread else None,
        "atr": float(signal.atr) if signal.atr else None,
        "created_at": signal.created_at.isoformat() if signal.created_at else None,
    }
