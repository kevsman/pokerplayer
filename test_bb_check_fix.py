#!/usr/bin/env python3

"""
Test script to verify that the BB check fix is working correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from preflop_decision_logic import make_preflop_decision
from hand_utils import get_preflop_hand_category

def test_bb_check_scenario():
    """Test BB with weak hand and bet_to_call = 0 - should CHECK"""
    print("Testing BB check scenario with weak hand...")
    
    # Set up test scenario: BB with weak hand, no bet to call
    my_player = {
        'hand': ['7♠', '3♥'],  # Weak hand
        'stack': 1.0
    }
    
    hand_category = get_preflop_hand_category(my_player['hand'], 'BB')
    print(f"Hand category: {hand_category}")
    
    # Scenario: BB facing no bet (everyone folded to BB, or limped)
    position = 'BB'
    bet_to_call = 0.0  # KEY: No bet to call
    can_check = True   # KEY: Can check
    my_stack = 1.0
    pot_size = 0.03    # Just blinds
    active_opponents_count = 1
    small_blind = 0.01
    big_blind = 0.02
    my_current_bet_this_street = 0.02  # BB already posted
    max_bet_on_table = 0.02  # Only BB posted
    min_raise = 0.04
    is_sb = False
    is_bb = True  # KEY: This is the BB
    
    # Action constants
    ACTION_FOLD = "fold"
    ACTION_CHECK = "check"
    ACTION_CALL = "call"
    ACTION_RAISE = "raise"
    
    print(f"\nTest scenario:")
    print(f"Hand: {my_player['hand']} ({hand_category})")
    print(f"Position: {position}")
    print(f"Bet to call: {bet_to_call}")
    print(f"Can check: {can_check}")
    print(f"Is BB: {is_bb}")
    print(f"Expected result: CHECK (not fold)")
    
    # Make decision
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
    
    print(f"\nResult:")
    print(f"Action: {action}")
    print(f"Amount: {amount}")
    
    if action == ACTION_CHECK:
        print("✅ SUCCESS: Bot correctly checks when it can check for free in BB")
        return True
    else:
        print("❌ FAILURE: Bot should check, not fold, when it can check for free in BB")
        return False

def test_another_weak_hand():
    """Test another weak hand scenario"""
    print("\n" + "="*60)
    print("Testing another weak hand scenario...")
    
    my_player = {
        'hand': ['A♥', '4♠'],  # A4o - weak ace
        'stack': 1.0
    }
    
    hand_category = get_preflop_hand_category(my_player['hand'], 'BB')
    print(f"Hand category: {hand_category}")
    
    # Same scenario
    position = 'BB'
    bet_to_call = 0.0
    can_check = True
    my_stack = 1.0
    pot_size = 0.03
    active_opponents_count = 1
    small_blind = 0.01
    big_blind = 0.02
    my_current_bet_this_street = 0.02
    max_bet_on_table = 0.02
    min_raise = 0.04
    is_sb = False
    is_bb = True
    
    ACTION_FOLD = "fold"
    ACTION_CHECK = "check"
    ACTION_CALL = "call"
    ACTION_RAISE = "raise"
    
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
    
    print(f"Action: {action}, Amount: {amount}")
    
    if action == ACTION_CHECK:
        print("✅ SUCCESS: A4o correctly checks in BB when no bet to call")
        return True
    else:
        print("❌ FAILURE: A4o should check in BB when no bet to call")
        return False

if __name__ == "__main__":
    print("Testing BB check fix...")
    print("="*60)
    
    test1_result = test_bb_check_scenario()
    test2_result = test_another_weak_hand()
    
    print("\n" + "="*60)
    print("SUMMARY:")
    if test1_result and test2_result:
        print("✅ ALL TESTS PASSED: BB check fix is working correctly!")
    else:
        print("❌ TESTS FAILED: BB check fix needs more work")
