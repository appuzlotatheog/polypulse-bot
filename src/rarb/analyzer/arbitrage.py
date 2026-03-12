"""Arbitrage analysis logic."""

from decimal import Decimal
from typing import Optional
from rarb.api.models import Market, MarketSnapshot, ArbitrageOpportunity
from rarb.config import get_settings
from rarb.utils.logging import get_logger

log = get_logger(__name__)

class ArbitrageAnalyzer:
    """Analyzes market snapshots for arbitrage opportunities."""

    def __init__(self, min_profit_threshold: Optional[float] = None):
        settings = get_settings()
        self.min_profit = Decimal(str(min_profit_threshold or settings.min_profit_threshold))

    async def analyze(self, snapshot: MarketSnapshot) -> Optional[ArbitrageOpportunity]:
        """Check if a market snapshot has arbitrage."""
        combined_ask = snapshot.combined_ask
        if combined_ask is None:
            return None

        profit = Decimal("1") - combined_ask
        if profit < self.min_profit:
            return None

        max_size = snapshot.min_liquidity_at_ask or Decimal("0")
        if max_size <= 0:
            return None

        yes_ask = snapshot.yes_best_ask or Decimal("0")
        no_ask = snapshot.no_best_ask or Decimal("0")

        expected_profit = profit * max_size

        return ArbitrageOpportunity(
            market=snapshot.market,
            yes_ask=yes_ask,
            no_ask=no_ask,
            combined_cost=combined_ask,
            profit_pct=float(profit),
            expected_profit=expected_profit,
            max_size=max_size
        )

    async def analyze_batch(self, snapshots: list[MarketSnapshot]) -> list[ArbitrageOpportunity]:
        """Analyze a list of snapshots."""
        opportunities = []
        for s in snapshots:
            opp = await self.analyze(s)
            if opp:
                opportunities.append(opp)
        
        # Sort by profit %
        opportunities.sort(key=lambda x: x.profit_pct, reverse=True)
        return opportunities

    async def get_alpha_suggestion(self, snapshots: list[MarketSnapshot]) -> Optional[str]:
        """Return the best opportunity based on pure math."""
        opps = await self.analyze_batch(snapshots)
        if opps:
            best = opps[0]
            return f"📊 MATH ALPHA: {best.market.question[:40]} | Profit: {best.profit_pct*100:.2f}%"
        return "Scan more markets for opportunities."
