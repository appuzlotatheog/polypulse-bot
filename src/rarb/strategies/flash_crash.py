"""
Flash Crash Strategy for rarb.

Ported and modernized from polymarket-trading-bot.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, List, Dict
from datetime import datetime

from rarb.api.models import MarketSnapshot, Order
from rarb.bot import ArbitrageBot
from rarb.utils.logging import get_logger

log = get_logger(__name__)

@dataclass
class PriceEvent:
    side: str
    drop: float
    old_price: float
    new_price: float
    timestamp: float

class PriceTracker:
    """Tracks price history to detect flash crashes."""
    
    def __init__(self, history_size: int = 100, drop_threshold: float = 0.30):
        self.history_size = history_size
        self.drop_threshold = drop_threshold
        self.history: Dict[str, List[float]] = {"yes": [], "no": []}
        
    def record(self, side: str, price: float):
        if not price:
            return
        
        self.history[side].append(price)
        if len(self.history[side]) > self.history_size:
            self.history[side].pop(0)
            
    def detect_flash_crash(self) -> Optional[PriceEvent]:
        import time
        for side in ["yes", "no"]:
            if len(self.history[side]) < 5:
                continue
                
            # Simple logic: Compare current price to max in recent history
            current = self.history[side][-1]
            recent_max = max(self.history[side][-20:]) # Look at last 20 ticks
            
            if recent_max > 0:
                drop = recent_max - current
                if drop >= self.drop_threshold:
                    return PriceEvent(
                        side=side,
                        drop=drop,
                        old_price=recent_max,
                        new_price=current,
                        timestamp=time.time()
                    )
        return None

class FlashCrashStrategy:
    """
    Flash Crash Trading Strategy.
    
    Monitors markets for sudden probability drops and executes buys.
    """
    
    def __init__(self, bot: ArbitrageBot, drop_threshold: float = 0.30):
        self.bot = bot
        self.prices = PriceTracker(drop_threshold=drop_threshold)
        
    async def on_snapshot(self, snapshot: MarketSnapshot):
        """Process a market snapshot."""
        # Record prices
        yes_price = float(snapshot.yes_best_ask or 0)
        no_price = float(snapshot.no_best_ask or 0)
        
        self.prices.record("yes", yes_price)
        self.prices.record("no", no_price)
        
        # Check for crash
        event = self.prices.detect_flash_crash()
        if event:
            log.info(
                f"FLASH CRASH DETECTED: {event.side.upper()}",
                drop=f"{event.drop:.2f}",
                price=f"{event.old_price:.2f} -> {event.new_price:.2f}"
            )
            
            # Execute trade logic here (buy the dip)
            # This would integrate with bot.executor
            # For now, just log it as the original code did
            
            # Example:
            # await self.bot.executor.execute_market_buy(...)
