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
| **3. Institutional & Macro** | Track capital flows and large-scale investor behavior. | ETF Inflows / Outflows | Indicates institutional appetite for crypto exposure. | SoSoValue API (Historical) |
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

- [x] Implement API connectors for CoinGecko, Alternative.me, and SoSoValue.  
- [x] Design SQLite schema and data storage logic.  
- [x] Implement daily ingestion pipeline with logging + CSV snapshots.  
- [x] Verify data coverage for BTC and ETH (14-day rolling window).
- [x] Implement backfill mode for initial historical data (300 days ETF, 30 days sentiment).
- [x] Implement daily sync mode for incremental updates (7 days).
- [x] Configure idempotent writes to prevent duplicates.
- [x] Add comprehensive error handling and retry logic.
- [x] Implement CSV backup functionality with proper field filtering.
- [x] Add daily snapshot computation with volatility calculations.

**Status:** ✅ **PHASE 1 COMPLETE** - All systems operational for production use.  

---

## 🧠 Agent Instruction Rules

1. **Primary focus:** In this phase, agents should only work on data ingestion and validation — *no dashboarding or AI summarization yet.*  
2. **When a new signal or source is introduced:**
   - Extend the schema in `storage.py` or database migration scripts.
   - Add a new connector under `src/connectors/`.
   - Update this file's **Signal Pillars** table to document the new data source and purpose.
3. **Agent interactions:**  
   - Agents should preserve schema compatibility and write idempotently (avoid duplicates).  
   - When enriching data, all timestamps must be stored in **UTC**.  
   - Any computed metrics (like volatility or change %) must be derived *after* ingestion in the transformation layer.
4. **Dependencies:**  
   - API calls must include timeout and retry logic.  
   - Ensure minimal rate-limit impact by caching recent API calls.  
   - Use environment variables defined in `.env` for credentials and paths.
5. **Testing expectation:**  
   - Run the ingestion pipeline locally with limited-day data before enabling automation.  
   - Verify table creation and upsert logic in SQLite before connecting to Streamlit or downstream agents.
6. **⚠️ NO MOCK DATA:**  
   - **This is a production system.** All data sources must use real APIs or data feeds.
   - Mock data makes it difficult to track data quality issues and debug problems.
   - If an API is unavailable, the connector should fail gracefully and log the issue, not generate fake data.
   - Document any temporary workarounds clearly and mark them for immediate replacement.
7. **🎯 SIMPLICITY & MODULARITY:**
   - **Keep it simple.** Minimize the number of files and documentation.
   - **Reuse code.** Don't duplicate logic - create modular, reusable functions.
   - **One source of truth.** All project documentation should be in AGENTS.md and README.md only.
   - **No redundant files.** If information exists in one place, don't create another file for it.
   - **Modular architecture.** Each module should have a single, clear responsibility.

---

## 📊 ETF Data Source Decision

### **Current Implementation: SoSoValue Historical Inflow Chart API**

**Endpoint:** `POST /openapi/v2/etf/historicalInflowChart`  
**Documentation:** https://sosovalue.gitbook.io/soso-value-api-doc/api-document/get-etf-historical-inflow-chart

**Why Historical over Current Metrics:**

1. **Time-Series Focus**
   - Provides 300 days of historical data in one API call
   - Perfect for trend analysis and dashboard charts
   - Matches our database schema (date-based records)

2. **Efficiency**
   - One API call fetches 300 days vs. daily calls for current data
   - Reduces API rate limit concerns
   - Lower operational overhead

3. **Phase 1 Requirements**
   - Institutional flow tracking over time
   - Historical backtesting capability
   - Trend visualization for dashboard

**Data Provided:**
- Daily aggregate ETF flows (all US BTC/ETH spot ETFs combined)
- Total net inflow, total value traded, total net assets
- Cumulative net inflow since ETF launch

**Limitations:**
- ❌ No individual ETF breakdown (IBIT, FBTC, GBTC, etc.)
- ❌ No fee rates or discount/premium data
- ❌ No per-institution analysis

### **Alternative: SoSoValue Current ETF Data Metrics API**

**Endpoint:** `POST /openapi/v2/etf/currentEtfDataMetrics`  
**Documentation:** https://sosovalue.gitbook.io/soso-value-api-doc/api-document/get-current-etf-data-metrics

**Advantages (for future consideration):**
- ✅ Individual ETF-level data (ticker, institution, fees)
- ✅ Fee rates for ETF comparison
- ✅ Discount/premium rates
- ✅ Data freshness status codes
- ✅ Detailed per-ETF metrics

**When to Consider Adding:**
- Phase 2: When building ETF comparison features
- When analyzing individual ETF strategies
- When fee analysis becomes important
- When tracking specific institutions (Grayscale, BlackRock, etc.)

**Note:** Both endpoints can coexist. Historical provides time-series, Current provides granular snapshots.

### **Setup Instructions**

1. **Get API Key:** Sign up at https://sosovalue.xyz/ (free)
2. **Create `.env` file** in project root:
   ```bash
   SOSOVALUE_API_KEY=your_api_key_here
   ```
3. **Initial backfill** (run once):
   ```bash
   python3 main.py --backfill  # Fetches 300 days ETF, 30 days sentiment
   ```
4. **Daily sync** (automated):
   ```bash
   python3 main.py  # Fetches last 7 days only (efficient)
   ```

---

## 📅 Ingestion Schedule & Strategy

### **Two-Phase Approach**

**Phase 1: Initial Backfill** (Run once)
- Fetches 300 days of ETF historical data
- Fetches 30 days of sentiment data
- Fetches 14 days of OHLC data
- Command: `python3 main.py --backfill`

**Phase 2: Daily Incremental Sync** (Automated)
- Fetches last 7 days only (catches any missed days)
- Much faster and API-efficient
- Idempotent writes ensure no duplicates
- Command: `python3 main.py`

### **Recommended Schedule**

**Daily at 3 AM UTC** - After all data sources have updated:

```bash
# Add to crontab
0 3 * * * cd /path/to/crypto_tracker && python3 main.py
```

**Why 3 AM UTC:**
- US market closes at 4 PM ET (9 PM UTC)
- ETF data finalized by ~2 AM UTC
- Fear & Greed updates at midnight UTC
- Safe buffer ensures all data available

### **Data Update Frequencies**

| Source | Updates | Our Fetch | Rationale |
|--------|---------|-----------|-----------|
| **CoinGecko** | Real-time | 14 days hourly | Hourly data doesn't change retroactively |
| **Fear & Greed** | Daily (midnight UTC) | Last 7 days | Only updates once per day |
| **SoSoValue ETF** | Daily (after market) | Last 7 days | Finalized ~6 hours after market close |

**Key Insight:** Since historical data doesn't change, we only need to fetch recent days. The database's idempotent writes (INSERT OR REPLACE) ensure no duplicates even if we re-fetch the same dates.

---

## 🎉 Phase 1 Summary

### **What Was Built**

✅ **Complete Data Ingestion System**
- Real-time data from 3 sources (CoinGecko, Alternative.me, SoSoValue)
- 300 days of historical ETF flow data
- 30 days of sentiment data
- 14 days of hourly price data for BTC & ETH

✅ **Production-Ready Features**
- Backfill mode for initial setup (`--backfill`)
- Daily sync mode for incremental updates (default)
- Idempotent writes (no duplicates, safe to re-run)
- Comprehensive error handling and retry logic
- CSV backups for audit trail
- Daily market snapshots with computed metrics

✅ **Operational Excellence**
- Automated scheduling (cron-ready)
- Detailed logging for debugging
- Configuration via environment variables
- Modular, reusable code architecture
- No mock data - 100% real production data

### **Commands**

```bash
# Initial setup (run once)
python3 main.py --backfill

# Daily sync (automated)
python3 main.py

# Check status
python3 main.py --status
```

### **Data Coverage**

| Source | Records | Timeframe | Update Frequency |
|--------|---------|-----------|------------------|
| **CoinGecko** | ~336/run | 14 days | Hourly data |
| **Alternative.me** | 30 | 30 days | Daily |
| **SoSoValue** | 300 | 300 days | Daily |
| **Snapshots** | 7 | 7 days | Computed |

### **Next: Phase 2**

With the ingestion layer complete and stable, **Phase 2** will focus on:
- Enhanced Streamlit dashboard with historical data
- Derived metrics (SMA, EMA, momentum indicators)
- Volatility analysis and trend detection
- AI-powered market summaries
- Trading signal generation (BUY/HOLD/WATCH)

---

**Phase 1 Status:** ✅ **COMPLETE & OPERATIONAL**  
**Ready for:** Production deployment and daily automated runs  
**Last Updated:** November 6, 2025
