"""Reddit RSS/JSON connector for social sentiment analysis (no API key required)"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from src.connectors.base import BaseConnector
from src.utils.sentiment_analyzer import (
    analyze_vader_sentiment,
    aggregate_sentiment_scores,
    extract_keywords,
    calculate_engagement_score,
    classify_sentiment
)
from src.utils.logger import setup_logger

logger = setup_logger()


class RedditRSSConnector(BaseConnector):
    """Connector for Reddit using public JSON endpoints (no API key required)"""
    
    def __init__(self, rate_limit_delay: float = 2.0):
        """
        Initialize Reddit RSS connector
        
        Args:
            rate_limit_delay: Delay between requests in seconds (Reddit recommends 2s)
        """
        super().__init__(base_url="https://www.reddit.com", rate_limit_delay=rate_limit_delay)
        self.session.headers.update({
            'User-Agent': 'CryptoIntelDashboard/1.0 (by /u/crypto_intel_bot)'
        })
    
    def fetch_subreddit_posts(
        self,
        subreddit_name: str,
        sort: str = 'hot',
        limit: int = 100,
        time_filter: str = 'day'
    ) -> List[Dict[str, Any]]:
        """
        Fetch posts from a subreddit using public JSON endpoint
        
        Args:
            subreddit_name: Name of subreddit (e.g., 'CryptoCurrency')
            sort: Sort order ('hot', 'new', 'top', 'rising')
            limit: Maximum number of posts to fetch (max 100)
            time_filter: Time filter for 'top' sort ('hour', 'day', 'week', 'month', 'year')
        
        Returns:
            List of post dictionaries with metadata and sentiment
        """
        logger.info(f"Fetching posts from r/{subreddit_name} (sort={sort}, limit={limit})")
        
        try:
            # Reddit JSON endpoint format
            endpoint = f"/r/{subreddit_name}/{sort}.json"
            params = {
                'limit': min(limit, 100)  # Reddit max is 100 per request
            }
            
            # Add time filter for 'top' sort
            if sort == 'top':
                params['t'] = time_filter
            
            response = self._make_request(endpoint, params)
            
            if 'data' not in response or 'children' not in response['data']:
                logger.warning(f"No data returned from r/{subreddit_name}")
                return []
            
            posts = []
            for child in response['data']['children']:
                post_data = child.get('data', {})
                
                # Skip stickied posts and ads
                if post_data.get('stickied', False) or post_data.get('promoted', False):
                    continue
                
                # Combine title and selftext for sentiment analysis
                title = post_data.get('title', '')
                selftext = post_data.get('selftext', '')
                text = f"{title} {selftext}".strip()
                
                if not text:
                    continue
                
                # Analyze sentiment
                sentiment = analyze_vader_sentiment(text)
                
                # Parse created timestamp
                created_utc = datetime.fromtimestamp(post_data.get('created_utc', 0))
                
                post_record = {
                    'post_id': post_data.get('id', ''),
                    'platform': 'reddit',
                    'subreddit': subreddit_name,
                    'title': title,
                    'text': selftext,
                    'author': post_data.get('author', '[deleted]'),
                    'created_utc': created_utc,
                    'score': post_data.get('score', 0),
                    'upvote_ratio': post_data.get('upvote_ratio', 0.0),
                    'num_comments': post_data.get('num_comments', 0),
                    'url': f"https://www.reddit.com{post_data.get('permalink', '')}",
                    'sentiment_compound': sentiment['compound'],
                    'sentiment_pos': sentiment['pos'],
                    'sentiment_neg': sentiment['neg'],
                    'sentiment_neu': sentiment['neu'],
                    'sentiment_label': classify_sentiment(sentiment['compound'])
                }
                
                posts.append(post_record)
            
            logger.info(f"Fetched {len(posts)} posts from r/{subreddit_name}")
            return posts
            
        except Exception as e:
            logger.error(f"Failed to fetch posts from r/{subreddit_name}: {e}")
            return []
    
    def fetch_daily_sentiment(
        self,
        subreddits: Optional[List[str]] = None,
        days_back: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Fetch and aggregate daily sentiment from multiple subreddits
        
        Args:
            subreddits: List of subreddit names (default: crypto-related)
            days_back: Number of days to fetch (default: 1)
        
        Returns:
            List of daily sentiment records by platform
        """
        if subreddits is None:
            subreddits = ['CryptoCurrency', 'Bitcoin', 'ethereum']
        
        logger.info(f"Fetching daily sentiment from {len(subreddits)} subreddits")
        
        results = []
        today = datetime.now().date()
        
        for subreddit_name in subreddits:
            try:
                # Determine sort and limit based on days_back
                if days_back <= 1:
                    sort = 'hot'
                    limit = 100
                elif days_back <= 7:
                    sort = 'top'
                    limit = 100
                    time_filter = 'week'
                else:
                    sort = 'top'
                    limit = 100
                    time_filter = 'month'
                
                # Fetch posts
                posts = self.fetch_subreddit_posts(
                    subreddit_name=subreddit_name,
                    sort=sort,
                    limit=limit,
                    time_filter=time_filter if days_back > 1 else 'day'
                )
                
                if not posts:
                    logger.warning(f"No posts fetched from r/{subreddit_name}")
                    continue
                
                # Group posts by date
                posts_by_date = defaultdict(list)
                for post in posts:
                    post_date = post['created_utc'].date()
                    # Only include posts within days_back window
                    if (today - post_date).days < days_back:
                        posts_by_date[post_date].append(post)
                
                # Aggregate sentiment for each date
                for date, date_posts in posts_by_date.items():
                    sentiment_scores = [p['sentiment_compound'] for p in date_posts]
                    aggregated = aggregate_sentiment_scores(sentiment_scores)
                    
                    # Count sentiment categories
                    positive = sum(1 for p in date_posts if p['sentiment_label'] == 'POSITIVE')
                    negative = sum(1 for p in date_posts if p['sentiment_label'] == 'NEGATIVE')
                    neutral = len(date_posts) - positive - negative
                    
                    # Extract keywords
                    texts = [f"{p['title']} {p['text']}" for p in date_posts]
                    keywords = extract_keywords(texts, top_n=10)
                    
                    # Calculate engagement
                    total_engagement = sum([
                        calculate_engagement_score(
                            upvotes=p['score'],
                            comments=p['num_comments'],
                            views=max(p['score'] * 10, 1)  # Estimate views
                        )
                        for p in date_posts
                    ])
                    avg_engagement = total_engagement / len(date_posts) if date_posts else 0
                    
                    record = {
                        'as_of_date': date.strftime('%Y-%m-%d'),
                        'platform': f'reddit_{subreddit_name.lower()}',
                        'mentions_count': len(date_posts),
                        'sentiment_score': aggregated['avg'],
                        'positive_mentions': positive,
                        'negative_mentions': negative,
                        'neutral_mentions': neutral,
                        'engagement_score': round(avg_engagement, 2),
                        'top_keywords': ','.join(keywords[:10]),
                        'source': 'REDDIT_RSS'
                    }
                    
                    results.append(record)
                    logger.info(
                        f"r/{subreddit_name} {date}: {len(date_posts)} posts, "
                        f"sentiment={aggregated['avg']:.3f}, engagement={avg_engagement:.2f}"
                    )
                
            except Exception as e:
                logger.error(f"Failed to process r/{subreddit_name}: {e}")
                continue
        
        logger.info(f"Aggregated sentiment for {len(results)} platform-date combinations")
        return results
    
    def fetch_raw_posts(
        self,
        subreddits: Optional[List[str]] = None,
        days_back: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Fetch raw posts from multiple subreddits (for storage before aggregation)
        
        Args:
            subreddits: List of subreddit names (default: crypto-related)
            days_back: Number of days to fetch (default: 1)
        
        Returns:
            List of raw post records with sentiment
        """
        if subreddits is None:
            subreddits = ['CryptoCurrency', 'Bitcoin', 'ethereum']
        
        logger.info(f"Fetching raw posts from {len(subreddits)} subreddits")
        
        all_posts = []
        today = datetime.now().date()
        
        for subreddit_name in subreddits:
            try:
                # Determine sort and limit based on days_back
                if days_back <= 1:
                    sort = 'hot'
                    limit = 100
                elif days_back <= 7:
                    sort = 'top'
                    limit = 100
                    time_filter = 'week'
                else:
                    sort = 'top'
                    limit = 100
                    time_filter = 'month'
                
                # Fetch posts
                posts = self.fetch_subreddit_posts(
                    subreddit_name=subreddit_name,
                    sort=sort,
                    limit=limit,
                    time_filter=time_filter if days_back > 1 else 'day'
                )
                
                if not posts:
                    logger.warning(f"No posts fetched from r/{subreddit_name}")
                    continue
                
                # Filter posts within days_back window
                for post in posts:
                    post_date = post['created_utc'].date()
                    if (today - post_date).days < days_back:
                        all_posts.append(post)
                
            except Exception as e:
                logger.error(f"Failed to process r/{subreddit_name}: {e}")
                continue
        
        logger.info(f"Fetched {len(all_posts)} raw posts total")
        return all_posts
    
    def fetch_data(self, days: int = 1) -> List[Dict[str, Any]]:
        """
        Main fetch method - gets daily sentiment from crypto subreddits
        
        Args:
            days: Number of days to fetch (default: 1)
        
        Returns:
            List of daily sentiment records
        """
        return self.fetch_daily_sentiment(days_back=days)

