"""Position tracking and management."""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional
from enum import Enum
from rarb.api.models import Market
from rarb.utils.logging import get_logger

log = get_logger(__name__)

class PositionSide(Enum):
    YES = "YES"
    NO = "NO"

class Position:
    def __init__(self, id: str, market: Market, side: PositionSide, token_id: str, price: Decimal, size: Decimal, order_id: str):
        self.id = id
        self.market = market
        self.side = side
        self.token_id = token_id
        self.price = price
        self.size = size
        self.order_id = order_id
        self.opened_at = datetime.now(timezone.utc)
        self.status = "OPEN"

class PositionManager:
    """Manages active trading positions."""

    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self._counter = 0

    async def open_position(self, market: Market, side: PositionSide, token_id: str, price: Decimal, size: Decimal, order_id: str) -> Position:
        """Track a new open position."""
        self._counter += 1
        pos_id = f"pos_{self._counter}_{int(datetime.now().timestamp())}"
        position = Position(pos_id, market, side, token_id, price, size, order_id)
        self.positions[pos_id] = position
        log.info(f"Position opened: {pos_id} | {market.question[:30]} | {side.value} | {price}")
        return position

    async def get_active_positions(self) -> List[Position]:
        """Return list of currently open positions."""
        return [p for p in self.positions.values() if p.status == "OPEN"]

_manager = None

def get_position_manager() -> PositionManager:
    """Global singleton for PositionManager."""
    global _manager
    if _manager is None:
        _manager = PositionManager()
    return _manager
