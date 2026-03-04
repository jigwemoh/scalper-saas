from fastapi import APIRouter

from api.v1.auth import router as auth_router
from api.v1.signals import router as signals_router
from api.v1.trades import router as trades_router
from api.v1.accounts import router as accounts_router
from api.v1.risk import router as risk_router
from api.v1.subscriptions import router as subscriptions_router
from api.v1.payments import router as payments_router
from api.v1.webhook import router as webhook_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(signals_router)
api_router.include_router(trades_router)
api_router.include_router(accounts_router)
api_router.include_router(risk_router)
api_router.include_router(subscriptions_router)
api_router.include_router(payments_router)
api_router.include_router(webhook_router)
