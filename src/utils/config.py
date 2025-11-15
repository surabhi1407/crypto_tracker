"""Configuration management using environment variables"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)


class Config:
    """Application configuration from environment variables"""
    
    # Database
    DB_PATH = os.getenv('DB_PATH', 'data/market_intel.db')
    
    # API Configuration
    COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY', None)
    SOSOVALUE_API_KEY = os.getenv('SOSOVALUE_API_KEY', None)
    RATE_LIMIT_DELAY = float(os.getenv('RATE_LIMIT_DELAY', '1.5'))
    
    # Binance Futures API (Phase 2)
    BINANCE_FUTURES_BASE_URL = os.getenv('BINANCE_FUTURES_BASE_URL', 'https://fapi.binance.com')
    BINANCE_RATE_LIMIT_WEIGHT = int(os.getenv('BINANCE_RATE_LIMIT_WEIGHT', '1200'))
    
    # Symbol mappings for Binance Futures
    BINANCE_SYMBOLS = {
        'bitcoin': 'BTCUSDT',
        'ethereum': 'ETHUSDT'
    }
    
    # Data Retention
    DATA_RETENTION_DAYS = int(os.getenv('DATA_RETENTION_DAYS', '365'))
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_PATH = os.getenv('LOG_PATH', 'logs/ingestion.log')
    
    # CSV Backup
    ENABLE_CSV_BACKUP = os.getenv('ENABLE_CSV_BACKUP', 'true').lower() == 'true'
    CSV_BACKUP_PATH = os.getenv('CSV_BACKUP_PATH', 'data/backups')
    
    # Timezone
    DEFAULT_TIMEZONE = os.getenv('DEFAULT_TIMEZONE', 'UTC')
    
    # Assets to track
    TRACKED_ASSETS = ['bitcoin', 'ethereum']
    
    # Phase 2 Feature Flags
    ENABLE_MARKET_METRICS = os.getenv('ENABLE_MARKET_METRICS', 'true').lower() == 'true'
    ENABLE_DERIVATIVES_DATA = os.getenv('ENABLE_DERIVATIVES_DATA', 'true').lower() == 'true'
    
    # Phase 3 API Configuration (NLP & Sentiment)
    REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID', None)
    REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET', None)
    REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT', 'CryptoIntelDashboard/1.0')
    
    NEWSAPI_KEY = os.getenv('NEWSAPI_KEY', None)
    
    # Phase 3 Feature Flags
    ENABLE_SOCIAL_SENTIMENT = os.getenv('ENABLE_SOCIAL_SENTIMENT', 'false').lower() == 'true'
    ENABLE_NEWS_SENTIMENT = os.getenv('ENABLE_NEWS_SENTIMENT', 'false').lower() == 'true'
    ENABLE_SEARCH_TRENDS = os.getenv('ENABLE_SEARCH_TRENDS', 'false').lower() == 'true'
    
    # Phase 3 Configuration
    CRYPTO_SUBREDDITS = ['CryptoCurrency', 'Bitcoin', 'ethereum']
    SEARCH_KEYWORDS = ['bitcoin', 'ethereum', 'cryptocurrency']
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration"""
        # Ensure required directories exist
        Path(cls.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(cls.LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
        
        if cls.ENABLE_CSV_BACKUP:
            Path(cls.CSV_BACKUP_PATH).mkdir(parents=True, exist_ok=True)
        
        return True
    
    @classmethod
    def display(cls) -> dict:
        """Return configuration as dictionary (excluding sensitive data)"""
        return {
            'DB_PATH': cls.DB_PATH,
            'RATE_LIMIT_DELAY': cls.RATE_LIMIT_DELAY,
            'DATA_RETENTION_DAYS': cls.DATA_RETENTION_DAYS,
            'LOG_LEVEL': cls.LOG_LEVEL,
            'ENABLE_CSV_BACKUP': cls.ENABLE_CSV_BACKUP,
            'TRACKED_ASSETS': cls.TRACKED_ASSETS,
            'HAS_COINGECKO_API_KEY': cls.COINGECKO_API_KEY is not None,
            'HAS_SOSOVALUE_API_KEY': cls.SOSOVALUE_API_KEY is not None,
            'ENABLE_MARKET_METRICS': cls.ENABLE_MARKET_METRICS,
            'ENABLE_DERIVATIVES_DATA': cls.ENABLE_DERIVATIVES_DATA,
            'BINANCE_FUTURES_BASE_URL': cls.BINANCE_FUTURES_BASE_URL,
            'HAS_REDDIT_CREDENTIALS': cls.REDDIT_CLIENT_ID is not None and cls.REDDIT_CLIENT_SECRET is not None,
            'HAS_NEWSAPI_KEY': cls.NEWSAPI_KEY is not None,
            'ENABLE_SOCIAL_SENTIMENT': cls.ENABLE_SOCIAL_SENTIMENT,
            'ENABLE_NEWS_SENTIMENT': cls.ENABLE_NEWS_SENTIMENT,
            'ENABLE_SEARCH_TRENDS': cls.ENABLE_SEARCH_TRENDS
        }

