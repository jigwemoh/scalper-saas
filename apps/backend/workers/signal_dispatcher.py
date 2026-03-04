"""
Reads signals from Redis queue and dispatches to MT5 bridge.
Enforces kill switch and risk sizing before execution.
"""
import asyncio
import json
import logging
import uuid

import redis.asyncio as aioredis

from config import get_settings
from database import AsyncSessionLocal
from models.mt5_account import MT5Account
from models.trade import Trade
from services.mt5_bridge_client import execute_order
from services.risk_service import evaluate_kill_switch, calculate_lot_size, apply_dynamic_scaling, log_risk_event
from services.trade_service import open_trade
from services.subscription_service import get_active_subscription, get_risk_pct_for_plan
from sqlalchemy import select
from datetime import datetime, timezone

logger = logging.getLogger("signal_dispatcher")
settings = get_settings()

SIGNAL_QUEUE_KEY = "signals:pending"


async def _get_streak(db, account_id: uuid.UUID) -> tuple[int, int]:
    """Returns (consecutive_wins, consecutive_losses) from the last 10 closed trades."""
    result = await db.execute(
        select(Trade)
        .where(Trade.account_id == account_id, Trade.status == "closed")
        .order_by(Trade.closed_at.desc())
        .limit(10)
    )
    trades = result.scalars().all()

    consecutive_wins = 0
    consecutive_losses = 0

    for trade in trades:
        pnl = float(trade.profit_loss or 0)
        if pnl > 0:
            if consecutive_losses > 0:
                break
            consecutive_wins += 1
        elif pnl < 0:
            if consecutive_wins > 0:
                break
            consecutive_losses += 1
        else:
            break

    return consecutive_wins, consecutive_losses


async def dispatch_one(redis: aioredis.Redis, raw: str) -> None:
    try:
        signal_data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error(f"Invalid signal JSON: {raw}")
        return

    signal_id_str = signal_data.get("signal_id")
    symbol = signal_data.get("symbol", "EURUSD")
    direction = signal_data.get("direction", "BUY")
    sl_pips = float(signal_data.get("sl_pips", 10))
    entry_price = signal_data.get("entry_price")
    stop_loss = signal_data.get("stop_loss")
    take_profit = signal_data.get("take_profit")

    # Validate signal_id is present — required for trade linkage
    if not signal_id_str:
        logger.warning("Signal missing signal_id — trade will have no signal linkage")

    async with AsyncSessionLocal() as db:
        try:
            # Get all active accounts to dispatch to
            result = await db.execute(
                select(MT5Account).where(MT5Account.is_active == True)  # noqa: E712
            )
            accounts = result.scalars().all()

            for account in accounts:
                try:
                    # Check subscription
                    sub = await get_active_subscription(db, account.user_id)
                    if not sub and account.user_id is not None:
                        continue  # Skip accounts without active subscription

                    # Check kill switch
                    ks = await evaluate_kill_switch(db, account.id)
                    if ks.blocked:
                        logger.info(f"Skip account {account.id}: {ks.reason}")
                        continue

                    # Calculate lot size with dynamic scaling based on win/loss streak
                    balance = float(account.account_balance or 1000)
                    plan_name = sub.plan_name if sub else "starter"
                    base_risk_pct = get_risk_pct_for_plan(plan_name)

                    wins, losses = await _get_streak(db, account.id)
                    scaled_risk_pct = apply_dynamic_scaling(base_risk_pct, wins, losses)
                    lot = calculate_lot_size(balance, sl_pips, symbol, scaled_risk_pct)

                    if wins > 1 or losses > 1:
                        logger.info(
                            f"Account {account.id}: streak wins={wins} losses={losses} "
                            f"risk {base_risk_pct:.3f} → {scaled_risk_pct:.3f}"
                        )

                    # Execute on bridge
                    result_exec = await execute_order(
                        symbol=symbol,
                        direction=direction,
                        volume=lot,
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                    )

                    if result_exec.get("status") == "executed":
                        ticket = result_exec.get("ticket")
                        actual_price = result_exec.get("price", entry_price)

                        await open_trade(
                            db=db,
                            account_id=account.id,
                            signal_id=uuid.UUID(signal_id_str) if signal_id_str else None,
                            symbol=symbol,
                            direction=direction,
                            lot_size=lot,
                            entry_price=actual_price,
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            mt5_ticket=ticket,
                        )
                        logger.info(f"Executed {direction} {lot} {symbol} ticket={ticket} on account {account.id}")
                    else:
                        err = result_exec.get("error", "Unknown error")
                        logger.error(f"Order failed for account {account.id}: {err}")
                        await log_risk_event(db, account.id, "order_failed", f"Order failed: {err}")

                except Exception as e:
                    logger.exception(f"Error dispatching to account {account.id}: {e}")
                    # Continue to next account — don't abort all accounts on one failure

            await db.commit()

        except Exception as e:
            logger.exception(f"Dispatch error: {e}")
            await db.rollback()


async def start_signal_dispatcher() -> None:
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    logger.info("Signal dispatcher started, waiting for signals...")

    while True:
        try:
            item = await r.blpop(SIGNAL_QUEUE_KEY, timeout=5)
            if item:
                _, raw = item
                await dispatch_one(r, raw)
        except Exception as e:
            logger.error(f"Redis error: {e}")
            await asyncio.sleep(5)
