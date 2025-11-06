"""CoinGecko API connector for crypto price and market data"""
from typing import List, Dict, Any
from datetime import datetime, timedelta
from src.connectors.base import BaseConnector
from src.utils.time_utils import timestamp_to_utc, classify_trading_session
from src.utils.logger import setup_logger

logger = setup_logger()


class CoinGeckoConnector(BaseConnector):
    """Connector for CoinGecko API to fetch OHLC and market data"""
    
    def __init__(self, api_key: str = None, rate_limit_delay: float = 1.5):
        """
        Initialize CoinGecko connector
        
        Args:
            api_key: Optional API key for Pro tier
            rate_limit_delay: Delay between requests
        """
        base_url = "https://api.coingecko.com/api/v3"
        super().__init__(base_url, rate_limit_delay)
        
        if api_key:
            self.session.headers.update({'x-cg-pro-api-key': api_key})
    
    def fetch_ohlc_hourly(
        self,
        coin_id: str,
        vs_currency: str = "usd",
        days: int = 14
    ) -> List[Dict[str, Any]]:
        """
        Fetch hourly price data for a cryptocurrency using market_chart endpoint
        
        Args:
            coin_id: CoinGecko coin ID (e.g., 'bitcoin', 'ethereum')
            vs_currency: Target currency (default: 'usd')
            days: Number of days to fetch
        
        Returns:
            List of dictionaries with normalized price data
        """
        logger.info(f"Fetching {days}-day price data for {coin_id}")
        
        try:
            # Use direct requests instead of base connector to match app.py behavior
            import requests
            import time
            
            url = f"{self.base_url}/coins/{coin_id}/market_chart"
            params = {
                'vs_currency': vs_currency,
                'days': days
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            if 'prices' not in data:
                logger.error(f"No price data in response for {coin_id}")
                return []
            
            # Normalize data from market_chart format
            # market_chart returns [timestamp, price] pairs
            normalized = []
            prices = data['prices']
            
            for price_entry in prices:
                ts_ms, price = price_entry
                dt_utc = timestamp_to_utc(ts_ms)
                
                # For market_chart, we use price as close
                # Open/high/low are approximated (same as close for simplicity)
                normalized.append({
                    'asset': coin_id.upper(),
                    'ts_utc': dt_utc,
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'session': classify_trading_session(dt_utc.hour)
                })
            
            logger.info(f"Successfully fetched {len(normalized)} price records for {coin_id}")
            return normalized
            
        except Exception as e:
            logger.error(f"Failed to fetch price data for {coin_id}: {e}")
            return []
    
    def fetch_current_price(
        self,
        coin_ids: List[str],
        vs_currency: str = "usd"
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetch current price and 24h change for multiple coins
        
        Args:
            coin_ids: List of CoinGecko coin IDs
            vs_currency: Target currency
        
        Returns:
            Dictionary mapping coin_id to price data
        """
        logger.info(f"Fetching current prices for {len(coin_ids)} coins")
        
        endpoint = "/simple/price"
        params = {
            'ids': ','.join(coin_ids),
            'vs_currencies': vs_currency,
            'include_24hr_change': 'true',
            'include_24hr_vol': 'true',
            'include_market_cap': 'true'
        }
        
        try:
            data = self._make_request(endpoint, params)
            logger.info(f"Successfully fetched prices for {len(data)} coins")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch current prices: {e}")
            return {}
    
    def fetch_market_chart(
        self,
        coin_id: str,
        vs_currency: str = "usd",
        days: int = 7
    ) -> Dict[str, List]:
        """
        Fetch market chart data (prices, volumes, market caps)
        
        Args:
            coin_id: CoinGecko coin ID
            vs_currency: Target currency
            days: Number of days
        
        Returns:
            Dictionary with prices, volumes, and market_caps lists
        """
        logger.info(f"Fetching {days}-day market chart for {coin_id}")
        
        endpoint = f"/coins/{coin_id}/market_chart"
        params = {
            'vs_currency': vs_currency,
            'days': days
        }
        
        try:
            data = self._make_request(endpoint, params)
            logger.info(f"Successfully fetched market chart for {coin_id}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch market chart for {coin_id}: {e}")
            return {'prices': [], 'volumes': [], 'market_caps': []}
    
    def fetch_data(self) -> Dict[str, Any]:
        """
        Main fetch method - gets data for BTC and ETH
        
        Returns:
            Dictionary with OHLC data for both assets
        """
        assets = ['bitcoin', 'ethereum']
        result = {}
        
        for asset in assets:
            result[asset] = self.fetch_ohlc_hourly(asset, days=14)
        
        return result

