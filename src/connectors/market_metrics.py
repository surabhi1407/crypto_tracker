"""Market metrics connector for volume, dominance, and market cap data"""
from typing import List, Dict, Any
from datetime import datetime
from src.connectors.base import BaseConnector
from src.utils.time_utils import get_date_string
from src.utils.logger import setup_logger

logger = setup_logger()


class MarketMetricsConnector(BaseConnector):
    """
    Connector for market-wide metrics from CoinGecko
    - Global market data (BTC dominance, total market cap)
    - Coin-specific metrics (volume, market cap, price change)
    """
    
    def __init__(self, api_key: str = None, rate_limit_delay: float = 1.5):
        """
        Initialize Market Metrics connector
        
        Args:
            api_key: Optional CoinGecko API key for Pro tier
            rate_limit_delay: Delay between requests
        """
        base_url = "https://api.coingecko.com/api/v3"
        super().__init__(base_url, rate_limit_delay)
        
        if api_key:
            self.session.headers.update({'x-cg-pro-api-key': api_key})
    
    def fetch_global_metrics(self) -> Dict[str, Any]:
        """
        Fetch global market metrics including BTC dominance
        
        Returns:
            Dictionary with global market data
        """
        logger.info("Fetching global market metrics from CoinGecko")
        
        try:
            endpoint = "/global"
            data = self._make_request(endpoint)
            
            if 'data' not in data:
                logger.error("No data field in global metrics response")
                return {}
            
            global_data = data['data']
            
            result = {
                'total_market_cap_usd': global_data.get('total_market_cap', {}).get('usd', 0),
                'total_volume_24h_usd': global_data.get('total_volume', {}).get('usd', 0),
                'btc_dominance_pct': global_data.get('market_cap_percentage', {}).get('btc', 0),
                'eth_dominance_pct': global_data.get('market_cap_percentage', {}).get('eth', 0),
                'active_cryptocurrencies': global_data.get('active_cryptocurrencies', 0),
                'markets': global_data.get('markets', 0)
            }
            
            logger.info(f"Fetched global metrics: BTC dominance={result['btc_dominance_pct']:.2f}%")
            return result
            
        except Exception as e:
            logger.error(f"Failed to fetch global metrics: {e}")
            return {}
    
    def fetch_coin_metrics(
        self,
        coin_ids: List[str],
        vs_currency: str = "usd"
    ) -> List[Dict[str, Any]]:
        """
        Fetch market metrics for specific coins
        
        Args:
            coin_ids: List of CoinGecko coin IDs (e.g., ['bitcoin', 'ethereum'])
            vs_currency: Target currency (default: 'usd')
        
        Returns:
            List of dictionaries with coin-specific metrics
        """
        logger.info(f"Fetching coin metrics for {len(coin_ids)} coins")
        
        try:
            endpoint = "/coins/markets"
            params = {
                'vs_currency': vs_currency,
                'ids': ','.join(coin_ids),
                'order': 'market_cap_desc',
                'per_page': 100,
                'page': 1,
                'sparkline': 'false',
                'price_change_percentage': '24h'
            }
            
            data = self._make_request(endpoint, params)
            
            if not isinstance(data, list):
                logger.error(f"Unexpected response format: {type(data)}")
                return []
            
            normalized = []
            for coin in data:
                normalized.append({
                    'asset': coin['id'].upper(),
                    'symbol': coin['symbol'].upper(),
                    'current_price': coin.get('current_price', 0),
                    'market_cap_usd': coin.get('market_cap', 0),
                    'volume_24h_usd': coin.get('total_volume', 0),
                    'price_change_24h_pct': coin.get('price_change_percentage_24h', 0),
                    'market_cap_rank': coin.get('market_cap_rank', 0),
                    'circulating_supply': coin.get('circulating_supply', 0),
                    'total_supply': coin.get('total_supply', 0)
                })
            
            logger.info(f"Successfully fetched metrics for {len(normalized)} coins")
            return normalized
            
        except Exception as e:
            logger.error(f"Failed to fetch coin metrics: {e}")
            return []
    
    def fetch_data(
        self,
        coin_ids: List[str] = None,
        as_of_date: str = None
    ) -> List[Dict[str, Any]]:
        """
        Main fetch method - combines global and coin-specific metrics
        
        Args:
            coin_ids: List of coin IDs to fetch (default: ['bitcoin', 'ethereum'])
            as_of_date: Date string in YYYY-MM-DD format (default: today)
        
        Returns:
            List of normalized market metrics records ready for database insertion
        """
        if coin_ids is None:
            coin_ids = ['bitcoin', 'ethereum']
        
        if as_of_date is None:
            as_of_date = get_date_string()
        
        logger.info(f"Fetching market metrics for {as_of_date}")
        
        # Fetch global metrics for BTC dominance
        global_metrics = self.fetch_global_metrics()
        btc_dominance = global_metrics.get('btc_dominance_pct', 0)
        
        # Fetch coin-specific metrics
        coin_metrics = self.fetch_coin_metrics(coin_ids)
        
        # Normalize for database insertion
        normalized = []
        for coin in coin_metrics:
            record = {
                'as_of_date': as_of_date,
                'asset': coin['asset'],
                'volume_24h_usd': coin['volume_24h_usd'],
                'market_cap_usd': coin['market_cap_usd'],
                'btc_dominance_pct': btc_dominance if coin['asset'] == 'BITCOIN' else None,
                'price_change_24h_pct': coin['price_change_24h_pct'],
                'source': 'COINGECKO'
            }
            normalized.append(record)
        
        logger.info(f"Prepared {len(normalized)} market metrics records for {as_of_date}")
        return normalized

