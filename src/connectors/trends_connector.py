"""Google Trends connector for search interest analysis"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from src.utils.logger import setup_logger

logger = setup_logger()


class TrendsConnector:
    """Connector for Google Trends search interest data"""
    
    def __init__(self, rate_limit_delay: float = 2.0):
        """
        Initialize Google Trends connector
        
        Args:
            rate_limit_delay: Delay between requests in seconds
        """
        self.rate_limit_delay = rate_limit_delay
        self._pytrends = None
    
    def _get_pytrends_instance(self):
        """Get or create pytrends instance"""
        if self._pytrends is None:
            try:
                from pytrends.request import TrendReq
                import time
                
                # Initialize with retries
                self._pytrends = TrendReq(
                    hl='en-US',
                    tz=0,
                    timeout=(10, 25),
                    retries=3,
                    backoff_factor=self.rate_limit_delay
                )
                
                logger.info("Google Trends API connection established")
                
            except ImportError:
                logger.error("pytrends library not installed. Run: pip install pytrends")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize Google Trends API: {e}")
                raise
        
        return self._pytrends
    
    def fetch_interest_over_time(
        self,
        keywords: List[str],
        timeframe: str = 'now 7-d',
        geo: str = ''
    ) -> Dict[str, Any]:
        """
        Fetch search interest over time for keywords
        
        Args:
            keywords: List of keywords to track (max 5)
            timeframe: Time range ('now 1-d', 'now 7-d', 'today 1-m', 'today 3-m', etc.)
            geo: Geographic location ('' for worldwide, 'US' for United States, etc.)
        
        Returns:
            Dictionary with interest data by keyword
        """
        if not keywords:
            logger.warning("No keywords provided for trends search")
            return {}
        
        # Limit to 5 keywords (Google Trends API limit)
        keywords = keywords[:5]
        
        logger.info(f"Fetching trends for keywords: {keywords}, timeframe={timeframe}")
        
        try:
            import time
            pytrends = self._get_pytrends_instance()
            
            # Build payload
            pytrends.build_payload(
                kw_list=keywords,
                cat=0,  # All categories
                timeframe=timeframe,
                geo=geo,
                gprop=''  # Web search
            )
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            # Get interest over time
            interest_df = pytrends.interest_over_time()
            
            if interest_df.empty:
                logger.warning(f"No trends data returned for keywords: {keywords}")
                return {}
            
            # Remove 'isPartial' column if present
            if 'isPartial' in interest_df.columns:
                interest_df = interest_df.drop(columns=['isPartial'])
            
            logger.info(f"Fetched trends data: {len(interest_df)} time points")
            
            return {
                'data': interest_df,
                'keywords': keywords,
                'timeframe': timeframe
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch Google Trends data: {e}")
            return {}
    
    def fetch_related_queries(self, keyword: str) -> Dict[str, List[str]]:
        """
        Fetch related queries for a keyword
        
        Args:
            keyword: Keyword to get related queries for
        
        Returns:
            Dictionary with 'top' and 'rising' related queries
        """
        logger.info(f"Fetching related queries for: {keyword}")
        
        try:
            import time
            pytrends = self._get_pytrends_instance()
            
            # Build payload
            pytrends.build_payload(
                kw_list=[keyword],
                timeframe='now 7-d'
            )
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            # Get related queries
            related = pytrends.related_queries()
            
            if not related or keyword not in related:
                logger.warning(f"No related queries found for: {keyword}")
                return {'top': [], 'rising': []}
            
            keyword_data = related[keyword]
            
            # Extract top queries
            top_queries = []
            if keyword_data.get('top') is not None and not keyword_data['top'].empty:
                top_queries = keyword_data['top']['query'].head(10).tolist()
            
            # Extract rising queries
            rising_queries = []
            if keyword_data.get('rising') is not None and not keyword_data['rising'].empty:
                rising_queries = keyword_data['rising']['query'].head(10).tolist()
            
            logger.info(f"Found {len(top_queries)} top and {len(rising_queries)} rising queries")
            
            return {
                'top': top_queries,
                'rising': rising_queries
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch related queries: {e}")
            return {'top': [], 'rising': []}
    
    def fetch_daily_interest(
        self,
        keywords: Optional[List[str]] = None,
        days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Fetch daily search interest for crypto keywords
        
        Args:
            keywords: List of keywords (default: crypto-related)
            days_back: Number of days to fetch (default: 7)
        
        Returns:
            List of daily interest records by keyword
        """
        if keywords is None:
            keywords = ['bitcoin', 'ethereum', 'cryptocurrency']
        
        logger.info(f"Fetching daily search interest for {len(keywords)} keywords")
        
        results = []
        
        # Determine timeframe
        if days_back <= 1:
            timeframe = 'now 1-d'
        elif days_back <= 7:
            timeframe = 'now 7-d'
        elif days_back <= 30:
            timeframe = 'today 1-m'
        else:
            timeframe = 'today 3-m'
        
        try:
            # Fetch interest over time
            trends_data = self.fetch_interest_over_time(
                keywords=keywords,
                timeframe=timeframe
            )
            
            if not trends_data or 'data' not in trends_data:
                logger.warning("No trends data available")
                return []
            
            interest_df = trends_data['data']
            
            # Process each keyword
            for keyword in keywords:
                if keyword not in interest_df.columns:
                    logger.warning(f"Keyword '{keyword}' not in trends data")
                    continue
                
                # Get data for the last days_back days
                recent_data = interest_df[keyword].tail(days_back)
                
                # Fetch related queries
                related = self.fetch_related_queries(keyword)
                related_queries_str = ','.join(related.get('top', [])[:5])
                
                # Create records for each day
                for date, interest_score in recent_data.items():
                    # Calculate change percentage (if we have previous data)
                    try:
                        prev_score = interest_df[keyword].shift(1).loc[date]
                        if prev_score and prev_score > 0:
                            change_pct = ((interest_score - prev_score) / prev_score) * 100
                        else:
                            change_pct = None
                    except:
                        change_pct = None
                    
                    record = {
                        'as_of_date': date.strftime('%Y-%m-%d'),
                        'keyword': keyword,
                        'interest_score': float(interest_score),
                        'interest_change_pct': round(change_pct, 2) if change_pct is not None else None,
                        'related_queries': related_queries_str,
                        'source': 'GOOGLE_TRENDS'
                    }
                    
                    results.append(record)
                    logger.debug(
                        f"{keyword} {date.strftime('%Y-%m-%d')}: "
                        f"interest={interest_score}, change={change_pct:.1f}%" if change_pct else ""
                    )
            
            logger.info(f"Processed {len(results)} search interest records")
            return results
            
        except Exception as e:
            logger.error(f"Failed to fetch daily interest: {e}")
            return []
    
    def fetch_raw_trends(
        self,
        keywords: Optional[List[str]] = None,
        days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Fetch raw search trends data (for storage before aggregation)
        
        Args:
            keywords: List of keywords (default: crypto-related)
            days_back: Number of days to fetch (default: 7)
        
        Returns:
            List of raw trend records
        """
        if keywords is None:
            keywords = ['bitcoin', 'ethereum', 'cryptocurrency']
        
        logger.info(f"Fetching raw search trends for {len(keywords)} keywords")
        
        results = []
        
        # Determine timeframe
        if days_back <= 1:
            timeframe = 'now 1-d'
        elif days_back <= 7:
            timeframe = 'now 7-d'
        elif days_back <= 30:
            timeframe = 'today 1-m'
        else:
            timeframe = 'today 3-m'
        
        try:
            # Fetch interest over time
            trends_data = self.fetch_interest_over_time(
                keywords=keywords,
                timeframe=timeframe
            )
            
            if not trends_data or 'data' not in trends_data:
                logger.warning("No trends data available")
                return []
            
            interest_df = trends_data['data']
            
            # Process each keyword
            for keyword in keywords:
                if keyword not in interest_df.columns:
                    logger.warning(f"Keyword '{keyword}' not in trends data")
                    continue
                
                # Get data for the last days_back days
                recent_data = interest_df[keyword].tail(days_back)
                
                # Create records for each timestamp
                for date, interest_score in recent_data.items():
                    record = {
                        'ts_utc': date,
                        'keyword': keyword,
                        'interest_score': float(interest_score),
                        'geo': '',
                        'timeframe': timeframe
                    }
                    
                    results.append(record)
            
            logger.info(f"Processed {len(results)} raw search trend records")
            return results
            
        except Exception as e:
            logger.error(f"Failed to fetch raw trends: {e}")
            return []
    
    def fetch_data(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Main fetch method - gets daily search interest
        
        Args:
            days: Number of days to fetch (default: 7)
        
        Returns:
            List of daily search interest records
        """
        return self.fetch_daily_interest(days_back=days)

