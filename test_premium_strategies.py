#!/usr/bin/env python3
"""
Test premium hand strategies in the massive database.
"""
from poker_bot_v2 import PokerBotV2

def test_premium_strategies():
    print("🎯 TESTING PREMIUM HAND STRATEGIES")
    print("=" * 50)
    
    bot = PokerBotV2()
    
    # Test premium hand buckets
    test_cases = [
        ("0", "AA (Pocket Aces)"),
        ("1", "KK (Pocket Kings)"),
        ("20", "AK (Ace King)"),
        ("25", "AQ (Ace Queen)"),
    ]
    
    for bucket, name in test_cases:
        print(f"\n🃏 Testing {name} (bucket {bucket}):")
        strategy = bot.strategy_lookup.get_strategy('0', bucket, 'pot1.5', ['fold', 'call', 'raise'])
        if strategy:
            fold_p = strategy.get('fold', 0)
            call_p = strategy.get('call', 0)
            raise_p = strategy.get('raise', 0)
            print(f"   Fold: {fold_p:.1%}")
            print(f"   Call: {call_p:.1%}")
            print(f"   Raise: {raise_p:.1%}")
            
            if raise_p > 0.5:
                print("   ✅ Correctly RAISES")
            elif fold_p > 0.6:
                print("   ❌ FOLDING too much")
            else:
                print("   ⚠️ Mixed strategy")
        else:
            print("   ❌ No strategy found")

if __name__ == "__main__":
    test_premium_strategies()
