"""Sentiment analysis utilities for text classification"""
from typing import Dict, List, Optional
from collections import Counter
import re
from src.utils.logger import setup_logger

logger = setup_logger()

# Lazy load heavy dependencies
_vader_analyzer = None
_finbert_tokenizer = None
_finbert_model = None


def get_vader_analyzer():
    """Lazy load VADER sentiment analyzer"""
    global _vader_analyzer
    if _vader_analyzer is None:
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            _vader_analyzer = SentimentIntensityAnalyzer()
            logger.info("VADER sentiment analyzer loaded")
        except ImportError as e:
            logger.error(f"Failed to import VADER: {e}")
            raise
    return _vader_analyzer


def get_finbert_model():
    """Lazy load FinBERT model and tokenizer"""
    global _finbert_tokenizer, _finbert_model
    if _finbert_tokenizer is None or _finbert_model is None:
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch
            
            model_name = "ProsusAI/finbert"
            _finbert_tokenizer = AutoTokenizer.from_pretrained(model_name)
            _finbert_model = AutoModelForSequenceClassification.from_pretrained(model_name)
            _finbert_model.eval()
            
            logger.info("FinBERT model loaded successfully")
        except ImportError as e:
            logger.error(f"Failed to import transformers: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load FinBERT model: {e}")
            raise
    
    return _finbert_tokenizer, _finbert_model


def analyze_vader_sentiment(text: str) -> Dict[str, float]:
    """
    Analyze sentiment using VADER (good for social media text)
    
    Args:
        text: Text to analyze
    
    Returns:
        Dictionary with sentiment scores:
        - compound: Overall sentiment (-1 to +1)
        - pos: Positive score (0 to 1)
        - neu: Neutral score (0 to 1)
        - neg: Negative score (0 to 1)
    """
    if not text or not text.strip():
        return {'compound': 0.0, 'pos': 0.0, 'neu': 1.0, 'neg': 0.0}
    
    try:
        analyzer = get_vader_analyzer()
        scores = analyzer.polarity_scores(text)
        return scores
    except Exception as e:
        logger.error(f"VADER sentiment analysis failed: {e}")
        return {'compound': 0.0, 'pos': 0.0, 'neu': 1.0, 'neg': 0.0}


def analyze_finbert_sentiment(text: str) -> Dict[str, float]:
    """
    Analyze sentiment using FinBERT (good for financial news)
    
    Args:
        text: Text to analyze (max 512 tokens)
    
    Returns:
        Dictionary with sentiment scores:
        - label: 'positive', 'negative', or 'neutral'
        - score: Confidence score (0 to 1)
        - compound: Normalized score (-1 to +1)
    """
    if not text or not text.strip():
        return {'label': 'neutral', 'score': 1.0, 'compound': 0.0}
    
    try:
        import torch
        tokenizer, model = get_finbert_model()
        
        # Tokenize and truncate to max length
        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        )
        
        # Get predictions
        with torch.no_grad():
            outputs = model(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
        
        # Map to labels (FinBERT: 0=positive, 1=negative, 2=neutral)
        labels = ['positive', 'negative', 'neutral']
        scores = predictions[0].tolist()
        
        max_idx = scores.index(max(scores))
        label = labels[max_idx]
        confidence = scores[max_idx]
        
        # Convert to compound score (-1 to +1)
        # positive=1, neutral=0, negative=-1, weighted by confidence
        if label == 'positive':
            compound = confidence
        elif label == 'negative':
            compound = -confidence
        else:
            compound = 0.0
        
        return {
            'label': label,
            'score': confidence,
            'compound': compound,
            'positive_prob': scores[0],
            'negative_prob': scores[1],
            'neutral_prob': scores[2]
        }
        
    except Exception as e:
        logger.error(f"FinBERT sentiment analysis failed: {e}")
        return {'label': 'neutral', 'score': 1.0, 'compound': 0.0}


def classify_sentiment(compound_score: float) -> str:
    """
    Classify sentiment based on compound score
    
    Args:
        compound_score: Compound sentiment score (-1 to +1)
    
    Returns:
        Classification: 'POSITIVE', 'NEGATIVE', or 'NEUTRAL'
    """
    if compound_score >= 0.05:
        return 'POSITIVE'
    elif compound_score <= -0.05:
        return 'NEGATIVE'
    else:
        return 'NEUTRAL'


def aggregate_sentiment_scores(scores: List[float]) -> Dict[str, float]:
    """
    Aggregate multiple sentiment scores
    
    Args:
        scores: List of compound sentiment scores (-1 to +1)
    
    Returns:
        Dictionary with aggregated statistics
    """
    if not scores:
        return {
            'avg': 0.0,
            'median': 0.0,
            'min': 0.0,
            'max': 0.0,
            'positive_pct': 0.0,
            'negative_pct': 0.0,
            'neutral_pct': 0.0
        }
    
    scores_sorted = sorted(scores)
    n = len(scores)
    
    # Calculate percentages
    positive = sum(1 for s in scores if s >= 0.05)
    negative = sum(1 for s in scores if s <= -0.05)
    neutral = n - positive - negative
    
    return {
        'avg': sum(scores) / n,
        'median': scores_sorted[n // 2] if n % 2 == 1 else (scores_sorted[n // 2 - 1] + scores_sorted[n // 2]) / 2,
        'min': min(scores),
        'max': max(scores),
        'positive_pct': (positive / n) * 100,
        'negative_pct': (negative / n) * 100,
        'neutral_pct': (neutral / n) * 100
    }


def extract_keywords(texts: List[str], top_n: int = 10) -> List[str]:
    """
    Extract top keywords from a list of texts
    
    Args:
        texts: List of text strings
        top_n: Number of top keywords to return
    
    Returns:
        List of top keywords
    """
    # Combine all texts
    combined = ' '.join(texts).lower()
    
    # Remove URLs, mentions, hashtags
    combined = re.sub(r'http\S+|www\S+|https\S+', '', combined)
    combined = re.sub(r'@\w+', '', combined)
    combined = re.sub(r'#\w+', '', combined)
    
    # Extract words (alphanumeric only, length > 3)
    words = re.findall(r'\b[a-z]{4,}\b', combined)
    
    # Common stop words to exclude
    stop_words = {
        'that', 'this', 'with', 'from', 'have', 'been', 'will',
        'your', 'more', 'about', 'what', 'when', 'there', 'their',
        'which', 'they', 'would', 'could', 'should', 'just', 'like',
        'than', 'into', 'very', 'also', 'some', 'other', 'only'
    }
    
    # Filter and count
    filtered = [w for w in words if w not in stop_words]
    counter = Counter(filtered)
    
    return [word for word, _ in counter.most_common(top_n)]


def calculate_engagement_score(
    upvotes: int = 0,
    comments: int = 0,
    shares: int = 0,
    views: int = 1
) -> float:
    """
    Calculate engagement score for social media content
    
    Args:
        upvotes: Number of upvotes/likes
        comments: Number of comments
        shares: Number of shares/retweets
        views: Number of views (default 1 to avoid division by zero)
    
    Returns:
        Engagement score (0 to 100+)
    """
    if views == 0:
        views = 1
    
    # Weighted engagement rate
    engagement = (upvotes * 1.0 + comments * 2.0 + shares * 3.0) / views
    
    # Normalize to 0-100 scale (log scale for better distribution)
    import math
    score = min(100, math.log1p(engagement * 1000) * 10)
    
    return float(round(score, 2))

