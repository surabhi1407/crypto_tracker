"""Base connector class with retry logic and rate limiting"""
import time
import requests
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from src.utils.logger import setup_logger

logger = setup_logger()


class BaseConnector(ABC):
    """Base class for API connectors with common functionality"""
    
    def __init__(self, base_url: str, rate_limit_delay: float = 1.5):
        """
        Initialize base connector
        
        Args:
            base_url: Base URL for the API
            rate_limit_delay: Delay between requests in seconds
        """
        self.base_url = base_url
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CryptoIntelDashboard/0.1.0'
        })
    
    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Make HTTP GET request with retry logic
        
        Args:
            endpoint: API endpoint (will be appended to base_url)
            params: Query parameters
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
        
        Returns:
            JSON response as dictionary
        
        Raises:
            requests.RequestException: If all retries fail
        """
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"Request to {url} (attempt {attempt + 1}/{max_retries})")
                
                response = self.session.get(
                    url,
                    params=params,
                    timeout=timeout
                )
                response.raise_for_status()
                
                # Rate limiting
                time.sleep(self.rate_limit_delay)
                
                return response.json()
                
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt + 1} for {url}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limit
                    wait_time = 2 ** (attempt + 1)
                    logger.warning(f"Rate limited. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"HTTP error {e.response.status_code}: {e}")
                    raise
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
        
        raise requests.RequestException(f"Failed after {max_retries} attempts")
    
    @abstractmethod
    def fetch_data(self) -> Any:
        """Fetch data from the API - to be implemented by subclasses"""
        pass

