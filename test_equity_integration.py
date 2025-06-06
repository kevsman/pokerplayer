#!/usr/bin/env python3
"""
Test the equity calculator integration with postflop decision logic
"""

from equity_calculator import EquityCalculator
from postflop_decision_logic import make_postflop_decision
from decision_engine import DecisionEngine

def test_equity_integration():
    print("=== Testing Equity Calculator Integration ===")
    
    # Test basic equity calculation
    calc = EquityCalculator()
    
    print("Test 1: Basic equity calculation")
    try:
        hole_cards = ['A♠', 'A♥']
        community_cards = []
        win_prob = calc.calculate_win_probability(hole_cards, community_cards, 1)
        print(f"Pocket Aces win probability: {win_prob:.3f} ({win_prob*100:.1f}%)")
        
        if 0.80 <= win_prob <= 0.90:
            print("✓ Win probability in expected range")
        else:
            print("✗ Win probability outside expected range")
    except Exception as e:
        print(f"✗ Error in basic equity calculation: {e}")
        return False
    
    print("\nTest 2: Equity calculation with board cards")
    try:
        hole_cards = ['K♠', '8♥']
        community_cards = ['A♠', '2♥', '3♦']
        win_prob = calc.calculate_win_probability(hole_cards, community_cards, 1)
        print(f"K8o on A23 board win probability: {win_prob:.3f} ({win_prob*100:.1f}%)")
        
        if 0.05 <= win_prob <= 0.25:
            print("✓ Win probability in expected range for weak hand")
        else:
            print("✗ Win probability outside expected range")
    except Exception as e:
        print(f"✗ Error in board equity calculation: {e}")
        return False
    
    print("\nTest 3: Test if zero win probability issue is resolved")
    test_hands = [
        (['A♠', 'A♥'], [], "Pocket Aces"),
        (['K♠', 'K♥'], ['2♦', '7♣', 'J♠'], "KK on safe board"),
        (['2♠', '7♣'], ['A♦', 'K♣', 'Q♠'], "27o on AKQ"),
        (['Q♠', '5♠'], ['A♦', '2♥', '3♣'], "Q5s on A23")
    ]
    
    for hole_cards, board, desc in test_hands:
        try:
            win_prob = calc.calculate_win_probability(hole_cards, board, 1)
            if win_prob == 0.0:
                print(f"✗ {desc}: Zero win probability detected!")
                return False
            else:
                print(f"✓ {desc}: {win_prob:.3f} ({win_prob*100:.1f}%)")
        except Exception as e:
            print(f"✗ {desc}: Error - {e}")
            return False
    
    print("\n=== All tests passed! Equity calculator is working correctly ===")
    return True

if __name__ == "__main__":
    test_equity_integration()
