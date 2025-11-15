"""Reddit API connector for social sentiment analysis"""
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


class RedditConnector(BaseConnector):
    """Connector for Reddit social sentiment data"""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        user_agent: str,
        rate_limit_delay: float = 2.0
    ):
        """
        Initialize Reddit connector
        
        Args:
            client_id: Reddit API client ID
            client_secret: Reddit API client secret
            user_agent: User agent string for Reddit API
            rate_limit_delay: Delay between requests in seconds
        """
        # Reddit uses OAuth2, not a simple REST API
        # We'll use PRAW (Python Reddit API Wrapper)
        super().__init__(base_url="https://oauth.reddit.com", rate_limit_delay=rate_limit_delay)
        
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self._reddit = None
    
    def _get_reddit_instance(self):
        """Get or create Reddit API instance"""
        if self._reddit is None:
            try:
                import praw
                
                self._reddit = praw.Reddit(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    user_agent=self.user_agent,
                    check_for_async=False
                )
                
                logger.info("Reddit API connection established")
                
            except ImportError:
                logger.error("praw library not installed. Run: pip install praw")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize Reddit API: {e}")
                raise
        
        return self._reddit
    
    def fetch_subreddit_posts(
        self,
        subreddit_name: str,
        time_filter: str = 'day',
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch posts from a subreddit
        
        Args:
            subreddit_name: Name of subreddit (e.g., 'CryptoCurrency')
            time_filter: Time filter ('hour', 'day', 'week', 'month', 'year')
            limit: Maximum number of posts to fetch
        
        Returns:
            List of post dictionaries with metadata and sentiment
        """
        logger.info(f"Fetching posts from r/{subreddit_name} (filter={time_filter}, limit={limit})")
        
        try:
            reddit = self._get_reddit_instance()
            subreddit = reddit.subreddit(subreddit_name)
            
            posts = []
            
            # Fetch hot posts from the time period
            for submission in subreddit.top(time_filter=time_filter, limit=limit):
                # Combine title and selftext for sentiment analysis
                text = f"{submission.title} {submission.selftext}"
                
                # Analyze sentiment
                sentiment = analyze_vader_sentiment(text)
                
                post_data = {
                    'id': submission.id,
                    'platform': 'reddit',
                    'subreddit': subreddit_name,
                    'title': submission.title,
                    'text': submission.selftext,
                    'author': str(submission.author) if submission.author else '[deleted]',
                    'created_utc': datetime.fromtimestamp(submission.created_utc),
                    'score': submission.score,
                    'upvote_ratio': submission.upvote_ratio,
                    'num_comments': submission.num_comments,
                    'url': submission.url,
                    'sentiment_compound': sentiment['compound'],
                    'sentiment_pos': sentiment['pos'],
                    'sentiment_neg': sentiment['neg'],
                    'sentiment_neu': sentiment['neu'],
                    'sentiment_label': classify_sentiment(sentiment['compound'])
                }
                
                posts.append(post_data)
            
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
                # Determine time filter based on days_back
                if days_back <= 1:
                    time_filter = 'day'
                    limit = 100
                elif days_back <= 7:
                    time_filter = 'week'
                    limit = 200
                else:
                    time_filter = 'month'
                    limit = 500
                
                # Fetch posts
                posts = self.fetch_subreddit_posts(
                    subreddit_name=subreddit_name,
                    time_filter=time_filter,
                    limit=limit
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
                        'source': 'REDDIT'
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
                # Determine time filter based on days_back
                if days_back <= 1:
                    time_filter = 'day'
                    limit = 100
                elif days_back <= 7:
                    time_filter = 'week'
                    limit = 200
                else:
                    time_filter = 'month'
                    limit = 500
                
                # Fetch posts
                posts = self.fetch_subreddit_posts(
                    subreddit_name=subreddit_name,
                    time_filter=time_filter,
                    limit=limit
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

