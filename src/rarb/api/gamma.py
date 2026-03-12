"""Client for Polymarket Gamma API."""

import httpx
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from rarb.api.models import Market, Token
from rarb.utils.logging import get_logger

log = get_logger(__name__)

class GammaClient:
    """Client for fetching market metadata from Gamma API."""

    def __init__(self, base_url: str = "https://gamma-api.polymarket.com"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url)

    async def fetch_all_active_markets(
        self,
        min_liquidity: float = 0,
        max_days_until_resolution: Optional[int] = None,
        min_volume: float = 0
    ) -> List[Market]:
        """Fetch active markets matching filters."""
        params = {
            "active": "true",
            "closed": "false",
        }
        try:
            resp = await self.client.get("/markets", params=params)
            resp.raise_for_status()
            data = resp.json()

            markets = []
            for m in data:
                # Basic filtering
                liquidity = float(m.get("liquidity", 0))
                volume = float(m.get("volume", 0))
                if liquidity < min_liquidity or volume < min_volume:
                    continue

                # Parse end_date
                end_date_str = m.get("endDate")
                end_date = None
                if end_date_str:
                    try:
                        end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                        if max_days_until_resolution:
                            days_until = (end_date - datetime.utcnow().replace(tzinfo=end_date.tzinfo)).days
                            if days_until > max_days_until_resolution:
                                continue
                    except ValueError:
                        pass

                # Extract tokens
                import json
                tokens = m.get("clobTokenIds", [])
                if isinstance(tokens, str):
                    try:
                        tokens = json.loads(tokens)
                    except:
                        continue
                
                if not isinstance(tokens, list) or len(tokens) < 2:
                    continue

                yes_token = Token(token_id=str(tokens[0]), symbol="YES", outcome="Yes")
                no_token = Token(token_id=str(tokens[1]), symbol="NO", outcome="No")

                markets.append(Market(
                    id=m["id"],
                    question=m["question"],
                    yes_token=yes_token,
                    no_token=no_token,
                    liquidity=liquidity,
                    volume=volume,
                    end_date=end_date,
                    neg_risk=m.get("negRisk", False)
                ))

            return markets
        except Exception as e:
            log.error(f"Failed to fetch markets: {e}")
            return []

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
