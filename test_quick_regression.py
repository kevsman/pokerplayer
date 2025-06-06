#!/usr/bin/env python3
"""
Quick regression test to verify AQ offsuit fix doesn't break other functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hand_utils import get_preflop_hand_category
from preflop_decision_logic import make_preflop_decision

def test_hand_decision(hand, position, bet_to_call, pot_size, max_bet_on_table, description):
    """Test a specific hand decision scenario"""
    print(f"\n=== {description} ===")
    
    # Get hand category
    category = get_preflop_hand_category(hand, position)
    print(f"Hand: {hand[0]}{hand[1]}, Position: {position}, Category: {category}")
    
    # Create test player
    my_player = {'hand': hand, 'stack': 1.0, 'current_bet': 0.0}
    
    # Make decision
    action, amount = make_preflop_decision(
        my_player=my_player,
        hand_category=category,
        position=position,
        bet_to_call=bet_to_call,
        can_check=False,
        my_stack=1.0,
        pot_size=pot_size,
        active_opponents_count=2,
        small_blind=0.01,
        big_blind=0.02,
        my_current_bet_this_street=0.0,
        max_bet_on_table=max_bet_on_table,
        min_raise=0.04,
        is_sb=False,
        is_bb=False,
        action_fold_const="fold",
        action_check_const="check", 
        action_call_const="call",
        action_raise_const="raise"
    )
    
    print(f"Action: {action}, Amount: €{amount}")
    return action, amount

def main():
    print("Running quick regression tests...")
    
    # Test 1: AQ offsuit with good pot odds (should CALL after fix)
    action1, _ = test_hand_decision(
        ['Ah', 'Qc'], 'CO', 0.16, 0.27, 0.18,
        "AQ offsuit with good pot odds"
    )
    
    # Test 2: AQ offsuit with poor pot odds (should FOLD)
    action2, _ = test_hand_decision(
        ['Ah', 'Qc'], 'CO', 0.30, 0.20, 0.32,
        "AQ offsuit with poor pot odds"
    )
    
    # Test 3: AA should still raise/call (premium hand)
    action3, _ = test_hand_decision(
        ['As', 'Ad'], 'CO', 0.16, 0.27, 0.18,
        "AA premium pair"
    )
    
    # Test 4: Weak hand should still fold
    action4, _ = test_hand_decision(
        ['7h', '2c'], 'CO', 0.16, 0.27, 0.18,
        "Weak hand 72o"
    )
    
    # Test 5: AKo (Strong Pair) should still call/raise
    action5, _ = test_hand_decision(
        ['As', 'Kc'], 'CO', 0.16, 0.27, 0.18,
        "AKo strong pair"
    )
    
    print(f"\n=== REGRESSION TEST RESULTS ===")
    print(f"AQ offsuit good pot odds: {action1} {'✅' if action1 == 'call' else '❌'}")
    print(f"AQ offsuit poor pot odds: {action2} {'✅' if action2 == 'fold' else '❌'}")
    print(f"AA premium pair: {action3} {'✅' if action3 in ['call', 'raise'] else '❌'}")
    print(f"72o weak hand: {action4} {'✅' if action4 == 'fold' else '❌'}")
    print(f"AKo strong pair: {action5} {'✅' if action5 in ['call', 'raise'] else '❌'}")
    
    all_passed = (
        action1 == 'call' and 
        action2 == 'fold' and 
        action3 in ['call', 'raise'] and 
        action4 == 'fold' and 
        action5 in ['call', 'raise']
    )
    
    print(f"\n{'🎉 All regression tests PASSED!' if all_passed else '❌ Some regression tests FAILED!'}")

if __name__ == '__main__':
    main()
