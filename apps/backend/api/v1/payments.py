"""
Paystack webhook handler.
Paystack sends POST to /payments/webhook on payment events.
Signature verified with HMAC-SHA512.
"""
import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import get_settings
from database import get_db
from services.subscription_service import activate_subscription, record_payment
from models.user import User

logger = logging.getLogger("payments")
router = APIRouter(prefix="/payments", tags=["payments"])
settings = get_settings()

# Map Paystack plan codes/amounts to our plan names
AMOUNT_TO_PLAN: dict[int, str] = {
    4900: "starter",   # $49 in USD cents (Paystack uses kobo for NGN)
    9900: "pro",
    19900: "elite",
}


def _verify_paystack_signature(body: bytes, signature: str) -> bool:
    secret = settings.paystack_secret_key.encode()
    computed = hmac.new(secret, body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(computed, signature)


@router.post("/webhook")
async def paystack_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    body = await request.body()
    signature = request.headers.get("x-paystack-signature", "")

    if settings.app_env != "development" and not _verify_paystack_signature(body, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = event.get("event")
    data = event.get("data", {})

    if event_type == "charge.success":
        email = data.get("customer", {}).get("email", "").lower()
        amount = data.get("amount", 0)  # in kobo (NGN) or cents (USD)
        reference = data.get("reference", "")
        metadata = data.get("metadata", {})
        plan_name = metadata.get("plan_name") or _infer_plan_from_amount(amount)

        if not plan_name:
            logger.warning(f"Unknown plan for amount {amount}")
            return {"status": "ignored"}

        # Look up user by email
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            logger.warning(f"User not found for email {email}")
            return {"status": "ignored"}

        # Record payment
        await record_payment(
            db=db,
            user_id=user.id,
            amount=amount / 100,
            provider="paystack",
            transaction_id=reference,
            plan_name=plan_name,
            status="success",
        )

        # Activate subscription
        await activate_subscription(db, user.id, plan_name)
        await db.commit()

        logger.info(f"Activated {plan_name} for {email}")
        return {"status": "ok"}

    return {"status": "ignored"}


def _infer_plan_from_amount(amount_kobo: int) -> str | None:
    # Paystack stores in smallest currency unit
    # Check by USD equivalent (amount / 100 USD)
    usd_cents = amount_kobo
    return AMOUNT_TO_PLAN.get(usd_cents)
