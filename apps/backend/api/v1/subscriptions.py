from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import get_current_user
from services.subscription_service import get_active_subscription, PLANS
from models.user import User

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/plans")
async def list_plans() -> list[dict]:
    return [
        {
            "name": name,
            "price_usd_monthly": details["price"],
            "risk_per_trade_pct": details["risk_pct"] * 100,
            "max_lots": details["max_lots"],
        }
        for name, details in PLANS.items()
    ]


@router.get("/me")
async def my_subscription(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    sub = await get_active_subscription(db, current_user.id)
    if not sub:
        return {"status": "none", "plan": None, "expires_at": None}
    return {
        "status": sub.status,
        "plan": sub.plan_name,
        "billing_cycle": sub.billing_cycle,
        "started_at": sub.started_at.isoformat() if sub.started_at else None,
        "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
    }
