"""Multi-provider AI market analyzer with enhanced provider support."""

import json
import asyncio
import httpx
from decimal import Decimal
from typing import Optional, Dict, Any, List, Callable

from rarb.api.models import MarketSnapshot, ArbitrageOpportunity
from rarb.config import get_settings
from rarb.utils.logging import get_logger

log = get_logger(__name__)

class AIAnalyzer:
    """
    Unified AI Analyzer supporting 10+ providers:
    - Gemini (Google Vertex AI)
    - OpenAI (GPT-4o, GPT-4o-mini, o1-preview)
    - Anthropic (Claude 3.5/3 Sonnet, Opus)
    - Groq (Llama, Mixtral - ultra-fast)
    - OpenRouter (50+ models)
    - NVIDIA (Nemotron)
    - HuggingFace Inference API
    - xAI (Grok)
    - Ollama (Local LLMs)
    - LM Studio (Local API)
    """

    def __init__(self, reporting_callback: Optional[Callable[[str, str], Any]] = None) -> None:
        self.settings = get_settings()
        self.client = httpx.AsyncClient(timeout=30.0, http2=True)
        self.provider_stats: Dict[str, int] = {"calls": 0, "success": 0, "rejected": 0}
        self.reporting_callback = reporting_callback
        
        from rarb.intelligence import get_browser_scout, get_x_pulse, get_market_oracle
        self.browser = get_browser_scout()
        self.x_pulse = get_x_pulse()
        self.oracle = get_market_oracle()
        
        log.info(f"🧠 AI Analyzer initialized | Provider: {self.settings.analyzer_type}")

    def report(self, action: str, target: str):
        if self.reporting_callback:
            try:
                res = self.reporting_callback(action, target)
                if asyncio.iscoroutine(res):
                    asyncio.create_task(res)
            except: pass

    async def analyze(self, snapshot: MarketSnapshot) -> Optional[ArbitrageOpportunity]:
        provider = self.settings.analyzer_type.lower()
        
        if provider == "standard":
            from rarb.analyzer.arbitrage import ArbitrageAnalyzer
            return await ArbitrageAnalyzer().analyze(snapshot)

        self.report("ANALYZING MARKET", snapshot.market.question)
        prompt = self._build_analysis_prompt(snapshot)
        system_prompt = self._get_system_prompt()
        result = await self._route_call(prompt, system_prompt, provider)
        
        if result and result.get("needs_research"):
            research_query = result.get("research_query", snapshot.market.question)
            log.info(f"🔍 AI requesting research: {research_query}")
            self.report("AI RESEARCH REQUESTED", research_query)
            
            self.report("SCANNING X PULSE", research_query)
            x_task = self.x_pulse.get_sentiment(research_query)
            
            oracle_task = asyncio.sleep(0, None)
            if "crypto" in research_query.lower():
                self.report("CONSULTING MARKET ORACLE", "BTC/USDT")
                oracle_task = self.oracle.get_price("BTC/USDT")
                
            browser_task = asyncio.sleep(0, None)
            if research_query.startswith("http"):
                self.report("BROWSING NEWS SOURCE", research_query)
                browser_task = self.browser.verify_claim(research_query, research_query)
            
            intel_results = await asyncio.gather(x_task, oracle_task, browser_task)
            
            research_data = f"\n\n**RESEARCH FINDINGS:**\n"
            if intel_results[0]:
                research_data += f"- X Sentiment: {intel_results[0].summary} (Confidence: {intel_results[0].confidence})\n"
            if len(intel_results) > 1 and intel_results[1]:
                research_data += f"- Crypto Market: BTC at ${intel_results[1].price} ({intel_results[1].change_24h}% 24h)\n"
            if len(intel_results) > 2 and intel_results[2]:
                research_data += f"- Web Verification: {intel_results[2].summary}\n"

            self.report("FINALIZING VERDICT", snapshot.market.question)
            result = await self._route_call(prompt + research_data, system_prompt, provider)

        self.provider_stats["calls"] += 1
        
        if result:
            self.provider_stats["success"] += 1
            should_trade = result.get("should_trade", False)
            confidence = result.get("confidence", 0)
            
            if should_trade and confidence >= self.settings.ai_confidence_threshold:
                log.info(
                    "✅ AI APPROVAL",
                    provider=provider,
                    confidence=f"{confidence*100:.1f}%",
                    reason=result.get("reason", "N/A")[:80]
                )
                from rarb.analyzer.arbitrage import ArbitrageAnalyzer
                return await ArbitrageAnalyzer().analyze(snapshot)
            else:
                self.provider_stats["rejected"] += 1
        
        return None

    async def _route_call(self, prompt: str, system: str, provider: str) -> Optional[Dict]:
        if provider == "gemini":
            return await self._call_gemini(prompt)
        elif provider == "openai":
            return await self._call_openai(prompt, system)
        elif provider == "anthropic":
            return await self._call_anthropic(prompt, system)
        elif provider == "groq":
            return await self._call_groq(prompt, system)
        elif provider in ["openrouter", "nvidia", "xai"]:
            return await self._call_openai_compatible(prompt, system, provider)
        elif provider == "huggingface":
            return await self._call_huggingface(prompt)
        elif provider in ["ollama", "lmstudio"]:
            return await self._call_local(prompt, system, provider)
        return None

    def _build_analysis_prompt(self, snapshot: MarketSnapshot) -> str:
        """Build detailed analysis prompt for AI."""
        yes_price = float(snapshot.yes_best_ask or 0)
        no_price = float(snapshot.no_best_ask or 0)
        combined = float(snapshot.combined_ask or 0)
        profit = (1 - combined) * 100 if combined else 0
        
        return f"""Analyze this Polymarket arbitrage opportunity for high-probability execution:

**MARKET DATA:**
- Question: {snapshot.market.question}
- YES Price: ${yes_price:.4f}
- NO Price: ${no_price:.4f}
- Combined Cost: ${combined:.4f}
- Profit Spread: {profit:.2f}%
- Liquidity: ${snapshot.market.liquidity:,.0f}
- Volume 24h: ${snapshot.market.volume:,.0f}
- Days to Resolution: {snapshot.market.days_until_resolution}
- Neg Risk: {snapshot.market.neg_risk}

**ARBITRAGE MATH:**
If combined < 1.00, buying both sides guarantees $1.00 payout.
Profit = 1.00 - combined_cost
Current spread: ${1 - combined:.4f} per share

**YOUR TASK:**
Evaluate this opportunity considering:
1. Mathematical edge (>0.5% profit)
2. Liquidity risk (can we enter/exit?)
3. Resolution risk (time to expiry)
4. Market sentiment/volume patterns
5. Any red flags or "trap" indicators

Respond ONLY in valid JSON format:
{{
    "should_trade": bool,
    "confidence": float 0-1,
    "reason": "1-2 sentence explanation",
    "risk_score": int 1-10,
    "recommended_size_usd": float,
    "key_factors": ["factor1", "factor2"]
}}"""

    def _get_system_prompt(self) -> str:
        return """You are a professional quantitative trading analyst for Polymarket.
Your role is to identify high-probability opportunities and avoid value traps.
Be conservative.

**CAPABILITIES:**
- You can request external research if you are uncertain about a claim or need real-time context.
- To request research, include "needs_research": true and a "research_query" in your JSON response.
- Research queries can cover:
    - X/Twitter sentiment (geopolitical events, breaking news)
    - Crypto market prices (BTC/ETH correlation)
    - Web news verification (Reuters, Bloomberg)

**GUIDELINES:**
1. Only trade with genuine mathematical edge or strong directional conviction.
2. Focus on: liquidity, timing, and geopolitical pulse.
3. If a news event is breaking, use research to verify the current state.
"""

    async def _call_gemini(self, prompt: str) -> Optional[Dict]:
        """Google Vertex AI - Gemini."""
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel
            
            project_id = self.settings.google_cloud_project
            if project_id:
                vertexai.init(project=project_id, location="us-central1")
            
            model = GenerativeModel(self.settings.gemini_model)
            response = await asyncio.to_thread(
                model.generate_content, 
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            result = self._parse_json(response.text)
            if result:
                result["provider"] = "gemini"
            return result
        except Exception as e:
            log.error(f"Gemini analysis failed: {e}")
            return None

    async def _call_openai(self, prompt: str, system: str) -> Optional[Dict]:
        """OpenAI - GPT-4o, o1, etc."""
        if not self.settings.openai_api_key:
            return None
        try:
            headers = {"Authorization": f"Bearer {self.settings.openai_api_key.get_secret_value()}"}
            data = {
                "model": self.settings.openai_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1
            }
            resp = await self.client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
            resp.raise_for_status()
            result = self._parse_json(resp.json()["choices"][0]["message"]["content"])
            if result:
                result["provider"] = "openai"
            return result
        except Exception as e:
            log.error(f"OpenAI analysis failed: {e}")
            return None

    async def _call_anthropic(self, prompt: str, system: str) -> Optional[Dict]:
        """Anthropic - Claude 3.5/3 Sonnet, Opus."""
        if not self.settings.anthropic_api_key:
            return None
        try:
            headers = {
                "x-api-key": self.settings.anthropic_api_key.get_secret_value(),
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            data = {
                "model": self.settings.anthropic_model,
                "max_tokens": 1024,
                "system": system,
                "messages": [{"role": "user", "content": prompt}]
            }
            resp = await self.client.post("https://api.anthropic.com/v1/messages", headers=headers, json=data)
            resp.raise_for_status()
            result = self._parse_json(resp.json()["content"][0]["text"])
            if result:
                result["provider"] = "anthropic"
            return result
        except Exception as e:
            log.error(f"Anthropic analysis failed: {e}")
            return None

    async def _call_groq(self, prompt: str, system: str) -> Optional[Dict]:
        """Groq - Ultra-fast Llama/Mixtral inference."""
        if not self.settings.groq_api_key:
            return None
        try:
            headers = {"Authorization": f"Bearer {self.settings.groq_api_key.get_secret_value()}"}
            data = {
                "model": self.settings.groq_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1
            }
            resp = await self.client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
            resp.raise_for_status()
            result = self._parse_json(resp.json()["choices"][0]["message"]["content"])
            if result:
                result["provider"] = "groq"
            return result
        except Exception as e:
            log.error(f"Groq analysis failed: {e}")
            return None

    async def _call_openai_compatible(self, prompt: str, system: str, provider: str) -> Optional[Dict]:
        """OpenAI-compatible APIs for OpenRouter, NVIDIA, xAI."""
        configs = {
            "openrouter": {
                "url": "https://openrouter.ai/api/v1/chat/completions",
                "key": self.settings.openrouter_api_key,
                "model": self.settings.openrouter_model,
                "headers": {
                    "Authorization": f"Bearer {self.settings.openrouter_api_key.get_secret_value() if self.settings.openrouter_api_key else ''}",
                    "HTTP-Referer": "https://github.com/polypulse-bot",
                    "X-Title": "Polypulse Bot"
                }
            },
            "nvidia": {
                "url": "https://integrate.api.nvidia.com/v1/chat/completions",
                "key": self.settings.nvidia_api_key,
                "model": self.settings.nvidia_model,
                "headers": {"Authorization": f"Bearer {self.settings.nvidia_api_key.get_secret_value() if self.settings.nvidia_api_key else ''}"}
            },
            "xai": {
                "url": "https://api.x.ai/v1/chat/completions",
                "key": self.settings.xai_api_key,
                "model": self.settings.xai_model,
                "headers": {"Authorization": f"Bearer {self.settings.xai_api_key.get_secret_value() if self.settings.xai_api_key else ''}"}
            }
        }
        
        cfg = configs.get(provider)
        if not cfg or not cfg["key"]:
            return None
            
        try:
            data = {
                "model": cfg["model"],
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"}
            }
            resp = await self.client.post(cfg["url"], headers=cfg["headers"], json=data)
            resp.raise_for_status()
            result = self._parse_json(resp.json()["choices"][0]["message"]["content"])
            if result:
                result["provider"] = provider
            return result
        except Exception as e:
            log.error(f"{provider} analysis failed: {e}")
            return None

    async def _call_huggingface(self, prompt: str) -> Optional[Dict]:
        """HuggingFace Inference API."""
        if not self.settings.huggingface_api_key:
            return None
        try:
            headers = {"Authorization": f"Bearer {self.settings.huggingface_api_key.get_secret_value()}"}
            data = {"inputs": prompt}
            resp = await self.client.post(
                f"https://api-inference.huggingface.co/models/{self.settings.huggingface_model}",
                headers=headers,
                json=data
            )
            resp.raise_for_status()
            result = self._parse_json(resp.json()[0]["generated_text"])
            if result:
                result["provider"] = "huggingface"
            return result
        except Exception as e:
            log.error(f"HuggingFace analysis failed: {e}")
            return None

    async def _call_local(self, prompt: str, system: str, provider: str) -> Optional[Dict]:
        """Local LLMs via Ollama or LM Studio."""
        configs = {
            "ollama": {"url": "http://localhost:11434/api/generate"},
            "lmstudio": {"url": "http://localhost:1234/v1/chat/completions"}
        }
        
        cfg = configs.get(provider)
        if not cfg:
            return None
        
        try:
            if provider == "ollama":
                data = {
                    "model": self.settings.local_model,
                    "prompt": f"{system}\n\n{prompt}",
                    "stream": False,
                    "format": "json"
                }
                resp = await self.client.post(cfg["url"], json=data)
                resp.raise_for_status()
                result = self._parse_json(resp.json()["response"])
            else:  # LM Studio
                data = {
                    "model": self.settings.local_model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": {"type": "json_object"}
                }
                resp = await self.client.post(cfg["url"], json=data)
                resp.raise_for_status()
                result = self._parse_json(resp.json()["choices"][0]["message"]["content"])
            
            if result:
                result["provider"] = provider
            return result
        except Exception as e:
            log.error(f"Local AI ({provider}) analysis failed: {e}")
            return None

    def _parse_json(self, text: str) -> Optional[Dict]:
        """Parse JSON response from AI providers."""
        try:
            text = text.strip()
            # Remove markdown code blocks
            if text.startswith('```'):
                text = '\n'.join(text.split('\n')[1:-1])
            text = text.strip('```json').strip('```').strip()
            return json.loads(text)
        except Exception:
            log.debug(f"Failed to parse JSON: {text[:200]}")
            return None

    async def get_alpha_suggestion(self, snapshots: List[MarketSnapshot]) -> Optional[str]:
        """Get AI recommendation for the single best trade opportunity."""
        if not snapshots or self.settings.analyzer_type == "standard":
            return "Scan more markets for AI Alpha insights."
        
        # Build summary of top opportunities
        top_opps = sorted(snapshots, key=lambda s: float(s.combined_ask or 1), reverse=True)[:10]
        market_summary = "\n".join([
            f"{i+1}. {s.market.question[:60]} | Profit: {(1-float(s.combined_ask or 1))*100:.2f}% | Liquidity: ${s.market.liquidity:,.0f}"
            for i, s in enumerate(top_opps)
        ])
        
        prompt = f"""
You are reviewing the top 10 Polymarket arbitrage opportunities.
Select the SINGLE BEST trade and explain why in one punchy sentence.

**OPPORTUNITIES:**
{market_summary}

**RESPONSE FORMAT (JSON):**
{{
    "best_rank": int 1-10,
    "market_name": "market question",
    "explanation": "why this is the best trade",
    "conviction": "HIGH/MEDIUM/LOW"
}}"""

        provider = self.settings.analyzer_type.lower()
        result = None
        
        if provider == "gemini":
            result = await self._call_gemini(prompt)
        elif provider == "openai":
            result = await self._call_openai(prompt, self._get_system_prompt())
        elif provider == "anthropic":
            result = await self._call_anthropic(prompt, self._get_system_prompt())
        
        if result:
            rank = result.get("best_rank", 1)
            market = result.get("market_name", "Unknown")
            explanation = result.get("explanation", "N/A")
            conviction = result.get("conviction", "MEDIUM")
            conviction_emoji = {"HIGH": "🔥", "MEDIUM": "⚡", "LOW": "💡"}.get(conviction, "💡")
            return f"{conviction_emoji} ALPHA PICK #{rank}: {market} — {explanation}"
        
        return "🔮 AI analyzing top alpha opportunities..."

    async def analyze_multi_angle(self, snapshot: MarketSnapshot) -> Dict[str, Optional[Dict]]:
        """Get analysis from multiple AI providers for ensemble decision."""
        providers = ["openai", "anthropic", "groq", "gemini"]
        results = {}
        
        prompt = self._build_analysis_prompt(snapshot)
        system = self._get_system_prompt()
        
        # Run analyses in parallel
        tasks = {
            "openai": self._call_openai(prompt, system),
            "anthropic": self._call_anthropic(prompt, system),
            "groq": self._call_groq(prompt, system),
            "gemini": self._call_gemini(prompt)
        }
        
        completed = await asyncio.gather(*tasks.values(), return_exceptions=True)
        for provider, result in zip(tasks.keys(), completed):
            if isinstance(result, dict) and result.get("confidence"):
                results[f"{provider}_confidence"] = result["confidence"]
                results[f"{provider}_should_trade"] = result["should_trade"]
        
        # Consensus logic
        if results:
            avg_confidence = sum(v for k, v in results.items() if k.endswith("_confidence")) / len([k for k in results if k.endswith("_confidence")])
            results["consensus_confidence"] = avg_confidence
            results["consensus_should_trade"] = avg_confidence >= 0.7
        
        return results

    async def close(self):
        """Cleanup resources."""
        await self.client.aclose()
