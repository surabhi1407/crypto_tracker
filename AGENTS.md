### Project: **Crypto Market Intelligence Dashboard**

---

## Overview
The **Crypto Market Intelligence Dashboard** tracks and interprets crypto-market health using **data + AI reasoning**.  
It evolves through modular phases:
1. **Data Ingestion & Transformation**
2. **Dashboarding & Visualization**
3. **AI Summaries & Reasoning**
4. **Decision Agents (BUY / HOLD / WATCH)**

This document is the single source of truth for project context.  
For implementation specifics, refer to referenced files inside `src/`.

---

## Completed Core Functionality

### **Phase 1 – Core Ingestion Layer**
**Status:** Production-ready  
**Files:**  
- Connectors → `src/connectors/{coingecko.py, alternative_me.py, sosovalue.py}`  
- Pipeline → `src/pipeline.py`  
- Storage/Schema → `src/storage/{database.py,schema.py}`  

**Signals Ingested**
| Category | Data | Source |
|-----------|-------|--------|
| Price & Volatility | BTC / ETH OHLC + 7 d realized vol | CoinGecko |
| Sentiment | Fear & Greed Index | Alternative.me |
| Institutional Flows | ETF inflows/outflows (300 d history) | SoSoValue |

**Features**
- Backfill + Daily Sync modes  
- Idempotent writes / retry logic  
- CSV backups + logging  
- Unified `daily_market_snapshot` output  

---

### **Phase 2 – Market Depth & Derivatives Layer**
**Status:** Operational (Released Nov 2025)  
**Files:**  
- `src/connectors/{market_metrics.py, binance_futures.py}`  
- Schema v2 migrations in `src/storage/schema.py`

**New Signals**
| Domain | Signals | Source |
|---------|----------|---------|
| Market Metrics | Volume, Dominance, Market Cap | CoinGecko |
| Derivatives | Funding Rates + Open Interest | Binance Futures (public API) |

**Highlights**
- End-to-end runtime ≈ 40 s (Ph1 + Ph2)  
- 33 % fewer API calls after optimization  
- All tests passing & schema v2 deployed  

**Known Notes**
- CoinGecko rate-limit errors (handled gracefully)  
- Optional parallel execution planned for temporal alignment  

For implementation details → see connectors and `ingestion_pipeline.py`.

---

### **Phase 3 – NLP + Sentiment Pipeline**
**Status:** Operational (Released Nov 2025)  
**Files:**  
- Connectors → `src/connectors/{reddit_connector.py, reddit_rss_connector.py, twitter_connector.py, news_connector.py, trends_connector.py}`  
- Sentiment Analysis → `src/utils/sentiment_analyzer.py`  
- Schema v4 migrations in `src/storage/schema.py`

**New Signals**
| Layer | Purpose | Source | Technology |
|--------|----------|--------|------------|
| **Social (Reddit)** | Retail mood ("what people feel") | Reddit (r/CryptoCurrency, r/Bitcoin, r/ethereum) | PRAW API or RSS JSON + VADER sentiment |
| **Social (Twitter)** | Real-time sentiment ("what people tweet") | Twitter/X API v2 | Twitter API + VADER sentiment |
| **News** | Narrative tone ("what media says") | NewsAPI | FinBERT (ProsusAI/finbert) |
| **Search Interest** | Attention cycles ("what people look for") | Google Trends | pytrends |

**Architecture: Raw Data + Aggregation Pattern**
Similar to Phase 1 (which stores raw OHLC data before computing daily snapshots), Phase 3 now:
1. **Stores raw data** → Individual posts, tweets, articles, and trend points with sentiment scores
2. **Computes aggregated metrics** → Daily sentiment summaries from raw data

This enables:
- **Historical reprocessing** with different sentiment analyzers
- **Audit trail** of source data
- **Flexible aggregation** strategies without re-fetching from APIs

**Implemented Tables**

*Raw Data Tables:*
```sql
CREATE TABLE social_posts_raw (
    post_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    subreddit TEXT,
    title TEXT,
    text TEXT,
    author TEXT,
    created_utc TIMESTAMP NOT NULL,
    score INTEGER,
    upvote_ratio REAL,
    num_comments INTEGER,
    url TEXT,
    sentiment_compound REAL,
    sentiment_pos REAL,
    sentiment_neg REAL,
    sentiment_neu REAL,
    sentiment_label TEXT,
    UNIQUE(post_id, platform)
);

CREATE TABLE news_articles_raw (
    article_url TEXT NOT NULL UNIQUE,
    title TEXT,
    description TEXT,
    source TEXT,
    author TEXT,
    published_at TIMESTAMP NOT NULL,
    sentiment_compound REAL,
    sentiment_label TEXT,
    sentiment_confidence REAL,
    positive_prob REAL,
    negative_prob REAL,
    neutral_prob REAL
);

CREATE TABLE search_trends_raw (
    ts_utc TIMESTAMP NOT NULL,
    keyword TEXT NOT NULL,
    interest_score REAL NOT NULL,
    geo TEXT DEFAULT '',
    timeframe TEXT,
    UNIQUE(ts_utc, keyword, geo)
);
```

*Aggregated Tables:*
```sql
CREATE TABLE social_sentiment_daily (
    as_of_date DATE,
    platform TEXT,
    mentions_count INTEGER,
    sentiment_score REAL,
    positive_mentions INTEGER,
    negative_mentions INTEGER,
    neutral_mentions INTEGER,
    engagement_score REAL,
    top_keywords TEXT,
    UNIQUE(as_of_date, platform)
);

CREATE TABLE news_sentiment_daily (
    as_of_date DATE,
    article_count INTEGER,
    avg_sentiment REAL,
    positive_pct REAL,
    negative_pct REAL,
    neutral_pct REAL,
    top_sources TEXT,
    top_keywords TEXT,
    UNIQUE(as_of_date)
);

CREATE TABLE search_interest_daily (
    as_of_date DATE,
    keyword TEXT,
    interest_score REAL,
    interest_change_pct REAL,
    related_queries TEXT,
    UNIQUE(as_of_date, keyword)
);
```

**Highlights**
- **Raw data storage** for all Phase 3 sources (posts, tweets, articles, trends)
- **Reddit RSS connector** - Works without API keys using public JSON endpoints
- **Twitter/X connector** - Uses Twitter API v2 with Bearer Token authentication
- **VADER Sentiment** for social media (optimized for informal text)  
- **FinBERT NLP** for financial news (fine-tuned on financial language)  
- **Multi-platform aggregation** with engagement scoring  
- **Keyword extraction** and related query tracking  
- **Graceful degradation** - each connector can fail independently  
- **Idempotent writes** - raw data can be re-ingested safely
- **Automatic fallback** - Reddit API → RSS if API unavailable
- **All tests passing** - 10/10 raw data tests, 9/9 schema tests, full unit test coverage

**Configuration**
Phase 3 features are opt-in via environment variables:

**Reddit (Two Options):**
- Option 1 (No API Key): `ENABLE_REDDIT_RSS=true` - Uses public JSON endpoints
- Option 2 (With API): `ENABLE_SOCIAL_SENTIMENT=true` + Reddit API credentials (falls back to RSS if API fails)

**Twitter:**
- `ENABLE_TWITTER_SENTIMENT=true` + `TWITTER_BEARER_TOKEN` (from Twitter Developer Portal)

**NewsAPI:**
- `ENABLE_NEWS_SENTIMENT=true` + NewsAPI key

**Google Trends:**
- `ENABLE_SEARCH_TRENDS=true` (no auth required)

**GitHub Actions Integration:**
The workflow (`.github/workflows/daily_ingestion.yml`) automatically:
- Enables Reddit RSS when Reddit API credentials are not available
- Enables Twitter sentiment when `TWITTER_BEARER_TOKEN` secret is configured
- Enables NewsAPI sentiment when `NEWSAPI_KEY` secret is configured
- Always enables Google Trends (no API key required)

For implementation details → see connectors and `ingestion_pipeline.py`.

---

## Work-In-Progress / Next Implementation

### **Phase 4 – Dashboarding & Visualization**
**Goal:** Build interactive dashboards to visualize market intelligence and sentiment trends.

---

## Code Quality & Design Guardrails (DO NOT REMOVE)

These standards apply to **all contributors and AI agents** implementing or updating code in this repository.  
They **must not** be deleted, ignored, or altered in any future revision of this file.

### 1. Architecture & Modularity
- All code must be **modular, reusable, and testable**.  
- Avoid hardcoding; prefer configs, constants, and environment variables.  
- Reuse shared logic from `src/utils/` or `src/common/` when applicable.  
- Each connector or pipeline should serve **one clear purpose**.

### 2. Design & Sign-Off
- Before implementation, ensure **technical design and schema changes** are reviewed and approved by a **senior architect**.  
- Update `AGENTS.md` with the planned design **before coding begins**.  
- Keep alignment with system-wide architecture (no unapproved new directories or patterns).

### 3. File & Documentation Discipline
- Only **two documentation files** are permitted:  
  - `AGENTS.md` → for architecture and context.  
  - `README.md` → for setup, usage, and developer instructions.  
- **Do not** create or maintain any additional `.md` files (e.g., `DESIGN.md`, `NOTES.md`).  
- Use in-line file references (e.g., `src/connectors/reddit_connector.py`) when pointing to implementations.

### 4. Testing & Validation
- Every new connector, transformation, or pipeline must include **unit and integration tests**.  
- Validate schema compatibility and idempotent inserts before merge.  
- Test ingestion both in **backfill** and **daily-sync** modes.  
- Simulate rate limits and network errors to confirm retry handling works as expected.

### 5. Readability & Code Standards
- Follow **PEP8** and consistent naming (`snake_case` for functions, `CamelCase` for classes).  
- Add docstrings for all public methods explaining purpose, inputs, and outputs.  
- Keep functions short (prefer under 40 lines) and self-contained.  
- Avoid excessive nesting; use helper functions to simplify logic.  
- Inline comments only where necessary — clarity comes from naming and structure.

### 6. Review & Deployment Workflow
- Implementation sequence must follow:  
  **Design → Sign-off → Implementation → Review → Test → Deploy.**  
- Code should not be merged without:
  - Linting and unit test pass  
  - Peer or architect review  
  - Documentation update in `AGENTS.md`  

### 7. Performance & Reliability
- Optimize for minimal API calls and reduced runtime.  
- Cache repetitive API responses when practical.  
- Ensure resilience to transient API failures and handle rate limits gracefully.  
- Keep database writes atomic and consistent.

### 8. Change Management
- Every new signal or schema change must first be documented under "Work-In-Progress" until validated.  
- After successful testing, move it to "Completed Core Functionality."  
- Maintain clear versioning and timestamps for each phase.

---
