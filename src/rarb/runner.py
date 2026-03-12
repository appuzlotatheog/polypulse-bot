"""Main entry points for the bot."""

import asyncio
import logging
import os
import sys
import time
import threading
from datetime import datetime, timezone
from typing import Optional

from rarb.bot import ArbitrageBot
from rarb.config import get_settings
from rarb.utils.logging import get_logger, setup_logging

log = get_logger(__name__)


class BotState:
    """Shared state for the dashboard."""
    
    def __init__(self):
        self.balance: float = 10000.0
        self.pnl: float = 0.0
        self.trades: int = 0
        self.buys: int = 0
        self.sells: int = 0
        self.volume: float = 0.0
        self.markets: int = 0
        self.opportunities: int = 0
        self.alerts: int = 0
        self.status: str = "Running"
        self.opportunities_list = []
        self.positions_list = []
    
    def add_trade(self, side: str, amount: float):
        self.trades += 1
        if side.upper() in ["YES", "BUY"]:
            self.buys += 1
        else:
            self.sells += 1
        self.volume += amount
    
    def add_opportunity(self, market: str, yes_price: float, no_price: float, profit_pct: float):
        self.opportunities += 1
        self.opportunities_list.append({
            "market": market,
            "yes_price": yes_price,
            "no_price": no_price,
            "profit_pct": profit_pct,
        })
        if len(self.opportunities_list) > 10:
            self.opportunities_list = self.opportunities_list[-10:]


_bot_state = BotState()


def get_bot_state() -> BotState:
    return _bot_state


def setup_logging(quiet: bool = False):
    """Setup logging - logs go to file, not console."""
    settings = get_settings()
    
    # Clear existing handlers
    root = logging.getLogger()
    root.handlers = []
    
    # File handler only
    fh = logging.FileHandler('rarb.log', mode='a')
    fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    fh.setLevel(logging.DEBUG)
    root.addHandler(fh)
    
    # Console handler only if not quiet
    if not quiet:
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(logging.Formatter('%(message)s'))
        ch.setLevel(logging.WARNING)  # Only warnings and above to console
        root.addHandler(ch)
    
    root.setLevel(logging.DEBUG)
    
    # Suppress noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


async def run_realtime_bot() -> None:
    """Entry point for running the real-time bot with dashboard."""
    settings = get_settings()
    setup_logging(quiet=False)
    
    # Start dashboard in background thread
    from rarb.dashboard.display import start as start_dashboard
    dash_thread = threading.Thread(target=start_dashboard, daemon=True)
    dash_thread.start()
    
    async with ArbitrageBot() as bot:
        bot.scanner.on_snapshot(bot.process_snapshot)
        
        log.info("Starting real-time bot...")
        _bot_state.markets = 17
        
        while True:
            if hasattr(bot, 'stats'):
                _bot_state.opportunities = bot.stats.opportunities_found
                _bot_state.trades = bot.stats.trades_executed
            
            await bot.execute_opportunities()
            
            for opp in bot._pending_opportunities[:5]:
                _bot_state.add_opportunity(
                    opp.market.question,
                    float(opp.yes_ask) if opp.yes_ask else 0,
                    float(opp.no_ask) if opp.no_ask else 0,
                    opp.profit_pct
                )
            
            await asyncio.sleep(0.5)


async def run_bot() -> None:
    """Entry point for polling mode."""
    settings = get_settings()
    setup_logging(quiet=False)
    
    # Start dashboard
    from rarb.dashboard.display import start as start_dashboard
    dash_thread = threading.Thread(target=start_dashboard, daemon=True)
    dash_thread.start()
    
    async with ArbitrageBot() as bot:
        while True:
            await bot.scanner.run_once()
            await bot.execute_opportunities()
            await asyncio.sleep(settings.poll_interval_seconds)
