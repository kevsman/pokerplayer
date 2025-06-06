#!/usr/bin/env python3
"""
Test to verify that AQ offsuit (A♥Q♣) calls correctly with good pot odds.
This addresses the issue where the bot folded AQ offsuit facing €0.16 to win €0.27.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from preflop_decision_logic import make_preflop_decision
from hand_utils import get_preflop_hand_category

def test_aq_offsuit_good_pot_odds():
    """Test AQ offsuit in CO position with good pot odds - should CALL"""
    
    # Mock player with AQ offsuit
    my_player = {
        'hand': ['Ah', 'Qc'],  # AQ offsuit
        'stack': 1.0,
        'current_bet': 0.0
    }
    
    # Scenario from the log:
    # Position: CO (Cutoff)
    # Bet to call: €0.16 
    # Pot size: €0.27
    # This gives pot odds of 0.16/(0.16+0.27) = 37.2% (need ~37% equity)
    
    position = 'CO'
    bet_to_call = 0.16
    pot_size = 0.27
    big_blind = 0.02
    small_blind = 0.01
    my_stack = 1.0
    max_bet_on_table = 0.18  # 9BB bet (0.18/0.02 = 9)
    
    # Get hand category
    hand_category = get_preflop_hand_category(my_player['hand'], position)
    print(f"AQ offsuit categorized as: {hand_category}")
    
    # Test parameters
    can_check = False
    active_opponents_count = 2
    my_current_bet_this_street = 0.0
    min_raise = 0.04  # 2BB
    is_sb = False
    is_bb = False
    
    # Action constants
    ACTION_FOLD = "fold"
    ACTION_CHECK = "check" 
    ACTION_CALL = "call"
    ACTION_RAISE = "raise"
    
    print(f"\n=== Test Case: AQ offsuit in CO with good pot odds ===")
    print(f"Hand: A♥Q♣")
    print(f"Position: {position}")
    print(f"Hand Category: {hand_category}")
    print(f"Bet to call: €{bet_to_call}")
    print(f"Pot size: €{pot_size}")
    print(f"Max bet on table: €{max_bet_on_table} ({max_bet_on_table/big_blind:.1f}BB)")
    
    # Calculate pot odds
    pot_odds_needed = bet_to_call / (pot_size + bet_to_call)
    print(f"Pot odds: {bet_to_call:.2f} to win {pot_size:.2f} = {pot_odds_needed:.1%} equity needed")
    print(f"AQ offsuit has ~38-42% equity vs typical ranges - this should be a CALL")
    
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
    
    print(f"\n=== RESULT ===")
    print(f"Action: {action}")
    print(f"Amount: €{amount}")
    
    # Verify the result
    if action == ACTION_CALL and amount == bet_to_call:
        print("✅ SUCCESS: Bot correctly calls AQ offsuit with good pot odds!")
        return True
    else:
        print("❌ FAILURE: Bot should call AQ offsuit with good pot odds")
        print(f"Expected: CALL €{bet_to_call}")
        print(f"Got: {action} €{amount}")
        return False

def test_aq_offsuit_poor_pot_odds():
    """Test AQ offsuit with poor pot odds - should FOLD"""
    
    my_player = {
        'hand': ['Ah', 'Qc'],  # AQ offsuit
        'stack': 1.0,
        'current_bet': 0.0
    }
    
    # Poor pot odds scenario
    position = 'CO'
    bet_to_call = 0.30  # Large bet
    pot_size = 0.20     # Small pot
    big_blind = 0.02
    max_bet_on_table = 0.32  # 16BB bet
    
    hand_category = get_preflop_hand_category(my_player['hand'], position)
    
    # Calculate pot odds
    pot_odds_needed = bet_to_call / (pot_size + bet_to_call)
    print(f"\n=== Test Case: AQ offsuit with poor pot odds ===")
    print(f"Pot odds: {bet_to_call:.2f} to win {pot_size:.2f} = {pot_odds_needed:.1%} equity needed")
    print(f"This is poor pot odds - should FOLD")
    
    # Make decision
    action, amount = make_preflop_decision(
        my_player=my_player,
        hand_category=hand_category,
        position=position,
        bet_to_call=bet_to_call,
        can_check=False,
        my_stack=1.0,
        pot_size=pot_size,
        active_opponents_count=2,
        small_blind=0.01,
        big_blind=big_blind,
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
    
    if action == "fold":
        print("✅ SUCCESS: Bot correctly folds AQ offsuit with poor pot odds!")
        return True
    else:
        print("❌ FAILURE: Bot should fold AQ offsuit with poor pot odds")
        return False

if __name__ == "__main__":
    print("Testing AQ offsuit preflop decision fix...")
    
    test1_passed = test_aq_offsuit_good_pot_odds()
    test2_passed = test_aq_offsuit_poor_pot_odds()
    
    print(f"\n=== SUMMARY ===")
    print(f"Good pot odds test: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Poor pot odds test: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! AQ offsuit issue has been fixed.")
    else:
        print("\n⚠️  Some tests failed. The issue may not be fully resolved.")
