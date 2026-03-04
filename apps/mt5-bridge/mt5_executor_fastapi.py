from typing import Optional, Literal, Any, Dict, cast
from datetime import datetime, timedelta, timezone
import logging
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    import MetaTrader5 as mt5  # type: ignore
except ImportError as e:  # pragma: no cover
    raise SystemExit("MetaTrader5 package is required on Windows with MT5 terminal running") from e

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
log = logging.getLogger("mt5-exec")

# Magic number identifies orders placed by this system; configurable per deployment
MT5_MAGIC_NUMBER = int(os.getenv("MT5_MAGIC_NUMBER", "20250101"))

app = FastAPI(title="MT5 Executor", version="0.2.0")


class ExecRequest(BaseModel):
    symbol: str
    direction: Literal["BUY", "SELL"]
    volume: float = Field(gt=0)
    entry_price: Optional[float] = None  # None => market order
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    comment: str = "API_EXECUTOR"


def ensure_init() -> bool:
    try:
        if mt5.initialize():  # type: ignore
            return True
        return False
    except Exception as exc:
        log.error("MT5 init failed: %s", exc)
        return False


def detect_filling(symbol_info: Any) -> int:
    # Only use supported filling modes for the symbol
    # Try FOK, then IOC, then RETURN, but only if supported
    allowed_modes = []
    if hasattr(symbol_info, "filling_mode"):
        filling_mode = getattr(symbol_info, "filling_mode")
        for mode in [getattr(mt5, "ORDER_FILLING_FOK", 0), getattr(mt5, "ORDER_FILLING_IOC", 1), getattr(mt5, "ORDER_FILLING_RETURN", 2)]:
            if filling_mode & (1 << mode):
                allowed_modes.append(mode)
    # Fallback to trade_fill_mode if no allowed modes found
    if allowed_modes:
        return allowed_modes[0]
    return int(getattr(symbol_info, "trade_fill_mode", getattr(mt5, "ORDER_FILLING_FOK", 0)))


def detect_order_type(direction: str, entry_price: Optional[float]) -> int:
    if entry_price is None:
        return mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL  # type: ignore
    return mt5.ORDER_TYPE_BUY_LIMIT if direction == "BUY" else mt5.ORDER_TYPE_SELL_LIMIT  # type: ignore


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/mt5/account")
def account() -> Dict[str, Any]:
    if not ensure_init():
        raise HTTPException(503, "MT5 init failed")
    info = mt5.account_info()  # type: ignore
    if not info:
        raise HTTPException(503, "MT5 account info not available")
    return {
        "equity": float(info.equity),  # type: ignore
        "balance": float(info.balance),  # type: ignore
        "margin_used": float(info.margin),  # type: ignore
        "margin_free": float(info.margin_free),  # type: ignore
        "margin_level": float(info.margin_level),  # type: ignore
        "leverage": float(getattr(info, "leverage", 0.0)),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/mt5/positions")
def positions() -> Any:
    if not ensure_init():
        raise HTTPException(503, "MT5 init failed")
    positions = mt5.positions_get()  # type: ignore
    if positions is None:
        return []
    out = []
    for p in positions:
        out.append({
            "ticket": int(p.ticket),  # type: ignore
            "symbol": str(p.symbol),  # type: ignore
            "type": int(getattr(p, "type", -1)),
            "volume": float(p.volume),  # type: ignore
            "price_open": float(p.price_open),  # type: ignore
            "price_current": float(p.price_current),  # type: ignore
            "profit": float(p.profit),  # type: ignore
            "sl": float(p.sl),  # type: ignore
            "tp": float(p.tp),  # type: ignore
            "time": int(p.time),  # type: ignore
        })
    return out


@app.get("/api/mt5/history_stats")
def history_stats(days: int = 365) -> Dict[str, Any]:
    if not ensure_init():
        raise HTTPException(503, "MT5 init failed")
    date_to = datetime.now()
    date_from = date_to - timedelta(days=days)
    deals = mt5.history_deals_get(date_from, date_to)  # type: ignore
    profits = []
    if deals:
        for d in deals:
            entry = int(getattr(d, "entry", 0))
            if entry == 1:  # DEAL_ENTRY_OUT
                profits.append(float(getattr(d, "profit", 0.0)))
    wins = [p for p in profits if p > 0]
    losses = [p for p in profits if p < 0]
    last_20 = profits[-20:] if len(profits) >= 20 else profits
    last_20_wins = sum(1 for p in last_20 if p > 0)
    last_20_win_rate = (last_20_wins / len(last_20)) if last_20 else 0.0
    return {
        "total_trades": len(profits),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "total_pnl": float(sum(profits)),
        "today_pnl": 0.0,  # optional to compute separately
        "last_20_win_rate": float(last_20_win_rate),
        "avg_win": float(sum(wins) / len(wins)) if wins else 0.0,
        "avg_loss": float(sum(losses) / len(losses)) if losses else 0.0,
    }


@app.post("/execute")
@app.post("/api/mt5/place_order")
@app.post("/api/mt5/send_order")
@app.post("/api/mt5/order")
@app.post("/api/send_order")
@app.post("/send_order")
async def execute_order(req: ExecRequest) -> Dict[str, Any]:
    if not ensure_init():
        return {"status": "error", "error": "MT5 init failed"}

    symbol_info: object = cast(object, mt5.symbol_info(req.symbol))  # type: ignore
    if symbol_info is None:
        return {"status": "error", "error": f"Symbol {req.symbol} not found"}

    # Make sure symbol is selected in Market Watch
    visible = bool(getattr(symbol_info, "visible", False))
    if not visible:
        mt5.symbol_select(req.symbol, True)  # type: ignore

    filling = detect_filling(symbol_info)
    order_type = detect_order_type(req.direction, req.entry_price)

    # Determine price
    if req.entry_price is None:
        price = float(getattr(symbol_info, "ask", 0.0)) if req.direction == "BUY" else float(getattr(symbol_info, "bid", 0.0))  # type: ignore
    else:
        price = float(req.entry_price)

    request: Dict[str, Any] = {
        "action": mt5.TRADE_ACTION_DEAL,  # type: ignore
        "symbol": req.symbol,
        "volume": float(req.volume),
        "type": order_type,
        "price": float(price),
        "deviation": 20,
        "magic": MT5_MAGIC_NUMBER,
        "comment": req.comment,
        "type_time": mt5.ORDER_TIME_GTC,  # type: ignore
        "type_filling": filling,
    }
    if req.stop_loss is not None:
        request["sl"] = float(req.stop_loss)
    if req.take_profit is not None:
        request["tp"] = float(req.take_profit)

    log.info("Sending order: %s", request)
    result: Any = mt5.order_send(request)  # type: ignore

    if result is None:
        err = mt5.last_error()  # type: ignore
        return {"status": "error", "error": f"order_send returned None: {err}"}

    if result.retcode != mt5.TRADE_RETCODE_DONE:  # type: ignore
        retcode = int(result.retcode)  # type: ignore
        comment = str(getattr(cast(Any, result), "comment", ""))
        log.error("Order rejected: retcode=%d comment=%s symbol=%s direction=%s", retcode, comment, req.symbol, req.direction)
        return {
            "status": "error",
            "retcode": retcode,
            "comment": comment,
            "symbol": req.symbol,
            "direction": req.direction,
            "volume": req.volume,
        }

    return {
        "status": "executed",
        "ticket": result.order,  # type: ignore
        "symbol": req.symbol,
        "direction": req.direction,
        "volume": req.volume,
        "price": float(price),
        "filling": filling,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
