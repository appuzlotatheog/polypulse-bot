# Plan: AI Intelligence Expansion - Geopolitical & Crypto Correlation

## 1. Project Context
The Polypulse Bot v2.0 is currently a "Passive Observer" that makes decisions based primarily on Polymarket orderbook data and AI-derived sentiment from market questions. To reach "Institutional Grade" performance, the bot needs "Active Intelligence"—the ability to verify claims, monitor breaking news on X (Twitter), and correlate Polymarket moves with broader Crypto market trends.

## 2. Architecture Overview
We will introduce a new module `rarb.intelligence` that serves as an "Active Scouting" layer. These scouts will be registered as **Tools** within the `AIAnalyzer`, allowing the LLM to trigger specific research tasks before providing a trade verdict.

### New Module Structure:
- `src/rarb/intelligence/`
    - `__init__.py`: Registry of scouts
    - `browser_scout.py`: Playwright-based AI researcher (Agent-Browser pattern)
    - `x_pulse.py`: X/Twitter sentinel (X-CLI pattern)
    - `market_oracle.py`: Crypto exchange correlation (CCXT pattern)
    - `models.py`: Intelligence data models (RiskScore, SentimentSignal)

## 3. Component Details

### A. BrowserScout (Playwright)
- **Goal**: Navigate news sites (Reuters, Bloomberg, AP) to verify event resolution status.
- **Pattern**: Port the `agent-browser` accessibility tree snapshotting to Python. Assign `@e1`, `@e2` refs to interactive elements so the AI can reliably click/scroll.
- **Guardrail**: Headless mode by default; strict 10s timeout to prevent execution bottlenecks.

### B. XPulse (X/Twitter)
- **Goal**: Monitor high-impact accounts and breaking news tags.
- **Pattern**: Implement a lightweight wrapper based on `x-cli` using OAuth 1.0a and Bearer tokens.
- **Signal**: Calculate a "Hype Velocity" score based on tweet frequency and sentiment for specific market keywords.

### C. MarketOracle (CCXT)
- **Goal**: Correlate BTC/ETH/SOL prices with Polymarket's crypto prediction markets.
- **Signal**: Detect if a Polymarket price move is lagging behind Binance/Coinbase prices (Arbitrage opportunity).

## 4. Integration Logic
- **AIAnalyzer**:
    - Add `tools` list to `analyze()` method.
    - Implement a 2-step loop:
        1. AI decides if research is needed.
        2. If yes, trigger Scout, ingest result, and provide final verdict.
- **MomentumStrategy**:
    - Ingest `GlobalRiskScore` from XPulse.
    - If Risk Score is HIGH (e.g. sudden geopolitical event), decrease trade size or pause execution.

## 5. Implementation Roadmap
1. [ ] **Intelligence Infrastructure**: Create `rarb.intelligence` module and shared models.
2. [ ] **Crypto Integration**: Implement `MarketOracle` using CCXT for live price feeds.
3. [ ] **X Integration**: Implement `XPulse` for keyword-based sentiment tracking.
4. [ ] **Browser Integration**: Implement `BrowserScout` with Playwright-stealth.
5. [ ] **AI Loop Update**: Update `AIAnalyzer` to support tool-assisted reasoning.
6. [ ] **Strategy Enhancement**: Connect `SentimentMomentumStrategy` to the intelligence layer.

## 6. Final Verification Wave
- [ ] **QA-1**: Verify `MarketOracle` price feeds match Binance within <100ms.
- [ ] **QA-2**: Verify `XPulse` can fetch tweets for a specific keyword without 429 errors.
- [ ] **QA-3**: Verify `BrowserScout` can successfully snapshot a news site and extract a specific headline.
- [ ] **QA-4**: End-to-end "Alpha Suggestion" test where AI uses X and Browser to confirm a trade.
