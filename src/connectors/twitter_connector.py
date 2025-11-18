"""Twitter/X API connector for social sentiment analysis"""
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


class TwitterConnector(BaseConnector):
    """Connector for Twitter/X API v2 with sentiment analysis"""
    
    def __init__(self, bearer_token: str, rate_limit_delay: float = 1.0):
        """
        Initialize Twitter connector
        
        Args:
            bearer_token: Twitter API v2 Bearer Token
            rate_limit_delay: Delay between requests in seconds
        """
        super().__init__(base_url="https://api.twitter.com/2", rate_limit_delay=rate_limit_delay)
        self.bearer_token = bearer_token
        self.session.headers.update({
            'Authorization': f'Bearer {bearer_token}',
            'User-Agent': 'CryptoIntelDashboard/1.0'
        })
    
    def search_tweets(
        self,
        query: str,
        max_results: int = 100,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for tweets using Twitter API v2
        
        Args:
            query: Search query (e.g., 'bitcoin OR ethereum')
            max_results: Maximum number of tweets (10-100)
            start_time: Start time in ISO 8601 format (YYYY-MM-DDTHH:mm:ssZ)
            end_time: End time in ISO 8601 format (YYYY-MM-DDTHH:mm:ssZ)
        
        Returns:
            List of tweet dictionaries with metadata and sentiment
        """
        logger.info(f"Searching tweets: query='{query}', max_results={max_results}")
        
        endpoint = "/tweets/search/recent"
        params = {
            'query': query,
            'max_results': min(max_results, 100),
            'tweet.fields': 'created_at,public_metrics,author_id,text',
            'expansions': 'author_id',
            'user.fields': 'username'
        }
        
        if start_time:
            params['start_time'] = start_time
        if end_time:
            params['end_time'] = end_time
        
        try:
            response = self._make_request(endpoint, params)
            
            if 'data' not in response:
                logger.warning("No tweets returned from Twitter API")
                return []
            
            # Map author IDs to usernames
            users = {}
            if 'includes' in response and 'users' in response['includes']:
                for user in response['includes']['users']:
                    users[user['id']] = user.get('username', 'unknown')
            
            tweets = []
            for tweet_data in response['data']:
                text = tweet_data.get('text', '')
                if not text:
                    continue
                
                # Analyze sentiment
                sentiment = analyze_vader_sentiment(text)
                
                # Parse created timestamp
                created_at = tweet_data.get('created_at', '')
                try:
                    created_utc = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except:
                    created_utc = datetime.now()
                
                # Get metrics
                metrics = tweet_data.get('public_metrics', {})
                
                # Map Twitter data to social_posts_raw schema format
                tweet_record = {
                    'post_id': tweet_data.get('id', ''),
                    'platform': 'twitter',
                    'subreddit': None,  # Not applicable for Twitter
                    'title': None,  # Twitter doesn't have titles
                    'text': text,
                    'author': users.get(tweet_data.get('author_id', ''), 'unknown'),
                    'created_utc': created_utc,
                    'score': metrics.get('like_count', 0),  # Use likes as score
                    'upvote_ratio': 0.0,  # Not applicable for Twitter
                    'num_comments': metrics.get('reply_count', 0),  # Use replies as comments
                    'url': f"https://twitter.com/i/web/status/{tweet_data.get('id', '')}",
                    'sentiment_compound': sentiment['compound'],
                    'sentiment_pos': sentiment['pos'],
                    'sentiment_neg': sentiment['neg'],
                    'sentiment_neu': sentiment['neu'],
                    'sentiment_label': classify_sentiment(sentiment['compound']),
                    # Store additional Twitter metrics for reference
                    'retweet_count': metrics.get('retweet_count', 0),
                    'quote_count': metrics.get('quote_count', 0)
                }
                
                tweets.append(tweet_record)
            
            logger.info(f"Fetched {len(tweets)} tweets from Twitter API")
            return tweets
            
        except Exception as e:
            logger.error(f"Failed to fetch tweets: {e}")
            return []
    
    def fetch_daily_sentiment(
        self,
        keywords: Optional[List[str]] = None,
        days_back: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Fetch and aggregate daily sentiment from Twitter
        
        Args:
            keywords: List of keywords to search (default: crypto-related)
            days_back: Number of days to fetch (default: 1)
        
        Returns:
            List of daily sentiment records
        """
        if keywords is None:
            keywords = ['bitcoin', 'ethereum', 'cryptocurrency']
        
        logger.info(f"Fetching daily Twitter sentiment for {len(keywords)} keywords")
        
        # Build query
        query = ' OR '.join(keywords)
        query += ' -is:retweet lang:en'  # Exclude retweets, English only
        
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)
        
        # Fetch tweets
        tweets = self.search_tweets(
            query=query,
            max_results=100,
            start_time=start_time.isoformat() + 'Z',
            end_time=end_time.isoformat() + 'Z'
        )
        
        if not tweets:
            logger.warning("No tweets fetched for sentiment analysis")
            return []
        
        # Group tweets by date
        tweets_by_date = defaultdict(list)
        today = datetime.now().date()
        
        for tweet in tweets:
            tweet_date = tweet['created_utc'].date()
            if (today - tweet_date).days < days_back:
                tweets_by_date[tweet_date].append(tweet)
        
        # Aggregate sentiment for each date
        results = []
        for date, date_tweets in tweets_by_date.items():
            sentiment_scores = [t['sentiment_compound'] for t in date_tweets]
            aggregated = aggregate_sentiment_scores(sentiment_scores)
            
            # Count sentiment categories
            positive = sum(1 for t in date_tweets if t['sentiment_label'] == 'POSITIVE')
            negative = sum(1 for t in date_tweets if t['sentiment_label'] == 'NEGATIVE')
            neutral = len(date_tweets) - positive - negative
            
            # Extract keywords
            texts = [t['text'] for t in date_tweets]
            keywords_list = extract_keywords(texts, top_n=10)
            
            # Calculate engagement (likes + retweets + replies)
            total_engagement = sum([
                calculate_engagement_score(
                    upvotes=t.get('score', t.get('like_count', 0)),
                    comments=t.get('num_comments', t.get('reply_count', 0)),
                    views=t.get('retweet_count', 0) + t.get('score', t.get('like_count', 0)) + t.get('num_comments', t.get('reply_count', 0))
                )
                for t in date_tweets
            ])
            avg_engagement = total_engagement / len(date_tweets) if date_tweets else 0
            
            record = {
                'as_of_date': date.strftime('%Y-%m-%d'),
                'platform': 'twitter',
                'mentions_count': len(date_tweets),
                'sentiment_score': aggregated['avg'],
                'positive_mentions': positive,
                'negative_mentions': negative,
                'neutral_mentions': neutral,
                'engagement_score': round(avg_engagement, 2),
                'top_keywords': ','.join(keywords_list[:10]),
                'source': 'TWITTER'
            }
            
            results.append(record)
            logger.info(
                f"Twitter {date}: {len(date_tweets)} tweets, "
                f"sentiment={aggregated['avg']:.3f}, engagement={avg_engagement:.2f}"
            )
        
        logger.info(f"Aggregated Twitter sentiment for {len(results)} days")
        return results
    
    def fetch_raw_tweets(
        self,
        keywords: Optional[List[str]] = None,
        days_back: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Fetch raw tweets (for storage before aggregation)
        
        Args:
            keywords: List of keywords to search (default: crypto-related)
            days_back: Number of days to fetch (default: 1)
        
        Returns:
            List of raw tweet records with sentiment
        """
        if keywords is None:
            keywords = ['bitcoin', 'ethereum', 'cryptocurrency']
        
        logger.info(f"Fetching raw tweets for {len(keywords)} keywords")
        
        # Build query
        query = ' OR '.join(keywords)
        query += ' -is:retweet lang:en'
        
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)
        
        tweets = self.search_tweets(
            query=query,
            max_results=100,
            start_time=start_time.isoformat() + 'Z',
            end_time=end_time.isoformat() + 'Z'
        )
        
        if not tweets:
            logger.warning("No tweets fetched")
            return []
        
        # Filter tweets within days_back window
        today = datetime.now().date()
        filtered_tweets = []
        
        for tweet in tweets:
            tweet_date = tweet['created_utc'].date()
            if (today - tweet_date).days < days_back:
                filtered_tweets.append(tweet)
        
        logger.info(f"Fetched {len(filtered_tweets)} raw tweets")
        return filtered_tweets
    
    def fetch_data(self, days: int = 1) -> List[Dict[str, Any]]:
        """
        Main fetch method - gets daily sentiment from Twitter
        
        Args:
            days: Number of days to fetch (default: 1)
        
        Returns:
            List of daily sentiment records
        """
        return self.fetch_daily_sentiment(days_back=days)

