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
        Compute and store daily market snapshot from raw data (Phase 1 + Phase 2)
        
        Args:
            as_of_date: Date in YYYY-MM-DD format
        """
        logger.info(f"Computing daily snapshot for {as_of_date}")
        
        sql = """
            INSERT OR REPLACE INTO daily_market_snapshot
            (as_of_date, asset, price_close_usd, price_chg_24h_pct, volume_24h_usd,
             realized_vol_7d_pct, fng_value, fng_classification, 
             etf_net_flow_usd, dominant_session, btc_dominance_pct, market_cap_usd,
             avg_funding_rate_pct, open_interest_usd)
            
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
            ),
            
            market_metrics AS (
                SELECT 
                    asset,
                    volume_24h_usd,
                    market_cap_usd,
                    btc_dominance_pct
                FROM market_metrics_daily
                WHERE as_of_date = ?
            ),
            
            funding_agg AS (
                SELECT 
                    asset,
                    AVG(funding_rate_pct) as avg_funding_rate_pct
                FROM funding_rates_snapshots
                WHERE DATE(ts_utc) = ?
                GROUP BY asset
            ),
            
            open_interest_agg AS (
                SELECT 
                    asset,
                    open_interest_usd
                FROM open_interest_daily
                WHERE as_of_date = ?
            )
            
            SELECT 
                ? as as_of_date,
                pm.asset,
                pm.price_close_usd,
                pm.price_chg_24h_pct,
                mm.volume_24h_usd,
                v.realized_vol_7d_pct,
                s.fng_value,
                s.fng_classification,
                e.etf_net_flow_usd,
                'US' as dominant_session,
                mm.btc_dominance_pct,
                mm.market_cap_usd,
                fr.avg_funding_rate_pct,
                oi.open_interest_usd
            FROM price_metrics pm
            LEFT JOIN volatility v ON pm.asset = v.asset
            LEFT JOIN market_metrics mm ON pm.asset = mm.asset
            LEFT JOIN funding_agg fr ON pm.asset = fr.asset
            LEFT JOIN open_interest_agg oi ON pm.asset = oi.asset
            CROSS JOIN sentiment s
            CROSS JOIN etf_agg e
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (as_of_date, as_of_date, as_of_date, 
                                    as_of_date, as_of_date, as_of_date,
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
    
    def insert_market_metrics(self, records: List[Dict[str, Any]]) -> int:
        """
        Insert market metrics data (volume, dominance, market cap) - idempotent
        
        Args:
            records: List of market metrics with keys:
                     as_of_date, asset, volume_24h_usd, market_cap_usd, 
                     btc_dominance_pct, price_change_24h_pct, source
        
        Returns:
            Number of records inserted/updated
        """
        if not records:
            logger.warning("No market metrics records to insert")
            return 0
        
        sql = """
            INSERT OR REPLACE INTO market_metrics_daily 
            (as_of_date, asset, volume_24h_usd, market_cap_usd, 
             btc_dominance_pct, price_change_24h_pct, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                data = [
                    (
                        r['as_of_date'],
                        r['asset'],
                        r.get('volume_24h_usd'),
                        r.get('market_cap_usd'),
                        r.get('btc_dominance_pct'),
                        r.get('price_change_24h_pct'),
                        r.get('source', 'COINGECKO')
                    )
                    for r in records
                ]
                
                cursor.executemany(sql, data)
                conn.commit()
                
                count = cursor.rowcount
                logger.info(f"Inserted/updated {count} market metrics records")
                return count
                
        except sqlite3.Error as e:
            logger.error(f"Failed to insert market metrics: {e}")
            raise
    
    def insert_funding_rates(self, records: List[Dict[str, Any]]) -> int:
        """
        Insert funding rate snapshots (idempotent)
        
        Args:
            records: List of funding rate records with keys:
                     ts_utc, asset, funding_rate_pct, funding_interval_hours,
                     mark_price, source
        
        Returns:
            Number of records inserted/updated
        """
        if not records:
            logger.warning("No funding rate records to insert")
            return 0
        
        sql = """
            INSERT OR REPLACE INTO funding_rates_snapshots 
            (ts_utc, asset, funding_rate_pct, funding_interval_hours, 
             mark_price, source)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                data = [
                    (
                        r['ts_utc'],
                        r['asset'],
                        r['funding_rate_pct'],
                        r.get('funding_interval_hours', 8),
                        r.get('mark_price'),
                        r.get('source', 'BINANCE')
                    )
                    for r in records
                ]
                
                cursor.executemany(sql, data)
                conn.commit()
                
                count = cursor.rowcount
                logger.info(f"Inserted/updated {count} funding rate records")
                return count
                
        except sqlite3.Error as e:
            logger.error(f"Failed to insert funding rates: {e}")
            raise
    
    def insert_open_interest(self, records: List[Dict[str, Any]]) -> int:
        """
        Insert open interest data (idempotent)
        
        Args:
            records: List of open interest records with keys:
                     as_of_date, asset, open_interest_usd, 
                     open_interest_contracts, source
        
        Returns:
            Number of records inserted/updated
        """
        if not records:
            logger.warning("No open interest records to insert")
            return 0
        
        sql = """
            INSERT OR REPLACE INTO open_interest_daily 
            (as_of_date, asset, open_interest_usd, open_interest_contracts, source)
            VALUES (?, ?, ?, ?, ?)
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                data = [
                    (
                        r['as_of_date'],
                        r['asset'],
                        r['open_interest_usd'],
                        r.get('open_interest_contracts'),
                        r.get('source', 'BINANCE')
                    )
                    for r in records
                ]
                
                cursor.executemany(sql, data)
                conn.commit()
                
                count = cursor.rowcount
                logger.info(f"Inserted/updated {count} open interest records")
                return count
                
        except sqlite3.Error as e:
            logger.error(f"Failed to insert open interest: {e}")
            raise
    
    def insert_social_posts_raw(self, records: List[Dict[str, Any]]) -> int:
        """
        Insert raw social media posts (idempotent)
        
        Args:
            records: List of social post records with keys:
                     post_id, platform, subreddit, title, text, author,
                     created_utc, score, upvote_ratio, num_comments, url,
                     sentiment_compound, sentiment_pos, sentiment_neg, 
                     sentiment_neu, sentiment_label
        
        Returns:
            Number of records inserted/updated
        """
        if not records:
            logger.warning("No social post records to insert")
            return 0
        
        sql = """
            INSERT OR REPLACE INTO social_posts_raw 
            (post_id, platform, subreddit, title, text, author,
             created_utc, score, upvote_ratio, num_comments, url,
             sentiment_compound, sentiment_pos, sentiment_neg, 
             sentiment_neu, sentiment_label)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                data = [
                    (
                        r['id'],
                        r['platform'],
                        r.get('subreddit'),
                        r.get('title'),
                        r.get('text'),
                        r.get('author'),
                        r['created_utc'],
                        r.get('score'),
                        r.get('upvote_ratio'),
                        r.get('num_comments'),
                        r.get('url'),
                        r.get('sentiment_compound'),
                        r.get('sentiment_pos'),
                        r.get('sentiment_neg'),
                        r.get('sentiment_neu'),
                        r.get('sentiment_label')
                    )
                    for r in records
                ]
                
                cursor.executemany(sql, data)
                conn.commit()
                
                count = cursor.rowcount
                logger.info(f"Inserted/updated {count} raw social post records")
                return count
                
        except sqlite3.Error as e:
            logger.error(f"Failed to insert raw social posts: {e}")
            raise
    
    def insert_social_sentiment(self, records: List[Dict[str, Any]]) -> int:
        """
        Insert social sentiment data (idempotent)
        
        Args:
            records: List of social sentiment records with keys:
                     as_of_date, platform, mentions_count, sentiment_score,
                     positive_mentions, negative_mentions, neutral_mentions,
                     engagement_score, top_keywords, source
        
        Returns:
            Number of records inserted/updated
        """
        if not records:
            logger.warning("No social sentiment records to insert")
            return 0
        
        sql = """
            INSERT OR REPLACE INTO social_sentiment_daily 
            (as_of_date, platform, mentions_count, sentiment_score,
             positive_mentions, negative_mentions, neutral_mentions,
             engagement_score, top_keywords, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                data = [
                    (
                        r['as_of_date'],
                        r['platform'],
                        r.get('mentions_count', 0),
                        r.get('sentiment_score'),
                        r.get('positive_mentions', 0),
                        r.get('negative_mentions', 0),
                        r.get('neutral_mentions', 0),
                        r.get('engagement_score'),
                        r.get('top_keywords'),
                        r.get('source', 'REDDIT')
                    )
                    for r in records
                ]
                
                cursor.executemany(sql, data)
                conn.commit()
                
                count = cursor.rowcount
                logger.info(f"Inserted/updated {count} social sentiment records")
                return count
                
        except sqlite3.Error as e:
            logger.error(f"Failed to insert social sentiment: {e}")
            raise
    
    def insert_news_articles_raw(self, records: List[Dict[str, Any]]) -> int:
        """
        Insert raw news articles (idempotent)
        
        Args:
            records: List of news article records with keys:
                     url, title, description, source, author, published_at,
                     sentiment_compound, sentiment_label, sentiment_confidence,
                     positive_prob, negative_prob, neutral_prob
        
        Returns:
            Number of records inserted/updated
        """
        if not records:
            logger.warning("No news article records to insert")
            return 0
        
        sql = """
            INSERT OR REPLACE INTO news_articles_raw 
            (article_url, title, description, source, author, published_at,
             sentiment_compound, sentiment_label, sentiment_confidence,
             positive_prob, negative_prob, neutral_prob)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                data = [
                    (
                        r['url'],
                        r.get('title'),
                        r.get('description'),
                        r.get('source'),
                        r.get('author'),
                        r['published_at'],
                        r.get('sentiment_compound'),
                        r.get('sentiment_label'),
                        r.get('sentiment_confidence'),
                        r.get('positive_prob'),
                        r.get('negative_prob'),
                        r.get('neutral_prob')
                    )
                    for r in records
                ]
                
                cursor.executemany(sql, data)
                conn.commit()
                
                count = cursor.rowcount
                logger.info(f"Inserted/updated {count} raw news article records")
                return count
                
        except sqlite3.Error as e:
            logger.error(f"Failed to insert raw news articles: {e}")
            raise
    
    def insert_news_sentiment(self, records: List[Dict[str, Any]]) -> int:
        """
        Insert news sentiment data (idempotent)
        
        Args:
            records: List of news sentiment records with keys:
                     as_of_date, article_count, avg_sentiment,
                     positive_pct, negative_pct, neutral_pct,
                     top_sources, top_keywords, source
        
        Returns:
            Number of records inserted/updated
        """
        if not records:
            logger.warning("No news sentiment records to insert")
            return 0
        
        sql = """
            INSERT OR REPLACE INTO news_sentiment_daily 
            (as_of_date, article_count, avg_sentiment, positive_pct,
             negative_pct, neutral_pct, top_sources, top_keywords, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                data = [
                    (
                        r['as_of_date'],
                        r.get('article_count', 0),
                        r.get('avg_sentiment'),
                        r.get('positive_pct'),
                        r.get('negative_pct'),
                        r.get('neutral_pct'),
                        r.get('top_sources'),
                        r.get('top_keywords'),
                        r.get('source', 'NEWSAPI')
                    )
                    for r in records
                ]
                
                cursor.executemany(sql, data)
                conn.commit()
                
                count = cursor.rowcount
                logger.info(f"Inserted/updated {count} news sentiment records")
                return count
                
        except sqlite3.Error as e:
            logger.error(f"Failed to insert news sentiment: {e}")
            raise
    
    def insert_search_trends_raw(self, records: List[Dict[str, Any]]) -> int:
        """
        Insert raw search trends data (idempotent)
        
        Args:
            records: List of search trend records with keys:
                     ts_utc, keyword, interest_score, geo, timeframe
        
        Returns:
            Number of records inserted/updated
        """
        if not records:
            logger.warning("No search trend records to insert")
            return 0
        
        sql = """
            INSERT OR REPLACE INTO search_trends_raw 
            (ts_utc, keyword, interest_score, geo, timeframe)
            VALUES (?, ?, ?, ?, ?)
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                data = [
                    (
                        r['ts_utc'],
                        r['keyword'],
                        r['interest_score'],
                        r.get('geo', ''),
                        r.get('timeframe')
                    )
                    for r in records
                ]
                
                cursor.executemany(sql, data)
                conn.commit()
                
                count = cursor.rowcount
                logger.info(f"Inserted/updated {count} raw search trend records")
                return count
                
        except sqlite3.Error as e:
            logger.error(f"Failed to insert raw search trends: {e}")
            raise
    
    def insert_search_interest(self, records: List[Dict[str, Any]]) -> int:
        """
        Insert search interest data (idempotent)
        
        Args:
            records: List of search interest records with keys:
                     as_of_date, keyword, interest_score,
                     interest_change_pct, related_queries, source
        
        Returns:
            Number of records inserted/updated
        """
        if not records:
            logger.warning("No search interest records to insert")
            return 0
        
        sql = """
            INSERT OR REPLACE INTO search_interest_daily 
            (as_of_date, keyword, interest_score, interest_change_pct,
             related_queries, source)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                data = [
                    (
                        r['as_of_date'],
                        r['keyword'],
                        r['interest_score'],
                        r.get('interest_change_pct'),
                        r.get('related_queries'),
                        r.get('source', 'GOOGLE_TRENDS')
                    )
                    for r in records
                ]
                
                cursor.executemany(sql, data)
                conn.commit()
                
                count = cursor.rowcount
                logger.info(f"Inserted/updated {count} search interest records")
                return count
                
        except sqlite3.Error as e:
            logger.error(f"Failed to insert search interest: {e}")
            raise
    
    def compute_social_sentiment_from_raw(self, as_of_date: str) -> None:
        """
        Compute and store daily social sentiment from raw posts
        
        Args:
            as_of_date: Date in YYYY-MM-DD format
        """
        logger.info(f"Computing social sentiment from raw data for {as_of_date}")
        
        sql = """
            INSERT OR REPLACE INTO social_sentiment_daily
            (as_of_date, platform, mentions_count, sentiment_score,
             positive_mentions, negative_mentions, neutral_mentions,
             engagement_score, top_keywords, source)
            
            WITH post_stats AS (
                SELECT 
                    DATE(created_utc) as post_date,
                    platform,
                    COUNT(*) as mentions_count,
                    AVG(sentiment_compound) as sentiment_score,
                    SUM(CASE WHEN sentiment_label = 'POSITIVE' THEN 1 ELSE 0 END) as positive_mentions,
                    SUM(CASE WHEN sentiment_label = 'NEGATIVE' THEN 1 ELSE 0 END) as negative_mentions,
                    SUM(CASE WHEN sentiment_label = 'NEUTRAL' THEN 1 ELSE 0 END) as neutral_mentions,
                    AVG(score * 1.0 + num_comments * 2.0) as engagement_score
                FROM social_posts_raw
                WHERE DATE(created_utc) = ?
                GROUP BY DATE(created_utc), platform
            )
            
            SELECT 
                ? as as_of_date,
                platform,
                mentions_count,
                sentiment_score,
                positive_mentions,
                negative_mentions,
                neutral_mentions,
                engagement_score,
                '' as top_keywords,
                'REDDIT' as source
            FROM post_stats
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (as_of_date, as_of_date))
                conn.commit()
                logger.info(f"Social sentiment computed from raw data for {as_of_date}")
                
        except sqlite3.Error as e:
            logger.error(f"Failed to compute social sentiment from raw: {e}")
            raise
    
    def compute_news_sentiment_from_raw(self, as_of_date: str) -> None:
        """
        Compute and store daily news sentiment from raw articles
        
        Args:
            as_of_date: Date in YYYY-MM-DD format
        """
        logger.info(f"Computing news sentiment from raw data for {as_of_date}")
        
        sql = """
            INSERT OR REPLACE INTO news_sentiment_daily
            (as_of_date, article_count, avg_sentiment, positive_pct,
             negative_pct, neutral_pct, top_sources, top_keywords, source)
            
            WITH article_stats AS (
                SELECT 
                    DATE(published_at) as pub_date,
                    COUNT(*) as article_count,
                    AVG(sentiment_compound) as avg_sentiment,
                    (SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as positive_pct,
                    (SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as negative_pct,
                    (SUM(CASE WHEN sentiment_label = 'neutral' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as neutral_pct
                FROM news_articles_raw
                WHERE DATE(published_at) = ?
                GROUP BY DATE(published_at)
            )
            
            SELECT 
                ? as as_of_date,
                article_count,
                avg_sentiment,
                positive_pct,
                negative_pct,
                neutral_pct,
                '' as top_sources,
                '' as top_keywords,
                'NEWSAPI' as source
            FROM article_stats
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (as_of_date, as_of_date))
                conn.commit()
                logger.info(f"News sentiment computed from raw data for {as_of_date}")
                
        except sqlite3.Error as e:
            logger.error(f"Failed to compute news sentiment from raw: {e}")
            raise
    
    def compute_search_interest_from_raw(self, as_of_date: str) -> None:
        """
        Compute and store daily search interest from raw trends
        
        Args:
            as_of_date: Date in YYYY-MM-DD format
        """
        logger.info(f"Computing search interest from raw data for {as_of_date}")
        
        sql = """
            INSERT OR REPLACE INTO search_interest_daily
            (as_of_date, keyword, interest_score, interest_change_pct,
             related_queries, source)
            
            WITH daily_interest AS (
                SELECT 
                    DATE(ts_utc) as trend_date,
                    keyword,
                    AVG(interest_score) as interest_score
                FROM search_trends_raw
                WHERE DATE(ts_utc) = ?
                GROUP BY DATE(ts_utc), keyword
            ),
            
            prev_interest AS (
                SELECT 
                    DATE(ts_utc) as trend_date,
                    keyword,
                    AVG(interest_score) as prev_score
                FROM search_trends_raw
                WHERE DATE(ts_utc) = DATE(?, '-1 day')
                GROUP BY DATE(ts_utc), keyword
            )
            
            SELECT 
                ? as as_of_date,
                di.keyword,
                di.interest_score,
                CASE 
                    WHEN pi.prev_score IS NOT NULL AND pi.prev_score > 0
                    THEN ((di.interest_score - pi.prev_score) / pi.prev_score * 100)
                    ELSE NULL
                END as interest_change_pct,
                '' as related_queries,
                'GOOGLE_TRENDS' as source
            FROM daily_interest di
            LEFT JOIN prev_interest pi ON di.keyword = pi.keyword
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (as_of_date, as_of_date, as_of_date))
                conn.commit()
                logger.info(f"Search interest computed from raw data for {as_of_date}")
                
        except sqlite3.Error as e:
            logger.error(f"Failed to compute search interest from raw: {e}")
            raise
    
    def get_record_counts(self) -> Dict[str, int]:
        """Get record counts for all tables"""
        tables = ['ohlc_hourly', 'sentiment_daily', 'etf_flows_daily', 
                  'daily_market_snapshot', 'market_metrics_daily',
                  'funding_rates_snapshots', 'open_interest_daily',
                  'social_posts_raw', 'social_sentiment_daily',
                  'news_articles_raw', 'news_sentiment_daily',
                  'search_trends_raw', 'search_interest_daily']
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

