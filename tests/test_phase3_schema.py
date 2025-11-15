"""Unit tests for Phase 3 database schema"""
import unittest
import sqlite3
import tempfile
import os
from src.storage.schema import DatabaseSchema
from src.storage.database import MarketDatabase


class TestPhase3Schema(unittest.TestCase):
    """Test Phase 3 schema creation and operations"""
    
    def setUp(self):
        """Create temporary database for testing"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        self.schema = DatabaseSchema(self.db_path)
        self.schema.initialize_database()
        self.db = MarketDatabase(self.db_path)
    
    def tearDown(self):
        """Clean up temporary database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_schema_version(self):
        """Test schema version is updated to 4"""
        self.assertEqual(self.schema.SCHEMA_VERSION, 4)
    
    def test_social_sentiment_table_exists(self):
        """Test social_sentiment_daily table creation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='social_sentiment_daily'"
        )
        result = cursor.fetchone()
        
        self.assertIsNotNone(result)
        conn.close()
    
    def test_news_sentiment_table_exists(self):
        """Test news_sentiment_daily table creation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='news_sentiment_daily'"
        )
        result = cursor.fetchone()
        
        self.assertIsNotNone(result)
        conn.close()
    
    def test_search_interest_table_exists(self):
        """Test search_interest_daily table creation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='search_interest_daily'"
        )
        result = cursor.fetchone()
        
        self.assertIsNotNone(result)
        conn.close()
    
    def test_insert_social_sentiment(self):
        """Test inserting social sentiment data"""
        records = [
            {
                'as_of_date': '2025-01-01',
                'platform': 'reddit_cryptocurrency',
                'mentions_count': 100,
                'sentiment_score': 0.5,
                'positive_mentions': 60,
                'negative_mentions': 20,
                'neutral_mentions': 20,
                'engagement_score': 75.5,
                'top_keywords': 'bitcoin,ethereum,bullish',
                'source': 'REDDIT'
            }
        ]
        
        count = self.db.insert_social_sentiment(records)
        self.assertEqual(count, 1)
        
        # Verify data
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM social_sentiment_daily")
        result = cursor.fetchone()[0]
        self.assertEqual(result, 1)
        conn.close()
    
    def test_insert_news_sentiment(self):
        """Test inserting news sentiment data"""
        records = [
            {
                'as_of_date': '2025-01-01',
                'article_count': 50,
                'avg_sentiment': 0.3,
                'positive_pct': 60.0,
                'negative_pct': 20.0,
                'neutral_pct': 20.0,
                'top_sources': 'CoinDesk,Bloomberg,Reuters',
                'top_keywords': 'bitcoin,rally,price',
                'source': 'NEWSAPI'
            }
        ]
        
        count = self.db.insert_news_sentiment(records)
        self.assertEqual(count, 1)
        
        # Verify data
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM news_sentiment_daily")
        result = cursor.fetchone()[0]
        self.assertEqual(result, 1)
        conn.close()
    
    def test_insert_search_interest(self):
        """Test inserting search interest data"""
        records = [
            {
                'as_of_date': '2025-01-01',
                'keyword': 'bitcoin',
                'interest_score': 85.0,
                'interest_change_pct': 5.2,
                'related_queries': 'btc,bitcoin price,buy bitcoin',
                'source': 'GOOGLE_TRENDS'
            }
        ]
        
        count = self.db.insert_search_interest(records)
        self.assertEqual(count, 1)
        
        # Verify data
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM search_interest_daily")
        result = cursor.fetchone()[0]
        self.assertEqual(result, 1)
        conn.close()
    
    def test_idempotent_inserts(self):
        """Test that duplicate inserts are idempotent"""
        records = [
            {
                'as_of_date': '2025-01-01',
                'platform': 'reddit_bitcoin',
                'mentions_count': 100,
                'sentiment_score': 0.5,
                'source': 'REDDIT'
            }
        ]
        
        # Insert twice
        count1 = self.db.insert_social_sentiment(records)
        count2 = self.db.insert_social_sentiment(records)
        
        # Should still have only 1 record
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM social_sentiment_daily")
        result = cursor.fetchone()[0]
        self.assertEqual(result, 1)
        conn.close()
    
    def test_phase3_indexes_created(self):
        """Test that Phase 3 indexes are created"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )
        indexes = [row[0] for row in cursor.fetchall()]
        
        # Check for Phase 3 indexes
        self.assertIn('idx_social_date', indexes)
        self.assertIn('idx_social_platform', indexes)
        self.assertIn('idx_news_date', indexes)
        self.assertIn('idx_search_date', indexes)
        self.assertIn('idx_search_keyword', indexes)
        
        conn.close()


if __name__ == '__main__':
    unittest.main()

