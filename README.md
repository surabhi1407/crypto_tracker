# 📊 Crypto Market Intelligence Dashboard

Data-driven crypto market analysis combining real-time data with AI reasoning for actionable trading insights.

**Status:** ✅ **Phase 1, 2 & 3 OPERATIONAL** - Production-ready multi-source data ingestion with NLP sentiment analysis.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure API key
echo "SOSOVALUE_API_KEY=your_key" > .env

# Run ingestion
python3 main.py
```

**Get API key:** https://sosovalue.xyz/ (free)

## 📊 Data Sources

### Phase 1 & 2: Market Data
| Source | Data | Status |
|--------|------|--------|
| **CoinGecko** | BTC/ETH prices, volume, market cap | ✅ Active |
| **Alternative.me** | Fear & Greed Index | ✅ Active |
| **SoSoValue** | ETF flows (300 days) | ✅ Active |
| **Binance Futures** | Funding rates, open interest | ✅ Active |

### Phase 3: NLP & Sentiment
| Source | Data | Status |
|--------|------|--------|
| **Reddit** | Social sentiment (VADER) | 🔧 Optional |
| **NewsAPI** | News sentiment (FinBERT) | 🔧 Optional |
| **Google Trends** | Search interest | 🔧 Optional |

## 💾 Database

SQLite database with 16 tables (raw + aggregated):

**Phase 1:**
- `ohlc_hourly` - Price data with trading sessions
- `sentiment_daily` - Fear & Greed sentiment
- `etf_flows_daily` - Institutional flows
- `daily_market_snapshot` - Consolidated metrics

**Phase 2:**
- `market_metrics_daily` - Volume, dominance, market cap
- `funding_rates_snapshots` - Derivatives funding rates
- `open_interest_daily` - Futures open interest

**Phase 3 (Raw Data):**
- `social_posts_raw` - Individual Reddit posts with sentiment
- `news_articles_raw` - Individual news articles with sentiment
- `search_trends_raw` - Raw Google Trends data points

**Phase 3 (Aggregated):**
- `social_sentiment_daily` - Reddit sentiment & engagement
- `news_sentiment_daily` - News article sentiment (FinBERT)
- `search_interest_daily` - Google Trends search data

**Architecture:** Phase 3 follows Phase 1's pattern of storing raw data before aggregation, enabling historical reprocessing with different sentiment analyzers without re-fetching from APIs.

## 🎯 Commands

```bash
# First time setup (fetch 300 days of historical data)
python3 main.py --backfill

# Daily sync (fetch last 7 days only)
python3 main.py

# Check database status
python3 main.py --status

# Validate setup
python3 test_pipeline.py

# View dashboard
streamlit run app.py
```

## ⏰ Recommended Schedule

**Daily sync at 3 AM UTC** (after all data sources update):

```bash
# Add to crontab
0 3 * * * cd /path/to/crypto_tracker && python3 main.py
```

## 📁 Project Structure

```
crypto_tracker/
├── main.py                 # Entry point
├── app.py                  # Streamlit dashboard
├── src/
│   ├── connectors/        # API integrations
│   ├── storage/           # Database layer
│   └── utils/             # Utilities
└── data/                  # SQLite + backups
```

## 📚 Documentation

- **AGENTS.md** - Complete project specification, architecture, and setup
- **README.md** - This file (quick reference)

## ⚙️ Configuration

Settings in `.env`:

```bash
# Phase 1 & 2 (Required)
SOSOVALUE_API_KEY=required
COINGECKO_API_KEY=optional
RATE_LIMIT_DELAY=1.5
ENABLE_CSV_BACKUP=true
LOG_LEVEL=INFO

# Phase 2 Feature Flags
ENABLE_MARKET_METRICS=true
ENABLE_DERIVATIVES_DATA=true

# Phase 3 API Keys (Optional)
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_secret
REDDIT_USER_AGENT=CryptoIntelDashboard/1.0
NEWSAPI_KEY=your_newsapi_key

# Phase 3 Feature Flags (Opt-in)
ENABLE_SOCIAL_SENTIMENT=false
ENABLE_NEWS_SENTIMENT=false
ENABLE_SEARCH_TRENDS=false
```

### Getting API Keys

**Reddit API** (for social sentiment):
1. Go to https://www.reddit.com/prefs/apps
2. Create an app (script type)
3. Copy client ID and secret

**NewsAPI** (for news sentiment):
1. Go to https://newsapi.org/
2. Sign up for free tier (100 requests/day)
3. Copy API key

**Google Trends** - No API key required!

## 🔧 Features

**Phase 1 & 2:**
- ✅ Automated data ingestion from 5 sources
- ✅ SQLite database with idempotent writes
- ✅ Retry logic and rate limiting
- ✅ CSV backups and comprehensive logging
- ✅ Trading session classification
- ✅ Derivatives data (funding rates, open interest)

**Phase 3 (NLP & Sentiment):**
- ✅ Reddit social sentiment analysis (VADER)
- ✅ Financial news sentiment (FinBERT)
- ✅ Google Trends search interest tracking
- ✅ Multi-platform sentiment aggregation
- ✅ Keyword extraction and engagement scoring
- ✅ Graceful degradation (optional connectors)
- ✅ Comprehensive unit test coverage

## 📝 Logs

Check `logs/ingestion_YYYYMMDD.log` for detailed execution information.

---

## 🧪 Testing

Run unit tests:
```bash
# Test Phase 3 schema
PYTHONPATH=. python3 tests/test_phase3_schema.py

# Test sentiment analyzer
PYTHONPATH=. python3 tests/test_sentiment_analyzer.py
```

---

## 📦 Installation

Install Phase 3 dependencies:
```bash
pip install -r requirements.txt
```

Note: Phase 3 dependencies include:
- `praw` - Reddit API
- `newsapi-python` - NewsAPI client
- `pytrends` - Google Trends
- `transformers` - FinBERT model
- `torch` - PyTorch for FinBERT
- `vaderSentiment` - VADER sentiment analyzer

---

**Phase 1, 2 & 3 Complete** ✅ | **Next: Phase 4 - Dashboarding & Visualization** 🚀

For detailed documentation, see `AGENTS.md`
