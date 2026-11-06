"""
FastAPI Server for ETF-t Agentic Paper Trading Web Cockpit.
Provides real-time WebSockets, REST endpoints, and automated background market execution.
"""

import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.engine.paper_engine import PaperTradingEngine
from src.config import get_config

# Initialize engine & config
engine = PaperTradingEngine()
config = get_config()

# Active websocket clients
connected_clients: Set[WebSocket] = set()

# Background agent evaluation task
background_task = None


async def broadcast_status():
    """Broadcast latest state and price ticks to all connected web clients."""
    if not connected_clients:
        return

    try:
        state = engine.get_account_state()
        history = engine.get_equity_history(limit=50)
        logs = engine.get_recent_logs(limit=30)
        orders = engine.get_recent_orders(limit=20)

        payload = {
            "type": "TICK_UPDATE",
            "state": state,
            "history": history,
            "logs": logs,
            "orders": orders
        }

        # Send to all clients
        disconnected = set()
        for ws in connected_clients:
            try:
                await ws.send_json(payload)
            except Exception:
                disconnected.add(ws)

        for ws in disconnected:
            connected_clients.discard(ws)
    except Exception as e:
        print(f"[WARN] Error during broadcast: {e}")


async def agent_autonomous_loop():
    """Autonomous loop: checks stop losses every 5s, rebalances periodically."""
    print("[*] Autonomous agent background loop started.")
    loop_count = 0
    while True:
        try:
            await asyncio.sleep(5)
            loop_count += 1

            # Check stop loss and profit targets on open positions every 5s
            engine.check_stop_losses_and_targets()

            # Every 60 seconds (12 ticks of 5s), trigger a market rebalance cycle
            if loop_count % 12 == 0:
                engine.run_rebalance_cycle()

            # Broadcast real-time state to browser
            await broadcast_status()

        except asyncio.CancelledError:
            print("[*] Agent autonomous loop stopped.")
            break
        except Exception as e:
            print(f"[ERROR] Autonomous loop exception: {e}")
            await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Run initial cycle and launch background worker
    engine.log_agent_thought("Agent server booted. Connecting to live paper trading engine...")
    engine.run_rebalance_cycle()
    
    global background_task
    background_task = asyncio.create_task(agent_autonomous_loop())
    yield
    # Shutdown
    if background_task:
        background_task.cancel()


app = FastAPI(title="ETF-t: Agentic Paper Trading Cockpit", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the single-page dashboard HTML."""
    index_path = WEB_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h1>Dashboard index.html not found</h1>", status_code=404)
    return FileResponse(index_path)


@app.get("/api/status")
async def get_status():
    """Retrieve full portfolio status and open positions."""
    return engine.get_account_state()


@app.get("/api/history")
async def get_history(limit: int = 100):
    """Retrieve equity snapshots for the chart."""
    return engine.get_equity_history(limit=limit)


@app.get("/api/orders")
async def get_orders(limit: int = 50):
    """Retrieve recent executed order fills."""
    return engine.get_recent_orders(limit=limit)


@app.get("/api/logs")
async def get_logs(limit: int = 50):
    """Retrieve agent decision stream logs."""
    return engine.get_recent_logs(limit=limit)


@app.post("/api/cycle")
async def trigger_cycle():
    """Manually trigger an immediate quantitative rebalance cycle."""
    updated = engine.run_rebalance_cycle()
    await broadcast_status()
    return {"status": "SUCCESS", "message": "Rebalance cycle executed", "state": updated}


@app.post("/api/liquidate")
async def trigger_liquidate():
    """Emergency liquidate all open positions to cash."""
    updated = engine.liquidate_all(reason="MANUAL_WEB_OVERRIDE")
    await broadcast_status()
    return {"status": "SUCCESS", "message": "All positions liquidated to cash", "state": updated}


class ResetRequest(BaseModel):
    balance: float = 100.0


@app.post("/api/reset")
async def reset_account(req: ResetRequest):
    """Reset paper account balance back to clean starting balance."""
    updated = engine.reset_account(new_balance=req.balance)
    await broadcast_status()
    return {"status": "SUCCESS", "message": f"Account reset to ${req.balance:.2f}", "state": updated}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Live streaming websocket connection for real-time browser updates."""
    await websocket.accept()
    connected_clients.add(websocket)
    
    # Send immediate snapshot on connect
    try:
        state = engine.get_account_state()
        history = engine.get_equity_history(limit=50)
        logs = engine.get_recent_logs(limit=30)
        orders = engine.get_recent_orders(limit=20)
        await websocket.send_json({
            "type": "INITIAL_STATE",
            "state": state,
            "history": history,
            "logs": logs,
            "orders": orders
        })

        # Keep connection open and listen for client commands
        while True:
            data = await websocket.receive_text()
            if data == "PING":
                await websocket.send_text("PONG")
            elif data == "CYCLE":
                engine.run_rebalance_cycle()
                await broadcast_status()

    except WebSocketDisconnect:
        connected_clients.discard(websocket)
    except Exception:
        connected_clients.discard(websocket)

