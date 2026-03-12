"""FastAPI dashboard for rarb."""

import os
import csv
from typing import List, Dict
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from rarb.config import get_settings
from rarb.utils.logging import get_logger

log = get_logger(__name__)
app = FastAPI(title="rarb Dashboard")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

def get_trade_history() -> List[Dict]:
    """Read trade history from CSV."""
    trades = []
    log_file = "trades_performance.csv"
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            reader = csv.DictReader(f)
            trades = list(reader)
    # Return latest 20 trades
    return trades[-20:][::-1]

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    settings = get_settings()
    trades = get_trade_history()
    
    total_trades = len(trades)
    avg_profit = 0
    total_pnl = 0
    if total_trades > 0:
        try:
            profits = [float(t['Profit %'].replace('%', '').replace('+', '')) for t in trades if t.get('Profit %')]
            avg_profit = sum(profits) / len(profits) if profits else 0
            pnls = [float(t['P&L ($)'].replace('$', '').replace('+', '')) for t in trades if t.get('P&L ($)')]
            total_pnl = sum(pnls)
        except Exception as e:
            log.debug(f"Error calculating stats: {e}")

    return templates.TemplateResponse("index.html", {
        "request": request,
        "settings": settings,
        "trades": trades,
        "stats": {
            "total_trades": total_trades,
            "avg_profit": f"{avg_profit:+.2f}%",
            "total_pnl": f"${total_pnl:+.2f}",
            "mode": "Dry Run" if settings.dry_run else "LIVE",
            "analyzer": settings.analyzer_type
        }
    })

@app.get("/api/stats")
async def get_stats():
    """API endpoint for real-time chart data."""
    # In a real app, this would return live market metrics
    import random
    return {
        "labels": ["10m ago", "8m ago", "6m ago", "4m ago", "2m ago", "Now"],
        "profit_spread": [random.uniform(0.1, 1.5) for _ in range(6)],
        "liquidity": [random.uniform(0.4, 1.2) for _ in range(6)]
    }

def run_dashboard(host: str = "0.0.0.0", port: int = 8080):
    import uvicorn
    log.info(f"Starting dashboard on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
