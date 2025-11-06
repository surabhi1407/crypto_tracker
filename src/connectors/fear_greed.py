"""Alternative.me Fear & Greed Index API connector"""
from typing import List, Dict, Any
from datetime import datetime
from src.connectors.base import BaseConnector
from src.utils.time_utils import get_date_string
from src.utils.logger import setup_logger

logger = setup_logger()


class FearGreedConnector(BaseConnector):
    """Connector for Alternative.me Fear & Greed Index"""
    
    def __init__(self, rate_limit_delay: float = 1.5):
        """Initialize Fear & Greed connector"""
        base_url = "https://api.alternative.me"
        super().__init__(base_url, rate_limit_delay)
    
    def fetch_fear_greed_index(self, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Fetch Fear & Greed Index data
        
        Args:
            limit: Number of days to fetch (default: 30)
        
        Returns:
            List of dictionaries with normalized sentiment data
        """
        logger.info(f"Fetching Fear & Greed Index for last {limit} days")
        
        endpoint = "/fng/"
        params = {'limit': limit}
        
        try:
            response = self._make_request(endpoint, params)
            
            if 'data' not in response:
                logger.error("Unexpected response format from Fear & Greed API")
                return []
            
            # Normalize data
            normalized = []
            for entry in response['data']:
                # Parse timestamp
                ts = int(entry['timestamp'])
                dt = datetime.fromtimestamp(ts)
                date_str = dt.strftime('%Y-%m-%d')
                
                normalized.append({
                    'as_of_date': date_str,
                    'fng_value': int(entry['value']),
                    'classification': entry['value_classification'].upper(),
                    'time_until_update': entry.get('time_until_update')
                })
            
            logger.info(f"Successfully fetched {len(normalized)} Fear & Greed records")
            return normalized
            
        except Exception as e:
            logger.error(f"Failed to fetch Fear & Greed Index: {e}")
            return []
    
    def fetch_latest(self) -> Dict[str, Any]:
        """
        Fetch only the latest Fear & Greed value
        
        Returns:
            Dictionary with latest sentiment data
        """
        logger.info("Fetching latest Fear & Greed Index")
        
        endpoint = "/fng/"
        params = {'limit': 1}
        
        try:
            response = self._make_request(endpoint, params)
            
            if 'data' not in response or not response['data']:
                logger.error("No data in Fear & Greed API response")
                return {}
            
            entry = response['data'][0]
            ts = int(entry['timestamp'])
            dt = datetime.fromtimestamp(ts)
            
            result = {
                'as_of_date': dt.strftime('%Y-%m-%d'),
                'fng_value': int(entry['value']),
                'classification': entry['value_classification'].upper(),
                'timestamp': dt
            }
            
            logger.info(f"Latest F&G: {result['fng_value']} ({result['classification']})")
            return result
            
        except Exception as e:
            logger.error(f"Failed to fetch latest Fear & Greed: {e}")
            return {}
    
    def fetch_data(self) -> List[Dict[str, Any]]:
        """
        Main fetch method - gets 30 days of Fear & Greed data
        
        Returns:
            List of sentiment records
        """
        return self.fetch_fear_greed_index(limit=30)

