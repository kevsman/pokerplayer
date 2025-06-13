#!/usr/bin/env python3
"""
Quick test to verify the improved preflop hand categorizations
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hand_utils import get_preflop_hand_category

def test_categorizations():
    """Test various hands to ensure they're categorized correctly"""
    
    test_hands = [
        # Premium hands
        (['A♠', 'A♥'], 'Premium Pair'),  # AA
        (['K♠', 'K♥'], 'Premium Pair'),  # KK  
        (['Q♠', 'Q♥'], 'Premium Pair'),  # QQ
        (['A♠', 'K♠'], 'Premium Pair'),  # AKs
        (['A♠', 'K♥'], 'Premium Pair'),  # AKo
        
        # Strong hands
        (['J♠', 'J♥'], 'Strong Pair'),   # JJ
        (['T♠', 'T♥'], 'Strong Pair'),   # TT
        (['9♠', '9♥'], 'Strong Pair'),   # 99 (moved from Medium)
        (['A♠', 'Q♠'], 'Strong Pair'),   # AQs
        (['A♠', 'Q♥'], 'Strong Pair'),   # AQo (fixed!)
        
        # Medium hands
        (['8♠', '8♥'], 'Medium Pair'),   # 88
        (['7♠', '7♥'], 'Medium Pair'),   # 77
        
        # Suited hands
        (['A♠', 'J♠'], 'Suited Ace'),    # AJs
        (['A♠', 'T♠'], 'Suited Ace'),    # ATs
        (['K♠', 'Q♠'], 'Suited Broadway'), # KQs
        (['K♠', 'J♠'], 'Suited Broadway'), # KJs
        (['Q♠', 'J♠'], 'Suited Broadway'), # QJs
        (['J♠', 'T♠'], 'Suited Broadway'), # JTs
        
        # Offsuit hands
        (['A♠', 'J♥'], 'Offsuit Ace'),   # AJo
        (['A♠', 'T♥'], 'Offsuit Ace'),   # ATo
        (['K♠', 'Q♥'], 'Offsuit Broadway'), # KQo
        (['K♠', 'J♥'], 'Offsuit Broadway'), # KJo
        (['Q♠', 'J♥'], 'Offsuit Broadway'), # QJo
        (['J♠', 'T♥'], 'Offsuit Broadway'), # JTo
        
        # Small pairs
        (['6♠', '6♥'], 'Small Pair'),    # 66
        (['5♠', '5♥'], 'Small Pair'),    # 55
        (['4♠', '4♥'], 'Small Pair'),    # 44
        (['3♠', '3♥'], 'Small Pair'),    # 33
        (['2♠', '2♥'], 'Small Pair'),    # 22
        
        # Connectors
        (['T♠', '9♠'], 'Suited Connector'), # T9s
        (['9♠', '8♠'], 'Suited Connector'), # 98s
        (['8♠', '7♠'], 'Suited Connector'), # 87s
        
        # Weak hands
        (['7♠', '2♥'], 'Weak'),          # 72o
        (['J♠', '3♥'], 'Weak'),          # J3o
    ]
    
    print("Testing hand categorizations...")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for hand, expected in test_hands:
        result = get_preflop_hand_category(hand, 'MP')  # Position doesn't affect categorization
        status = "✓" if result == expected else "✗"
        print(f"{status} {hand[0]} {hand[1]}: Expected '{expected}', Got '{result}'")
        
        if result == expected:
            passed += 1
        else:
            failed += 1
    
    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✓ All tests passed! Hand categorization is working correctly.")
    else:
        print(f"✗ {failed} tests failed. Check the categorization logic.")

if __name__ == "__main__":
    test_categorizations()
