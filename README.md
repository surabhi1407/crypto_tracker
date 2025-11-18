# Crypto Market Intelligence Dashboard

Data-driven crypto market analysis combining real-time data with AI reasoning for actionable trading insights.

**Status:** Phase 1, 2 & 3 OPERATIONAL

## Data Sources and Tables

### Market Data
| Source | Data | Status |
|--------|------|--------|
| **CoinGecko** | BTC/ETH prices, volume, market cap | Active |
| **Alternative.me** | Fear & Greed Index | Active |
| **SoSoValue** | ETF flows (300 days) | Active |
| **Binance Futures** | Funding rates, open interest | Active |

### Tables
#### Raw
- `ohlc_hourly` - Price data with trading sessions
- `daily_market_snapshot` - Consolidated metrics
- `market_metrics_daily` - Volume, dominance, market cap
- `funding_rates_snapshots` - Derivatives funding rates
#### Aggregated
- `open_interest_daily` - Futures open interest
- `sentiment_daily` - Fear & Greed sentiment
- `etf_flows_daily` - Institutional flows

### NLP & Sentiment
| Source | Data | Status |
|--------|------|--------|
| **Reddit** | Social sentiment (VADER) - RSS/API | Active |
| **Twitter/X** | Social sentiment (VADER) | Active |
| **NewsAPI** | News sentiment (FinBERT) | Active |
| **Google Trends** | Search interest | Optional |

### Tables
#### Raw
- `social_posts_raw` - Individual Reddit/Twitter posts with sentiment
- `news_articles_raw` - Individual news articles with sentiment
- `search_trends_raw` - Raw Google Trends data points
#### Aggregated
- `social_sentiment_daily` - Reddit/Twitter sentiment & engagement
- `news_sentiment_daily` - News article sentiment (FinBERT)
- `search_interest_daily` - Google Trends search data

## Commands

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

## Project Structure

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

## Documentation

- **AGENTS.md** - Complete project specification, architecture, and setup
- **README.md** - This file (quick reference)

## Configuration

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
TWITTER_BEARER_TOKEN=your_twitter_bearer_token

# Phase 3 Feature Flags (Opt-in)
ENABLE_SOCIAL_SENTIMENT=false
ENABLE_REDDIT_RSS=false
ENABLE_TWITTER_SENTIMENT=false
ENABLE_NEWS_SENTIMENT=false
ENABLE_SEARCH_TRENDS=false
```

### Getting API Keys

**Reddit RSS** (for social sentiment - no API key required):
- No API key needed! Set `ENABLE_REDDIT_RSS=true` to use public JSON endpoints
- Alternatively, use Reddit API: https://www.reddit.com/prefs/apps (create script app)

**Twitter/X** (for social sentiment):
1. Go to https://developer.twitter.com/
2. Add `TWITTER_BEARER_TOKEN` to `.env` and set `ENABLE_TWITTER_SENTIMENT=true`

**NewsAPI** (for news sentiment):
1. Go to https://newsapi.org/

**Google Trends** - No API key required!

---

## Testing

Run unit tests:
```bash
# Test Phase 3 schema
PYTHONPATH=. python3 tests/test_phase3_schema.py

# Test sentiment analyzer
PYTHONPATH=. python3 tests/test_sentiment_analyzer.py
```