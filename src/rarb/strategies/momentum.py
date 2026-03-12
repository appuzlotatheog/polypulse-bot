"""Momentum Breakout Strategy for Polymarket."""

from decimal import Decimal
from typing import Optional, Dict
from dataclasses import dataclass
import time

from rarb.api.models import MarketSnapshot
from rarb.config import get_settings
from rarb.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class MomentumSignal:
    """Momentum breakout signal."""
    side: str
    strength: float  # 0-1
    breakout_level: float
    volume_confirmation: bool
    rsi: Optional[float]


class MomentumStrategy:
    """
    Momentum Breakout Trading Strategy.
    
    Core idea: Ride strong directional moves when:
    - Price breaks above resistance with volume
    - RSI confirms momentum (but not overbought)
    - Recent news/sentiment supports the move
    
    Best for:
    - Breaking news markets
    - High-volume trending markets
    - Binary resolution probability shifts
    """
    
    def __init__(
        self,
        breakout_threshold: float = 0.15,
        min_volume_ratio: float = 1.5,
        rsi_max: float = 75,
        stop_loss_pct: float = 0.20,
    ):
        self.breakout_threshold = breakout_threshold
        self.min_volume_ratio = min_volume_ratio
        self.rsi_max = rsi_max
        self.stop_loss_pct = stop_loss_pct
        
        self.price_history: Dict[str, list] = {}
        self.volume_history: Dict[str, list] = {}
        
        log.info("🚀 Momentum Strategy initialized")
    
    def _update_history(self, snapshot: MarketSnapshot):
        """Record price and volume history."""
        market_id = snapshot.market.id
        
        if market_id not in self.price_history:
            self.price_history[market_id] = []
            self.volume_history[market_id] = []
        
        yes_price = float(snapshot.yes_best_ask or 0)
        no_price = float(snapshot.no_best_ask or 0)
        
        timestamp = time.time()
        self.price_history[market_id].append((timestamp, yes_price, no_price))
        self.volume_history[market_id].append((timestamp, snapshot.market.volume))
        
        # Keep last 50 ticks
        if len(self.price_history[market_id]) > 50:
            self.price_history[market_id].pop(0)
        if len(self.volume_history[market_id]) > 50:
            self.volume_history[market_id].pop(0)
    
    def _calculate_rsi(self, prices: list, period: int = 8) -> Optional[float]:
        """Calculate RSI indicator."""
        if len(prices) < period + 1:
            return None
        
        gains = []
        losses = []
        for i in range(1, len(prices)):
            change = prices[i][-1] - prices[i-1][-1]
            if change > 0:
                gains.append(change)
            else:
                losses.append(abs(change))
        
        avg_gain = sum(gains[-period:]) / period if gains else 0
        avg_loss = sum(losses[-period:]) / period if losses else 1
        
        rs = avg_gain / avg_loss if avg_loss else 0
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _detect_breakout(self, market_id: str, side_idx: int) -> Optional[float]:
        """Detect price breakout above resistance."""
        history = self.price_history.get(market_id, [])
        if len(history) < 20:
            return None
        
        prices = [p[side_idx] for p in history if p[side_idx] and p[side_idx] > 0]
        if len(prices) < 10:
            return None
        
        current = prices[-1]
        recent_high = max(prices[-10:])
        
        # Check if breaking above recent high
        if current > recent_high:
            breakout_pct = (current - recent_high) / recent_high
            if breakout_pct >= self.breakout_threshold:
                return current
        
        return None
    
    def _volume_confirmation(self, market_id: str) -> bool:
        """Check if volume confirms the breakout."""
        volume = self.volume_history.get(market_id, [])
        if len(volume) < 10:
            return True  # No history, assume confirmed
        
        recent_avg = sum(v[-1] for v in volume[-10:]) / 10
        older_avg = sum(v[-1] for v in volume[-20:-10]) / 10 if len(volume) > 20 else recent_avg
        
        return recent_avg >= older_avg * self.min_volume_ratio
    
    async def analyze(self, snapshot: MarketSnapshot) -> Optional[MomentumSignal]:
        """Analyze for momentum breakout opportunity."""
        self._update_history(snapshot)
        
        market_id = snapshot.market.id
        
        # Check YES side breakout
        yes_breakout = self._detect_breakout(market_id, 1)  # index 1 = yes_price
        if yes_breakout:
            volume_confirmed = self._volume_confirmation(market_id)
            if not volume_confirmed:
                return None
            
            yes_history = self.price_history[market_id]
            yes_prices = [p[1] for p in yes_history if p[1] and p[1] > 0]
            rsi = self._calculate_rsi(yes_prices)
            
            if rsi and rsi > self.rsi_max:
                return None  # Overbought
            
            strength = min((rsi or 50) / 100, 0.95) if rsi else 0.6
            
            log.info(
                "🚀 MOMENTUM BREAKOUT - YES",
                market=snapshot.market.question[:40],
                breakout_level=f"${yes_breakout:.3f}",
                rsi=f"{rsi:.1f}" if rsi else "N/A",
                volume="✓" if volume_confirmed else "✗"
            )
            
            return MomentumSignal(
                side="YES",
                strength=strength,
                breakout_level=yes_breakout,
                volume_confirmation=volume_confirmed,
                rsi=rsi
            )
        
        # Check NO side breakout
        no_breakout = self._detect_breakout(market_id, 2)  # index 2 = no_price
        if no_breakout:
            volume_confirmed = self._volume_confirmation(market_id)
            if not volume_confirmed:
                return None
            
            no_history = self.price_history[market_id]
            no_prices = [p[2] for p in no_history if p[2] and p[2] > 0]
            rsi = self._calculate_rsi(no_prices)
            
            if rsi and rsi > self.rsi_max:
                return None
            
            strength = min((rsi or 50) / 100, 0.95) if rsi else 0.6
            
            log.info(
                "🚀 MOMENTUM BREAKOUT - NO",
                market=snapshot.market.question[:40],
                breakout_level=f"${no_breakout:.3f}",
                rsi=f"{rsi:.1f}" if rsi else "N/A"
            )
            
            return MomentumSignal(
                side="NO",
                strength=strength,
                breakout_level=no_breakout,
                volume_confirmation=volume_confirmed,
                rsi=rsi
            )
        
        return None


class SentimentMomentumStrategy(MomentumStrategy):
    """
    Momentum strategy enhanced with AI sentiment analysis.
    Uses AI to verify if breakout has fundamental support.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings = get_settings()
    
    async def analyze(self, snapshot: MarketSnapshot) -> Optional[MomentumSignal]:
        signal = await super().analyze(snapshot)
        if not signal:
            return None
        
        if self.settings.analyzer_type == "standard":
            return signal
        
        if self.settings.use_sentiment_filter:
            from rarb.intelligence import get_x_pulse
            pulse = get_x_pulse()
            
            intel = await pulse.get_sentiment(snapshot.market.question)
            
            if intel and intel.confidence > 0.6:
                log.info(f"🧠 Intelligence confirmed breakout: {intel.summary}")
                signal.strength *= (1.0 + (intel.confidence - 0.5))
            elif intel:
                log.debug("⚠️ Intelligence could not confirm breakout, proceeding with caution")
        
        return signal
