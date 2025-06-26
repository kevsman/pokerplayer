#!/usr/bin/env python3
"""
Quick test to verify GPU strategy lookup is working correctly.
"""
import sys

def test_strategy_lookup():
    print("🧪 QUICK STRATEGY LOOKUP TEST")
    print("=" * 40)
    
    try:
        from poker_bot_v2 import PokerBotV2
        
        print("🚀 Loading bot...")
        bot = PokerBotV2()
        
        print(f"📊 Loaded {len(bot.strategy_lookup.strategy_table):,} strategies")
        
        # Test a few different scenarios
        test_cases = [
            ("0", "10", "pot1.5", ['fold', 'call', 'raise']),
            ("0", "100", "pot2.0", ['fold', 'call', 'raise']),
            ("0", "1000", "pot0.8", ['fold', 'call', 'raise']),
        ]
        
        for i, (street, hand, board, actions) in enumerate(test_cases, 1):
            print(f"\n🎯 Test {i}: street={street}, hand={hand}, board={board}")
            
            strategy = bot.strategy_lookup.get_strategy(street, hand, board, actions)
            
            if strategy:
                print(f"  ✅ Strategy found!")
                print(f"     Fold: {strategy.get('fold', 0):.1%}")
                print(f"     Call: {strategy.get('call', 0):.1%}")
                print(f"     Raise: {strategy.get('raise', 0):.1%}")
                
                # Test action decision
                if strategy.get('raise', 0) > 0.5:
                    action = "RAISE"
                elif strategy.get('call', 0) > 0.4:
                    action = "CALL"
                else:
                    action = "FOLD"
                print(f"     → Recommended action: {action}")
            else:
                print(f"  ❌ No strategy found")
        
        print(f"\n✅ Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_strategy_lookup()
    sys.exit(0 if success else 1)
