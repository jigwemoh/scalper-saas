import uuid
from datetime import datetime, timezone, date, timedelta
from typing import Literal
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models.risk import RiskEvent, DailyPerformance
from models.trade import Trade


@dataclass
class KillSwitchStatus:
    blocked: bool
    level: Literal["none", "soft_pause", "daily_kill", "weekly_kill"]
    reason: str


# Pip value per lot for common pairs (approximate, USD accounts)
PIP_VALUES: dict[str, float] = {
    "EURUSD": 10.0,
    "GBPUSD": 10.0,
    "AUDUSD": 10.0,
    "NZDUSD": 10.0,
    "USDJPY": 9.1,
    "USDCAD": 7.7,
    "USDCHF": 10.0,
    "XAUUSD": 1.0,   # Gold: $1 per 0.01 lot per pip
    "BTCUSD": 1.0,
}


def calculate_lot_size(
    account_balance: float,
    sl_pips: float,
    symbol: str = "EURUSD",
    risk_pct: float = 0.02,
) -> float:
    pip_value = PIP_VALUES.get(symbol, 10.0)
    risk_amount = account_balance * risk_pct
    lot_size = risk_amount / (sl_pips * pip_value)
    # Round to 2 decimal places, minimum 0.01
    lot_size = max(round(lot_size, 2), 0.01)
    return lot_size


def apply_dynamic_scaling(base_risk_pct: float, consecutive_wins: int, consecutive_losses: int) -> float:
    multiplier = 1.0
    if consecutive_wins >= 2:
        multiplier = min(1.0 + (consecutive_wins - 1) * 0.1, 1.5)  # Max 50% increase
    elif consecutive_losses >= 2:
        multiplier = max(1.0 - (consecutive_losses - 1) * 0.2, 0.25)  # Min 75% reduction
    adjusted = base_risk_pct * multiplier
    # Hard cap: never exceed 3%, never below 0.5%
    return max(min(adjusted, 0.03), 0.005)


async def get_today_performance(db: AsyncSession, account_id: uuid.UUID) -> DailyPerformance | None:
    today = date.today()
    result = await db.execute(
        select(DailyPerformance).where(
            DailyPerformance.account_id == account_id,
            DailyPerformance.date == today,
        )
    )
    return result.scalar_one_or_none()


async def get_weekly_drawdown(db: AsyncSession, account_id: uuid.UUID) -> float:
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    result = await db.execute(
        select(func.sum(DailyPerformance.daily_return_percent)).where(
            DailyPerformance.account_id == account_id,
            DailyPerformance.date >= week_ago.date(),
        )
    )
    total = result.scalar() or 0.0
    return float(total)


async def evaluate_kill_switch(db: AsyncSession, account_id: uuid.UUID) -> KillSwitchStatus:
    today_perf = await get_today_performance(db, account_id)

    if today_perf:
        daily_return = float(today_perf.daily_return_percent)

        if daily_return <= -8.0:
            return KillSwitchStatus(
                blocked=True,
                level="daily_kill",
                reason=f"Daily drawdown {daily_return:.2f}% exceeded -8% hard kill",
            )
        if daily_return <= -6.0:
            return KillSwitchStatus(
                blocked=True,
                level="soft_pause",
                reason=f"Daily drawdown {daily_return:.2f}% exceeded -6% soft pause",
            )

    weekly_return = await get_weekly_drawdown(db, account_id)
    if weekly_return <= -12.0:
        return KillSwitchStatus(
            blocked=True,
            level="weekly_kill",
            reason=f"Weekly drawdown {weekly_return:.2f}% exceeded -12% weekly kill",
        )

    return KillSwitchStatus(blocked=False, level="none", reason="")


async def log_risk_event(
    db: AsyncSession,
    account_id: uuid.UUID,
    event_type: str,
    description: str,
) -> RiskEvent:
    event = RiskEvent(account_id=account_id, event_type=event_type, description=description)
    db.add(event)
    await db.flush()
    return event


async def upsert_daily_performance(
    db: AsyncSession,
    account_id: uuid.UUID,
    starting_balance: float,
    ending_balance: float,
    total_trades: int,
    max_drawdown_percent: float = 0.0,
) -> DailyPerformance:
    today = date.today()
    daily_return = ((ending_balance - starting_balance) / starting_balance) * 100 if starting_balance else 0.0

    existing = await get_today_performance(db, account_id)
    if existing:
        existing.ending_balance = ending_balance  # type: ignore[assignment]
        existing.daily_return_percent = daily_return  # type: ignore[assignment]
        existing.total_trades = total_trades  # type: ignore[assignment]
        existing.max_drawdown_percent = max_drawdown_percent  # type: ignore[assignment]
        await db.flush()
        return existing

    perf = DailyPerformance(
        account_id=account_id,
        date=today,
        starting_balance=starting_balance,
        ending_balance=ending_balance,
        daily_return_percent=daily_return,
        max_drawdown_percent=max_drawdown_percent,
        total_trades=total_trades,
    )
    db.add(perf)
    await db.flush()
    return perf
