# polypulse-bot v2.0

polypulse-bot is a professional-grade, high-frequency arbitrage trading system for Polymarket. It combines real-time blockchain data, low-latency WebSocket execution, and multi-provider AI analysis to identify and execute profitable opportunities.

## 🚀 Core Features

*   **Active Intelligence Layer:** Integrated `BrowserScout` (Playwright) for news verification and `XPulse` (X/Twitter) for high-frequency sentiment monitoring.
*   **Crypto Market Correlation:** `MarketOracle` (CCXT) provides real-time correlation between Polymarket moves and major exchanges (Binance/Coinbase).
*   **Multi-Strategy Engine:** Supports Mathematical Arbitrage, Flash-Crash absorption, Mean Reversion (Z-Score), and Momentum Breakout strategies.
*   **Institutional AI Suite:** Support for 10+ providers including Gemini, OpenAI (GPT-4o/o1), Anthropic (Claude 3.5), Groq, OpenRouter, NVIDIA, xAI (Grok), and Local LLMs (Ollama).
*   **High-Frequency Core:** Custom asynchronous execution using Polymarket CLOB protocols for sub-second order placement.
*   **Advanced UI/UX:** Premium Bento-style Terminal Interface (TUI) and modern Tailwind CSS Web Dashboard with real-time Chart.js analytics.

## 🛠 System Requirements

*   Python 3.10 or higher
*   Node.js & Bun (for oh-my-opencode integration)
*   Playwright dependencies (installed via setup script)
*   Polymarket API credentials (L2 Auth)
*   Polygon Mainnet Wallet

## 📦 Installation

1.  **Interactive Setup:**
    ```bash
    bash setup.sh
    ```
    This script handles environment creation, dependency installation (including Playwright drivers), and credential configuration with built-in, one-sentence tutorials for all API keys (X, OpenAI, Gemini, etc.).

2.  **Activate Environment:**
    ```bash
    source .venv/bin/activate
    ```

3.  **Launch Interface:**
    *   **TUI Dashboard:** `python -m rarb tui`
    *   **Web Dashboard:** `python -m rarb dashboard`

## 🧩 Intelligence API Key Tutorials

To unlock the full potential of the **Active Intelligence Layer**, you'll need the following:

*   **Google Gemini:** Get your keys at [Google AI Studio](https://aistudio.google.com).
*   **OpenAI:** Create an account and key at [OpenAI Platform](https://platform.openai.com).
*   **Anthropic:** Obtain keys from the [Anthropic Console](https://console.anthropic.com).
*   **X (Twitter) API:** Create a developer app at the [X Portal](https://developer.x.com). Ensure you generate all 5 tokens (API Key, Secret, Bearer, Access Token, and Access Secret) with "Read and Write" permissions.
*   **Crypto Feeds:** Most feeds use public APIs via CCXT, no keys required for basic pricing.

## 📖 Documentation

### Command Reference

*   `python -m rarb tui`: Institutional-grade interactive terminal dashboard.
*   `python -m rarb run --realtime`: Start the trading engine with live WebSocket feeds.
*   `python -m rarb scan`: Deep-scan all active markets for AI-verified alpha.
*   `python -m rarb config`: Validate API connections and review system settings.

### Intelligence Configuration

The bot supports **2-step reasoning loops**. If the AI is uncertain about a market event, it will autonomously trigger:
1.  **BrowserScout**: To verify claims on news sites like Reuters or Bloomberg.
2.  **XPulse**: To check breaking news velocity and sentiment on X.
3.  **MarketOracle**: To correlate price lagging against BTC/ETH spot markets.

**Supported AI Providers:**
*   `gemini`: Google Vertex AI (High-logic)
*   `openai`: GPT-4o / GPT-4o-mini
*   `anthropic`: Claude 3.5 Sonnet / Opus
*   `groq`: Llama 3.1 (Ultra-fast inference)
*   `xai`: Grok-beta
*   `openrouter`: 50+ models via OpenRouter
*   `ollama`: Local LLM support

## ⚖️ Security and Risk Disclaimer

This software is for educational and research purposes. Prediction market trading involves significant capital risk. Always test new strategies in `dry_run: true` mode.

## 📄 License

MIT License. Developed by the RARB Team.

