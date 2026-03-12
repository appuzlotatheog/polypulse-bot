"""Crypto market data oracle using CCXT."""

import asyncio
import ccxt.async_support as ccxt
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime

from rarb.intelligence.models import CryptoPrice
from rarb.utils.logging import get_logger

log = get_logger(__name__)

class MarketOracle:
    """
    Crypto Market Oracle.
    
    Provides real-time price feeds from major exchanges (Binance, Coinbase)
    to correlate with Polymarket crypto prediction markets.
    """

    def __init__(self, exchange_id: str = "binance"):
        self.exchange_id = exchange_id
        self.exchange = getattr(ccxt, exchange_id)({
            'enableRateLimit': True,
        })
        self._price_cache: Dict[str, CryptoPrice] = {}
        log.info(f"🌐 MarketOracle initialized | Exchange: {exchange_id}")

    async def get_price(self, symbol: str) -> Optional[CryptoPrice]:
        """
        Fetch real-time price for a crypto asset.
        
        Args:
            symbol: Trading pair (e.g., BTC/USDT)
            
        Returns:
            CryptoPrice or None if fetch fails
        """
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            
            price = CryptoPrice(
                symbol=symbol,
                price=Decimal(str(ticker['last'])),
                change_24h=float(ticker['percentage'] or 0.0),
                volume_24h=float(ticker['baseVolume'] or 0.0),
                exchange=self.exchange_id,
                timestamp=datetime.utcnow()
            )
            
            self._price_cache[symbol] = price
            return price

        except Exception as e:
            log.error(f"Failed to fetch price for {symbol} from {self.exchange_id}: {e}")
            return self._price_cache.get(symbol)

    async def get_prices(self, symbols: List[str]) -> Dict[str, CryptoPrice]:
        """Fetch multiple prices concurrently."""
        tasks = [self.get_price(s) for s in symbols]
        results = await asyncio.gather(*tasks)
        return {s: r for s, r in zip(symbols, results) if r is not None}

    async def close(self):
        """Close exchange connection."""
        await self.exchange.close()

# Singleton instance
_oracle = None

def get_market_oracle() -> MarketOracle:
    global _oracle
    if _oracle is None:
        _oracle = MarketOracle()
    return _oracle
