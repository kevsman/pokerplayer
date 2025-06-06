#!/usr/bin/env python3
"""
Test script to verify AQ offsuit calling logic fix
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from preflop_decision_logic import make_preflop_decision
from hand_utils import get_preflop_hand_category

def test_aq_offsuit_call_scenario():
    """Test AQ offsuit calling with good pot odds - should CALL, not FOLD"""
    
    # Simulate the exact scenario from the log
    my_player = {
        'hand': ['Ah', 'Qc'],  # AQ offsuit
        'stack': 1.0  # €1.00
    }
    
    # Hand should be categorized as "Offsuit Broadway"
    hand_category = get_preflop_hand_category(my_player['hand'], 'CO')
    print(f"Hand category: {hand_category}")
    
    # Simulate game state from the log
    position = 'CO'  # Cutoff position
    bet_to_call = 0.16  # €0.16 to call
    can_check = False
    my_stack = 1.0  # €1.00
    pot_size = 0.27  # €0.27 in pot
    active_opponents_count = 1
    small_blind = 0.01  # €0.01
    big_blind = 0.02   # €0.02
    my_current_bet_this_street = 0
    max_bet_on_table = 0.16  # The bet we're facing
    min_raise = 0.32  # Minimum raise would be 2x the bet
    is_sb = False
    is_bb = False
    
    # Action constants
    ACTION_FOLD = "fold"
    ACTION_CHECK = "check" 
    ACTION_CALL = "call"
    ACTION_RAISE = "raise"
    
    print(f"\nTesting scenario:")
    print(f"Hand: {my_player['hand']} ({hand_category})")
    print(f"Position: {position}")
    print(f"Bet to call: €{bet_to_call}")
    print(f"Pot size: €{pot_size}")
    print(f"Pot odds: {bet_to_call}/{bet_to_call + pot_size} = {bet_to_call/(bet_to_call + pot_size):.1%} equity needed")
    print(f"Max bet on table: €{max_bet_on_table} ({max_bet_on_table/big_blind:.1f}BB)")
    
    # Make the decision
    action, amount = make_preflop_decision(
        my_player=my_player,
        hand_category=hand_category,
        position=position,
        bet_to_call=bet_to_call,
        can_check=can_check,
        my_stack=my_stack,
        pot_size=pot_size,
        active_opponents_count=active_opponents_count,
        small_blind=small_blind,
        big_blind=big_blind,
        my_current_bet_this_street=my_current_bet_this_street,
        max_bet_on_table=max_bet_on_table,
        min_raise=min_raise,
        is_sb=is_sb,
        is_bb=is_bb,
        action_fold_const=ACTION_FOLD,
        action_check_const=ACTION_CHECK,
        action_call_const=ACTION_CALL,
        action_raise_const=ACTION_RAISE
    )
    
    print(f"\nDecision: {action}")
    if amount > 0:
        print(f"Amount: €{amount}")
    
    # Verify the fix
    if action == ACTION_CALL:
        print("✅ SUCCESS: Bot correctly calls with AQ offsuit with good pot odds")
        return True
    else:
        print("❌ FAILURE: Bot should call with AQ offsuit with good pot odds")
        return False

def test_aq_offsuit_poor_odds():
    """Test AQ offsuit with poor pot odds - should FOLD"""
    
    my_player = {
        'hand': ['Ah', 'Qc'],  # AQ offsuit
        'stack': 1.0
    }
    
    hand_category = get_preflop_hand_category(my_player['hand'], 'CO')
    
    # Scenario with poor pot odds (large bet, small pot)
    position = 'CO'
    bet_to_call = 0.80  # Very large bet
    can_check = False
    my_stack = 1.0
    pot_size = 0.10   # Small pot
    active_opponents_count = 1
    small_blind = 0.01
    big_blind = 0.02
    my_current_bet_this_street = 0
    max_bet_on_table = 0.80
    min_raise = 1.60
    is_sb = False
    is_bb = False
    
    ACTION_FOLD = "fold"
    ACTION_CHECK = "check"
    ACTION_CALL = "call"
    ACTION_RAISE = "raise"
    
    pot_odds_needed = bet_to_call / (pot_size + bet_to_call)
    print(f"\nTesting poor odds scenario:")
    print(f"Bet to call: €{bet_to_call}")
    print(f"Pot size: €{pot_size}")
    print(f"Pot odds: {pot_odds_needed:.1%} equity needed (should be > 40%)")
    
    action, amount = make_preflop_decision(
        my_player=my_player,
        hand_category=hand_category,
        position=position,
        bet_to_call=bet_to_call,
        can_check=can_check,
        my_stack=my_stack,
        pot_size=pot_size,
        active_opponents_count=active_opponents_count,
        small_blind=small_blind,
        big_blind=big_blind,
        my_current_bet_this_street=my_current_bet_this_street,
        max_bet_on_table=max_bet_on_table,
        min_raise=min_raise,
        is_sb=is_sb,
        is_bb=is_bb,
        action_fold_const=ACTION_FOLD,
        action_check_const=ACTION_CHECK,
        action_call_const=ACTION_CALL,
        action_raise_const=ACTION_RAISE
    )
    
    print(f"Decision: {action}")
    
    if action == ACTION_FOLD:
        print("✅ SUCCESS: Bot correctly folds AQ offsuit with poor pot odds")
        return True
    else:
        print("❌ FAILURE: Bot should fold AQ offsuit with poor pot odds")
        return False

if __name__ == "__main__":
    print("Testing AQ offsuit calling fix...")
    print("=" * 50)
    
    success1 = test_aq_offsuit_call_scenario()
    print()
    success2 = test_aq_offsuit_poor_odds()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("🎉 ALL TESTS PASSED: AQ offsuit logic is working correctly!")
    else:
        print("⚠️  SOME TESTS FAILED: Further investigation needed")
