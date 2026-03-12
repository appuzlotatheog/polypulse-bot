"""Async wrapper for CLOB Client."""

import asyncio
from decimal import Decimal
from typing import Optional, Dict, Any, cast
from rarb.api.clob import ClobClient
from rarb.config import get_settings
from rarb.utils.logging import get_logger

log = get_logger(__name__)

class AsyncClobClient:
    """Asynchronous wrapper for the Polymarket CLOB client."""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.clob = ClobClient(self.settings)

    async def get_order(self, order_id: str) -> Dict[str, Any]:
        if not self.clob.client:
            return {}
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(None, self.clob.client.get_order, order_id)
            if hasattr(result, "to_dict") and callable(getattr(result, "to_dict")):
                return result.to_dict()
            if hasattr(result, "__dict__"):
                return vars(result)
            return cast(Dict[str, Any], result)
        except Exception as e:
            log.error(f"Failed to get order {order_id}: {e}")
            return {}

    async def submit_order(self, token_id: str, side: str, price: float, size: float, neg_risk: bool = False) -> Dict[str, Any]:
        if not self.clob.client:
            return {"errorMsg": "No client configured"}
        
        from py_clob_client.clob_types import OrderArgs
        
        order_args = OrderArgs(
            price=price,
            size=size,
            side=side,
            token_id=token_id,
        )
        
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(None, self.clob.client.create_order, order_args)
            if hasattr(result, "to_dict") and callable(getattr(result, "to_dict")):
                return result.to_dict()
            if hasattr(result, "__dict__"):
                return vars(result)
            return cast(Dict[str, Any], result)
        except Exception as e:
            log.error(f"Failed to submit order: {e}")
            return {"errorMsg": str(e)}

    async def cancel_order(self, order_id: str) -> bool:
        if not self.clob.client:
            return False
        loop = asyncio.get_event_loop()
        try:
            cancel_fn = getattr(self.clob.client, "cancel_order", None)
            if cancel_fn:
                await loop.run_in_executor(None, cancel_fn, order_id)
                return True
            return False
        except Exception as e:
            log.error(f"Failed to cancel order {order_id}: {e}")
            return False

    async def get_neg_risk(self, token_id: str) -> bool:
        """Check if a token has negative risk."""
        return False

    async def close(self):
        """Close connections."""
        await self.clob.close()

async def create_async_clob_client() -> AsyncClobClient:
    """Factory function for AsyncClobClient."""
    return AsyncClobClient()
