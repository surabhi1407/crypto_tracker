# 🤖 AGENTS.md  
### Project: **Crypto Market Intelligence Dashboard**

---

## 🧩 Overview

The **Crypto Market Intelligence Dashboard** is designed to track and interpret crypto market health using **data + AI reasoning**.  
The end goal is to provide both objective metrics and GPT-based insights that explain market conditions in natural language and output simple trading actions such as **BUY / HOLD / WATCH**.

The system will evolve in stages, starting with **data ingestion and transformation**, followed by **dashboarding, AI summaries, and decision agents**.

---

## 🎯 Phase 1 Goal — Data Ingestion Layer

### Purpose
To automatically pull, normalize, and store daily crypto market signals from multiple public APIs.  
This layer forms the foundation for all subsequent analysis, visualization, and AI reasoning.

---

## 🔍 Signal Pillars (for Ingestion Context)

Below are the five core signal pillars the project will gradually integrate.  
In **Phase 1**, we will start with the most critical: *Market Structure, Sentiment, and Institutional Flows.*

| Pillar | Purpose | Key Signals (Phase 1 subset) | Why it Matters | Source |
|--------|----------|-------------------------------|----------------|---------|
| **1. Market Structure** | Capture quantitative backbone of the market — price, volatility, and liquidity. | Spot Price (BTC, ETH), Volume, Rolling Volatility, BTC Dominance | Provides hard data for trend and volatility analysis. | CoinGecko / Binance APIs |
| **2. Sentiment & Attention** | Understand public mood and speculative interest. | Fear & Greed Index | Measures crowd psychology that drives short-term momentum. | Alternative.me API |
| **3. Institutional & Macro** | Track capital flows and large-scale investor behavior. | ETF Inflows / Outflows | Indicates institutional appetite for crypto exposure. | SoSoValue / Farside APIs |
| **4. On-Chain Activity** *(later)* | Measure network usage and investor movement. | Exchange flows, Active addresses, Stablecoin supply | Fundamental liquidity view of crypto ecosystem. | Glassnode / CoinMetrics |
| **5. Derived Metrics** *(later)* | Combine multiple signals into composite scores. | Market Heat Score, Momentum Index | Simplifies complex data for AI reasoning. | Computed internally |

---

## 🏗️ Ingestion Architecture Summary

### Design Goals
- **Automated daily ingestion** of selected signals.  
- **Unified schema** for prices, sentiment, and ETF data.  
- **Idempotent writes** (no duplication).  
- **Local first → Cloud ready** (SQLite → BigQuery migration).  

### Data Flow
1. **Fetch APIs:** CoinGecko (BTC/ETH price + volatility), Alternative.me (Fear & Greed), SoSoValue (ETF flows).  
2. **Clean & Normalize:** Standardize timestamps (UTC), field names, and asset tags.  
3. **Store Snapshots:** Write to SQLite under `/data/market_intel.db` + optional CSV backups.  
4. **Transform Prep:** Compute 24 h change %, 7 d rolling volatility, and tag sessions (ASIA/EUROPE/US).  
5. **Output:** A ready-to-use `daily_market_snapshot` table for visualization and AI layers.  

---

## 🧱 Database Schema (Phase 1)

| Table | Purpose | Key Fields |
|--------|----------|------------|
| **ohlc_hourly** | Hourly price data from CoinGecko. | `asset`, `ts_utc`, `price`, `session` |
| **sentiment_daily** | Daily Fear & Greed index. | `as_of_date`, `fng_value`, `classification` |
| **etf_flows_daily** | Institutional ETF flow data. | `as_of_date`, `ticker`, `net_flow_usd` |
| **daily_market_snapshot** | Consolidated daily view for dashboard. | `as_of_date`, `asset`, `price_close_usd`, `price_chg_24h_pct`, `realized_vol_7d_pct`, `fng_value`, `etf_net_flow_usd`, `dominant_session` |

---

## ⚙️ Agent Context for Cursor

| Agent | Responsibility | Notes |
|--------|----------------|-------|
| **IngestionAgent** | Executes the daily ingestion pipeline (`main.py`) to pull API data and update SQLite. | Must handle retries and idempotent writes. |
| **SchemaAgent** | Maintains schema definitions for each table and ensures backward compatibility. | Helps when adding new signals. |
| **MetricsAgent (later)** | Will compute derived metrics like SMA and volatility after ingestion. | Not part of Phase 1. |

---

## ✅ Phase 1 Deliverables

- [ ] Implement API connectors for CoinGecko, Alternative.me, and SoSoValue.  
- [ ] Design SQLite schema and data storage logic.  
- [ ] Implement daily ingestion pipeline with logging + CSV snapshots.  
- [ ] Verify data coverage for BTC and ETH (14-day rolling window).  

---

## 🧠 Agent Instruction Rules

1. **Primary focus:** In this phase, agents should only work on data ingestion and validation — *no dashboarding or AI summarization yet.*  
2. **When a new signal or source is introduced:**
   - Extend the schema in `storage.py` or database migration scripts.
   - Add a new connector under `src/connectors/`.
   - Update this file’s **Signal Pillars** table to document the new data source and purpose.
3. **Agent interactions:**  
   - Agents should preserve schema compatibility and write idempotently (avoid duplicates).  
   - When enriching data, all timestamps must be stored in **UTC**.  
   - Any computed metrics (like volatility or change %) must be derived *after* ingestion in the transformation layer.
4. **Dependencies:**  
   - API calls must include timeout and retry logic.  
   - Ensure minimal rate-limit impact by caching recent API calls.  
   - Use environment variables defined in `.env` for credentials and paths.
5. **Testing expectation:**  
   - Run the ingestion pipeline locally with mock or limited-day data before enabling automation.  
   - Verify table creation and upsert logic in SQLite before connecting to Streamlit or downstream agents.

---

Once this ingestion layer is stable, **Phase 2** will focus on the **Transformation + Dashboard** layer and later the **AI Decision Agent**.
