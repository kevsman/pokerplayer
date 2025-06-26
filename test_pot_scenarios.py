#!/usr/bin/env python3
"""
Test different pot scenarios to understand when AA should raise vs fold.
"""

def test_pot_scenarios():
    print("🎯 TESTING AA WITH DIFFERENT POT SCENARIOS")
    print("=" * 50)
    
    try:
        from poker_bot_v2 import PokerBotV2
        
        bot = PokerBotV2()
        
        # Test AA with different pot ratios
        pot_scenarios = [
            "pot0.1",  # Very small pot
            "pot0.5",  # Small pot  
            "pot1.0",  # Medium pot
            "pot1.5",  # Large pot (current test)
            "pot2.0",  # Very large pot
            "pot3.0",  # Huge pot
        ]
        
        hand_bucket = "174999"  # AA
        
        for pot_bucket in pot_scenarios:
            print(f"\n🃏 AA with {pot_bucket}:")
            
            strategy = bot.strategy_lookup.get_strategy("0", hand_bucket, pot_bucket, ['fold', 'call', 'raise'])
            
            if strategy:
                fold_pct = strategy['fold'] * 100
                call_pct = strategy['call'] * 100  
                raise_pct = strategy['raise'] * 100
                
                if raise_pct > 50:
                    action = "RAISE"
                elif call_pct > 40:
                    action = "CALL"
                else:
                    action = "FOLD"
                    
                print(f"   Fold: {fold_pct:.1f}%, Call: {call_pct:.1f}%, Raise: {raise_pct:.1f}% → {action}")
            else:
                print(f"   No strategy found")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_pot_scenarios()
