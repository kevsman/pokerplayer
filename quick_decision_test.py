#!/usr/bin/env python3
"""
Simple test to confirm GPU strategies are being used instead of fallback.
"""

def quick_decision_test():
    print("🎯 QUICK DECISION TEST - GPU vs Fallback")
    print("=" * 50)
    
    try:
        from poker_bot_v2 import PokerBotV2
        
        print("🚀 Loading bot...")
        bot = PokerBotV2()
        
        # Test case: Premium hand (should clearly use strategy)
        test_hands = [
            ["A♠", "A♥"],  # Pocket Aces
            ["K♠", "K♥"],  # Pocket Kings  
            ["A♠", "K♠"],  # AK suited
        ]
        
        for i, hole_cards in enumerate(test_hands, 1):
            print(f"\n🃏 Test {i}: {hole_cards[0]} {hole_cards[1]}")
            
            # Use the same improved bucketing as the main test
            card1_rank = hole_cards[0][0]
            card2_rank = hole_cards[1][0]
            hand_str = ''.join(sorted([card1_rank, card2_rank]))
            
            # Improved hand strength mapping
            hand_strength_map = {
                'AA': 174999,  # Best possible hand
                'KK': 174900, 'QQ': 174800, 'JJ': 174700, 'TT': 174600,
                '99': 174500, '88': 174400, '77': 174300, '66': 174200,
                '55': 174100, '44': 174000, '33': 173900, '22': 173800,
                'AK': 173700, 'AQ': 173600, 'AJ': 173500, 'AT': 173400,
                'A9': 173300, 'A8': 173200, 'A7': 173100, 'A6': 173000,
                'A5': 172900, 'A4': 172800, 'A3': 172700, 'A2': 172600,
                'KQ': 172500, 'KJ': 172400, 'KT': 172300, 'K9': 172200,
            }
            
            # Get base strength
            if hand_str in hand_strength_map:
                base_strength = hand_strength_map[hand_str]
            else:
                base_strength = hash(hand_str) % 170000
            
            # Add suited bonus
            is_suited = hole_cards[0][1] == hole_cards[1][1]
            if is_suited and card1_rank != card2_rank:
                hand_bucket = str(min(174999, base_strength + 1000))
            else:
                hand_bucket = str(base_strength)
            
            board_bucket = "pot1.5"
            
            print(f"   Lookup: street=0, hand={hand_bucket}, board={board_bucket}")
            
            strategy = bot.strategy_lookup.get_strategy("0", hand_bucket, board_bucket, ['fold', 'call', 'raise'])
            
            if strategy:
                print(f"   ✅ GPU Strategy found!")
                print(f"      Fold: {strategy.get('fold', 0):.1%}")
                print(f"      Call: {strategy.get('call', 0):.1%}")
                print(f"      Raise: {strategy.get('raise', 0):.1%}")
                
                # Determine action
                if strategy.get('raise', 0) > 0.5:
                    action = "RAISE"
                elif strategy.get('call', 0) > 0.4:
                    action = "CALL"
                else:
                    action = "FOLD"
                    
                print(f"      → GPU Action: {action}")
            else:
                print(f"   ❌ Using fallback logic")
        
        print(f"\n✅ Test complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    quick_decision_test()
