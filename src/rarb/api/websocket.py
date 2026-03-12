"""Advanced WebSocket client for real-time Polymarket data."""

import asyncio
import json
import websockets
from decimal import Decimal
from typing import Dict, List, Optional, Callable, Any
from rarb.utils.logging import get_logger

log = get_logger(__name__)

class WebSocketClient:
    """High-performance WebSocket client for Polymarket CLOB."""

    def __init__(self):
        self.uri = "wss://clob.polymarket.com/ws/v2"
        self.subscriptions: Dict[str, set] = {}
        self.on_book_update: Optional[Callable] = None
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False
        self._reconnect_delay = 1.0

    async def connect(self):
        """Connect and maintain connection with auto-reconnect."""
        self._running = True
        while self._running:
            try:
                log.info(f"Connecting to WebSocket: {self.uri}")
                async with websockets.connect(self.uri) as ws:
                    self._ws = ws
                    log.info("WebSocket connected")
                    
                    # Resubscribe to existing topics
                    await self._resubscribe()
                    
                    async for message in ws:
                        await self._handle_message(message)
                        
            except Exception as e:
                log.error(f"WebSocket error: {e}")
                if self._running:
                    await asyncio.sleep(self._reconnect_delay)
                    self._reconnect_delay = min(self._reconnect_delay * 2, 60)

    async def subscribe(self, token_ids: List[str], channel: str = "book"):
        """Subscribe to token orderbooks."""
        payload = {
            "type": "subscribe",
            "assets": token_ids,
            "channel": channel
        }
        if self._ws:
            await self._ws.send(json.dumps(payload))
        
        if channel not in self.subscriptions:
            self.subscriptions[channel] = set()
        self.subscriptions[channel].update(token_ids)

    async def _resubscribe(self):
        """Restore subscriptions after reconnect."""
        for channel, assets in self.subscriptions.items():
            await self.subscribe(list(assets), channel)

    async def _handle_message(self, message: str):
        """Process incoming messages."""
        try:
            data = json.loads(message)
            if data.get("type") == "book" and self.on_book_update:
                await self.on_book_update(data)
        except Exception as e:
            log.debug(f"Error handling WS message: {e}")

    async def stop(self):
        self._running = False
        if self._ws:
            await self._ws.close()
