import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from models.signal import AISignal


async def save_signal(db: AsyncSession, data: dict[str, Any]) -> AISignal:
    signal = AISignal(
        symbol=data["symbol"],
        timeframe=data["timeframe"],
        direction=data["direction"],
        probability=data["probability"],
        expected_move_pips=data.get("expected_move_pips"),
        regime=data.get("regime"),
        spread=data.get("spread"),
        atr=data.get("atr"),
        session=data.get("session"),
        entry_price=data.get("entry_price"),
        stop_loss=data.get("stop_loss"),
        take_profit=data.get("take_profit"),
    )
    db.add(signal)
    await db.flush()
    return signal


async def get_latest_signals(
    db: AsyncSession,
    symbol: str | None = None,
    limit: int = 20,
) -> list[AISignal]:
    query = select(AISignal).order_by(desc(AISignal.created_at)).limit(limit)
    if symbol:
        query = query.where(AISignal.symbol == symbol.upper())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_signal_by_id(db: AsyncSession, signal_id: uuid.UUID) -> AISignal | None:
    result = await db.execute(select(AISignal).where(AISignal.id == signal_id))
    return result.scalar_one_or_none()


async def get_recent_signals(
    db: AsyncSession,
    since_minutes: int = 60,
    symbol: str | None = None,
) -> list[AISignal]:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
    query = (
        select(AISignal)
        .where(AISignal.created_at >= cutoff)
        .order_by(desc(AISignal.created_at))
    )
    if symbol:
        query = query.where(AISignal.symbol == symbol.upper())
    result = await db.execute(query)
    return list(result.scalars().all())
