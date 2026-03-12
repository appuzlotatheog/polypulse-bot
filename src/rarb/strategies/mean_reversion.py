"""Mean Reversion Strategy for Polymarket."""

from decimal import Decimal
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import statistics

from rarb.api.models import MarketSnapshot, Market
from rarb.config import get_settings
from rarb.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class PriceWindow:
    """Tracks price history for mean reversion analysis."""
    prices: List[float] = field(default_factory=list)
    size: int = 100
    
    def add(self, price: float):
        if not price or price <= 0:
            return
        self.prices.append(price)
        if len(self.prices) > self.size:
            self.prices.pop(0)
    
    @property
    def mean(self) -> Optional[float]:
        if len(self.prices) < 5:
            return None
        return statistics.mean(self.prices)
    
    @property
    def std(self) -> Optional[float]:
        if len(self.prices) < 5:
            return None
        return statistics.stdev(self.prices)
    
    @property
    def z_score(self, current: float) -> Optional[float]:
        if not self.mean or not self.std or self.std == 0:
            return None
        return (current - self.mean) / self.std


class MeanReversionStrategy:
    """
    Mean Reversion Trading Strategy.
    
    Core idea: prices tend to revert to their historical mean.
    - Buy YES when price is significantly below mean (z-score < -1.5)
    - Buy NO when price is significantly below mean (z-score < -1.5)
    - Exit when price returns to mean or hits profit target
    
    Works best in:
    - Stable markets with clear resolution probability
    - Markets with temporary overreactions to news
    - High-liquidity environments
    """
    
    def __init__(
        self,
        min_zscore_entry: float = -1.5,
        zscore_exit: float = -0.5,
        profit_target_pct: float = 0.15,
        stop_loss_pct: float = 0.25,
    ):
        settings = get_settings()
        self.min_zscore_entry = settings.max_zscore_3min or min_zscore_entry
        self.zscore_exit = zscore_exit
        self.profit_target_pct = profit_target_pct
        self.stop_loss_pct = stop_loss_pct
        
        # Track prices per market
        self.price_windows: Dict[str, PriceWindow] = {}
        self.entry_prices: Dict[str, Dict] = {}
        
        log.info(
            "📊 Mean Reversion Strategy initialized",
            entry_zscore=self.min_zscore_entry,
            exit_zscore=self.zscore_exit,
            profit_target=f"{self.profit_target_pct*100:.0f}%"
        )
    
    def _get_window(self, market_id: str) -> PriceWindow:
        """Get or create price window for market."""
        if market_id not in self.price_windows:
            self.price_windows[market_id] = PriceWindow(size=100)
        return self.price_windows[market_id]
    
    async def analyze(self, snapshot: MarketSnapshot) -> Optional[Dict]:
        """
        Analyze market for mean reversion opportunity.
        
        Returns opportunity dict or None.
        """
        market_id = snapshot.market.id
        window = self._get_window(market_id)
        
        # Record current prices
        yes_price = float(snapshot.yes_best_ask or 0)
        no_price = float(snapshot.no_best_ask or 0)
        
        if yes_price > 0:
            window.add(yes_price)
        if no_price > 0:
            window.add(no_price)
        
        # Need sufficient history
        if len(window.prices) < 10:
            return None
        
        # Calculate z-score for YES
        if yes_price > 0:
            zscore = window.z_score(yes_price)
            if zscore is None:
                return None
            
            # Check for mean reversion signal
            if zscore < self.min_zscore_entry:
                # Price is significantly below mean - potential buy
                mean_price = window.mean
                expected_reversion = mean_price - yes_price
                expected_profit_pct = expected_reversion / yes_price
                
                if expected_profit_pct >= self.profit_target_pct:
                    if snapshot.market.days_until_resolution > 1:
                        log.info(
                            "📈 MEAN REVERSION SIGNAL",
                            market=snapshot.market.question[:40],
                            side="YES",
                            current_price=f"${yes_price:.3f}",
                            mean_price=f"${mean_price:.3f}",
                            zscore=f"{zscore:.2f}",
                            expected_profit=f"{expected_profit_pct*100:.1f}%"
                        )
                        
                        return {
                            "side": "YES",
                            "entry_price": Decimal(str(yes_price)),
                            "target_price": Decimal(str(mean_price)),
                            "stop_loss": Decimal(str(yes_price * (1 - self.stop_loss_pct))),
                            "size": snapshot.market.liquidity * 0.1,  # 10% of liquidity
                            "confidence": min(abs(zscore) / 3.0, 0.95),
                            "reason": f"Z-score {zscore:.2f} - price below mean"
                        }
        
        # Check NO side
        if no_price > 0:
            zscore = window.z_score(no_price)
            if zscore is not None and zscore < self.min_zscore_entry:
                mean_price = window.mean
                expected_profit_pct = (mean_price - no_price) / no_price
                
                if expected_profit_pct >= self.profit_target_pct:
                    if snapshot.market.days_until_resolution > 1:
                        log.info(
                            "📈 MEAN REVERSION SIGNAL",
                            market=snapshot.market.question[:40],
                            side="NO",
                            current_price=f"${no_price:.3f}",
                            mean_price=f"${mean_price:.3f}",
                            zscore=f"{zscore:.2f}"
                        )
                        
                        return {
                            "side": "NO",
                            "entry_price": Decimal(str(no_price)),
                            "target_price": Decimal(str(mean_price)),
                            "stop_loss": Decimal(str(no_price * (1 - self.stop_loss_pct))),
                            "size": snapshot.market.liquidity * 0.1,
                            "confidence": min(abs(zscore) / 3.0, 0.95),
                            "reason": f"Z-score {zscore:.2f} - price below mean"
                        }
        
        return None
    
    def should_exit(self, market_id: str, current_price: float, entry_price: float) -> bool:
        """Check if position should be exited."""
        if market_id not in self.price_windows:
            return False
        
        window = self.price_windows[market_id]
        if not window.mean:
            return False
        
        # Check profit target
        profit_pct = (current_price - entry_price) / entry_price
        if profit_pct >= self.profit_target_pct:
            log.info("✅ Mean reversion profit target hit", profit=f"{profit_pct*100:.1f}%")
            return True
        
        # Check if price reverted to mean
        zscore = window.z_score(current_price)
        if zscore is not None and zscore >= self.zscore_exit:
            log.info("✅ Price reverted to mean", zscore=f"{zscore:.2f}")
            return True
        
        # Check stop loss
        loss_pct = (entry_price - current_price) / entry_price
        if loss_pct >= self.stop_loss_pct:
            log.warning("⛔ Mean reversion stop loss hit", loss=f"{loss_pct*100:.1f}%")
            return True
        
        return False
    
    async def on_snapshot(self, snapshot: MarketSnapshot):
        """Process snapshot - record prices."""
        await self.analyze(snapshot)


class EnhancedMeanReversionStrategy(MeanReversionStrategy):
    """
    Enhanced Mean Reversion with additional filters:
    - Volume confirmation
    - RSI oversold check
    - Time decay adjustment
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.min_volume_60s = get_settings().min_volume_60s_usd
    
    async def analyze(self, snapshot: MarketSnapshot) -> Optional[Dict]:
        """Enhanced analysis with volume and RSI filters."""
        # Basic mean reversion signal
        basic_signal = await super().analyze(snapshot)
        if not basic_signal:
            return None
        
        # Volume filter
        if self.min_volume_60s and snapshot.market.volume < self.min_volume_60s:
            return None
        
        # Time decay filter - avoid markets very close to resolution
        if snapshot.market.days_until_resolution < 0.1:  # < 2.4 hours
            return None
        
        # RSI filter if enabled
        settings = get_settings()
        if settings.max_rsi_overbought:
            # Calculate simple RSI(8)
            window = self._get_window(snapshot.market.id)
            if len(window.prices) >= 8:
                gains = []
                losses = []
                for i in range(1, len(window.prices)):
                    change = window.prices[i] - window.prices[i-1]
                    if change > 0:
                        gains.append(change)
                    else:
                        losses.append(abs(change))
                
                avg_gain = sum(gains) / 8 if gains else 0
                avg_loss = sum(losses) / 8 if losses else 1
                rs = avg_gain / avg_loss if avg_loss else 0
                rsi = 100 - (100 / (1 + rs))
                
                if rsi > settings.max_rsi_overbought:
                    return None
        
        return basic_signal
