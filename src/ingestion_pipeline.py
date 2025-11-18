"""Main ingestion pipeline orchestrator"""
from typing import Dict, Any, List
from datetime import datetime
from src.connectors.coingecko import CoinGeckoConnector
from src.connectors.fear_greed import FearGreedConnector
from src.connectors.etf_flows import ETFFlowsConnector
from src.connectors.market_metrics import MarketMetricsConnector
from src.connectors.binance_futures import BinanceFuturesConnector
from src.connectors.reddit_connector import RedditConnector
from src.connectors.reddit_rss_connector import RedditRSSConnector
from src.connectors.twitter_connector import TwitterConnector
from src.connectors.news_connector import NewsConnector
from src.connectors.trends_connector import TrendsConnector
from src.storage.database import MarketDatabase
from src.utils.csv_backup import CSVBackup
from src.utils.config import Config
from src.utils.logger import setup_logger
from src.utils.time_utils import get_date_string

logger = setup_logger()


class IngestionPipeline:
    """Orchestrates daily data ingestion from multiple sources"""
    
    def __init__(self):
        """Initialize pipeline with connectors and database"""
        logger.info("Initializing Ingestion Pipeline")
        
        # Validate configuration
        Config.validate()
        
        # Initialize Phase 1 connectors
        self.coingecko = CoinGeckoConnector(
            api_key=Config.COINGECKO_API_KEY,
            rate_limit_delay=Config.RATE_LIMIT_DELAY
        )
        self.fear_greed = FearGreedConnector(
            rate_limit_delay=Config.RATE_LIMIT_DELAY
        )
        self.etf_flows = ETFFlowsConnector(
            api_key=Config.SOSOVALUE_API_KEY,
            rate_limit_delay=Config.RATE_LIMIT_DELAY
        )
        
        # Initialize Phase 2 connectors
        self.market_metrics = None
        self.binance_futures = None
        
        if Config.ENABLE_MARKET_METRICS:
            self.market_metrics = MarketMetricsConnector(
                api_key=Config.COINGECKO_API_KEY,
                rate_limit_delay=Config.RATE_LIMIT_DELAY
            )
            logger.info("Market metrics connector enabled")
        
        if Config.ENABLE_DERIVATIVES_DATA:
            self.binance_futures = BinanceFuturesConnector(
                rate_limit_delay=0.5
            )
            logger.info("Binance futures connector enabled")
        
        # Initialize Phase 3 connectors
        self.reddit = None
        self.reddit_rss = None
        self.twitter = None
        self.news = None
        self.trends = None
        
        # Reddit: Try API first, fallback to RSS if API unavailable
        if Config.ENABLE_SOCIAL_SENTIMENT and Config.REDDIT_CLIENT_ID:
            try:
                self.reddit = RedditConnector(
                    client_id=Config.REDDIT_CLIENT_ID,
                    client_secret=Config.REDDIT_CLIENT_SECRET,
                    user_agent=Config.REDDIT_USER_AGENT,
                    rate_limit_delay=2.0
                )
                logger.info("Reddit API connector enabled")
            except Exception as e:
                logger.warning(f"Reddit API connector initialization failed: {e}")
        
        # Reddit RSS fallback (no API key required)
        if Config.ENABLE_REDDIT_RSS or (Config.ENABLE_SOCIAL_SENTIMENT and not self.reddit):
            try:
                self.reddit_rss = RedditRSSConnector(rate_limit_delay=2.0)
                logger.info("Reddit RSS connector enabled (no API key required)")
            except Exception as e:
                logger.warning(f"Reddit RSS connector initialization failed: {e}")
        
        # Twitter connector
        if Config.ENABLE_TWITTER_SENTIMENT and Config.TWITTER_BEARER_TOKEN:
            try:
                self.twitter = TwitterConnector(
                    bearer_token=Config.TWITTER_BEARER_TOKEN,
                    rate_limit_delay=1.0
                )
                logger.info("Twitter connector enabled")
            except Exception as e:
                logger.warning(f"Twitter connector initialization failed: {e}")
        
        if Config.ENABLE_NEWS_SENTIMENT and Config.NEWSAPI_KEY:
            try:
                self.news = NewsConnector(
                    api_key=Config.NEWSAPI_KEY,
                    rate_limit_delay=1.0
                )
                logger.info("News connector enabled")
            except Exception as e:
                logger.warning(f"News connector initialization failed: {e}")
        
        if Config.ENABLE_SEARCH_TRENDS:
            try:
                self.trends = TrendsConnector(
                    rate_limit_delay=2.0
                )
                logger.info("Google Trends connector enabled")
            except Exception as e:
                logger.warning(f"Trends connector initialization failed: {e}")
        
        # Initialize database
        self.db = MarketDatabase(Config.DB_PATH)
        
        # Initialize CSV backup if enabled
        self.csv_backup = None
        if Config.ENABLE_CSV_BACKUP:
            self.csv_backup = CSVBackup(Config.CSV_BACKUP_PATH)
        
        logger.info("Pipeline initialization complete")
    
    def ingest_ohlc_data(self) -> Dict[str, Any]:
        """
        Ingest OHLC data for tracked assets
        
        Returns:
            Dictionary with ingestion statistics
        """
        logger.info("Starting OHLC data ingestion")
        stats = {'success': False, 'records': 0, 'errors': []}
        
        try:
            all_records = []
            
            for asset in Config.TRACKED_ASSETS:
                logger.info(f"Fetching OHLC data for {asset}")
                records = self.coingecko.fetch_ohlc_hourly(
                    coin_id=asset,
                    vs_currency='usd',
                    days=14
                )
                
                if records:
                    all_records.extend(records)
                    logger.info(f"Fetched {len(records)} records for {asset}")
                else:
                    logger.warning(f"No OHLC data received for {asset}")
            
            if all_records:
                # Insert into database
                count = self.db.insert_ohlc_data(all_records)
                stats['records'] = count
                stats['success'] = True
                
                # CSV backup if enabled
                if self.csv_backup:
                    self.csv_backup.save_ohlc_backup(all_records)
                
                logger.info(f"OHLC ingestion complete: {count} records")
            else:
                logger.warning("No OHLC data to ingest")
            
        except Exception as e:
            logger.error(f"OHLC ingestion failed: {e}")
            stats['errors'].append(str(e))
        
        return stats
    
    def ingest_sentiment_data(self, days: int = 7) -> Dict[str, Any]:
        """
        Ingest Fear & Greed sentiment data
        
        Args:
            days: Number of days to fetch (default: 7 for daily sync)
        
        Returns:
            Dictionary with ingestion statistics
        """
        logger.info(f"Starting sentiment data ingestion (last {days} days)")
        stats = {'success': False, 'records': 0, 'errors': []}
        
        try:
            records = self.fear_greed.fetch_fear_greed_index(limit=days)
            
            if records:
                # Insert into database
                count = self.db.insert_sentiment_data(records)
                stats['records'] = count
                stats['success'] = True
                
                # CSV backup if enabled
                if self.csv_backup:
                    self.csv_backup.save_sentiment_backup(records)
                
                logger.info(f"Sentiment ingestion complete: {count} records")
            else:
                logger.warning("No sentiment data to ingest")
            
        except Exception as e:
            logger.error(f"Sentiment ingestion failed: {e}")
            stats['errors'].append(str(e))
        
        return stats
    
    def ingest_etf_flows(self, days: int = 7) -> Dict[str, Any]:
        """
        Ingest ETF flow data
        
        Args:
            days: Number of days to fetch (default: 7 for daily sync)
        
        Returns:
            Dictionary with ingestion statistics
        """
        logger.info(f"Starting ETF flows ingestion (last {days} days)")
        stats = {'success': False, 'records': 0, 'errors': []}
        
        try:
            records = self.etf_flows.fetch_etf_flows(days=days)
            
            if records:
                # Insert into database
                count = self.db.insert_etf_flows(records)
                stats['records'] = count
                stats['success'] = True
                
                # CSV backup if enabled
                if self.csv_backup:
                    self.csv_backup.save_etf_backup(records)
                
                logger.info(f"ETF flows ingestion complete: {count} records")
            else:
                logger.warning("No ETF flow data to ingest")
            
        except Exception as e:
            logger.error(f"ETF flows ingestion failed: {e}")
            stats['errors'].append(str(e))
        
        return stats
    
    def ingest_market_metrics(self) -> Dict[str, Any]:
        """
        Ingest market metrics (volume, dominance, market cap)
        
        Returns:
            Dictionary with ingestion statistics
        """
        if not self.market_metrics:
            logger.info("Market metrics connector disabled, skipping")
            return {'success': True, 'records': 0, 'errors': [], 'skipped': True}
        
        logger.info("Starting market metrics ingestion")
        stats = {'success': False, 'records': 0, 'errors': []}
        
        try:
            records = self.market_metrics.fetch_data(
                coin_ids=Config.TRACKED_ASSETS
            )
            
            if records:
                # Insert into database
                count = self.db.insert_market_metrics(records)
                stats['records'] = count
                stats['success'] = True
                
                logger.info(f"Market metrics ingestion complete: {count} records")
            else:
                logger.warning("No market metrics data to ingest")
            
        except Exception as e:
            logger.error(f"Market metrics ingestion failed: {e}")
            stats['errors'].append(str(e))
        
        return stats
    
    def ingest_funding_rates(self) -> Dict[str, Any]:
        """
        Ingest funding rates from Binance Futures
        
        Returns:
            Dictionary with ingestion statistics
        """
        if not self.binance_futures:
            logger.info("Binance futures connector disabled, skipping funding rates")
            return {'success': True, 'records': 0, 'errors': [], 'skipped': True}
        
        logger.info("Starting funding rates ingestion")
        stats = {'success': False, 'records': 0, 'errors': []}
        
        try:
            records = self.binance_futures.fetch_funding_rates_for_assets(
                coin_ids=Config.TRACKED_ASSETS
            )
            
            if records:
                # Insert into database
                count = self.db.insert_funding_rates(records)
                stats['records'] = count
                stats['success'] = True
                
                logger.info(f"Funding rates ingestion complete: {count} records")
            else:
                logger.warning("No funding rate data to ingest")
            
        except Exception as e:
            logger.error(f"Funding rates ingestion failed: {e}")
            stats['errors'].append(str(e))
        
        return stats
    
    def ingest_open_interest(self) -> Dict[str, Any]:
        """
        Ingest open interest from Binance Futures
        
        Returns:
            Dictionary with ingestion statistics
        """
        if not self.binance_futures:
            logger.info("Binance futures connector disabled, skipping open interest")
            return {'success': True, 'records': 0, 'errors': [], 'skipped': True}
        
        logger.info("Starting open interest ingestion")
        stats = {'success': False, 'records': 0, 'errors': []}
        
        try:
            records = self.binance_futures.fetch_open_interest_for_assets(
                coin_ids=Config.TRACKED_ASSETS
            )
            
            if records:
                # Insert into database
                count = self.db.insert_open_interest(records)
                stats['records'] = count
                stats['success'] = True
                
                logger.info(f"Open interest ingestion complete: {count} records")
            else:
                logger.warning("No open interest data to ingest")
            
        except Exception as e:
            logger.error(f"Open interest ingestion failed: {e}")
            stats['errors'].append(str(e))
        
        return stats
    
    def ingest_social_sentiment(self, days: int = 1) -> Dict[str, Any]:
        """
        Ingest social sentiment from Reddit (raw posts + aggregated sentiment)
        Uses Reddit API if available, otherwise falls back to RSS
        
        Args:
            days: Number of days to fetch (default: 1)
        
        Returns:
            Dictionary with ingestion statistics
        """
        # Use Reddit API if available, otherwise use RSS
        reddit_connector = self.reddit if self.reddit else self.reddit_rss
        
        if not reddit_connector:
            logger.info("Reddit connectors disabled, skipping social sentiment")
            return {'success': True, 'raw_records': 0, 'aggregated_records': 0, 'errors': [], 'skipped': True}
        
        connector_type = "API" if self.reddit else "RSS"
        logger.info(f"Starting social sentiment ingestion via Reddit {connector_type} (last {days} days)")
        stats = {'success': False, 'raw_records': 0, 'aggregated_records': 0, 'errors': []}
        
        try:
            # Step 1: Fetch and store raw posts
            logger.info(f"Fetching raw social posts via Reddit {connector_type}...")
            raw_posts = reddit_connector.fetch_raw_posts(days_back=days)
            
            if raw_posts:
                # Insert raw posts into database
                raw_count = self.db.insert_social_posts_raw(raw_posts)
                stats['raw_records'] = raw_count
                logger.info(f"Stored {raw_count} raw social posts")
                
                # Step 2: Compute aggregated sentiment from raw data
                logger.info("Computing aggregated sentiment from raw posts...")
                from datetime import timedelta
                today = datetime.now()
                
                for i in range(days):
                    date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
                    try:
                        self.db.compute_social_sentiment_from_raw(date)
                        stats['aggregated_records'] += 1
                    except Exception as e:
                        logger.warning(f"Failed to compute sentiment for {date}: {e}")
                        stats['errors'].append(f"Aggregation {date}: {str(e)}")
                
                stats['success'] = True
                logger.info(f"Social sentiment ingestion complete: {raw_count} raw posts, {stats['aggregated_records']} daily aggregates")
            else:
                logger.warning("No social sentiment data to ingest")
            
        except Exception as e:
            logger.error(f"Social sentiment ingestion failed: {e}")
            stats['errors'].append(str(e))
        
        return stats
    
    def ingest_news_sentiment(self, days: int = 1) -> Dict[str, Any]:
        """
        Ingest news sentiment from NewsAPI (raw articles + aggregated sentiment)
        
        Args:
            days: Number of days to fetch (default: 1)
        
        Returns:
            Dictionary with ingestion statistics
        """
        if not self.news:
            logger.info("News connector disabled, skipping news sentiment")
            return {'success': True, 'raw_records': 0, 'aggregated_records': 0, 'errors': [], 'skipped': True}
        
        logger.info(f"Starting news sentiment ingestion (last {days} days)")
        stats = {'success': False, 'raw_records': 0, 'aggregated_records': 0, 'errors': []}
        
        try:
            # Step 1: Fetch and store raw articles
            logger.info("Fetching raw news articles...")
            raw_articles = self.news.fetch_raw_articles(days_back=days)
            
            if raw_articles:
                # Insert raw articles into database
                raw_count = self.db.insert_news_articles_raw(raw_articles)
                stats['raw_records'] = raw_count
                logger.info(f"Stored {raw_count} raw news articles")
                
                # Step 2: Compute aggregated sentiment from raw data
                logger.info("Computing aggregated sentiment from raw articles...")
                from datetime import timedelta
                today = datetime.now()
                
                for i in range(days):
                    date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
                    try:
                        self.db.compute_news_sentiment_from_raw(date)
                        stats['aggregated_records'] += 1
                    except Exception as e:
                        logger.warning(f"Failed to compute sentiment for {date}: {e}")
                        stats['errors'].append(f"Aggregation {date}: {str(e)}")
                
                stats['success'] = True
                logger.info(f"News sentiment ingestion complete: {raw_count} raw articles, {stats['aggregated_records']} daily aggregates")
            else:
                logger.warning("No news sentiment data to ingest")
            
        except Exception as e:
            logger.error(f"News sentiment ingestion failed: {e}")
            stats['errors'].append(str(e))
        
        return stats
    
    def ingest_search_trends(self, days: int = 7) -> Dict[str, Any]:
        """
        Ingest search interest from Google Trends (raw trends + aggregated interest)
        
        Args:
            days: Number of days to fetch (default: 7)
        
        Returns:
            Dictionary with ingestion statistics
        """
        if not self.trends:
            logger.info("Trends connector disabled, skipping search trends")
            return {'success': True, 'raw_records': 0, 'aggregated_records': 0, 'errors': [], 'skipped': True}
        
        logger.info(f"Starting search trends ingestion (last {days} days)")
        stats = {'success': False, 'raw_records': 0, 'aggregated_records': 0, 'errors': []}
        
        try:
            # Step 1: Fetch and store raw trends
            logger.info("Fetching raw search trends...")
            raw_trends = self.trends.fetch_raw_trends(days_back=days)
            
            if raw_trends:
                # Insert raw trends into database
                raw_count = self.db.insert_search_trends_raw(raw_trends)
                stats['raw_records'] = raw_count
                logger.info(f"Stored {raw_count} raw search trend records")
                
                # Step 2: Compute aggregated interest from raw data
                logger.info("Computing aggregated search interest from raw trends...")
                from datetime import timedelta
                today = datetime.now()
                
                for i in range(days):
                    date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
                    try:
                        self.db.compute_search_interest_from_raw(date)
                        stats['aggregated_records'] += 1
                    except Exception as e:
                        logger.warning(f"Failed to compute interest for {date}: {e}")
                        stats['errors'].append(f"Aggregation {date}: {str(e)}")
                
                stats['success'] = True
                logger.info(f"Search trends ingestion complete: {raw_count} raw trends, {stats['aggregated_records']} daily aggregates")
            else:
                logger.warning("No search trends data to ingest")
            
        except Exception as e:
            logger.error(f"Search trends ingestion failed: {e}")
            stats['errors'].append(str(e))
        
        return stats
    
    def ingest_twitter_sentiment(self, days: int = 1) -> Dict[str, Any]:
        """
        Ingest Twitter sentiment (raw tweets + aggregated sentiment)
        
        Args:
            days: Number of days to fetch (default: 1)
        
        Returns:
            Dictionary with ingestion statistics
        """
        if not self.twitter:
            logger.info("Twitter connector disabled, skipping Twitter sentiment")
            return {'success': True, 'raw_records': 0, 'aggregated_records': 0, 'errors': [], 'skipped': True}
        
        logger.info(f"Starting Twitter sentiment ingestion (last {days} days)")
        stats = {'success': False, 'raw_records': 0, 'aggregated_records': 0, 'errors': []}
        
        try:
            # Step 1: Fetch and store raw tweets
            logger.info("Fetching raw tweets...")
            raw_tweets = self.twitter.fetch_raw_tweets(days_back=days)
            
            if raw_tweets:
                # Insert raw tweets into database (using same table as Reddit posts)
                raw_count = self.db.insert_social_posts_raw(raw_tweets)
                stats['raw_records'] = raw_count
                logger.info(f"Stored {raw_count} raw tweets")
                
                # Step 2: Compute aggregated sentiment from raw data
                logger.info("Computing aggregated sentiment from raw tweets...")
                from datetime import timedelta
                today = datetime.now()
                
                for i in range(days):
                    date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
                    try:
                        # Use the same aggregation method but filter by platform='twitter'
                        self.db.compute_social_sentiment_from_raw(date, platform='twitter')
                        stats['aggregated_records'] += 1
                    except Exception as e:
                        logger.warning(f"Failed to compute Twitter sentiment for {date}: {e}")
                        stats['errors'].append(f"Aggregation {date}: {str(e)}")
                
                stats['success'] = True
                logger.info(f"Twitter sentiment ingestion complete: {raw_count} raw tweets, {stats['aggregated_records']} daily aggregates")
            else:
                logger.warning("No Twitter sentiment data to ingest")
            
        except Exception as e:
            logger.error(f"Twitter sentiment ingestion failed: {e}")
            stats['errors'].append(str(e))
        
        return stats
    
    def compute_snapshots(self, days: int = 7) -> Dict[str, Any]:
        """
        Compute daily market snapshots
        
        Args:
            days: Number of recent days to compute snapshots for
        
        Returns:
            Dictionary with computation statistics
        """
        logger.info(f"Computing daily snapshots for last {days} days")
        stats = {'success': False, 'snapshots': 0, 'errors': []}
        
        try:
            from datetime import timedelta
            today = datetime.now()
            
            for i in range(days):
                date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
                
                try:
                    self.db.compute_daily_snapshot(date)
                    stats['snapshots'] += 1
                except Exception as e:
                    logger.warning(f"Failed to compute snapshot for {date}: {e}")
                    stats['errors'].append(f"{date}: {str(e)}")
            
            stats['success'] = stats['snapshots'] > 0
            logger.info(f"Computed {stats['snapshots']} daily snapshots")
            
        except Exception as e:
            logger.error(f"Snapshot computation failed: {e}")
            stats['errors'].append(str(e))
        
        return stats
    
    def run_full_ingestion(self, etf_days: int = 7, sentiment_days: int = 7, nlp_days: int = 1) -> Dict[str, Any]:
        """
        Run complete ingestion pipeline (Phase 1 + Phase 2 + Phase 3)
        
        Args:
            etf_days: Number of days of ETF data to fetch (default: 7 for daily sync, 300 for backfill)
            sentiment_days: Number of days of sentiment data to fetch (default: 7 for daily sync, 30 for backfill)
            nlp_days: Number of days of NLP/sentiment data to fetch (default: 1 for daily sync, 7 for backfill)
        
        Returns:
            Dictionary with overall statistics
        """
        logger.info("=" * 60)
        logger.info("STARTING FULL INGESTION PIPELINE (PHASE 1 + PHASE 2 + PHASE 3)")
        logger.info(f"Mode: ETF={etf_days} days, Sentiment={sentiment_days} days, NLP={nlp_days} days")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        results = {
            'timestamp': start_time.isoformat(),
            'config': Config.display(),
            'mode': 'BACKFILL' if etf_days > 30 else 'DAILY_SYNC',
            'ohlc': {},
            'sentiment': {},
            'etf_flows': {},
            'market_metrics': {},
            'funding_rates': {},
            'open_interest': {},
            'social_sentiment': {},
            'twitter_sentiment': {},
            'news_sentiment': {},
            'search_trends': {},
            'snapshots': {},
            'overall_success': False
        }
        
        # Phase 1 Ingestion
        logger.info("\n=== PHASE 1: Core Market Data ===")
        
        # Step 1: Ingest OHLC data
        logger.info("\n[1/7] Ingesting OHLC data...")
        results['ohlc'] = self.ingest_ohlc_data()
        
        # Step 2: Ingest sentiment data
        logger.info(f"\n[2/7] Ingesting sentiment data (last {sentiment_days} days)...")
        results['sentiment'] = self.ingest_sentiment_data(days=sentiment_days)
        
        # Step 3: Ingest ETF flows
        logger.info(f"\n[3/7] Ingesting ETF flows (last {etf_days} days)...")
        results['etf_flows'] = self.ingest_etf_flows(days=etf_days)
        
        # Phase 2 Ingestion
        logger.info("\n=== PHASE 2: Market Structure & Derivatives ===")
        
        # Step 4: Ingest market metrics
        logger.info("\n[4/7] Ingesting market metrics (volume, dominance)...")
        results['market_metrics'] = self.ingest_market_metrics()
        
        # Step 5: Ingest funding rates
        logger.info("\n[5/7] Ingesting funding rates...")
        results['funding_rates'] = self.ingest_funding_rates()
        
        # Step 6: Ingest open interest
        logger.info("\n[6/10] Ingesting open interest...")
        results['open_interest'] = self.ingest_open_interest()
        
        # Phase 3 Ingestion
        logger.info("\n=== PHASE 3: NLP & Sentiment Analysis ===")
        
        # Step 7: Ingest social sentiment (Reddit)
        logger.info(f"\n[7/11] Ingesting social sentiment (Reddit) (last {nlp_days} days)...")
        results['social_sentiment'] = self.ingest_social_sentiment(days=nlp_days)
        
        # Step 8: Ingest Twitter sentiment
        logger.info(f"\n[8/11] Ingesting Twitter sentiment (last {nlp_days} days)...")
        results['twitter_sentiment'] = self.ingest_twitter_sentiment(days=nlp_days)
        
        # Step 9: Ingest news sentiment
        logger.info(f"\n[9/11] Ingesting news sentiment (last {nlp_days} days)...")
        results['news_sentiment'] = self.ingest_news_sentiment(days=nlp_days)
        
        # Step 10: Ingest search trends
        logger.info(f"\n[10/11] Ingesting search trends (last 7 days)...")
        results['search_trends'] = self.ingest_search_trends(days=7)
        
        # Step 11: Compute daily snapshots
        logger.info("\n[11/11] Computing daily snapshots...")
        results['snapshots'] = self.compute_snapshots(days=7)
        
        # Overall success if at least Phase 1 core data succeeded
        results['overall_success'] = (
            results['ohlc']['success'] and 
            results['sentiment']['success']
        )
        
        # Get final record counts
        record_counts = self.db.get_record_counts()
        results['record_counts'] = record_counts
        
        # Cleanup old backups if enabled
        if self.csv_backup:
            deleted = self.csv_backup.cleanup_old_backups(days_to_keep=30)
            results['backups_cleaned'] = deleted
        
        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()
        results['duration_seconds'] = duration
        
        logger.info("=" * 60)
        logger.info(f"INGESTION PIPELINE COMPLETE")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Overall Success: {results['overall_success']}")
        logger.info(f"Record Counts: {record_counts}")
        logger.info("=" * 60)
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current database status
        
        Returns:
            Dictionary with database statistics
        """
        return {
            'record_counts': self.db.get_record_counts(),
            'config': Config.display()
        }


def main():
    """Main entry point for ingestion pipeline"""
    try:
        pipeline = IngestionPipeline()
        results = pipeline.run_full_ingestion()
        
        # Print summary
        print("\n" + "=" * 60)
        print("INGESTION SUMMARY")
        print("=" * 60)
        print(f"Overall Success: {results['overall_success']}")
        print(f"Duration: {results['duration_seconds']:.2f}s")
        print(f"\nRecord Counts:")
        for table, count in results['record_counts'].items():
            print(f"  {table}: {count}")
        print("=" * 60)
        
        return 0 if results['overall_success'] else 1
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())

