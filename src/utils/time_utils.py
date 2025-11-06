"""Time and timezone utilities"""
from datetime import datetime, timezone
import pytz


def get_utc_now() -> datetime:
    """Get current UTC datetime"""
    return datetime.now(timezone.utc)


def timestamp_to_utc(ts_ms: int) -> datetime:
    """
    Convert millisecond timestamp to UTC datetime
    
    Args:
        ts_ms: Timestamp in milliseconds
    
    Returns:
        UTC datetime object
    """
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)


def get_date_string(dt: datetime = None) -> str:
    """
    Get date string in YYYY-MM-DD format
    
    Args:
        dt: Datetime object (defaults to current UTC time)
    
    Returns:
        Date string
    """
    if dt is None:
        dt = get_utc_now()
    return dt.strftime('%Y-%m-%d')


def classify_trading_session(hour_utc: int) -> str:
    """
    Classify trading session based on UTC hour
    
    Args:
        hour_utc: Hour in UTC (0-23)
    
    Returns:
        Session name: ASIA, EUROPE, or US
    """
    if 0 <= hour_utc < 8:
        return "ASIA"
    elif 8 <= hour_utc < 16:
        return "EUROPE"
    else:
        return "US"

