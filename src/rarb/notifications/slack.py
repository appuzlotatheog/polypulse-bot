"""Slack notification client."""

from typing import Optional
from rarb.utils.logging import get_logger

log = get_logger(__name__)

class SlackNotifier:
    """Sends notifications to Slack."""
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url

    async def notify_arbitrage(self, market, yes_ask, no_ask, combined, profit_pct):
        """Send arbitrage alert to Slack."""
        log.info(f"Slack: Arbitrage alert for {market}")

_notifier = None

def get_notifier():
    """Get the global notifier instance."""
    global _notifier
    if _notifier is None:
        _notifier = SlackNotifier()
    return _notifier
