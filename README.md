# 📊 Crypto Market Intelligence Dashboard

Data-driven crypto market analysis combining real-time data with AI reasoning for actionable trading insights.

**Phase 1 Status:** ✅ **COMPLETE & OPERATIONAL** - Production-ready data ingestion system.

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

| Source | Data | Status |
|--------|------|--------|
| **CoinGecko** | BTC/ETH prices (14 days) | ✅ Active |
| **Alternative.me** | Fear & Greed Index (30 days) | ✅ Active |
| **SoSoValue** | ETF flows (300 days) | ✅ Active |

## 💾 Database

SQLite database with 4 tables:
- `ohlc_hourly` - Price data with trading sessions
- `sentiment_daily` - Fear & Greed sentiment
- `etf_flows_daily` - Institutional flows
- `daily_market_snapshot` - Consolidated metrics

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

Optional settings in `.env`:

```bash
SOSOVALUE_API_KEY=required
COINGECKO_API_KEY=optional
RATE_LIMIT_DELAY=1.5
ENABLE_CSV_BACKUP=true
LOG_LEVEL=INFO
```

## 🔧 Features

- ✅ Automated data ingestion from 3 sources
- ✅ SQLite database with idempotent writes
- ✅ Retry logic and rate limiting
- ✅ CSV backups and comprehensive logging
- ✅ Trading session classification
- ✅ No mock data - production ready

## 📝 Logs

Check `logs/ingestion_YYYYMMDD.log` for detailed execution information.

---

**Phase 1 Complete** ✅ | **Next: Dashboard Enhancement & AI Integration** 🚀

For detailed documentation, see `AGENTS.md`
