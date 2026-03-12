"""Main bot orchestration."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any, Callable

from rarb.api.models import ArbitrageOpportunity
from rarb.config import get_settings
from rarb.executor.executor import ExecutionResult, ExecutionStatus, OrderExecutor
from rarb.notifications.slack import get_notifier
from rarb.scanner.market_scanner import MarketScanner, MarketSnapshot
from rarb.utils.logging import get_logger

log = get_logger(__name__)

@dataclass
class BotStats:
    """Runtime statistics for the bot."""
    started_at: datetime = field(default_factory=datetime.utcnow)
    opportunities_found: int = 0
    trades_executed: int = 0
    total_profit: Decimal = Decimal("0")

class ArbitrageBot:
    def __init__(
        self,
        scanner: Optional[MarketScanner] = None,
        analyzer: Optional[Any] = None,
        executor: Optional[OrderExecutor] = None,
        reporting_callback: Optional[Callable[[str, str], Any]] = None,
    ) -> None:
        settings = get_settings()
        self.scanner = scanner or MarketScanner(min_liquidity=settings.min_liquidity_usd)
        
        if analyzer:
            self.analyzer = analyzer
        elif settings.analyzer_type.lower() != "standard":
            from rarb.analyzer.ai_analyzer import AIAnalyzer
            self.analyzer = AIAnalyzer(reporting_callback=reporting_callback)
            log.info(f"Using AI Analyzer ({settings.analyzer_type})")
        else:
            from rarb.analyzer.arbitrage import ArbitrageAnalyzer
            self.analyzer = ArbitrageAnalyzer()
            log.info("Using Standard Arbitrage Analyzer")

        self.executor = executor or OrderExecutor()
        self.stats = BotStats()
        self._pending_opportunities: list[ArbitrageOpportunity] = []

    async def process_snapshot(self, snapshot: MarketSnapshot) -> None:
        """Process a market snapshot and find opportunities."""
        opportunity = await self.analyzer.analyze(snapshot)
        if opportunity:
            self.stats.opportunities_found += 1
            self._pending_opportunities.append(opportunity)

    async def execute_opportunities(self) -> list[ExecutionResult]:
        """Execute all pending opportunities."""
        results = []
        if not self._pending_opportunities:
            return results

        # Execute top opportunity
        opportunity = self._pending_opportunities.pop(0)
        result = await self.executor.execute(opportunity)
        results.append(result)
        
        if result.status == ExecutionStatus.FILLED:
            self.stats.trades_executed += 1
            self.stats.total_profit += result.expected_profit
            
        return results

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.scanner.close()
