from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from dependencies import get_current_user
from models.user import User
from models.mt5_account import MT5Account
from services.mt5_bridge_client import get_account_info

router = APIRouter(prefix="/accounts", tags=["accounts"])


class LinkAccountRequest(BaseModel):
    broker_name: str
    account_number: str
    server_name: str
    leverage: int = 100
    risk_profile: str = "balanced"  # starter | balanced | aggressive


@router.post("/link", status_code=201)
async def link_account(
    req: LinkAccountRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    account = MT5Account(
        user_id=current_user.id,
        broker_name=req.broker_name,
        account_number=req.account_number,
        server_name=req.server_name,
        leverage=req.leverage,
        risk_profile=req.risk_profile,
    )
    db.add(account)
    await db.commit()
    return {"id": str(account.id), "message": "Account linked successfully"}


@router.get("/")
async def list_accounts(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    result = await db.execute(
        select(MT5Account).where(MT5Account.user_id == current_user.id)
    )
    accounts = result.scalars().all()
    return [_account_dict(a) for a in accounts]


@router.get("/{account_id}/live")
async def live_account_data(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    result = await db.execute(
        select(MT5Account).where(
            MT5Account.id == account_id,
            MT5Account.user_id == current_user.id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    live_data = await get_account_info()
    return {
        "account": _account_dict(account),
        "live": live_data,
    }


def _account_dict(a: MT5Account) -> dict:
    return {
        "id": str(a.id),
        "broker_name": a.broker_name,
        "account_number": a.account_number,
        "server_name": a.server_name,
        "leverage": a.leverage,
        "account_balance": float(a.account_balance) if a.account_balance else None,
        "account_equity": float(a.account_equity) if a.account_equity else None,
        "risk_profile": a.risk_profile,
        "is_active": a.is_active,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
