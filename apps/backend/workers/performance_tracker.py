"""
Runs every 60 seconds to update daily_performance for all active accounts.
Uses live MT5 data from the bridge.
"""
import asyncio
import logging
from datetime import date

from sqlalchemy import select

from database import AsyncSessionLocal
from models.mt5_account import MT5Account
from services.mt5_bridge_client import get_account_info, get_history_stats
from services.risk_service import upsert_daily_performance, evaluate_kill_switch, log_risk_event

logger = logging.getLogger("performance_tracker")


async def _snapshot_all_accounts() -> None:
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(MT5Account).where(MT5Account.is_active == True))  # noqa: E712
            accounts = result.scalars().all()

            account_info = await get_account_info()
            if not account_info:
                return

            history = await get_history_stats(days=1)
            today_trades = history.get("total_trades", 0) if history else 0

            for account in accounts:
                try:
                    balance = float(account_info.get("balance", 0))
                    equity = float(account_info.get("equity", 0))

                    # Update account balance/equity
                    account.account_balance = balance  # type: ignore[assignment]
                    account.account_equity = equity  # type: ignore[assignment]

                    # Use starting balance from DB or current if not set
                    starting = float(account.account_balance or balance)

                    perf = await upsert_daily_performance(
                        db=db,
                        account_id=account.id,
                        starting_balance=starting,
                        ending_balance=equity,
                        total_trades=today_trades,
                    )

                    # Auto-check kill switches
                    ks = await evaluate_kill_switch(db, account.id)
                    if ks.blocked:
                        await log_risk_event(
                            db, account.id, ks.level, ks.reason
                        )
                        logger.warning(f"Kill switch triggered for account {account.id}: {ks.reason}")

                except Exception as e:
                    logger.error(f"Error snapshotting account {account.id}: {e}")

            await db.commit()
        except Exception as e:
            logger.error(f"Performance tracker error: {e}")
            await db.rollback()


async def start_performance_tracker() -> None:
    while True:
        await _snapshot_all_accounts()
        await asyncio.sleep(60)
