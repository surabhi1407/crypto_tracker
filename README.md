# Crypto Market Intelligence Dashboard

A modular system that collects, stores, and analyzes crypto-market signals for regime detection, sentiment understanding, and AI-assisted decision insights.

This repository follows:
- **PRODUCT.md** → product vision, roadmap, KPIs
- **AGENTS.md** → engineering architecture, phases, guardrails

## Data Sources
- Market Data: CoinGecko (price, volatility, volume, dominance)
- Sentiment: Fear & Greed Index, Reddit, Twitter, News (FinBERT)
- Institutional: SoSoValue ETF flows
- Derivatives: Binance Futures (funding rate, open interest)
- Search: Google Trends

## Commands
```bash
python3 main.py --backfill   # historical load
python3 main.py              # daily sync
streamlit run app.py         # dashboard (Phase 4)
