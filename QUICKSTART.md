# 🚀 Quick Start Guide

Get up and running with the Crypto Market Intelligence Dashboard in 5 minutes!

## Step 1: Install Dependencies

### Option A: Automated (Recommended)
```bash
./setup.sh
```

### Option B: Manual
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

## Step 2: Run the Pipeline

```bash
python3 main.py
```

**First run takes ~15-30 seconds** to fetch:
- 672 hourly price records (BTC & ETH, 14 days)
- 30 days of Fear & Greed sentiment
- 150 ETF flow records

## Step 3: Verify Success

You should see:
```
✅ Overall Success: True
📈 Data Ingested:
   • OHLC Records: 672 (✅)
   • Sentiment Records: 30 (✅)
   • ETF Flow Records: 150 (✅)
```

## Step 4: Explore the Data

### Check Database
```bash
sqlite3 data/market_intel.db

-- Try these queries:
SELECT COUNT(*) FROM ohlc_hourly;
SELECT * FROM sentiment_daily ORDER BY as_of_date DESC LIMIT 5;
SELECT * FROM daily_market_snapshot ORDER BY as_of_date DESC LIMIT 3;
```

### Check Logs
```bash
tail -f logs/ingestion_*.log
```

### Check CSV Backups
```bash
ls -lh data/backups/
```

## Step 5: View Dashboard (Optional)

```bash
streamlit run app.py
```

Open browser to `http://localhost:8501`

---

## Common Commands

```bash
# Run ingestion
python3 main.py

# Check status
python3 main.py --status

# Test setup
python3 test_pipeline.py

# View logs
tail -20 logs/ingestion_*.log

# Clean old backups (keeps last 30 days)
# Automatic on each run
```

## Troubleshooting

### "Module not found" errors
```bash
pip install -r requirements.txt
```

### "Permission denied" on macOS
```bash
# Use virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### API rate limits
Edit `.env`:
```bash
RATE_LIMIT_DELAY=3.0  # Increase delay
```

### No data returned
- Check internet connection
- Check logs: `tail logs/ingestion_*.log`
- CoinGecko API may be temporarily unavailable

---

## What's Next?

1. **Schedule Daily Runs**
   ```bash
   # Add to crontab (runs daily at 9 AM)
   0 9 * * * cd /path/to/crypto_tracker && python3 main.py
   ```

2. **Customize Configuration**
   - Edit `.env` file
   - Add CoinGecko Pro API key (optional)
   - Adjust rate limits

3. **Explore the Code**
   - Start with `main.py`
   - Read `AGENTS.md` for architecture
   - Check `PHASE1_COMPLETE.md` for details

---

**Need Help?** Check `README.md` or `PHASE1_COMPLETE.md` for detailed documentation.

