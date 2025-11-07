"""Database schema definitions for SQLite"""
import sqlite3
from pathlib import Path
from typing import Optional
from src.utils.logger import setup_logger

logger = setup_logger()


class DatabaseSchema:
    """Manages database schema creation and migrations"""
    
    # Schema version for future migrations
    SCHEMA_VERSION = 2  # Updated for Phase 2
    
    # Table creation SQL statements
    TABLES = {
        'ohlc_hourly': """
            CREATE TABLE IF NOT EXISTS ohlc_hourly (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset TEXT NOT NULL,
                ts_utc TIMESTAMP NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                session TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(asset, ts_utc)
            )
        """,
        
        'sentiment_daily': """
            CREATE TABLE IF NOT EXISTS sentiment_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                as_of_date DATE NOT NULL UNIQUE,
                fng_value INTEGER NOT NULL,
                classification TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        
        'etf_flows_daily': """
            CREATE TABLE IF NOT EXISTS etf_flows_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                as_of_date DATE NOT NULL,
                ticker TEXT NOT NULL,
                net_flow_usd REAL,
                aum_usd REAL,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(as_of_date, ticker)
            )
        """,
        
        'market_metrics_daily': """
            CREATE TABLE IF NOT EXISTS market_metrics_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                as_of_date DATE NOT NULL,
                asset TEXT NOT NULL,
                volume_24h_usd REAL,
                market_cap_usd REAL,
                btc_dominance_pct REAL,
                price_change_24h_pct REAL,
                source TEXT DEFAULT 'COINGECKO',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(as_of_date, asset)
            )
        """,
        
        'funding_rates_snapshots': """
            CREATE TABLE IF NOT EXISTS funding_rates_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_utc TIMESTAMP NOT NULL,
                asset TEXT NOT NULL,
                funding_rate_pct REAL NOT NULL,
                funding_interval_hours INTEGER DEFAULT 8,
                mark_price REAL,
                source TEXT DEFAULT 'BINANCE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ts_utc, asset, source)
            )
        """,
        
        'open_interest_daily': """
            CREATE TABLE IF NOT EXISTS open_interest_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                as_of_date DATE NOT NULL,
                asset TEXT NOT NULL,
                open_interest_usd REAL NOT NULL,
                open_interest_contracts REAL,
                source TEXT DEFAULT 'BINANCE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(as_of_date, asset, source)
            )
        """,
        
        'daily_market_snapshot': """
            CREATE TABLE IF NOT EXISTS daily_market_snapshot (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                as_of_date DATE NOT NULL,
                asset TEXT NOT NULL,
                price_close_usd REAL,
                price_chg_24h_pct REAL,
                volume_24h_usd REAL,
                realized_vol_7d_pct REAL,
                fng_value INTEGER,
                fng_classification TEXT,
                etf_net_flow_usd REAL,
                dominant_session TEXT,
                btc_dominance_pct REAL,
                market_cap_usd REAL,
                avg_funding_rate_pct REAL,
                open_interest_usd REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(as_of_date, asset)
            )
        """,
        
        'schema_version': """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
    }
    
    # Index definitions for query performance
    INDEXES = [
        # Phase 1 indexes
        "CREATE INDEX IF NOT EXISTS idx_ohlc_asset_ts ON ohlc_hourly(asset, ts_utc)",
        "CREATE INDEX IF NOT EXISTS idx_ohlc_ts ON ohlc_hourly(ts_utc)",
        "CREATE INDEX IF NOT EXISTS idx_sentiment_date ON sentiment_daily(as_of_date)",
        "CREATE INDEX IF NOT EXISTS idx_etf_date ON etf_flows_daily(as_of_date)",
        "CREATE INDEX IF NOT EXISTS idx_etf_ticker ON etf_flows_daily(ticker)",
        "CREATE INDEX IF NOT EXISTS idx_snapshot_date ON daily_market_snapshot(as_of_date)",
        "CREATE INDEX IF NOT EXISTS idx_snapshot_asset ON daily_market_snapshot(asset)",
        
        # Phase 2 indexes
        "CREATE INDEX IF NOT EXISTS idx_market_metrics_date ON market_metrics_daily(as_of_date)",
        "CREATE INDEX IF NOT EXISTS idx_market_metrics_asset ON market_metrics_daily(asset)",
        "CREATE INDEX IF NOT EXISTS idx_funding_ts ON funding_rates_snapshots(ts_utc)",
        "CREATE INDEX IF NOT EXISTS idx_funding_asset ON funding_rates_snapshots(asset)",
        "CREATE INDEX IF NOT EXISTS idx_oi_date ON open_interest_daily(as_of_date)",
        "CREATE INDEX IF NOT EXISTS idx_oi_asset ON open_interest_daily(asset)",
    ]
    
    def __init__(self, db_path: str):
        """
        Initialize schema manager
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def initialize_database(self) -> None:
        """Create all tables and indexes if they don't exist"""
        logger.info(f"Initializing database at {self.db_path}")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create tables
                for table_name, create_sql in self.TABLES.items():
                    logger.debug(f"Creating table: {table_name}")
                    cursor.execute(create_sql)
                
                # Create indexes
                for index_sql in self.INDEXES:
                    logger.debug(f"Creating index")
                    cursor.execute(index_sql)
                
                # Record schema version
                cursor.execute(
                    "INSERT OR IGNORE INTO schema_version (version) VALUES (?)",
                    (self.SCHEMA_VERSION,)
                )
                
                conn.commit()
                logger.info("Database initialization complete")
                
        except sqlite3.Error as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def get_current_version(self) -> Optional[int]:
        """Get current schema version"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(version) FROM schema_version")
                result = cursor.fetchone()
                return result[0] if result else None
        except sqlite3.Error:
            return None
    
    def verify_schema(self) -> bool:
        """Verify all required tables exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                existing_tables = {row[0] for row in cursor.fetchall()}
                
                required_tables = set(self.TABLES.keys())
                missing_tables = required_tables - existing_tables
                
                if missing_tables:
                    logger.warning(f"Missing tables: {missing_tables}")
                    return False
                
                logger.info("Schema verification passed")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Schema verification failed: {e}")
            return False

