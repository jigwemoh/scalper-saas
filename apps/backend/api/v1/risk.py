from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from dependencies import get_current_user
from services.risk_service import evaluate_kill_switch, get_today_performance
from models.user import User
from models.mt5_account import MT5Account
from models.risk import RiskEvent, DailyPerformance

router = APIRouter(prefix="/risk", tags=["risk"])


async def _get_user_account(db: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID) -> MT5Account:
    result = await db.execute(
        select(MT5Account).where(MT5Account.id == account_id, MT5Account.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.get("/kill-switch/{account_id}")
async def kill_switch_status(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    await _get_user_account(db, current_user.id, account_id)
    status = await evaluate_kill_switch(db, account_id)
    return {
        "blocked": status.blocked,
        "level": status.level,
        "reason": status.reason,
    }


@router.get("/events/{account_id}")
async def risk_events(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=20, le=100),
) -> list[dict]:
    await _get_user_account(db, current_user.id, account_id)
    result = await db.execute(
        select(RiskEvent)
        .where(RiskEvent.account_id == account_id)
        .order_by(RiskEvent.triggered_at.desc())
        .limit(limit)
    )
    events = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "description": e.description,
            "triggered_at": e.triggered_at.isoformat(),
        }
        for e in events
    ]


@router.get("/performance/{account_id}")
async def performance_history(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=30, le=365),
) -> list[dict]:
    await _get_user_account(db, current_user.id, account_id)
    result = await db.execute(
        select(DailyPerformance)
        .where(DailyPerformance.account_id == account_id)
        .order_by(DailyPerformance.date.desc())
        .limit(limit)
    )
    perfs = result.scalars().all()
    return [
        {
            "date": str(p.date),
            "starting_balance": float(p.starting_balance),
            "ending_balance": float(p.ending_balance),
            "daily_return_percent": float(p.daily_return_percent),
            "max_drawdown_percent": float(p.max_drawdown_percent),
            "total_trades": p.total_trades,
        }
        for p in perfs
    ]
