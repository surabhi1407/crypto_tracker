# 📊 Crypto Market Intelligence Dashboard

A data-driven crypto market analysis system that combines **real-time market data** with **AI reasoning** to provide actionable trading insights.

## 🎯 Current Status: Phase 1 - Data Ingestion Layer ✅

The foundation is complete! The system now automatically ingests, normalizes, and stores crypto market signals from multiple sources.

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template (optional - works with defaults)
cp .env.example .env
```

### Run Data Ingestion

```bash
# Run the full ingestion pipeline
python main.py

# Check database status
python main.py --status
```

## 📁 Project Structure

```
crypto_tracker/
├── main.py                    # Entry point for ingestion pipeline
├── app.py                     # Streamlit dashboard (existing)
├── AGENTS.md                  # Detailed project specification
├── requirements.txt           # Python dependencies
├── src/
│   ├── connectors/           # API connectors
│   │   ├── base.py          # Base connector with retry logic
│   │   ├── coingecko.py     # CoinGecko API (BTC/ETH prices)
│   │   ├── fear_greed.py    # Alternative.me (sentiment)
│   │   └── etf_flows.py     # ETF flow data (mock for now)
│   ├── storage/             # Database layer
│   │   ├── schema.py        # SQLite schema definitions
│   │   └── database.py      # Database operations
│   └── utils/               # Utilities
│       ├── logger.py        # Logging configuration
│       ├── time_utils.py    # Time/timezone helpers
│       ├── csv_backup.py    # CSV backup functionality
│       └── config.py        # Environment configuration
├── data/
│   ├── market_intel.db      # SQLite database (created on first run)
│   └── backups/             # CSV backups (optional)
└── logs/                     # Application logs
```

## 📊 Data Sources (Phase 1)

| Source | Data Type | Update Frequency |
|--------|-----------|------------------|
| **CoinGecko** | BTC/ETH OHLC prices | Hourly (14-day window) |
| **Alternative.me** | Fear & Greed Index | Daily (30-day history) |
| **ETF Flows** | Institutional flows | Daily (mock data for now) |

## 💾 Database Schema

### Tables

1. **ohlc_hourly** - Hourly price data with trading sessions
2. **sentiment_daily** - Fear & Greed sentiment index
3. **etf_flows_daily** - ETF inflow/outflow data
4. **daily_market_snapshot** - Consolidated daily metrics

See `src/storage/schema.py` for detailed schema definitions.

## 🔧 Configuration

Create a `.env` file to customize settings (optional):

```bash
# Database
DB_PATH=data/market_intel.db

# API Settings
COINGECKO_API_KEY=          # Optional: Pro API key
RATE_LIMIT_DELAY=1.5        # Seconds between API calls

# CSV Backups
ENABLE_CSV_BACKUP=true
CSV_BACKUP_PATH=data/backups

# Logging
LOG_LEVEL=INFO
```

## 📈 Features

### ✅ Implemented (Phase 1)

- [x] Automated data ingestion from multiple APIs
- [x] SQLite database with normalized schema
- [x] Idempotent writes (no duplicates)
- [x] Retry logic and rate limiting
- [x] CSV backup functionality
- [x] Comprehensive logging
- [x] Trading session classification (ASIA/EUROPE/US)
- [x] Daily market snapshots with computed metrics

### 🔜 Coming Next (Phase 2)

- [ ] Enhanced Streamlit dashboard with historical data
- [ ] Volatility analysis and trend indicators
- [ ] ETF flow visualization
- [ ] AI-powered market summaries
- [ ] Trading signal generation (BUY/HOLD/WATCH)

## 🧪 Testing the Pipeline

```bash
# Run ingestion (fetches last 14 days of data)
python main.py

# Expected output:
# ✅ OHLC Records: ~672 (14 days × 24 hours × 2 assets)
# ✅ Sentiment Records: 30
# ✅ ETF Flow Records: 150 (mock data)
# ✅ Daily Snapshots: 7
```

## 📝 Logs

Logs are stored in `logs/ingestion_YYYYMMDD.log` with detailed information about:
- API requests and responses
- Database operations
- Errors and warnings
- Performance metrics

## 🤖 Agent Architecture

This project uses an agent-based design documented in `AGENTS.md`:

- **IngestionAgent** - Orchestrates daily data pipeline
- **SchemaAgent** - Manages database schema evolution
- **MetricsAgent** (Phase 2) - Computes derived metrics

## 🛠️ Development

### Adding a New Data Source

1. Create connector in `src/connectors/`
2. Extend schema in `src/storage/schema.py`
3. Add ingestion step in `src/ingestion_pipeline.py`
4. Update `AGENTS.md` signal pillars table

### Running the Dashboard

```bash
streamlit run app.py
```

## 📚 Documentation

- **AGENTS.md** - Complete project specification and agent context
- **Code Comments** - Inline documentation in all modules
- **Logs** - Detailed execution logs in `logs/` directory

## 🔐 Security Notes

- No API keys required for basic functionality
- All credentials should be stored in `.env` (not committed)
- Rate limiting prevents API abuse
- Sandbox-ready (no external writes beyond workspace)

## 📄 License

MIT License - See LICENSE file for details

---

**Phase 1 Complete** ✅ | **Next: Dashboard Enhancement & AI Integration** 🚀