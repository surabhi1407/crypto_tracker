"""Example script demonstrating raw data queries and reprocessing"""
import sqlite3
from datetime import datetime, timedelta

# Connect to database
DB_PATH = 'data/market_intel.db'
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=" * 60)
print("PHASE 3 RAW DATA QUERY EXAMPLES")
print("=" * 60)

# Example 1: Query raw social posts
print("\n1. Top 5 Most Positive Reddit Posts (Last 7 Days)")
print("-" * 60)
cursor.execute("""
    SELECT 
        DATE(created_utc) as date,
        subreddit,
        title,
        sentiment_compound,
        score,
        num_comments
    FROM social_posts_raw
    WHERE created_utc >= datetime('now', '-7 days')
      AND sentiment_compound > 0.5
    ORDER BY sentiment_compound DESC, score DESC
    LIMIT 5
""")

for row in cursor.fetchall():
    print(f"Date: {row[0]}")
    print(f"  Subreddit: r/{row[1]}")
    print(f"  Title: {row[2][:60]}...")
    print(f"  Sentiment: {row[3]:.3f} | Score: {row[4]} | Comments: {row[5]}")
    print()

# Example 2: Query raw news articles
print("\n2. Recent News Articles by Sentiment")
print("-" * 60)
cursor.execute("""
    SELECT 
        DATE(published_at) as date,
        source,
        title,
        sentiment_label,
        sentiment_confidence
    FROM news_articles_raw
    WHERE published_at >= datetime('now', '-7 days')
    ORDER BY published_at DESC
    LIMIT 5
""")

for row in cursor.fetchall():
    print(f"Date: {row[0]} | Source: {row[1]}")
    print(f"  Title: {row[2][:60]}...")
    print(f"  Sentiment: {row[3]} (confidence: {row[4]:.2f})")
    print()

# Example 3: Query raw search trends
print("\n3. Search Interest Trends (Last 7 Days)")
print("-" * 60)
cursor.execute("""
    SELECT 
        DATE(ts_utc) as date,
        keyword,
        AVG(interest_score) as avg_interest
    FROM search_trends_raw
    WHERE ts_utc >= datetime('now', '-7 days')
    GROUP BY DATE(ts_utc), keyword
    ORDER BY date DESC, avg_interest DESC
""")

for row in cursor.fetchall():
    print(f"{row[0]} | {row[1]}: {row[2]:.1f}")

# Example 4: Sentiment distribution by subreddit
print("\n4. Sentiment Distribution by Subreddit")
print("-" * 60)
cursor.execute("""
    SELECT 
        subreddit,
        COUNT(*) as total_posts,
        AVG(sentiment_compound) as avg_sentiment,
        SUM(CASE WHEN sentiment_label = 'POSITIVE' THEN 1 ELSE 0 END) as positive,
        SUM(CASE WHEN sentiment_label = 'NEGATIVE' THEN 1 ELSE 0 END) as negative,
        SUM(CASE WHEN sentiment_label = 'NEUTRAL' THEN 1 ELSE 0 END) as neutral
    FROM social_posts_raw
    WHERE created_utc >= datetime('now', '-7 days')
    GROUP BY subreddit
    ORDER BY total_posts DESC
""")

for row in cursor.fetchall():
    print(f"\nr/{row[0]}")
    print(f"  Total Posts: {row[1]}")
    print(f"  Avg Sentiment: {row[2]:.3f}")
    print(f"  Distribution: {row[3]} positive, {row[4]} negative, {row[5]} neutral")

# Example 5: Compare raw vs aggregated data
print("\n5. Raw vs Aggregated Comparison (Today)")
print("-" * 60)
today = datetime.now().strftime('%Y-%m-%d')

# Raw data
cursor.execute("""
    SELECT 
        COUNT(*) as posts,
        AVG(sentiment_compound) as avg_sentiment
    FROM social_posts_raw
    WHERE DATE(created_utc) = ?
""", (today,))
raw_data = cursor.fetchone()

# Aggregated data
cursor.execute("""
    SELECT 
        SUM(mentions_count) as posts,
        AVG(sentiment_score) as avg_sentiment
    FROM social_sentiment_daily
    WHERE as_of_date = ?
""", (today,))
agg_data = cursor.fetchone()

if raw_data[0] and agg_data[0]:
    print(f"Raw Data: {raw_data[0]} posts, avg sentiment: {raw_data[1]:.3f}")
    print(f"Aggregated: {agg_data[0]} posts, avg sentiment: {agg_data[1]:.3f}")
    print(f"Match: {'✅ Yes' if abs(raw_data[0] - agg_data[0]) < 2 else '❌ No'}")
else:
    print("No data available for today yet")

# Example 6: Record counts
print("\n6. Database Statistics")
print("-" * 60)
cursor.execute("SELECT COUNT(*) FROM social_posts_raw")
social_raw = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM news_articles_raw")
news_raw = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM search_trends_raw")
trends_raw = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM social_sentiment_daily")
social_agg = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM news_sentiment_daily")
news_agg = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM search_interest_daily")
trends_agg = cursor.fetchone()[0]

print(f"Social:  {social_raw:,} raw posts → {social_agg} daily aggregates")
print(f"News:    {news_raw:,} raw articles → {news_agg} daily aggregates")
print(f"Trends:  {trends_raw:,} raw points → {trends_agg} daily aggregates")

conn.close()

print("\n" + "=" * 60)
print("✅ Query examples completed!")
print("=" * 60)


