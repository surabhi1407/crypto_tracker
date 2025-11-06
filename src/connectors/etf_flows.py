"""ETF flows connector for institutional flow data"""
from typing import List, Dict, Any
from datetime import datetime, timedelta
from src.connectors.base import BaseConnector
from src.utils.time_utils import get_date_string, get_utc_now
from src.utils.logger import setup_logger

logger = setup_logger()


class ETFFlowsConnector(BaseConnector):
    """
    Connector for ETF flow data from SoSoValue API
    
    Uses SoSoValue's official API to fetch real Bitcoin and Ethereum ETF flow data.
    API Documentation: https://sosovalue.gitbook.io/soso-value-api-doc/
    """
    
    def __init__(self, api_key: str = None, rate_limit_delay: float = 1.5):
        """
        Initialize ETF Flows connector
        
        Args:
            api_key: SoSoValue API key (required)
            rate_limit_delay: Delay between requests
        """
        base_url = "https://api.sosovalue.xyz"
        super().__init__(base_url, rate_limit_delay)
        
        self.api_key = api_key
        if api_key:
            self.session.headers.update({
                'x-soso-api-key': api_key,
                'Content-Type': 'application/json'
            })
    
    def fetch_etf_flows(
        self,
        start_date: str = None,
        end_date: str = None,
        days: int = 30,
        etf_type: str = "us-btc-spot"
    ) -> List[Dict[str, Any]]:
        """
        Fetch real ETF flow data from SoSoValue API
        
        Args:
            start_date: Start date in YYYY-MM-DD format (not used, API returns last 300 days)
            end_date: End date in YYYY-MM-DD format (not used, API returns last 300 days)
            days: Number of days to fetch (max 300 from API)
            etf_type: "us-btc-spot" or "us-eth-spot"
        
        Returns:
            List of dictionaries with ETF flow data
        """
        if not self.api_key:
            logger.error("SoSoValue API key not configured!")
            logger.error("Get your free API key at: https://sosovalue.xyz/")
            logger.error("Add to .env: SOSOVALUE_API_KEY=your_key_here")
            return []
        
        logger.info(f"Fetching real {etf_type} ETF flows from SoSoValue API")
        
        try:
            endpoint = "/openapi/v2/etf/historicalInflowChart"
            
            # SoSoValue uses POST with JSON body
            import json
            payload = {"type": etf_type}
            
            # Override the base _make_request for POST
            response = self.session.post(
                f"{self.base_url}{endpoint}",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            # Rate limiting
            import time
            time.sleep(self.rate_limit_delay)
            
            data = response.json()
            
            # Check API response
            if data.get('code') != 0:
                logger.error(f"SoSoValue API error: {data.get('msg', 'Unknown error')}")
                return []
            
            # Parse and normalize data
            normalized = []
            
            # Handle response structure - data.list is an array
            data_obj = data.get('data', {})
            if isinstance(data_obj, dict):
                etf_list = data_obj.get('list', [])
            elif isinstance(data_obj, list):
                etf_list = data_obj
            else:
                logger.error(f"Unexpected data structure: {type(data_obj)}")
                return []
            
            # Limit to requested days
            etf_list = etf_list[:days] if days < len(etf_list) else etf_list
            
            for entry in etf_list:
                try:
                    normalized.append({
                        'as_of_date': entry.get('date', ''),
                        'ticker': etf_type.upper().replace('-', '_'),  # Use type as ticker
                        'net_flow_usd': float(entry.get('totalNetInflow', 0) or 0),
                        'aum_usd': float(entry.get('totalNetAssets', 0) or 0),
                        'total_value_traded': float(entry.get('totalValueTraded', 0) or 0),
                        'cumulative_net_inflow': float(entry.get('cumNetInflow', 0) or 0),
                        'source': 'SOSOVALUE'
                    })
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Skipping malformed entry: {e}")
            
            logger.info(f"Successfully fetched {len(normalized)} real ETF flow records from SoSoValue")
            return normalized
            
        except Exception as e:
            logger.error(f"Failed to fetch ETF flows from SoSoValue: {e}")
            return []
    
    def fetch_daily_aggregate(self, date: str = None) -> Dict[str, Any]:
        """
        Fetch aggregated ETF flows for a specific date
        
        Args:
            date: Date in YYYY-MM-DD format (defaults to today)
        
        Returns:
            Dictionary with aggregated flow data
        """
        if date is None:
            date = get_date_string()
        
        logger.info(f"Fetching aggregate ETF flows for {date}")
        
        flows = self.fetch_etf_flows(days=1)
        if not flows:
            return {
                'as_of_date': date,
                'total_net_flow_usd': 0,
                'num_etfs': 0
            }
        
        total_flow = sum(f['net_flow_usd'] for f in flows if f['as_of_date'] == date)
        
        return {
            'as_of_date': date,
            'total_net_flow_usd': total_flow,
            'num_etfs': len([f for f in flows if f['as_of_date'] == date])
        }
    
    def fetch_data(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Main fetch method - gets recent BTC ETF flow data
        
        Args:
            days: Number of days to fetch (default: 7 for daily updates)
        
        Returns:
            List of ETF flow records from SoSoValue API
        """
        # Fetch Bitcoin ETF flows
        # Use 7 days by default to ensure we catch any missed days
        # API returns 300 days but we only store what's new (idempotent)
        return self.fetch_etf_flows(days=days, etf_type="us-btc-spot")
    
    def fetch_both_btc_and_eth(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Fetch both Bitcoin and Ethereum ETF flows
        
        Args:
            days: Number of days to fetch
        
        Returns:
            Combined list of BTC and ETH ETF flow records
        """
        all_flows = []
        
        # Fetch BTC ETF flows
        btc_flows = self.fetch_etf_flows(days=days, etf_type="us-btc-spot")
        all_flows.extend(btc_flows)
        
        # Fetch ETH ETF flows
        eth_flows = self.fetch_etf_flows(days=days, etf_type="us-eth-spot")
        all_flows.extend(eth_flows)
        
        return all_flows

