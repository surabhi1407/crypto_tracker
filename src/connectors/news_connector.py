"""NewsAPI connector for news sentiment analysis using FinBERT"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import Counter
from src.connectors.base import BaseConnector
from src.utils.sentiment_analyzer import (
    analyze_finbert_sentiment,
    aggregate_sentiment_scores,
    extract_keywords,
    classify_sentiment
)
from src.utils.logger import setup_logger

logger = setup_logger()


class NewsConnector(BaseConnector):
    """Connector for NewsAPI with FinBERT sentiment analysis"""
    
    def __init__(self, api_key: str, rate_limit_delay: float = 1.0):
        """
        Initialize NewsAPI connector
        
        Args:
            api_key: NewsAPI API key
            rate_limit_delay: Delay between requests in seconds
        """
        base_url = "https://newsapi.org/v2"
        super().__init__(base_url, rate_limit_delay)
        self.api_key = api_key
    
    def fetch_crypto_news(
        self,
        query: str = 'bitcoin OR ethereum OR cryptocurrency',
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        language: str = 'en',
        page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch crypto-related news articles
        
        Args:
            query: Search query for news articles
            from_date: Start date (YYYY-MM-DD format)
            to_date: End date (YYYY-MM-DD format)
            language: Language code (default: 'en')
            page_size: Number of articles per page (max 100)
        
        Returns:
            List of article dictionaries with metadata and sentiment
        """
        logger.info(f"Fetching news articles: query='{query}', from={from_date}, to={to_date}")
        
        endpoint = "/everything"
        
        params = {
            'q': query,
            'language': language,
            'sortBy': 'publishedAt',
            'pageSize': min(page_size, 100),
            'apiKey': self.api_key
        }
        
        if from_date:
            params['from'] = from_date
        if to_date:
            params['to'] = to_date
        
        try:
            response = self._make_request(endpoint, params)
            
            if response.get('status') != 'ok':
                logger.error(f"NewsAPI error: {response.get('message', 'Unknown error')}")
                return []
            
            articles = response.get('articles', [])
            logger.info(f"Fetched {len(articles)} articles from NewsAPI")
            
            # Process articles with sentiment analysis
            processed = []
            for article in articles:
                # Combine title and description for sentiment
                text = f"{article.get('title', '')} {article.get('description', '')}"
                
                # Skip if no meaningful text
                if not text.strip() or text.strip() == '[Removed]':
                    continue
                
                # Analyze sentiment using FinBERT
                sentiment = analyze_finbert_sentiment(text)
                
                # Parse published date
                published_at = article.get('publishedAt', '')
                try:
                    pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                except:
                    pub_date = datetime.now()
                
                processed_article = {
                    'title': article.get('title', ''),
                    'description': article.get('description', ''),
                    'source': article.get('source', {}).get('name', 'Unknown'),
                    'author': article.get('author', 'Unknown'),
                    'url': article.get('url', ''),
                    'published_at': pub_date,
                    'sentiment_compound': sentiment['compound'],
                    'sentiment_label': sentiment['label'],
                    'sentiment_confidence': sentiment['score'],
                    'positive_prob': sentiment.get('positive_prob', 0),
                    'negative_prob': sentiment.get('negative_prob', 0),
                    'neutral_prob': sentiment.get('neutral_prob', 0)
                }
                
                processed.append(processed_article)
            
            logger.info(f"Processed {len(processed)} articles with FinBERT sentiment")
            return processed
            
        except Exception as e:
            logger.error(f"Failed to fetch news articles: {e}")
            return []
    
    def fetch_daily_sentiment(
        self,
        days_back: int = 1,
        query: str = 'bitcoin OR ethereum OR cryptocurrency'
    ) -> List[Dict[str, Any]]:
        """
        Fetch and aggregate daily news sentiment
        
        Args:
            days_back: Number of days to fetch (default: 1)
            query: Search query for news articles
        
        Returns:
            List of daily sentiment records
        """
        logger.info(f"Fetching daily news sentiment for last {days_back} days")
        
        results = []
        today = datetime.now().date()
        
        # Fetch articles for the date range
        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        to_date = datetime.now().strftime('%Y-%m-%d')
        
        articles = self.fetch_crypto_news(
            query=query,
            from_date=from_date,
            to_date=to_date,
            page_size=100
        )
        
        if not articles:
            logger.warning("No articles fetched for sentiment analysis")
            return []
        
        # Group articles by date
        from collections import defaultdict
        articles_by_date = defaultdict(list)
        
        for article in articles:
            article_date = article['published_at'].date()
            # Only include articles within days_back window
            if (today - article_date).days < days_back:
                articles_by_date[article_date].append(article)
        
        # Aggregate sentiment for each date
        for date, date_articles in articles_by_date.items():
            sentiment_scores = [a['sentiment_compound'] for a in date_articles]
            aggregated = aggregate_sentiment_scores(sentiment_scores)
            
            # Count sentiment categories
            positive = sum(1 for a in date_articles if a['sentiment_label'] == 'positive')
            negative = sum(1 for a in date_articles if a['sentiment_label'] == 'negative')
            neutral = len(date_articles) - positive - negative
            
            # Extract top sources
            sources = [a['source'] for a in date_articles if a['source'] != 'Unknown']
            source_counter = Counter(sources)
            top_sources = [src for src, _ in source_counter.most_common(5)]
            
            # Extract keywords from titles
            titles = [a['title'] for a in date_articles]
            keywords = extract_keywords(titles, top_n=10)
            
            record = {
                'as_of_date': date.strftime('%Y-%m-%d'),
                'article_count': len(date_articles),
                'avg_sentiment': aggregated['avg'],
                'positive_pct': aggregated['positive_pct'],
                'negative_pct': aggregated['negative_pct'],
                'neutral_pct': aggregated['neutral_pct'],
                'top_sources': ','.join(top_sources),
                'top_keywords': ','.join(keywords[:10]),
                'source': 'NEWSAPI'
            }
            
            results.append(record)
            logger.info(
                f"News {date}: {len(date_articles)} articles, "
                f"sentiment={aggregated['avg']:.3f}, "
                f"pos={aggregated['positive_pct']:.1f}%, neg={aggregated['negative_pct']:.1f}%"
            )
        
        logger.info(f"Aggregated news sentiment for {len(results)} days")
        return results
    
    def fetch_raw_articles(
        self,
        days_back: int = 1,
        query: str = 'bitcoin OR ethereum OR cryptocurrency'
    ) -> List[Dict[str, Any]]:
        """
        Fetch raw news articles (for storage before aggregation)
        
        Args:
            days_back: Number of days to fetch (default: 1)
            query: Search query for news articles
        
        Returns:
            List of raw article records with sentiment
        """
        logger.info(f"Fetching raw news articles for last {days_back} days")
        
        # Fetch articles for the date range
        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        to_date = datetime.now().strftime('%Y-%m-%d')
        
        articles = self.fetch_crypto_news(
            query=query,
            from_date=from_date,
            to_date=to_date,
            page_size=100
        )
        
        if not articles:
            logger.warning("No articles fetched")
            return []
        
        # Filter articles within days_back window
        today = datetime.now().date()
        filtered_articles = []
        
        for article in articles:
            article_date = article['published_at'].date()
            if (today - article_date).days < days_back:
                filtered_articles.append(article)
        
        logger.info(f"Fetched {len(filtered_articles)} raw articles")
        return filtered_articles
    
    def fetch_data(self, days: int = 1) -> List[Dict[str, Any]]:
        """
        Main fetch method - gets daily news sentiment
        
        Args:
            days: Number of days to fetch (default: 1)
        
        Returns:
            List of daily news sentiment records
        """
        return self.fetch_daily_sentiment(days_back=days)

