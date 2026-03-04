import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.subscription import Subscription, Payment
from models.user import User

PLANS = {
    "starter": {"price": 49.0, "risk_pct": 0.005, "max_lots": 0.1},
    "pro": {"price": 99.0, "risk_pct": 0.015, "max_lots": 1.0},
    "elite": {"price": 199.0, "risk_pct": 0.025, "max_lots": 5.0},
}


async def get_active_subscription(db: AsyncSession, user_id: uuid.UUID) -> Subscription | None:
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.status == "active",
            Subscription.expires_at > datetime.now(timezone.utc),
        )
    )
    return result.scalar_one_or_none()


async def activate_subscription(
    db: AsyncSession,
    user_id: uuid.UUID,
    plan_name: str,
    billing_cycle: str = "monthly",
) -> Subscription:
    plan = PLANS.get(plan_name.lower())
    if plan is None:
        raise ValueError(f"Unknown plan: {plan_name}")

    days = 30 if billing_cycle == "monthly" else 365
    now = datetime.now(timezone.utc)

    # Cancel any existing active subscription
    existing = await get_active_subscription(db, user_id)
    if existing:
        existing.status = "cancelled"  # type: ignore[assignment]

    sub = Subscription(
        user_id=user_id,
        plan_name=plan_name.lower(),
        price=plan["price"],
        billing_cycle=billing_cycle,
        status="active",
        started_at=now,
        expires_at=now + timedelta(days=days),
    )
    db.add(sub)
    await db.flush()
    return sub


async def record_payment(
    db: AsyncSession,
    user_id: uuid.UUID,
    amount: float,
    provider: str,
    transaction_id: str,
    plan_name: str,
    status: str = "success",
) -> Payment:
    payment = Payment(
        user_id=user_id,
        amount=amount,
        payment_provider=provider,
        provider_transaction_id=transaction_id,
        status=status,
        plan_name=plan_name,
    )
    db.add(payment)
    await db.flush()
    return payment


def get_risk_pct_for_plan(plan_name: str) -> float:
    plan = PLANS.get(plan_name.lower(), PLANS["starter"])
    return plan["risk_pct"]
