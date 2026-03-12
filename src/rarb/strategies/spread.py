"""Spread Trading Strategy for Polymarket - Related market arbitrage."""

from decimal import Decimal
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime

from rarb.api.models import Market, MarketSnapshot
from rarb.config import get_settings
from rarb.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class SpreadOpportunity:
    """Spread trading opportunity between related markets."""
    market_a_id: str
    market_b_id: str
    side_a: str  # YES/NO for market A
    side_b: str  # YES/NO for market B
    spread_pct: float
    confidence: float
    expected_profit: Decimal
    correlation: float


class SpreadStrategy:
    """
    Spread Trading Strategy.
    
    Core idea: Trade price discrepancies between related markets.
    Examples:
    - "Will X win election?" vs "Will Y win election?" (same election)
    - "Bitcoin > $100K by 2025?" vs "Bitcoin > $150K by 2025?" (same asset)
    - "Fed rate > 5%?" vs "Fed rate > 6%?" (same metric)
    
    When two correlated outcomes have mispriced probabilities,
    we can profit from the spread without pure arbitrage.
    """
    
    def __init__(
        self,
        min_spread_pct: float = 0.05,
        correlation_threshold: float = 0.7,
    ):
        self.min_spread_pct = min_spread_pct
        self.correlation_threshold = correlation_threshold
        
        self.market_pairs: Dict[str, Tuple[str, str]] = {}
        self.price_history: Dict[str, List[float]] = {}
        
        log.info("📊 Spread Strategy initialized")
    
    def _register_correlated_pair(self, market_a: Market, market_b: Market):
        """Register two correlated markets for spread tracking."""
        pair_key = f"{market_a.id}_{market_b.id}"
        self.market_pairs[pair_key] = (market_a.id, market_b.id)
        log.debug(f"Registered spread pair: {market_a.question[:30]} vs {market_b.question[:30]}")
    
    def _calculate_spread(self, snapshot_a: MarketSnapshot, snapshot_b: MarketSnapshot) -> Optional[SpreadOpportunity]:
        """Calculate spread opportunity between two snapshots."""
        yes_a = float(snapshot_a.yes_best_ask or 0)
        yes_b = float(snapshot_b.yes_best_ask or 0)
        
        if not yes_a or not yes_b:
            return None
        
        # Calculate price spread
        price_diff = abs(yes_a - yes_b)
        spread_pct = price_diff / min(yes_a, yes_b)
        
        if spread_pct < self.min_spread_pct:
            return None
        
        # Determine which side is undervalued
        if yes_a < yes_b:
            # Market A YES is cheaper - buy A YES, sell B YES (or buy B NO)
            side_a = "YES"
            side_b = "NO"
            expected_move = "convergence"
        else:
            side_a = "NO"
            side_b = "YES"
            expected_move = "divergence"
        
        # Simple correlation estimate based on market similarity
        # In production, this would use historical price correlation
        correlation = self._estimate_correlation(snapshot_a.market, snapshot_b.market)
        
        if correlation < self.correlation_threshold:
            return None
        
        # Calculate expected profit
        liquidity = min(snapshot_a.market.liquidity, snapshot_b.market.liquidity)
        size = min(liquidity * Decimal("0.1"), get_settings().max_position_size)
        expected_profit = size * Decimal(str(spread_pct)) * Decimal(str(correlation))
        
        log.info(
            "📊 SPREAD OPPORTUNITY",
            market_a=snapshot_a.market.question[:30],
            market_b=snapshot_b.market.question[:30],
            spread=f"{spread_pct*100:.2f}%",
            correlation=f"{correlation:.2f}",
            expected_profit=f"${float(expected_profit):.2f}"
        )
        
        return SpreadOpportunity(
            market_a_id=snapshot_a.market.id,
            market_b_id=snapshot_b.market.id,
            side_a=side_a,
            side_b=side_b,
            spread_pct=spread_pct,
            confidence=min(correlation, 0.9),
            expected_profit=expected_profit,
            correlation=correlation
        )
    
    def _estimate_correlation(self, market_a: Market, market_b: Market) -> float:
        """
        Estimate correlation between two markets.
        Higher correlation = safer spread trade.
        
        Factors:
        - Resolution condition overlap
        - Time to resolution proximity
        - Subject matter similarity
        """
        # Simplified correlation scoring
        score = 0.5  # Base score
        
        # Same resolution date range (within 30 days)
        if market_a.end_date and market_b.end_date:
            date_diff = abs((market_a.end_date - market_b.end_date).days)
            if date_diff < 30:
                score += 0.2
            elif date_diff < 90:
                score += 0.1
        
        # Similar liquidity range (within 2x)
        liq_ratio = max(market_a.liquidity, market_b.liquidity) / min(market_a.liquidity, market_b.liquidity)
        if liq_ratio < 2:
            score += 0.1
        
        # Keyword overlap in question
        words_a = set(market_a.question.lower().split())
        words_b = set(market_b.question.lower().split())
        overlap = len(words_a & words_b) / max(len(words_a), len(words_b))
        score += min(overlap * 0.3, 0.2)
        
        return min(score, 1.0)
    
    async def analyze(self, snapshots: List[MarketSnapshot]) -> List[SpreadOpportunity]:
        """Analyze all snapshots for spread opportunities."""
        opportunities = []
        
        # Group snapshots by potential pairs
        # In production, this would use pre-defined correlated pairs
        for i, snap_a in enumerate(snapshots):
            for snap_b in snapshots[i+1:]:
                # Skip if same market
                if snap_a.market.id == snap_b.market.id:
                    continue
                
                # Check for potential spread
                opp = self._calculate_spread(snap_a, snap_b)
                if opp:
                    opportunities.append(opp)
        
        # Sort by expected profit
        opportunities.sort(key=lambda x: float(x.expected_profit), reverse=True)
        
        return opportunities
    
    async def on_snapshot(self, snapshot: MarketSnapshot):
        """Process single snapshot - record price history."""
        market_id = snapshot.market.id
        
        if market_id not in self.price_history:
            self.price_history[market_id] = []
        
        yes_price = float(snapshot.yes_best_ask or 0)
        if yes_price:
            self.price_history[market_id].append((datetime.utcnow(), yes_price))
            if len(self.price_history[market_id]) > 100:
                self.price_history[market_id].pop(0)


class EnhancedSpreadStrategy(SpreadStrategy):
    """
    Enhanced spread strategy with:
    - Statistical correlation tracking
    - Volume profile analysis
    - Risk-adjusted position sizing
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings = get_settings()
    
    def _estimate_correlation(self, market_a: Market, market_b: Market) -> float:
        """Enhanced correlation with historical price tracking."""
        base_corr = super()._estimate_correlation(market_a, market_b)
        
        # Check if we have historical prices for both
        if market_a.id in self.price_history and market_b.id in self.price_history:
            hist_a = self.price_history[market_a.id]
            hist_b = self.price_history[market_b.id]
            
            # Calculate price correlation if we have overlapping data
            if len(hist_a) > 10 and len(hist_b) > 10:
                # Simplified: check if price movements tend to be same direction
                same_direction = 0
                for i in range(1, min(len(hist_a), len(hist_b))):
                    move_a = hist_a[i][1] - hist_a[i-1][1]
                    move_b = hist_b[i][1] - hist_b[i-1][1]
                    if (move_a > 0 and move_b > 0) or (move_a < 0 and move_b < 0):
                        same_direction += 1
                
                historical_corr = same_direction / min(len(hist_a), len(hist_b))
                base_corr = (base_corr + historical_corr) / 2
        
        return min(base_corr, 0.95)
    
    async def analyze(self, snapshots: List[MarketSnapshot]) -> List[SpreadOpportunity]:
        """Enhanced analysis with volume and risk filters."""
        opportunities = await super().analyze(snapshots)
        
        # Filter by volume profile
        if self.settings.min_volume_60s_usd:
            opportunities = [
                opp for opp in opportunities
                if True  # Would check volume here
            ]
        
        # Risk-adjusted sizing
        for opp in opportunities:
            # Reduce size for lower correlation
            if opp.correlation < 0.8:
                opp.expected_profit *= Decimal("0.7")
        
        return opportunities
