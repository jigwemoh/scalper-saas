"""
Simple shared-secret middleware for the MT5 bridge.
All requests must include: X-Bridge-Secret: <secret>
Set MT5_BRIDGE_SECRET env variable on the Windows VPS.
"""
import os
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

BRIDGE_SECRET = os.getenv("MT5_BRIDGE_SECRET", "dev-bridge-secret")

# Paths that don't require auth (health checks)
PUBLIC_PATHS = {"/health", "/", "/docs", "/openapi.json", "/redoc", "/api/health/system"}


class BridgeAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        secret = request.headers.get("X-Bridge-Secret", "")
        if secret != BRIDGE_SECRET:
            raise HTTPException(status_code=401, detail="Invalid bridge secret")

        return await call_next(request)
