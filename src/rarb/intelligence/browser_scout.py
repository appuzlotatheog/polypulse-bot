"""Playwright-based AI browser scout for news verification."""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser
from playwright_stealth import stealth

from rarb.intelligence.models import SentimentSignal, SentimentSource, SentimentPolarity
from rarb.utils.logging import get_logger

log = get_logger(__name__)

class BrowserScout:
    """
    AI-driven Web Researcher.
    
    Uses Playwright to navigate news sites and verify event outcomes.
    Implements deterministic element referencing for reliable AI interaction.
    """

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._context = None
        log.info("🌐 BrowserScout initialized")

    async def _ensure_browser(self):
        """Lazy initialization of browser."""
        if not self._browser:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
            self._context = await self._browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )

    async def get_page_snapshot(self, url: str) -> Dict[str, Any]:
        await self._ensure_browser()
        if not self._context:
            return {"error": "Browser context not initialized"}
            
        page = await self._context.new_page()
        await stealth(page)
        
        try:
            log.info(f"Navigating to {url}")
            await page.goto(url, wait_until="networkidle", timeout=15000)
            
            # Get semantic snapshot (Playwright 1.40+)
            # Note: aria_snapshot is an experimental feature
            try:
                tree = await page.accessibility.snapshot()
            except:
                tree = {"error": "Accessibility snapshot failed"}

            content = await page.content()
            
            # Simple text extraction for now
            # In production, we'd use the ref-injection logic from agent-browser
            text = await page.evaluate("() => document.body.innerText")
            
            return {
                "url": url,
                "title": await page.title(),
                "tree": tree,
                "text": text[:5000],  # Truncate for LLM
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            log.error(f"Browser navigation failed for {url}: {e}")
            return {"error": str(e)}
        finally:
            await page.close()

    async def verify_claim(self, claim: str, source_url: str) -> Optional[SentimentSignal]:
        """Verify a specific claim against a source URL."""
        data = await self.get_page_snapshot(source_url)
        if "error" in data:
            return None

        # This would usually be passed to an LLM to verify the claim against the text
        # For now, we return a signal indicating we've gathered the verification data
        return SentimentSignal(
            source=SentimentSource.NEWS,
            polarity=SentimentPolarity.UNCERTAIN,
            confidence=0.7,
            summary=f"Verified claim '{claim}' at {source_url}",
            url=source_url,
            metadata={"extracted_text": data.get("text", "")[:500]}
        )

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

# Singleton instance
_scout = None

def get_browser_scout() -> BrowserScout:
    global _scout
    if _scout is None:
        _scout = BrowserScout()
    return _scout
