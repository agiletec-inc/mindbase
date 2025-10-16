#!/usr/bin/env python3
"""
Test script for MindBase collectors
Tests all collectors and displays collection statistics
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add collectors directory to path
collectors_path = Path(__file__).parent.parent / "collectors"
sys.path.insert(0, str(collectors_path))

from cursor_collector import CursorCollector
from windsurf_collector import WindsurfCollector
from claude_collector import ClaudeDesktopCollector
from chatgpt_collector import ChatGPTCollector

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_collector(collector_class, name: str):
    """Test a single collector"""
    print(f"\n{'='*60}")
    print(f"Testing {name} Collector")
    print(f"{'='*60}")

    try:
        # Initialize collector
        collector = collector_class()
        logger.info(f"Initialized {name} collector")

        # Get data paths
        data_paths = collector.get_data_paths()
        print(f"\n📁 Data Paths Found: {len(data_paths)}")
        for path in data_paths[:5]:  # Show first 5 paths
            print(f"   - {path}")
        if len(data_paths) > 5:
            print(f"   ... and {len(data_paths) - 5} more")

        # Collect conversations
        print(f"\n🔍 Collecting conversations...")
        conversations = collector.collect()

        # Display statistics
        print(f"\n📊 Collection Statistics:")
        print(f"   Total Conversations: {len(conversations)}")

        if conversations:
            # Time range
            timestamps = [conv.created_at for conv in conversations if conv.created_at]
            if timestamps:
                oldest = min(timestamps)
                newest = max(timestamps)
                print(f"   Time Range: {oldest.date()} to {newest.date()}")

            # Sample conversations
            print(f"\n📝 Sample Conversations (first 3):")
            for i, conv in enumerate(conversations[:3], 1):
                print(f"\n   {i}. {conv.title[:80]}...")
                print(f"      Source: {conv.source}")
                print(f"      Created: {conv.created_at}")
                print(f"      Messages: {len(conv.messages)}")
                if conv.project:
                    print(f"      Project: {conv.project}")

            # Message statistics
            total_messages = sum(len(conv.messages) for conv in conversations)
            avg_messages = total_messages / len(conversations) if conversations else 0
            print(f"\n   Total Messages: {total_messages}")
            print(f"   Average Messages per Conversation: {avg_messages:.1f}")

            # Role distribution
            user_messages = sum(
                len([m for m in conv.messages if m.role == 'user'])
                for conv in conversations
            )
            assistant_messages = sum(
                len([m for m in conv.messages if m.role == 'assistant'])
                for conv in conversations
            )
            print(f"   User Messages: {user_messages}")
            print(f"   Assistant Messages: {assistant_messages}")

        else:
            print("   ⚠️  No conversations found")
            print("   This might be normal if:")
            print("   - The application hasn't been used recently")
            print("   - Data is stored in a different location")
            print("   - The application is not installed")

        return len(conversations)

    except Exception as e:
        print(f"\n❌ Error testing {name} collector:")
        print(f"   {str(e)}")
        logger.exception(f"Error in {name} collector")
        return 0


def main():
    """Main test function"""
    print("="*60)
    print("MindBase Collectors Test Suite")
    print("="*60)
    print(f"Test Time: {datetime.now()}")

    # Test all collectors
    collectors = [
        (CursorCollector, "Cursor"),
        (WindsurfCollector, "Windsurf"),
        (ClaudeDesktopCollector, "Claude Desktop"),
        (ChatGPTCollector, "ChatGPT"),
    ]

    results = {}
    for collector_class, name in collectors:
        count = test_collector(collector_class, name)
        results[name] = count

    # Summary
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    total = sum(results.values())
    print(f"\nTotal Conversations Collected: {total}")
    print("\nBy Source:")
    for name, count in results.items():
        status = "✅" if count > 0 else "⚠️ "
        print(f"   {status} {name}: {count}")

    # Data availability assessment
    print(f"\n{'='*60}")
    print("Assessment")
    print(f"{'='*60}")

    if total == 0:
        print("\n⚠️  No conversations found from any source.")
        print("\nPossible reasons:")
        print("1. Applications not installed")
        print("2. No conversation history yet")
        print("3. Data stored in different locations")
        print("\nNext steps:")
        print("- Verify application installations")
        print("- Use applications and create conversation history")
        print("- Check data paths in collectors")
    elif total < 10:
        print("\n✅ Some data found, but limited.")
        print("\nRecommendations:")
        print("- Continue using AI applications to build history")
        print("- Verify all expected applications are installed")
    else:
        print("\n✅ Good data availability!")
        print(f"\nYou have {total} conversations ready for:")
        print("- Semantic search")
        print("- Time-series analysis")
        print("- Knowledge extraction")

    print(f"\n{'='*60}")


if __name__ == "__main__":
    main()
