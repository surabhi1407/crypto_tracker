"""Database operations for data ingestion and retrieval"""
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from src.storage.schema import DatabaseSchema
from src.utils.logger import setup_logger

logger = setup_logger()


class MarketDatabase:
    """Handles all database operations with idempotent writes"""
    
    def __init__(self, db_path: str):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.schema = DatabaseSchema(db_path)
        
        # Initialize schema if needed
        if not self.schema.verify_schema():
            self.schema.initialize_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def insert_ohlc_data(self, records: List[Dict[str, Any]]) -> int:
        """
        Insert OHLC hourly data (idempotent - uses REPLACE)
        
        Args:
            records: List of OHLC records with keys:
                     asset, ts_utc, open, high, low, close, session
        
        Returns:
            Number of records inserted/updated
        """
        if not records:
            logger.warning("No OHLC records to insert")
            return 0
        
        sql = """
            INSERT OR REPLACE INTO ohlc_hourly 
            (asset, ts_utc, open, high, low, close, session)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                data = [
                    (
                        r['asset'],
                        r['ts_utc'],
                        r['open'],
                        r['high'],
                        r['low'],
                        r['close'],
                        r.get('session')
                    )
                    for r in records
                ]
                
                cursor.executemany(sql, data)
                conn.commit()
                
                count = cursor.rowcount
                logger.info(f"Inserted/updated {count} OHLC records")
                return count
                
        except sqlite3.Error as e:
            logger.error(f"Failed to insert OHLC data: {e}")
            raise
    
    def insert_sentiment_data(self, records: List[Dict[str, Any]]) -> int:
        """
        Insert sentiment (Fear & Greed) data (idempotent)
        
        Args:
            records: List of sentiment records with keys:
                     as_of_date, fng_value, classification
        
        Returns:
            Number of records inserted/updated
        """
        if not records:
            logger.warning("No sentiment records to insert")
            return 0
        
        sql = """
            INSERT OR REPLACE INTO sentiment_daily 
            (as_of_date, fng_value, classification)
            VALUES (?, ?, ?)
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                data = [
                    (r['as_of_date'], r['fng_value'], r['classification'])
                    for r in records
                ]
                
                cursor.executemany(sql, data)
                conn.commit()
                
                count = cursor.rowcount
                logger.info(f"Inserted/updated {count} sentiment records")
                return count
                
        except sqlite3.Error as e:
            logger.error(f"Failed to insert sentiment data: {e}")
            raise
    
    def insert_etf_flows(self, records: List[Dict[str, Any]]) -> int:
        """
        Insert ETF flow data (idempotent)
        
        Args:
            records: List of ETF flow records with keys:
                     as_of_date, ticker, net_flow_usd, aum_usd, source
        
        Returns:
            Number of records inserted/updated
        """
        if not records:
            logger.warning("No ETF flow records to insert")
            return 0
        
        sql = """
            INSERT OR REPLACE INTO etf_flows_daily 
            (as_of_date, ticker, net_flow_usd, aum_usd, source)
            VALUES (?, ?, ?, ?, ?)
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                data = [
                    (
                        r['as_of_date'],
                        r['ticker'],
                        r.get('net_flow_usd'),
                        r.get('aum_usd'),
                        r.get('source', 'API')
                    )
                    for r in records
                ]
                
                cursor.executemany(sql, data)
                conn.commit()
                
                count = cursor.rowcount
                logger.info(f"Inserted/updated {count} ETF flow records")
                return count
                
        except sqlite3.Error as e:
            logger.error(f"Failed to insert ETF flow data: {e}")
            raise
    
    def compute_daily_snapshot(self, as_of_date: str) -> None:
        """
        Compute and store daily market snapshot from raw data
        
        Args:
            as_of_date: Date in YYYY-MM-DD format
        """
        logger.info(f"Computing daily snapshot for {as_of_date}")
        
        sql = """
            INSERT OR REPLACE INTO daily_market_snapshot
            (as_of_date, asset, price_close_usd, price_chg_24h_pct, 
             realized_vol_7d_pct, fng_value, fng_classification, 
             etf_net_flow_usd, dominant_session)
            
            WITH latest_prices AS (
                SELECT 
                    asset,
                    close as price_close_usd,
                    ts_utc,
                    LAG(close, 24) OVER (PARTITION BY asset ORDER BY ts_utc) as price_24h_ago
                FROM ohlc_hourly
                WHERE DATE(ts_utc) = ?
            ),
            
            price_metrics AS (
                SELECT 
                    asset,
                    price_close_usd,
                    CASE 
                        WHEN price_24h_ago IS NOT NULL 
                        THEN ((price_close_usd - price_24h_ago) / price_24h_ago * 100)
                        ELSE NULL
                    END as price_chg_24h_pct
                FROM latest_prices
                WHERE ts_utc = (SELECT MAX(ts_utc) FROM latest_prices)
            ),
            
            volatility AS (
                SELECT 
                    asset,
                    -- SQLite doesn't have STDEV, so we calculate manually
                    -- Coefficient of variation: (stddev / mean) * 100
                    -- stddev = sqrt(avg(x^2) - avg(x)^2)
                    (SQRT(AVG(close * close) - AVG(close) * AVG(close)) / AVG(close)) * 100 as realized_vol_7d_pct
                FROM ohlc_hourly
                WHERE ts_utc >= DATE(?, '-7 days')
                  AND ts_utc <= DATE(?)
                GROUP BY asset
            ),
            
            sentiment AS (
                SELECT fng_value, classification as fng_classification
                FROM sentiment_daily
                WHERE as_of_date = ?
            ),
            
            etf_agg AS (
                SELECT SUM(net_flow_usd) as etf_net_flow_usd
                FROM etf_flows_daily
                WHERE as_of_date = ?
            )
            
            SELECT 
                ? as as_of_date,
                pm.asset,
                pm.price_close_usd,
                pm.price_chg_24h_pct,
                v.realized_vol_7d_pct,
                s.fng_value,
                s.fng_classification,
                e.etf_net_flow_usd,
                'US' as dominant_session
            FROM price_metrics pm
            LEFT JOIN volatility v ON pm.asset = v.asset
            CROSS JOIN sentiment s
            CROSS JOIN etf_agg e
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (as_of_date, as_of_date, as_of_date, 
                                    as_of_date, as_of_date, as_of_date))
                conn.commit()
                logger.info(f"Daily snapshot computed for {as_of_date}")
                
        except sqlite3.Error as e:
            logger.error(f"Failed to compute daily snapshot: {e}")
            raise
    
    def get_latest_ohlc_timestamp(self, asset: str) -> Optional[datetime]:
        """Get the latest timestamp for an asset's OHLC data"""
        sql = "SELECT MAX(ts_utc) FROM ohlc_hourly WHERE asset = ?"
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (asset,))
                result = cursor.fetchone()
                
                if result and result[0]:
                    return datetime.fromisoformat(result[0])
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get latest timestamp: {e}")
            return None
    
    def get_record_counts(self) -> Dict[str, int]:
        """Get record counts for all tables"""
        tables = ['ohlc_hourly', 'sentiment_daily', 'etf_flows_daily', 
                  'daily_market_snapshot']
        counts = {}
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    counts[table] = cursor.fetchone()[0]
                
                return counts
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get record counts: {e}")
            return {}

