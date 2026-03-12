"""Client for Polymarket CLOB (Central Limit Order Book) API."""

import asyncio
from decimal import Decimal
from typing import Optional
from py_clob_client.client import ClobClient as PyClobClient
from py_clob_client.clob_types import ApiCreds, OrderArgs
from rarb.api.models import OrderBook, Order
from rarb.config import get_settings
from rarb.utils.logging import get_logger

log = get_logger(__name__)

class ClobClient:
    """Client for order placement and orderbook data via CLOB API."""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.client: Optional[PyClobClient] = None
        self._setup_client()

    def _setup_client(self):
        """Initialize the py-clob-client."""
        if not self.settings.private_key:
            log.warning("No private key configured for ClobClient")
            return

        api_key_str: str = self.settings.poly_api_key or ""
        creds = ApiCreds(
            api_key=api_key_str,
            api_secret=self.settings.poly_api_secret.get_secret_value() if self.settings.poly_api_secret else "",
            api_passphrase=self.settings.poly_api_passphrase.get_secret_value() if self.settings.poly_api_passphrase else "",
        )
        self.client = PyClobClient(
            host=self.settings.clob_base_url,
            key=self.settings.private_key.get_secret_value(),
            chain_id=self.settings.chain_id,
            creds=creds,
        )

    async def get_orderbook(self, token_id: str) -> OrderBook:
        """Fetch orderbook for a token with retries."""
        if not self.client:
            return OrderBook()

        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                # py-clob-client's get_order_book is synchronous in older versions
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, self.client.get_order_book, token_id)
                
                # Handle both dict and object (OrderBookSummary)
                if hasattr(data, "bids") and hasattr(data, "asks"):
                    raw_bids = data.bids
                    raw_asks = data.asks
                elif isinstance(data, dict):
                    raw_bids = data.get("bids", [])
                    raw_asks = data.get("asks", [])
                else:
                    return OrderBook()

                def parse_orders(raw_list):
                    orders = []
                    for item in raw_list:
                        try:
                            if hasattr(item, "price") and hasattr(item, "size"):
                                orders.append(Order(price=Decimal(str(item.price)), size=Decimal(str(item.size))))
                            elif isinstance(item, dict):
                                orders.append(Order(price=Decimal(str(item["price"])), size=Decimal(str(item["size"]))))
                        except:
                            continue
                    return orders

                return OrderBook(
                    bids=parse_orders(raw_bids),
                    asks=parse_orders(raw_asks)
                )
            except Exception as e:
                if "429" in str(e) or "rate limit" in str(e).lower() or attempt < max_retries - 1:
                    log.debug(f"Retry {attempt+1}/{max_retries} for {token_id} due to: {e}")
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue
                log.error(f"Failed to fetch orderbook for {token_id} after {max_retries} attempts: {e}")
                return OrderBook()
        
        return OrderBook()

    async def close(self):
        """Close connections."""
        # py-clob-client doesn't always have a close method, depends on version
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
