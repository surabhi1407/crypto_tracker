"""Binance Futures connector for derivatives data (funding rates, open interest)"""
import time
from typing import List, Dict, Any
from datetime import datetime, timezone
from src.connectors.base import BaseConnector
from src.utils.time_utils import get_date_string
from src.utils.logger import setup_logger

logger = setup_logger()


class BinanceFuturesConnector(BaseConnector):
    """
    Connector for Binance Futures API
    - Funding rates (8-hour snapshots)
    - Open interest (daily aggregates)
    
    API Documentation: https://binance-docs.github.io/apidocs/futures/en/
    """
    
    # Symbol mappings from coin_id to Binance futures symbol
    SYMBOL_MAP = {
        'bitcoin': 'BTCUSDT',
        'ethereum': 'ETHUSDT'
    }
    
    def __init__(self, rate_limit_delay: float = 0.5):
        """
        Initialize Binance Futures connector
        
        Args:
            rate_limit_delay: Delay between requests (Binance uses weight-based limiting)
        
        Note: Binance Futures API is public, no API key required for market data
        """
        base_url = "https://fapi.binance.com"
        super().__init__(base_url, rate_limit_delay)
        
        # Weight tracking for rate limiting (1200 weight per minute)
        self.weight_used = 0
        self.weight_reset_time = time.time() + 60
        self.max_weight_per_minute = 1200
    
    def _check_rate_limit(self, weight: int = 1):
        """
        Check and enforce Binance weight-based rate limiting
        
        Args:
            weight: API weight of the upcoming request
        """
        current_time = time.time()
        
        # Reset weight counter if minute has passed
        if current_time > self.weight_reset_time:
            self.weight_used = 0
            self.weight_reset_time = current_time + 60
            logger.debug("Rate limit weight counter reset")
        
        # Check if we're approaching the limit
        if self.weight_used + weight > self.max_weight_per_minute:
            sleep_time = self.weight_reset_time - current_time
            logger.warning(f"Approaching rate limit, sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
            self.weight_used = 0
            self.weight_reset_time = time.time() + 60
        
        self.weight_used += weight
    
    def fetch_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch current funding rate for a symbol
        
        Args:
            symbol: Binance futures symbol (e.g., 'BTCUSDT')
        
        Returns:
            Dictionary with funding rate data
        """
        logger.info(f"Fetching funding rate for {symbol}")
        
        try:
            self._check_rate_limit(weight=1)
            
            endpoint = "/fapi/v1/premiumIndex"
            params = {'symbol': symbol}
            
            data = self._make_request(endpoint, params)
            
            # Parse funding time (milliseconds timestamp)
            funding_time = datetime.fromtimestamp(
                data['nextFundingTime'] / 1000, 
                tz=timezone.utc
            )
            
            result = {
                'symbol': symbol,
                'funding_rate': float(data['lastFundingRate']),
                'mark_price': float(data['markPrice']),
                'index_price': float(data['indexPrice']),
                'next_funding_time': funding_time,
                'funding_interval_hours': 8  # Binance standard
            }
            
            logger.info(f"Funding rate for {symbol}: {result['funding_rate']:.6f}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to fetch funding rate for {symbol}: {e}")
            return {}
    
    def fetch_open_interest(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch current open interest for a symbol
        
        Args:
            symbol: Binance futures symbol (e.g., 'BTCUSDT')
        
        Returns:
            Dictionary with open interest data
        """
        logger.info(f"Fetching open interest for {symbol}")
        
        try:
            self._check_rate_limit(weight=1)
            
            endpoint = "/fapi/v1/openInterest"
            params = {'symbol': symbol}
            
            data = self._make_request(endpoint, params)
            
            result = {
                'symbol': symbol,
                'open_interest': float(data['openInterest']),
                'timestamp': datetime.fromtimestamp(
                    data['time'] / 1000,
                    tz=timezone.utc
                )
            }
            
            logger.info(f"Open interest for {symbol}: {result['open_interest']:.2f} contracts")
            return result
            
        except Exception as e:
            logger.error(f"Failed to fetch open interest for {symbol}: {e}")
            return {}
    
    def fetch_funding_rates_for_assets(
        self,
        coin_ids: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch funding rates for multiple assets
        
        Args:
            coin_ids: List of coin IDs (e.g., ['bitcoin', 'ethereum'])
        
        Returns:
            List of normalized funding rate records
        """
        if coin_ids is None:
            coin_ids = ['bitcoin', 'ethereum']
        
        logger.info(f"Fetching funding rates for {len(coin_ids)} assets")
        
        normalized = []
        current_time = datetime.now(timezone.utc)
        
        for coin_id in coin_ids:
            symbol = self.SYMBOL_MAP.get(coin_id)
            if not symbol:
                logger.warning(f"No Binance symbol mapping for {coin_id}")
                continue
            
            funding_data = self.fetch_funding_rate(symbol)
            
            if funding_data:
                # Convert funding rate to percentage
                funding_rate_pct = funding_data['funding_rate'] * 100
                
                record = {
                    'ts_utc': current_time.isoformat(),
                    'asset': coin_id.upper(),
                    'funding_rate_pct': funding_rate_pct,
                    'funding_interval_hours': funding_data['funding_interval_hours'],
                    'mark_price': funding_data['mark_price'],
                    'source': 'BINANCE'
                }
                normalized.append(record)
        
        logger.info(f"Prepared {len(normalized)} funding rate records")
        return normalized
    
    def fetch_open_interest_for_assets(
        self,
        coin_ids: List[str] = None,
        as_of_date: str = None,
        mark_prices: Dict[str, float] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch open interest for multiple assets
        
        Args:
            coin_ids: List of coin IDs (e.g., ['bitcoin', 'ethereum'])
            as_of_date: Date string in YYYY-MM-DD format (default: today)
            mark_prices: Optional dict of symbol -> mark_price to avoid redundant API calls
        
        Returns:
            List of normalized open interest records
        """
        if coin_ids is None:
            coin_ids = ['bitcoin', 'ethereum']
        
        if as_of_date is None:
            as_of_date = get_date_string()
        
        logger.info(f"Fetching open interest for {len(coin_ids)} assets")
        
        normalized = []
        
        for coin_id in coin_ids:
            symbol = self.SYMBOL_MAP.get(coin_id)
            if not symbol:
                logger.warning(f"No Binance symbol mapping for {coin_id}")
                continue
            
            oi_data = self.fetch_open_interest(symbol)
            
            if oi_data:
                # Use provided mark price or fetch from funding rate endpoint if not available
                if mark_prices and symbol in mark_prices:
                    mark_price = mark_prices[symbol]
                else:
                    # Fetch from premium index endpoint (same as funding rate)
                    funding_data = self.fetch_funding_rate(symbol)
                    mark_price = funding_data.get('mark_price', 0) if funding_data else 0
                
                open_interest_usd = oi_data['open_interest'] * mark_price
                
                record = {
                    'as_of_date': as_of_date,
                    'asset': coin_id.upper(),
                    'open_interest_usd': open_interest_usd,
                    'open_interest_contracts': oi_data['open_interest'],
                    'source': 'BINANCE'
                }
                normalized.append(record)
        
        logger.info(f"Prepared {len(normalized)} open interest records")
        return normalized
    
    def fetch_data(
        self,
        coin_ids: List[str] = None,
        as_of_date: str = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Main fetch method - gets both funding rates and open interest
        Optimized to reuse mark prices from funding rate calls
        
        Args:
            coin_ids: List of coin IDs to fetch
            as_of_date: Date string for open interest
        
        Returns:
            Dictionary with 'funding_rates' and 'open_interest' lists
        """
        if coin_ids is None:
            coin_ids = ['bitcoin', 'ethereum']
        
        logger.info(f"Fetching Binance derivatives data for {coin_ids}")
        
        # Fetch funding rates first (includes mark prices)
        funding_rates = self.fetch_funding_rates_for_assets(coin_ids)
        
        # Extract mark prices from funding rate data to avoid redundant API calls
        mark_prices = {}
        for fr in funding_rates:
            symbol = self.SYMBOL_MAP.get(fr['asset'].lower())
            if symbol and 'mark_price' in fr:
                mark_prices[symbol] = fr['mark_price']
        
        # Fetch open interest, reusing mark prices
        open_interest = self.fetch_open_interest_for_assets(coin_ids, as_of_date, mark_prices)
        
        result = {
            'funding_rates': funding_rates,
            'open_interest': open_interest
        }
        
        logger.info(
            f"Fetched {len(result['funding_rates'])} funding rates, "
            f"{len(result['open_interest'])} OI records"
        )
        
        return result

