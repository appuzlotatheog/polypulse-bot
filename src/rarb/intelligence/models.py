"""Data models for intelligence and scouting."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict, Any

class SentimentSource(Enum):
    TWITTER = "twitter"
    NEWS = "news"
    CRYPTO = "crypto"
    MANUAL = "manual"

class SentimentPolarity(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    UNCERTAIN = "uncertain"

@dataclass
class SentimentSignal:
    """A discrete signal from an intelligence source."""
    source: SentimentSource
    polarity: SentimentPolarity
    confidence: float  # 0.0 to 1.0
    summary: str
    url: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RiskScore:
    """Global or market-specific risk assessment."""
    level: int  # 1-10 (10 = extreme risk)
    reason: str
    factors: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class CryptoPrice:
    """Real-time crypto asset price."""
    symbol: str  # e.g., BTC/USDT
    price: Decimal
    change_24h: float
    volume_24h: float
    exchange: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class IntelligenceReport:
    """Aggregated intelligence report for a specific market."""
    market_id: str
    signals: List[SentimentSignal]
    risk_score: Optional[RiskScore] = None
    related_crypto: Optional[CryptoPrice] = None
    verdict: str = "NEUTRAL"
    timestamp: datetime = field(default_factory=datetime.utcnow)
