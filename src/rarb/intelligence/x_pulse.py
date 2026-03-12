"""X (Twitter) sentiment monitoring sentinel."""

import asyncio
import httpx
import hmac
import hashlib
import time
import base64
import urllib.parse
from typing import Dict, List, Optional, Any
from datetime import datetime

from rarb.intelligence.models import SentimentSignal, SentimentSource, SentimentPolarity
from rarb.config import get_settings
from rarb.utils.logging import get_logger

log = get_logger(__name__)

class XPulse:
    """
    X (Twitter) Intelligence Sentinel.
    
    Monitors high-impact accounts and keywords for breaking news
    and geopolitical sentiment.
    """

    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(timeout=10.0)
        
        # Keys from settings
        self.api_key = self.settings.x_api_key.get_secret_value() if self.settings.x_api_key else None
        self.api_secret = self.settings.x_api_secret.get_secret_value() if self.settings.x_api_secret else None
        self.access_token = self.settings.x_access_token.get_secret_value() if self.settings.x_access_token else None
        self.access_token_secret = self.settings.x_access_token_secret.get_secret_value() if self.settings.x_access_token_secret else None
        self.bearer_token = self.settings.x_bearer_token.get_secret_value() if self.settings.x_bearer_token else None

        log.info("🐦 XPulse initialized")

    def _get_oauth_header(self, method: str, url: str, params: Dict[str, Any]) -> str:
        """Generate OAuth 1.0a header."""
        if not all([self.api_key, self.api_secret, self.access_token, self.access_token_secret]):
            return ""

        nonce = str(int(time.time() * 1000000))
        timestamp = str(int(time.time()))
        
        oauth_params = {
            "oauth_consumer_key": self.api_key,
            "oauth_nonce": nonce,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": timestamp,
            "oauth_token": self.access_token,
            "oauth_version": "1.0",
        }
        
        # Combine and sort all parameters
        all_params = {**params, **oauth_params}
        encoded_params = "&".join(
            f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(str(v), safe='')}"
            for k, v in sorted(all_params.items())
        )
        
        base_string = f"{method.upper()}&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote(encoded_params, safe='')}"
        signing_key = f"{urllib.parse.quote(self.api_secret, safe='')}&{urllib.parse.quote(self.access_token_secret, safe='')}"
        
        signature = base64.b64encode(
            hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
        ).decode()
        
        oauth_params["oauth_signature"] = signature
        
        header = "OAuth " + ", ".join(
            f'{k}="{urllib.parse.quote(v, safe="")}"'
            for k, v in sorted(oauth_params.items())
        )
        return header

    async def search_tweets(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for recent tweets."""
        if not self.bearer_token:
            log.warning("X Bearer token missing, skipping search")
            return []

        url = "https://api.twitter.com/2/tweets/search/recent"
        params = {
            "query": query,
            "max_results": max_results,
            "tweet.fields": "created_at,public_metrics,lang",
        }
        
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        
        try:
            resp = await self.client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
        except Exception as e:
            log.error(f"X search failed for '{query}': {e}")
            return []

    async def get_sentiment(self, keyword: str) -> Optional[SentimentSignal]:
        """Analyze sentiment for a specific keyword/market."""
        tweets = await self.search_tweets(keyword, max_results=20)
        if not tweets:
            return None

        # Simplified sentiment analysis
        # In production, this would be passed to an LLM for classification
        tweet_text = " ".join([t["text"] for t in tweets])
        
        # Placeholder for AI classification
        # For now, we'll return a signal indicating we've gathered data
        return SentimentSignal(
            source=SentimentSource.TWITTER,
            polarity=SentimentPolarity.NEUTRAL,
            confidence=0.5,
            summary=f"Found {len(tweets)} tweets for '{keyword}'",
            metadata={"tweet_count": len(tweets), "latest_tweet": tweets[0]["text"] if tweets else ""}
        )

    async def close(self):
        await self.client.aclose()

# Singleton instance
_pulse = None

def get_x_pulse() -> XPulse:
    global _pulse
    if _pulse is None:
        _pulse = XPulse()
    return _pulse
