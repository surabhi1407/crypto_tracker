"""Tests for Phase 3 raw data storage and aggregation"""
import unittest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path

from src.storage.database import MarketDatabase
from src.storage.schema import DatabaseSchema


class TestRawDataStorage(unittest.TestCase):
    """Test raw data storage and aggregation for Phase 3"""
    
    def setUp(self):
        """Set up test database"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_raw_data.db')
        self.db = MarketDatabase(self.db_path)
    
    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_schema_version_updated(self):
        """Test that schema version is updated to 4"""
        schema = DatabaseSchema(self.db_path)
        self.assertEqual(schema.SCHEMA_VERSION, 4)
    
    def test_raw_tables_exist(self):
        """Test that raw data tables are created"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check for raw data tables
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN (?, ?, ?)",
            ('social_posts_raw', 'news_articles_raw', 'search_trends_raw')
        )
        tables = [row[0] for row in cursor.fetchall()]
        
        self.assertIn('social_posts_raw', tables)
        self.assertIn('news_articles_raw', tables)
        self.assertIn('search_trends_raw', tables)
        
        conn.close()
    
    def test_insert_social_posts_raw(self):
        """Test inserting raw social posts"""
        test_posts = [
            {
                'id': 'post123',
                'platform': 'reddit',
                'subreddit': 'CryptoCurrency',
                'title': 'Bitcoin hits new high',
                'text': 'This is amazing news for crypto!',
                'author': 'testuser',
                'created_utc': datetime.now(),
                'score': 100,
                'upvote_ratio': 0.95,
                'num_comments': 50,
                'url': 'https://reddit.com/r/CryptoCurrency/post123',
                'sentiment_compound': 0.8,
                'sentiment_pos': 0.7,
                'sentiment_neg': 0.1,
                'sentiment_neu': 0.2,
                'sentiment_label': 'POSITIVE'
            },
            {
                'id': 'post456',
                'platform': 'reddit',
                'subreddit': 'Bitcoin',
                'title': 'Market crash incoming',
                'text': 'This looks bad for crypto',
                'author': 'testuser2',
                'created_utc': datetime.now(),
                'score': 50,
                'upvote_ratio': 0.75,
                'num_comments': 25,
                'url': 'https://reddit.com/r/Bitcoin/post456',
                'sentiment_compound': -0.6,
                'sentiment_pos': 0.1,
                'sentiment_neg': 0.7,
                'sentiment_neu': 0.2,
                'sentiment_label': 'NEGATIVE'
            }
        ]
        
        count = self.db.insert_social_posts_raw(test_posts)
        self.assertEqual(count, 2)
        
        # Verify data was inserted
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM social_posts_raw")
        result = cursor.fetchone()[0]
        self.assertEqual(result, 2)
        conn.close()
    
    def test_insert_news_articles_raw(self):
        """Test inserting raw news articles"""
        test_articles = [
            {
                'url': 'https://news.com/article1',
                'title': 'Bitcoin price surges',
                'description': 'Bitcoin reaches all-time high',
                'source': 'CryptoNews',
                'author': 'John Doe',
                'published_at': datetime.now(),
                'sentiment_compound': 0.7,
                'sentiment_label': 'positive',
                'sentiment_confidence': 0.9,
                'positive_prob': 0.8,
                'negative_prob': 0.1,
                'neutral_prob': 0.1
            },
            {
                'url': 'https://news.com/article2',
                'title': 'Ethereum faces challenges',
                'description': 'Network congestion continues',
                'source': 'TechNews',
                'author': 'Jane Smith',
                'published_at': datetime.now(),
                'sentiment_compound': -0.4,
                'sentiment_label': 'negative',
                'sentiment_confidence': 0.85,
                'positive_prob': 0.1,
                'negative_prob': 0.7,
                'neutral_prob': 0.2
            }
        ]
        
        count = self.db.insert_news_articles_raw(test_articles)
        self.assertEqual(count, 2)
        
        # Verify data was inserted
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM news_articles_raw")
        result = cursor.fetchone()[0]
        self.assertEqual(result, 2)
        conn.close()
    
    def test_insert_search_trends_raw(self):
        """Test inserting raw search trends"""
        test_trends = [
            {
                'ts_utc': datetime.now(),
                'keyword': 'bitcoin',
                'interest_score': 85.0,
                'geo': '',
                'timeframe': 'now 7-d'
            },
            {
                'ts_utc': datetime.now(),
                'keyword': 'ethereum',
                'interest_score': 72.0,
                'geo': '',
                'timeframe': 'now 7-d'
            }
        ]
        
        count = self.db.insert_search_trends_raw(test_trends)
        self.assertEqual(count, 2)
        
        # Verify data was inserted
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM search_trends_raw")
        result = cursor.fetchone()[0]
        self.assertEqual(result, 2)
        conn.close()
    
    def test_compute_social_sentiment_from_raw(self):
        """Test computing aggregated social sentiment from raw posts"""
        today = datetime.now()
        test_date = today.strftime('%Y-%m-%d')
        
        # Insert raw posts
        test_posts = [
            {
                'id': f'post{i}',
                'platform': 'reddit_cryptocurrency',
                'subreddit': 'CryptoCurrency',
                'title': f'Post {i}',
                'text': 'Test content',
                'author': 'testuser',
                'created_utc': today,
                'score': 100,
                'upvote_ratio': 0.9,
                'num_comments': 10,
                'url': f'https://reddit.com/post{i}',
                'sentiment_compound': 0.5 if i % 2 == 0 else -0.3,
                'sentiment_pos': 0.6 if i % 2 == 0 else 0.2,
                'sentiment_neg': 0.2 if i % 2 == 0 else 0.6,
                'sentiment_neu': 0.2,
                'sentiment_label': 'POSITIVE' if i % 2 == 0 else 'NEGATIVE'
            }
            for i in range(10)
        ]
        
        self.db.insert_social_posts_raw(test_posts)
        
        # Compute aggregated sentiment
        self.db.compute_social_sentiment_from_raw(test_date)
        
        # Verify aggregated data was created
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT mentions_count, positive_mentions, negative_mentions FROM social_sentiment_daily WHERE as_of_date = ?",
            (test_date,)
        )
        result = cursor.fetchone()
        
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 10)  # mentions_count
        self.assertEqual(result[1], 5)   # positive_mentions
        self.assertEqual(result[2], 5)   # negative_mentions
        
        conn.close()
    
    def test_compute_news_sentiment_from_raw(self):
        """Test computing aggregated news sentiment from raw articles"""
        today = datetime.now()
        test_date = today.strftime('%Y-%m-%d')
        
        # Insert raw articles
        test_articles = [
            {
                'url': f'https://news.com/article{i}',
                'title': f'Article {i}',
                'description': 'Test content',
                'source': 'TestNews',
                'author': 'Author',
                'published_at': today,
                'sentiment_compound': 0.6 if i < 7 else -0.4,
                'sentiment_label': 'positive' if i < 7 else 'negative',
                'sentiment_confidence': 0.9,
                'positive_prob': 0.7 if i < 7 else 0.2,
                'negative_prob': 0.2 if i < 7 else 0.7,
                'neutral_prob': 0.1
            }
            for i in range(10)
        ]
        
        self.db.insert_news_articles_raw(test_articles)
        
        # Compute aggregated sentiment
        self.db.compute_news_sentiment_from_raw(test_date)
        
        # Verify aggregated data was created
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT article_count, positive_pct, negative_pct FROM news_sentiment_daily WHERE as_of_date = ?",
            (test_date,)
        )
        result = cursor.fetchone()
        
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 10)  # article_count
        self.assertEqual(result[1], 70.0)  # positive_pct (7 out of 10)
        self.assertEqual(result[2], 30.0)  # negative_pct (3 out of 10)
        
        conn.close()
    
    def test_compute_search_interest_from_raw(self):
        """Test computing aggregated search interest from raw trends"""
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        test_date = today.strftime('%Y-%m-%d')
        
        # Insert raw trends for today and yesterday
        test_trends = [
            {
                'ts_utc': today,
                'keyword': 'bitcoin',
                'interest_score': 90.0,
                'geo': '',
                'timeframe': 'now 7-d'
            },
            {
                'ts_utc': yesterday,
                'keyword': 'bitcoin',
                'interest_score': 80.0,
                'geo': '',
                'timeframe': 'now 7-d'
            }
        ]
        
        self.db.insert_search_trends_raw(test_trends)
        
        # Compute aggregated interest
        self.db.compute_search_interest_from_raw(test_date)
        
        # Verify aggregated data was created
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT interest_score, interest_change_pct FROM search_interest_daily WHERE as_of_date = ? AND keyword = ?",
            (test_date, 'bitcoin')
        )
        result = cursor.fetchone()
        
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 90.0)  # interest_score
        self.assertAlmostEqual(result[1], 12.5, places=1)  # interest_change_pct ((90-80)/80*100)
        
        conn.close()
    
    def test_idempotent_raw_inserts(self):
        """Test that raw data inserts are idempotent"""
        test_post = {
            'id': 'unique_post',
            'platform': 'reddit',
            'subreddit': 'Bitcoin',
            'title': 'Test',
            'text': 'Content',
            'author': 'user',
            'created_utc': datetime.now(),
            'score': 10,
            'upvote_ratio': 0.8,
            'num_comments': 5,
            'url': 'https://reddit.com/test',
            'sentiment_compound': 0.5,
            'sentiment_pos': 0.6,
            'sentiment_neg': 0.2,
            'sentiment_neu': 0.2,
            'sentiment_label': 'POSITIVE'
        }
        
        # Insert twice
        self.db.insert_social_posts_raw([test_post])
        self.db.insert_social_posts_raw([test_post])
        
        # Verify only one record exists
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM social_posts_raw WHERE post_id = ?", ('unique_post',))
        result = cursor.fetchone()[0]
        self.assertEqual(result, 1)
        conn.close()
    
    def test_record_counts_include_raw_tables(self):
        """Test that get_record_counts includes raw data tables"""
        counts = self.db.get_record_counts()
        
        # Verify raw tables are included
        self.assertIn('social_posts_raw', counts)
        self.assertIn('news_articles_raw', counts)
        self.assertIn('search_trends_raw', counts)
        
        # All should be 0 initially
        self.assertEqual(counts['social_posts_raw'], 0)
        self.assertEqual(counts['news_articles_raw'], 0)
        self.assertEqual(counts['search_trends_raw'], 0)


if __name__ == '__main__':
    unittest.main()

