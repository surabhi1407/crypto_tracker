"""CSV backup utilities for data snapshots"""
import csv
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from src.utils.logger import setup_logger

logger = setup_logger()


class CSVBackup:
    """Handles CSV backup operations for market data"""
    
    def __init__(self, backup_dir: str = "data/backups"):
        """
        Initialize CSV backup handler
        
        Args:
            backup_dir: Directory for CSV backups
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def save_to_csv(
        self,
        data: List[Dict[str, Any]],
        filename: str,
        fieldnames: List[str] = None
    ) -> Path:
        """
        Save data to CSV file
        
        Args:
            data: List of dictionaries to save
            filename: Base filename (without extension)
            fieldnames: Optional list of field names (inferred if not provided)
        
        Returns:
            Path to saved CSV file
        """
        if not data:
            logger.warning(f"No data to save for {filename}")
            return None
        
        # Add timestamp to filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = self.backup_dir / f"{filename}_{timestamp}.csv"
        
        # Infer fieldnames from first record if not provided
        if fieldnames is None:
            fieldnames = list(data[0].keys())
        
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            
            logger.info(f"Saved {len(data)} records to {csv_path}")
            return csv_path
            
        except Exception as e:
            logger.error(f"Failed to save CSV backup: {e}")
            raise
    
    def save_ohlc_backup(self, data: List[Dict[str, Any]]) -> Path:
        """Save OHLC data backup"""
        fieldnames = ['asset', 'ts_utc', 'open', 'high', 'low', 'close', 'session']
        return self.save_to_csv(data, 'ohlc_hourly', fieldnames)
    
    def save_sentiment_backup(self, data: List[Dict[str, Any]]) -> Path:
        """Save sentiment data backup"""
        # Remove extra fields that aren't needed for backup
        cleaned_data = [
            {
                'as_of_date': d['as_of_date'],
                'fng_value': d['fng_value'],
                'classification': d['classification']
            }
            for d in data
        ]
        fieldnames = ['as_of_date', 'fng_value', 'classification']
        return self.save_to_csv(cleaned_data, 'sentiment_daily', fieldnames)
    
    def save_etf_backup(self, data: List[Dict[str, Any]]) -> Path:
        """Save ETF flow data backup"""
        # Clean data to only include fields we want in CSV
        cleaned_data = [
            {
                'as_of_date': d['as_of_date'],
                'ticker': d['ticker'],
                'net_flow_usd': d.get('net_flow_usd'),
                'aum_usd': d.get('aum_usd'),
                'source': d.get('source', 'UNKNOWN')
            }
            for d in data
        ]
        fieldnames = ['as_of_date', 'ticker', 'net_flow_usd', 'aum_usd', 'source']
        return self.save_to_csv(cleaned_data, 'etf_flows_daily', fieldnames)
    
    def cleanup_old_backups(self, days_to_keep: int = 30) -> int:
        """
        Remove backup files older than specified days
        
        Args:
            days_to_keep: Number of days to retain backups
        
        Returns:
            Number of files deleted
        """
        logger.info(f"Cleaning up backups older than {days_to_keep} days")
        
        cutoff_time = datetime.now().timestamp() - (days_to_keep * 86400)
        deleted_count = 0
        
        try:
            for csv_file in self.backup_dir.glob("*.csv"):
                if csv_file.stat().st_mtime < cutoff_time:
                    csv_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old backup: {csv_file.name}")
            
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} old backup files")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
            return 0

