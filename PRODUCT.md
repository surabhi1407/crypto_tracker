
---

# ✅ **PRODUCT.md**

# Crypto Tracker — Product Control Center

This file defines the product vision, roadmap, KPIs, and decision framework.  
For architecture and implementation rules → see **AGENTS.md**.

## 1. Product Vision
Understand crypto-market regimes using real data + sentiment + institutional flows + derivatives + AI reasoning.  
Goal: clarity, not price prediction.

## 2. Current State
- Phase 1: Data Layer → DONE
- Phase 2: Market Metrics & Derivatives → DONE
- Phase 3: Sentiment Intelligence → DONE
- Phase 4: Dashboard → PENDING
- Phase 5: Analytics Layer → NOT STARTED
- Phase 6: Monitoring → NOT STARTED
- Phase 7: Multi-Agent System → PLANNED

## 3. Roadmap
### Phase 1 — Data Layer (✓)
OHLC, volatility, ETF flows, fear/greed, SQLite, backups.

### Phase 2 — Metrics & Derivatives (✓)
Market cap, dominance, funding rate, open interest.

### Phase 3 — Sentiment (✓)
Reddit, Twitter, news (FinBERT), Google Trends.

### Phase 4 — Dashboarding (⏳)
Streamlit: price, volatility, sentiment, ETF flows, KPIs.

### Phase 5 — Analytics Layer (⏳)
Correlation matrix, lag analysis, regime detection, signal scoring.

### Phase 6 — Monitoring (⏳)
GitHub Actions alerts, health logs, ingestion validation.

### Phase 7 — Multi-Agent System (⏳)
Data Agent → Insight Agent → Strategy Agent → Reflection Agent.

## 4. KPI Framework
- Volatility regime  
- ETF net flows  
- Sentiment composite score  
- Funding rate & open interest  
- Trend regime (up / down / range)

## 5. Signal Dictionary
Price/volatility, ETF flows, sentiment (Reddit/Twitter/News), funding rate, OI, market metrics, search trends.

## 6. Architecture

Ingestion → Raw Tables → Aggregation → Analytics → AI Reasoning → Dashboard

## 7. Weekly Log
(maintain manually)

## 8. Next Steps Checklist
- Build analytics layer  
- Add monitoring  
- Build Streamlit dashboard  
- Implement multi-agent reasoning  
