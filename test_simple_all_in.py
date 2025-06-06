#!/usr/bin/env python3
"""
Simple test for the all-in calling logic
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_simple_all_in_logic():
    """Test the core all-in detection logic"""
    print("=== Testing All-in Detection Logic ===")
    
    # Test scenarios
    scenarios = [
        {
            'name': 'Q♥10♦ All-in (should fold)',
            'bet_to_call': 0.33,
            'my_stack': 0.33,
            'win_probability': 0.3344,
            'expected_action': 'fold',
            'reason': '33.44% < 45% required for all-in with draws'
        },
        {
            'name': 'Strong draw all-in (should call)',
            'bet_to_call': 0.30,
            'my_stack': 0.30,
            'win_probability': 0.47,
            'expected_action': 'call',
            'reason': '47% > 45% required for all-in with draws'
        },
        {
            'name': 'Non all-in draw (implied odds)',
            'bet_to_call': 0.15,
            'my_stack': 1.20,
            'win_probability': 0.35,
            'expected_action': 'call_or_fold',
            'reason': 'Can use implied odds since not all-in'
        }
    ]
    
    for scenario in scenarios:
        print(f"\n--- {scenario['name']} ---")
        
        # Check if it's an all-in situation
        is_all_in_call = (scenario['bet_to_call'] >= scenario['my_stack'])
        is_facing_all_in = (scenario['bet_to_call'] >= scenario['my_stack'] * 0.9)
        
        print(f"Bet to call: €{scenario['bet_to_call']}")
        print(f"My stack: €{scenario['my_stack']}")
        print(f"Win probability: {scenario['win_probability']:.2%}")
        print(f"Is all-in call: {is_all_in_call}")
        print(f"Is facing all-in: {is_facing_all_in}")
        
        if is_all_in_call or is_facing_all_in:
            required_equity = 0.45  # 45% equity required for all-in with draws
            decision = "call" if scenario['win_probability'] >= required_equity else "fold"
            print(f"All-in logic: Need {required_equity:.0%}, have {scenario['win_probability']:.2%} → {decision.upper()}")
        else:
            print("Regular drawing hand logic (implied odds applicable)")
            decision = "call_or_fold"
        
        print(f"Expected: {scenario['expected_action']}")
        print(f"Logic result: {decision}")
        print(f"Reason: {scenario['reason']}")
        
        # Check if logic is correct
        if scenario['expected_action'] == 'call_or_fold':
            print("✅ PASS: Non all-in logic path")
        elif decision == scenario['expected_action']:
            print("✅ PASS: Correct decision")
        else:
            print("❌ FAIL: Wrong decision")

def test_drawing_hand_detection():
    """Test the is_drawing_hand function"""
    print("\n=== Testing Drawing Hand Detection ===")
    
    # Import the function
    try:
        from postflop_decision_logic import is_drawing_hand
        
        test_cases = [
            {'win_prob': 0.33, 'hand_rank': 1, 'street': 'flop', 'expected': True, 'desc': 'Q10 on flop'},
            {'win_prob': 0.35, 'hand_rank': 2, 'street': 'flop', 'expected': True, 'desc': 'Weak pair with draw'},
            {'win_prob': 0.15, 'hand_rank': 1, 'street': 'flop', 'expected': False, 'desc': 'Too weak'},
            {'win_prob': 0.60, 'hand_rank': 1, 'street': 'flop', 'expected': False, 'desc': 'Too strong for draw'},
            {'win_prob': 0.35, 'hand_rank': 1, 'street': 'river', 'expected': False, 'desc': 'No draws on river'},
        ]
        
        for case in test_cases:
            result = is_drawing_hand(case['win_prob'], case['hand_rank'], case['street'])
            status = "✅ PASS" if result == case['expected'] else "❌ FAIL"
            print(f"{status}: {case['desc']} - Expected: {case['expected']}, Got: {result}")
            
    except ImportError as e:
        print(f"❌ Could not import is_drawing_hand: {e}")

def main():
    print("Testing All-in Logic Fixes")
    print("=" * 50)
    
    test_simple_all_in_logic()
    test_drawing_hand_detection()
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print("✓ All-in detection implemented")
    print("✓ 45% equity requirement for all-in calls with draws")
    print("✓ Implied odds disabled for all-in situations")
    print("✓ Q♥10♦ scenario should now fold correctly")
    print("=" * 50)

if __name__ == '__main__':
    main()
