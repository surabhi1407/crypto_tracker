"""Unit tests for sentiment analyzer utilities"""
import unittest
from src.utils.sentiment_analyzer import (
    analyze_vader_sentiment,
    classify_sentiment,
    aggregate_sentiment_scores,
    extract_keywords,
    calculate_engagement_score
)


class TestSentimentAnalyzer(unittest.TestCase):
    """Test sentiment analysis utilities"""
    
    def test_vader_positive_sentiment(self):
        """Test VADER with positive text"""
        text = "Bitcoin is amazing! Great gains today!"
        result = analyze_vader_sentiment(text)
        
        self.assertIn('compound', result)
        self.assertGreater(result['compound'], 0)
        self.assertGreater(result['pos'], 0)
    
    def test_vader_negative_sentiment(self):
        """Test VADER with negative text"""
        text = "Terrible crash! Lost everything. Very bad."
        result = analyze_vader_sentiment(text)
        
        self.assertIn('compound', result)
        self.assertLess(result['compound'], 0)
        self.assertGreater(result['neg'], 0)
    
    def test_vader_neutral_sentiment(self):
        """Test VADER with neutral text"""
        text = "Bitcoin price is at 50000 dollars."
        result = analyze_vader_sentiment(text)
        
        self.assertIn('compound', result)
        self.assertGreater(result['neu'], 0.5)
    
    def test_vader_empty_text(self):
        """Test VADER with empty text"""
        result = analyze_vader_sentiment("")
        
        self.assertEqual(result['compound'], 0.0)
        self.assertEqual(result['neu'], 1.0)
    
    def test_classify_sentiment_positive(self):
        """Test sentiment classification - positive"""
        self.assertEqual(classify_sentiment(0.5), 'POSITIVE')
        self.assertEqual(classify_sentiment(0.05), 'POSITIVE')
    
    def test_classify_sentiment_negative(self):
        """Test sentiment classification - negative"""
        self.assertEqual(classify_sentiment(-0.5), 'NEGATIVE')
        self.assertEqual(classify_sentiment(-0.05), 'NEGATIVE')
    
    def test_classify_sentiment_neutral(self):
        """Test sentiment classification - neutral"""
        self.assertEqual(classify_sentiment(0.0), 'NEUTRAL')
        self.assertEqual(classify_sentiment(0.04), 'NEUTRAL')
        self.assertEqual(classify_sentiment(-0.04), 'NEUTRAL')
    
    def test_aggregate_sentiment_scores(self):
        """Test sentiment score aggregation"""
        scores = [0.5, -0.3, 0.1, 0.8, -0.1]
        result = aggregate_sentiment_scores(scores)
        
        self.assertIn('avg', result)
        self.assertIn('median', result)
        self.assertIn('positive_pct', result)
        self.assertIn('negative_pct', result)
        self.assertIn('neutral_pct', result)
        
        # Check percentages sum to 100
        total_pct = result['positive_pct'] + result['negative_pct'] + result['neutral_pct']
        self.assertAlmostEqual(total_pct, 100.0, places=1)
    
    def test_aggregate_empty_scores(self):
        """Test aggregation with empty scores"""
        result = aggregate_sentiment_scores([])
        
        self.assertEqual(result['avg'], 0.0)
        self.assertEqual(result['positive_pct'], 0.0)
    
    def test_extract_keywords(self):
        """Test keyword extraction"""
        texts = [
            "Bitcoin price surges to new highs",
            "Ethereum network upgrade successful",
            "Cryptocurrency market shows strong momentum"
        ]
        keywords = extract_keywords(texts, top_n=5)
        
        self.assertIsInstance(keywords, list)
        self.assertLessEqual(len(keywords), 5)
        self.assertIn('bitcoin', keywords)
    
    def test_extract_keywords_empty(self):
        """Test keyword extraction with empty input"""
        keywords = extract_keywords([], top_n=5)
        
        self.assertIsInstance(keywords, list)
        self.assertEqual(len(keywords), 0)
    
    def test_calculate_engagement_score(self):
        """Test engagement score calculation"""
        score = calculate_engagement_score(
            upvotes=100,
            comments=20,
            shares=5,
            views=1000
        )
        
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
    
    def test_calculate_engagement_zero_views(self):
        """Test engagement with zero views"""
        score = calculate_engagement_score(
            upvotes=10,
            comments=5,
            shares=2,
            views=0
        )
        
        # Should handle division by zero gracefully
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0)


if __name__ == '__main__':
    unittest.main()

