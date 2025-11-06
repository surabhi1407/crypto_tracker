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
            'HAS_SOSOVALUE_API_KEY': cls.SOSOVALUE_API_KEY is not None
        }

