"""Data models for Polymarket API."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

@dataclass
class Token:
    """Represents a token (YES or NO) in a market."""
    token_id: str
    symbol: str
    outcome: str

@dataclass
class Market:
    """Represents a Polymarket prediction market."""
    id: str
    question: str
    yes_token: Token
    no_token: Token
    liquidity: float = 0.0
    volume: float = 0.0
    end_date: Optional[datetime] = None
    neg_risk: bool = False
    yes_price: Optional[Decimal] = None
    no_price: Optional[Decimal] = None

    @property
    def days_until_resolution(self) -> int:
        if not self.end_date:
            return 999
        delta = self.end_date - datetime.utcnow()
        return max(0, delta.days)

@dataclass
class Order:
    """Represents an order on the order book."""
    price: Decimal
    size: Decimal

@dataclass
class OrderBook:
    """Represents a collection of bids and asks for a token."""
    bids: List[Order] = field(default_factory=list)
    asks: List[Order] = field(default_factory=list)

    @property
    def best_bid(self) -> Optional[Decimal]:
        """Get the highest bid price."""
        if not self.bids:
            return None
        return max(o.price for o in self.bids)

    @property
    def best_ask(self) -> Optional[Decimal]:
        """Get the lowest ask price."""
        if not self.asks:
            return None
        return min(o.price for o in self.asks)

    @property
    def best_ask_size(self) -> Optional[Decimal]:
        """Get the size at the lowest ask price."""
        if not self.asks:
            return None
        best_ask = self.best_ask
        if best_ask is None:
            return None
        total = sum(o.size for o in self.asks if o.price == best_ask)
        return Decimal(str(total)) if total else None

@dataclass
class MarketSnapshot:
    """A snapshot of a market with current orderbook data."""
    market: Market
    yes_orderbook: OrderBook
    no_orderbook: OrderBook

    @property
    def yes_best_ask(self) -> Optional[Decimal]:
        return self.yes_orderbook.best_ask

    @property
    def no_best_ask(self) -> Optional[Decimal]:
        return self.no_orderbook.best_ask

    @property
    def combined_ask(self) -> Optional[Decimal]:
        if self.yes_best_ask is None or self.no_best_ask is None:
            return None
        return self.yes_best_ask + self.no_best_ask

    @property
    def min_liquidity_at_ask(self) -> Optional[Decimal]:
        yes_size = self.yes_orderbook.best_ask_size
        no_size = self.no_orderbook.best_ask_size
        if yes_size is None or no_size is None:
            return None
        return min(yes_size, no_size)

@dataclass
class ArbitrageOpportunity:
    """Represents a detected arbitrage opportunity."""
    market: Market
    yes_ask: Optional[Decimal] = None
    no_ask: Optional[Decimal] = None
    combined_cost: Optional[Decimal] = None
    profit_pct: float = 0.0
    expected_profit: Decimal = Decimal("0")
    max_size: Decimal = Decimal("0")
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def max_trade_size(self) -> Decimal:
        """Alias for max_size for CLI compatibility."""
        return self.max_size
