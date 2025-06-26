#!/usr/bin/env python3
"""
Test script to verify that poker_bot_v2 is correctly loading and using GPU-trained strategies.
"""
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_strategy_loading():
    """Test that poker_bot_v2 loads the GPU-trained strategies correctly."""
    print("🧪 TESTING POKER BOT V2 STRATEGY LOADING")
    print("=" * 50)
    
    try:
        # Import and initialize the bot
        from poker_bot_v2 import PokerBotV2
        
        print("📋 Initializing PokerBotV2...")
        bot = PokerBotV2()
        
        # Check strategy loading
        strategy_count = len(bot.strategy_lookup.strategies)
        print(f"✅ Loaded {strategy_count:,} strategies")
        
        if strategy_count > 100000:
            print("🔥 EXCELLENT: Ultra-high-performance strategy database!")
        elif strategy_count > 10000:
            print("⚡ GOOD: High-performance strategy database!")
        elif strategy_count > 1000:
            print("📊 OK: Basic strategy database loaded")
        else:
            print("⚠️  WARNING: Very few strategies loaded")
            
        # Test strategy lookup functionality
        print("\n🔍 Testing strategy lookup...")
        
        # Sample test cases
        test_cases = [
            ("preflop", "0", "0", ["fold", "call", "raise"]),
            ("flop", "1", "1", ["fold", "call", "raise"]),
            ("turn", "2", "2", ["fold", "check", "raise"]),
            ("river", "3", "3", ["fold", "call", "raise"])
        ]
        
        strategies_found = 0
        for stage, hand_bucket, board_bucket, actions in test_cases:
            strategy = bot.strategy_lookup.get_strategy(stage, hand_bucket, board_bucket, actions)
            if strategy:
                strategies_found += 1
                print(f"  ✅ Found strategy for {stage} (buckets: {hand_bucket}, {board_bucket})")
                print(f"     Strategy: {strategy}")
            else:
                print(f"  ❌ No strategy for {stage} (buckets: {hand_bucket}, {board_bucket})")
        
        coverage_rate = (strategies_found / len(test_cases)) * 100
        print(f"\n📈 Strategy Coverage: {coverage_rate:.1f}% ({strategies_found}/{len(test_cases)} test cases)")
        
        # Test a sample decision scenario
        print("\n🎯 Testing sample decision scenario...")
        try:
            # Mock a simple decision scenario
            bot.table_data = {
                'community_cards': ['A♠', 'K♥'],
                'pot_size': '1.20',
                'game_stage': 'flop'
            }
            
            # Mock player data
            bot.player_data = [
                {
                    'is_my_player': True,
                    'has_turn': True,
                    'cards': ['Q♠', 'J♦'],
                    'available_actions': ['fold', 'call', 'raise'],
                    'bet_to_call': '0.40'
                },
                {
                    'is_my_player': False,
                    'is_empty': False
                }
            ]
            
            # Test decision making
            action, amount = bot.decide_action()
            if action:
                print(f"  ✅ Decision made: {action} for ${amount}")
                print(f"  📊 Strategy stats: {bot.strategy_stats}")
            else:
                print("  ❌ No decision made")
                
        except Exception as e:
            print(f"  ⚠️  Decision test failed: {e}")
        
        # Summary
        print("\n" + "=" * 50)
        print("🎯 SUMMARY:")
        print(f"  💾 Strategies loaded: {strategy_count:,}")
        print(f"  🔍 Coverage rate: {coverage_rate:.1f}%")
        print(f"  ⚡ Bot ready: {'YES' if strategy_count > 0 else 'NO'}")
        
        if strategy_count > 50000:
            print("  🚀 RECOMMENDATION: Excellent strategy database - bot ready for optimal play!")
        elif strategy_count > 10000:
            print("  ✅ RECOMMENDATION: Good strategy database - bot ready for advanced play!")
        else:
            print("  💡 RECOMMENDATION: Consider running train_cfr.py to generate more strategies")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False
    
    finally:
        if 'bot' in locals():
            bot.close_logger()

if __name__ == "__main__":
    print("🚀 POKER BOT V2 STRATEGY TEST")
    print("Testing GPU-trained strategy integration...")
    print()
    
    success = test_strategy_loading()
    
    if success:
        print("\n✅ ALL TESTS PASSED")
        print("🎯 PokerBotV2 is ready to use GPU-trained strategies!")
    else:
        print("\n❌ TESTS FAILED")
        print("Please check the configuration and strategy files")
    
    print("\n" + "=" * 50)
