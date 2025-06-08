#!/usr/bin/env python3
"""
Test to reproduce and fix the KQ offsuit calling with pair of 9s issue.
Based on the log: Hand: ['Q♠', 'K♥'], Rank: One Pair, 9s, Community Cards: ['9♣', '9♦', '7♦', '5♠']
The bot incorrectly called a bet of 0.24 when pot was 0.48
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from postflop_decision_logic import make_postflop_decision
from decision_engine import DecisionEngine
from unittest.mock import Mock

def test_kq_pair_of_nines_should_fold():
    """Test that KQ with pair of 9s on board should fold to significant betting"""
    
    # Mock decision engine
    decision_engine = Mock()
    decision_engine.should_bluff_func = Mock(return_value=False)
    
    # Test scenario from log
    numerical_hand_rank = 2  # One pair
    hand_description = "One Pair, 9s"
    bet_to_call = 0.24
    can_check = False
    pot_size = 0.48
    my_stack = 0.50  # From log: Stack: €0.74 - bet_to_call = 0.50
    win_probability = 0.35  # Estimated based on weak pair with medium kicker
    pot_odds_to_call = bet_to_call / (pot_size + bet_to_call)  # 0.24 / 0.72 = 33.3%
    game_stage = 'turn'
    spr = my_stack / pot_size  # ~1.04
    
    # Action constants
    ACTION_FOLD = "fold"
    ACTION_CHECK = "check" 
    ACTION_CALL = "call"
    ACTION_RAISE = "raise"
    
    my_player_data = {
        'current_bet': 0.24,  # Already committed this much
        'hand': ['Q♠', 'K♥'],
        'community_cards': ['9♣', '9♦', '7♦', '5♠']
    }
    
    big_blind_amount = 0.02
    base_aggression_factor = 1.0
    max_bet_on_table = 0.24
    active_opponents_count = 1
    
    print(f"Testing KQ with pair of 9s scenario:")
    print(f"Hand rank: {numerical_hand_rank} ({hand_description})")
    print(f"Win probability: {win_probability:.2%}")
    print(f"Pot odds needed: {pot_odds_to_call:.2%}")
    print(f"Bet to call: {bet_to_call}, Pot: {pot_size}, Stack: {my_stack}")
    print(f"SPR: {spr:.2f}")
    
    # Call the decision function
    action, amount = make_postflop_decision(
        decision_engine_instance=decision_engine,
        numerical_hand_rank=numerical_hand_rank,
        hand_description=hand_description,
        bet_to_call=bet_to_call,
        can_check=can_check,
        pot_size=pot_size,
        my_stack=my_stack,
        win_probability=win_probability,
        pot_odds_to_call=pot_odds_to_call,
        game_stage=game_stage,
        spr=spr,
        action_fold_const=ACTION_FOLD,
        action_check_const=ACTION_CHECK,
        action_call_const=ACTION_CALL,
        action_raise_const=ACTION_RAISE,
        my_player_data=my_player_data,
        big_blind_amount=big_blind_amount,
        base_aggression_factor=base_aggression_factor,
        max_bet_on_table=max_bet_on_table,
        active_opponents_count=active_opponents_count,
        opponent_tracker=None
    )
    
    print(f"\nDecision: {action}, Amount: {amount}")
    
    # The bot should FOLD in this scenario
    # - Only has pair of 9s with K kicker
    # - Win probability (35%) > pot odds (33%), but barely
    # - Facing a 50% pot bet on the turn
    # - This is a marginal spot that should be folded
    expected_action = ACTION_FOLD
    
    if action == expected_action:
        print(f"✅ PASS: Correctly decided to {action}")
        return True
    else:
        print(f"❌ FAIL: Expected {expected_action}, but got {action}")
        return False

def test_kq_pair_of_nines_with_higher_win_prob():
    """Test with higher win probability to see when it would call"""
    
    # Mock decision engine
    decision_engine = Mock()
    decision_engine.should_bluff_func = Mock(return_value=False)
    
    # Same scenario but with higher win probability
    numerical_hand_rank = 2  # One pair
    hand_description = "One Pair, 9s"
    bet_to_call = 0.24
    can_check = False
    pot_size = 0.48
    my_stack = 0.50
    win_probability = 0.55  # Higher win probability
    pot_odds_to_call = bet_to_call / (pot_size + bet_to_call)
    game_stage = 'turn'
    spr = my_stack / pot_size
    
    # Action constants
    ACTION_FOLD = "fold"
    ACTION_CHECK = "check" 
    ACTION_CALL = "call"
    ACTION_RAISE = "raise"
    
    my_player_data = {
        'current_bet': 0.24,
        'hand': ['Q♠', 'K♥'],
        'community_cards': ['9♣', '9♦', '7♦', '5♠']
    }
    
    big_blind_amount = 0.02
    base_aggression_factor = 1.0
    max_bet_on_table = 0.24
    active_opponents_count = 1
    
    print(f"\nTesting KQ with pair of 9s (higher win prob):")
    print(f"Win probability: {win_probability:.2%}")
    print(f"Pot odds needed: {pot_odds_to_call:.2%}")
    
    # Call the decision function
    action, amount = make_postflop_decision(
        decision_engine_instance=decision_engine,
        numerical_hand_rank=numerical_hand_rank,
        hand_description=hand_description,
        bet_to_call=bet_to_call,
        can_check=can_check,
        pot_size=pot_size,
        my_stack=my_stack,
        win_probability=win_probability,
        pot_odds_to_call=pot_odds_to_call,
        game_stage=game_stage,
        spr=spr,
        action_fold_const=ACTION_FOLD,
        action_check_const=ACTION_CHECK,
        action_call_const=ACTION_CALL,
        action_raise_const=ACTION_RAISE,
        my_player_data=my_player_data,
        big_blind_amount=big_blind_amount,
        base_aggression_factor=base_aggression_factor,
        max_bet_on_table=max_bet_on_table,
        active_opponents_count=active_opponents_count,
        opponent_tracker=None
    )
    
    print(f"Decision: {action}, Amount: {amount}")
    
    # With higher win probability, calling might be acceptable
    if action in [ACTION_CALL, ACTION_FOLD]:
        print(f"✅ Decision {action} is reasonable with {win_probability:.2%} equity")
        return True
    else:
        print(f"❌ Unexpected action: {action}")
        return False

if __name__ == "__main__":
    print("Testing KQ pair of 9s scenario...")
    
    test1_passed = test_kq_pair_of_nines_should_fold()
    test2_passed = test_kq_pair_of_nines_with_higher_win_prob()
    
    if test1_passed and test2_passed:
        print(f"\n✅ All tests passed!")
    else:
        print(f"\n❌ Some tests failed - need to fix the logic")
