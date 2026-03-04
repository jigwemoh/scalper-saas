import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from models.trade import Trade


async def open_trade(
    db: AsyncSession,
    account_id: uuid.UUID,
    signal_id: uuid.UUID | None,
    symbol: str,
    direction: str,
    lot_size: float,
    entry_price: float | None,
    stop_loss: float | None,
    take_profit: float | None,
    mt5_ticket: int | None = None,
) -> Trade:
    trade = Trade(
        account_id=account_id,
        signal_id=signal_id,
        symbol=symbol,
        direction=direction,
        lot_size=lot_size,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        mt5_ticket=mt5_ticket,
        status="open",
        opened_at=datetime.now(timezone.utc),
    )
    db.add(trade)
    await db.flush()
    return trade


async def close_trade(
    db: AsyncSession,
    trade_id: uuid.UUID,
    exit_price: float,
    profit_loss: float,
) -> Trade | None:
    result = await db.execute(select(Trade).where(Trade.id == trade_id))
    trade = result.scalar_one_or_none()
    if trade:
        trade.exit_price = exit_price  # type: ignore[assignment]
        trade.profit_loss = profit_loss  # type: ignore[assignment]
        trade.status = "closed"  # type: ignore[assignment]
        trade.closed_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await db.flush()
    return trade


async def get_open_trades(db: AsyncSession, account_id: uuid.UUID) -> list[Trade]:
    result = await db.execute(
        select(Trade)
        .where(Trade.account_id == account_id, Trade.status == "open")
        .order_by(desc(Trade.opened_at))
    )
    return list(result.scalars().all())


async def get_trade_history(
    db: AsyncSession,
    account_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[Trade]:
    result = await db.execute(
        select(Trade)
        .where(Trade.account_id == account_id)
        .order_by(desc(Trade.opened_at))
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_trade_by_ticket(db: AsyncSession, mt5_ticket: int) -> Trade | None:
    result = await db.execute(select(Trade).where(Trade.mt5_ticket == mt5_ticket))
    return result.scalar_one_or_none()
