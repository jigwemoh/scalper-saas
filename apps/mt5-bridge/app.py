import os
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, cast
import asyncio

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from bridge_auth import BridgeAuthMiddleware
from candle_endpoint import router as candle_router

# Try to import MetaTrader5 (available on Windows)
try:
    import MetaTrader5 as mt5  # type: ignore
    mt5_available = True
except ImportError:
    mt5 = None  # type: ignore
    mt5_available = False

logger = logging.getLogger("mt5_bridge")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

# Global state
_initialized = False
MT5_LOGIN = os.getenv("MT5_LOGIN")
MT5_PASSWORD = os.getenv("MT5_PASSWORD")
MT5_SERVER = os.getenv("MT5_SERVER")

# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Start background task on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    asyncio.create_task(poll_mt5_updates())
    yield
    # Shutdown (if needed)

app = FastAPI(title="MT5 Bridge", version="0.2.0", lifespan=lifespan)

# Auth middleware — all non-health requests require X-Bridge-Secret header
app.add_middleware(BridgeAuthMiddleware)

# CORS configuration (adjust origins for your frontend/backend hosts)
origins = os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000,http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()],  # type: ignore
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include candle data endpoint
app.include_router(candle_router)


def _connect() -> bool:
    """Initialize MT5. Try plain init, then with credentials if provided."""
    global _initialized
    if not mt5_available or mt5 is None:
        logger.error("MetaTrader5 Python module not available on this host.")
        return False
    if _initialized:
        return True
    try:
        ok_raw: Any = mt5.initialize()  # type: ignore
        ok: bool = cast(bool, ok_raw)
        if not ok and all([MT5_LOGIN, MT5_PASSWORD, MT5_SERVER]):
            # Type assertions for Pylance
            login = int(str(MT5_LOGIN))
            password = str(MT5_PASSWORD)
            server = str(MT5_SERVER)
            ok_raw2: Any = mt5.initialize(server=server, login=login, password=password)  # type: ignore
            ok = cast(bool, ok_raw2)
        _initialized = ok
        if not ok:
            try:
                err = mt5.last_error()  # type: ignore
                logger.error(f"MT5 initialize failed: last_error={err}")
            except Exception:
                logger.error("MT5 initialize failed and last_error unavailable.")
        else:
            try:
                ver = mt5.version()  # type: ignore
                term = mt5.terminal_info()  # type: ignore
                logger.info(f"MT5 initialized. version={ver}, terminal_info={term}")
            except Exception:
                logger.info("MT5 initialized.")
        return _initialized
    except Exception as e:
        logger.exception(f"MT5 initialize error: {e}")
        return False


@app.get("/api/health/system")
def health() -> Dict[str, Any]:
    return {
        "mt5_available": mt5_available,
        "initialized": _initialized,
    }


@app.get("/api/mt5/account")
def account() -> Dict[str, float]:
    if not _connect():
        raise HTTPException(status_code=503, detail="MT5 not available or not initialized")
    info = mt5.account_info()  # type: ignore
    if not info:
        raise HTTPException(status_code=503, detail="MT5 account info unavailable")
    return {
        "equity": float(info.equity),  # type: ignore
        "balance": float(info.balance),  # type: ignore
        "margin_used": float(info.margin),  # type: ignore
        "margin_free": float(info.margin_free),  # type: ignore
        "margin_level": float(info.margin_level),  # type: ignore
        "leverage": float(getattr(info, "leverage", 0.0)),  # type: ignore
    }


@app.get("/api/mt5/positions")
def positions() -> List[Dict[str, Any]]:
    if not _connect():
        raise HTTPException(status_code=503, detail="MT5 not available or not initialized")
    positions = mt5.positions_get()  # type: ignore
    if positions is None:
        return []
    result: List[Dict[str, Any]] = []
    for p in positions:  # type: ignore
        result.append({
            "ticket": int(p.ticket),  # type: ignore
            "symbol": str(p.symbol),  # type: ignore
            "volume": float(p.volume),  # type: ignore
            "price_open": float(p.price_open),  # type: ignore
            "price_current": float(p.price_current),  # type: ignore
            "profit": float(p.profit),  # type: ignore
            "sl": float(p.sl),  # type: ignore
            "tp": float(p.tp),  # type: ignore
            "time": int(p.time),  # type: ignore
        })
    return result


@app.get("/api/mt5/history_stats")
def history_stats(days: int = 365) -> Dict[str, Any]:
    if not _connect():
        raise HTTPException(status_code=503, detail="MT5 not available or not initialized")
    date_to = datetime.now()
    date_from = date_to - timedelta(days=days)
    deals = mt5.history_deals_get(date_from, date_to)  # type: ignore
    if deals is None:
        # No history is a valid case
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "today_pnl": 0.0,
            "last_20_win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
        }
    profits: List[float] = []
    for d in deals:  # type: ignore
        profit = float(getattr(d, "profit", 0.0))  # type: ignore
        entry = int(getattr(d, "entry", 0))  # type: ignore
        # DEAL_ENTRY_OUT = 1 per MT5 docs
        if entry == 1:
            profits.append(profit)

    # Today's PnL
    today_start = datetime.combine(datetime.today(), datetime.min.time())
    today_end = datetime.combine(datetime.today(), datetime.max.time())
    today_deals = mt5.history_deals_get(today_start, today_end)  # type: ignore
    today_pnl = 0.0
    if today_deals:
        for d in today_deals:  # type: ignore
            entry = int(getattr(d, "entry", 0))  # type: ignore
            if entry == 1:
                today_pnl += float(getattr(d, "profit", 0.0))  # type: ignore

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
        "today_pnl": float(today_pnl),
        "last_20_win_rate": float(last_20_win_rate),
        "avg_win": float(sum(wins) / len(wins)) if wins else 0.0,
        "avg_loss": float(sum(losses) / len(losses)) if losses else 0.0,
    }


# Convenience root
@app.get("/")
def root() -> Dict[str, Any]:
    return {"status": "ok", "mt5_available": mt5_available, "initialized": _initialized}


# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; updates are broadcasted from background task
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Background task to poll MT5 and broadcast updates
async def poll_mt5_updates():
    previous_account = None
    previous_positions = None
    while True:
        try:
            if not _connect():
                await asyncio.sleep(5)
                continue

            # Check account info
            account_info = mt5.account_info()  # type: ignore
            if account_info:
                current_account = {
                    "equity": float(account_info.equity),  # type: ignore
                    "balance": float(account_info.balance),  # type: ignore
                    "margin_used": float(account_info.margin),  # type: ignore
                    "margin_free": float(account_info.margin_free),  # type: ignore
                    "margin_level": float(account_info.margin_level),  # type: ignore
                    "leverage": float(getattr(account_info, "leverage", 0.0)),  # type: ignore
                }
                if previous_account != current_account:
                    await manager.broadcast({"type": "account_update", "data": current_account})
                    previous_account = current_account

            # Check positions
            positions = mt5.positions_get()  # type: ignore
            if positions is not None:
                current_positions: List[Dict[str, Any]] = []
                for p in positions:  # type: ignore
                    current_positions.append({
                        "ticket": int(p.ticket),  # type: ignore
                        "symbol": str(p.symbol),  # type: ignore
                        "volume": float(p.volume),  # type: ignore
                        "price_open": float(p.price_open),  # type: ignore
                        "price_current": float(p.price_current),  # type: ignore
                        "profit": float(p.profit),  # type: ignore
                        "sl": float(p.sl),  # type: ignore
                        "tp": float(p.tp),  # type: ignore
                        "time": int(p.time),  # type: ignore
                    })
                if previous_positions != current_positions:
                    await manager.broadcast({"type": "positions_update", "data": current_positions})
                    previous_positions = current_positions

        except Exception as e:
            logger.error(f"Error polling MT5: {e}")

        await asyncio.sleep(1)  # Poll every second
