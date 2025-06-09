#!/usr/bin/env python3
"""Test that J4 suited is no longer classified as Suited Playable"""

from hand_utils import get_preflop_hand_category

def test_j4s_classification():
    """Test that J4s is now properly classified as Weak instead of Suited Playable"""
    
    # Test J4 suited
    j4s_category = get_preflop_hand_category(['J♦', '4♦'], 'CO')
    print(f"J4 suited classification: {j4s_category}")
    
    # Test other hands for comparison
    test_hands = [
        (['J♦', '4♦'], 'J4s'),
        (['J♦', '5♦'], 'J5s'), 
        (['J♦', '6♦'], 'J6s'),
        (['J♦', '7♦'], 'J7s'),
        (['T♦', '4♦'], 'T4s'),
        (['T♦', '5♦'], 'T5s'),
        (['T♦', '6♦'], 'T6s'),
        (['9♦', '4♦'], '94s'),
        (['9♦', '5♦'], '95s'),
        (['9♦', '6♦'], '96s'),
    ]
    
    print("\nHand classifications after fix:")
    for hand, name in test_hands:
        category = get_preflop_hand_category(hand, 'CO')
        print(f"{name}: {category}")
    
    # Verify J4s is NOT Suited Playable
    assert j4s_category != "Suited Playable", f"J4s should NOT be Suited Playable, got: {j4s_category}"
    
    # J6s+ should still be Suited Playable
    j6s_category = get_preflop_hand_category(['J♦', '6♦'], 'CO')
    assert j6s_category == "Suited Playable", f"J6s should be Suited Playable, got: {j6s_category}"
    
    print("\n✅ Fix verified: J4s is no longer classified as Suited Playable")
    print(f"✅ J4s is now: {j4s_category}")
    print(f"✅ J6s remains: {j6s_category}")

if __name__ == "__main__":
    test_j4s_classification()
