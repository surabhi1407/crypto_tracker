#!/usr/bin/env python3
"""
Quick test script to verify the ingestion pipeline setup

This script performs basic validation without making API calls.
"""

import sys
from pathlib import Path

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        from src.connectors.base import BaseConnector
        from src.connectors.coingecko import CoinGeckoConnector
        from src.connectors.fear_greed import FearGreedConnector
        from src.connectors.etf_flows import ETFFlowsConnector
        from src.storage.schema import DatabaseSchema
        from src.storage.database import MarketDatabase
        from src.utils.logger import setup_logger
        from src.utils.time_utils import get_utc_now
        from src.utils.csv_backup import CSVBackup
        from src.utils.config import Config
        from src.ingestion_pipeline import IngestionPipeline
        
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_config():
    """Test configuration loading"""
    print("\nTesting configuration...")
    
    try:
        from src.utils.config import Config
        
        Config.validate()
        config = Config.display()
        
        print("✅ Configuration loaded:")
        for key, value in config.items():
            print(f"   • {key}: {value}")
        
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def test_database_schema():
    """Test database schema creation"""
    print("\nTesting database schema...")
    
    try:
        from src.storage.schema import DatabaseSchema
        import tempfile
        
        # Use temporary database for testing
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            tmp_db = tmp.name
        
        schema = DatabaseSchema(tmp_db)
        schema.initialize_database()
        
        if schema.verify_schema():
            print("✅ Database schema created and verified")
            
            # Cleanup
            Path(tmp_db).unlink()
            return True
        else:
            print("❌ Schema verification failed")
            return False
            
    except Exception as e:
        print(f"❌ Database schema test failed: {e}")
        return False


def test_logger():
    """Test logger setup"""
    print("\nTesting logger...")
    
    try:
        from src.utils.logger import setup_logger
        
        logger = setup_logger("test_logger")
        logger.info("Test log message")
        
        print("✅ Logger initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Logger test failed: {e}")
        return False


def test_time_utils():
    """Test time utilities"""
    print("\nTesting time utilities...")
    
    try:
        from src.utils.time_utils import (
            get_utc_now, 
            get_date_string, 
            classify_trading_session
        )
        
        now = get_utc_now()
        date_str = get_date_string()
        session = classify_trading_session(now.hour)
        
        print(f"✅ Time utils working:")
        print(f"   • Current UTC: {now}")
        print(f"   • Date string: {date_str}")
        print(f"   • Trading session: {session}")
        
        return True
    except Exception as e:
        print(f"❌ Time utils test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 70)
    print("🧪 CRYPTO MARKET INTELLIGENCE - PIPELINE VALIDATION")
    print("=" * 70)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Database Schema", test_database_schema),
        ("Logger", test_logger),
        ("Time Utilities", test_time_utils),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            results.append(test_func())
        except Exception as e:
            print(f"❌ {name} test crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    for i, (name, _) in enumerate(tests):
        status = "✅ PASS" if results[i] else "❌ FAIL"
        print(f"{status} - {name}")
    
    print("=" * 70)
    print(f"Result: {passed}/{total} tests passed")
    print("=" * 70)
    
    if passed == total:
        print("\n🎉 All tests passed! Ready to run: python main.py")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

