"""Intelligence layer for active scouting and market research.

This module provides "Observer" services that can be used by the AIAnalyzer
and strategies to gather external data:
- BrowserScout: Web browsing and news verification
- XPulse: X (Twitter) sentiment monitoring
- MarketOracle: Crypto market data correlation
"""

from rarb.intelligence.browser_scout import BrowserScout, get_browser_scout
from rarb.intelligence.x_pulse import XPulse, get_x_pulse
from rarb.intelligence.market_oracle import MarketOracle, get_market_oracle
from rarb.intelligence.models import (
    SentimentSignal, RiskScore, CryptoPrice, IntelligenceReport,
    SentimentSource, SentimentPolarity
)

__all__ = [
    "BrowserScout",
    "get_browser_scout",
    "XPulse",
    "get_x_pulse",
    "MarketOracle",
    "get_market_oracle",
    "SentimentSignal",
    "RiskScore",
    "CryptoPrice",
    "IntelligenceReport",
    "SentimentSource",
    "SentimentPolarity",
]
