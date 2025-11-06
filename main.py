#!/usr/bin/env python3
"""
Crypto Market Intelligence Dashboard - Data Ingestion Entry Point

This script runs the Phase 1 data ingestion pipeline that:
1. Fetches OHLC data from CoinGecko (BTC & ETH)
2. Fetches Fear & Greed Index from Alternative.me
3. Fetches ETF flow data (currently mock data)
4. Computes daily market snapshots
5. Stores everything in SQLite with optional CSV backups

Usage:
    python main.py              # Run full ingestion
    python main.py --status     # Show database status
    python main.py --help       # Show help
"""

import sys
import argparse
from src.ingestion_pipeline import IngestionPipeline
from src.utils.logger import setup_logger

logger = setup_logger()


def run_ingestion(backfill=False):
    """
    Run the full ingestion pipeline
    
    Args:
        backfill: If True, fetch full historical data (300 days ETF, 30 days sentiment)
                  If False, fetch recent data only (7 days ETF, 7 days sentiment)
    """
    mode = "BACKFILL" if backfill else "DAILY SYNC"
    logger.info(f"Starting ingestion via main.py - Mode: {mode}")
    pipeline = IngestionPipeline()
    
    if backfill:
        logger.info("Running BACKFILL mode - fetching full historical data")
        results = pipeline.run_full_ingestion(etf_days=300, sentiment_days=30)
    else:
        logger.info("Running DAILY SYNC mode - fetching recent data only")
        results = pipeline.run_full_ingestion(etf_days=7, sentiment_days=7)
    
    # Print summary to console
    print("\n" + "=" * 70)
    print("📊 CRYPTO MARKET INTELLIGENCE - INGESTION SUMMARY")
    print("=" * 70)
    print(f"✅ Overall Success: {results['overall_success']}")
    print(f"⏱️  Duration: {results['duration_seconds']:.2f} seconds")
    
    print(f"\n📈 Data Ingested:")
    print(f"   • OHLC Records: {results['ohlc']['records']} "
          f"({'✅' if results['ohlc']['success'] else '❌'})")
    print(f"   • Sentiment Records: {results['sentiment']['records']} "
          f"({'✅' if results['sentiment']['success'] else '❌'})")
    print(f"   • ETF Flow Records: {results['etf_flows']['records']} "
          f"({'✅' if results['etf_flows']['success'] else '❌'})")
    print(f"   • Daily Snapshots: {results['snapshots']['snapshots']} "
          f"({'✅' if results['snapshots']['success'] else '❌'})")
    
    print(f"\n💾 Database Record Counts:")
    for table, count in results['record_counts'].items():
        print(f"   • {table}: {count:,}")
    
    if results.get('backups_cleaned', 0) > 0:
        print(f"\n🧹 Cleaned up {results['backups_cleaned']} old backup files")
    
    print("=" * 70)
    
    return 0 if results['overall_success'] else 1


def show_status():
    """Show current database status"""
    pipeline = IngestionPipeline()
    status = pipeline.get_status()
    
    print("\n" + "=" * 70)
    print("📊 CRYPTO MARKET INTELLIGENCE - DATABASE STATUS")
    print("=" * 70)
    
    print("\n💾 Record Counts:")
    for table, count in status['record_counts'].items():
        print(f"   • {table}: {count:,}")
    
    print("\n⚙️  Configuration:")
    for key, value in status['config'].items():
        print(f"   • {key}: {value}")
    
    print("=" * 70)
    
    return 0


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description="Crypto Market Intelligence Dashboard - Data Ingestion Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py              Run full ingestion pipeline
  python main.py --status     Show database status
  
For more information, see AGENTS.md
        """
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show database status instead of running ingestion'
    )
    
    parser.add_argument(
        '--backfill',
        action='store_true',
        help='Run initial backfill (300 days ETF, 30 days sentiment). Use this for first run only.'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Crypto Market Intelligence Dashboard v0.1.0 (Phase 1)'
    )
    
    args = parser.parse_args()
    
    try:
        if args.status:
            return show_status()
        else:
            return run_ingestion(backfill=args.backfill)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Ingestion interrupted by user")
        logger.warning("Ingestion interrupted by user")
        return 130
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error(f"Main execution failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

