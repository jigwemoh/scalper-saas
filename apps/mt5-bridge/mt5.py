from typing import Any, Dict, Optional, Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from api.services.mt5_service import mt5_service

router = APIRouter(prefix="/mt5", tags=["mt5"])


class OrderRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol, e.g. EURUSD")
    direction: Literal["BUY", "SELL"] = Field(..., description="BUY or SELL")
    volume: float = Field(..., gt=0, description="Lot size")
    entry_price: Optional[float] = Field(default=None, description="Limit price; None for market")
    stop_loss: Optional[float] = Field(default=None)
    take_profit: Optional[float] = Field(default=None)


@router.get("/account")
def get_account() -> Dict[str, Any]:
    info = mt5_service.get_account_info()
    if info is None:
        raise HTTPException(status_code=503, detail="MT5 account info not available")
    info_out: Dict[str, Any] = dict(info)
    info_out["timestamp"] = datetime.now(timezone.utc).isoformat()
    return info_out


@router.get("/positions")
def get_positions() -> Dict[str, Any]:
    positions = mt5_service.get_positions()
    if positions is None:
        raise HTTPException(status_code=503, detail="MT5 positions not available")
    return {"count": len(positions), "positions": positions}


@router.get("/orders")
def get_orders() -> Dict[str, Any]:
    orders = mt5_service.get_orders()
    if orders is None:
        raise HTTPException(status_code=503, detail="MT5 orders not available")
    return {"count": len(orders), "orders": orders}


@router.get("/history")
def get_history() -> Dict[str, Any]:
    stats = mt5_service.get_history_stats(days=365)
    if stats is None:
        raise HTTPException(status_code=503, detail="MT5 trade history not available")
    return stats


@router.post("/place_order")
@router.post("/send_order")  # alias for bridge compatibility
def place_order(req: OrderRequest) -> Dict[str, Any]:
    """Place a market or limit order through the configured MT5 service/bridge."""
    try:
        result = mt5_service.place_order(
            symbol=req.symbol,
            direction=req.direction,
            volume=req.volume,
            entry_price=req.entry_price,
            sl=req.stop_loss,
            tp=req.take_profit,
        )
        if result is None:
            raise HTTPException(status_code=502, detail="MT5 order placement failed")
        return result
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - runtime errors surfaced to client
        raise HTTPException(status_code=500, detail=f"Order placement error: {exc}")
