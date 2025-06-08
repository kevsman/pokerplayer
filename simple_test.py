#!/usr/bin/env python3
"""
Simple test for the all-in scenario fix
"""
import sys
print("Starting test...", flush=True)

try:
    from postflop_decision_logic import make_postflop_decision
    from unittest.mock import Mock
    print("Imports successful", flush=True)
    
    # Mock decision engine
    decision_engine = Mock()
    decision_engine.should_bluff_func = Mock(return_value=False)
    
    # All-in scenario parameters
    numerical_hand_rank = 2  # One pair
    hand_description = "One Pair, 9s"
    bet_to_call = 0.50  # All-in bet
    can_check = False
    pot_size = 1.55
    my_stack = 0.50
    win_probability = 0.35
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
        'hand': ['QS', 'KH'],
        'community_cards': ['9C', '9D', '7D', '5S'],
        'is_all_in_call_available': True
    }
    
    big_blind_amount = 0.02
    base_aggression_factor = 1.0
    max_bet_on_table = 0.50
    active_opponents_count = 1
      print(f"Testing all-in KQ with pair of 9s scenario:", flush=True)
    print(f"Hand rank: {numerical_hand_rank} ({hand_description})", flush=True)
    print(f"Win probability: {win_probability:.2%}", flush=True)
    print(f"Pot odds needed: {pot_odds_to_call:.2%}", flush=True)
    print(f"Bet to call: {bet_to_call} (ALL-IN), Pot: {pot_size}, Stack: {my_stack}", flush=True)
    
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
    print(f"\nDecision: {action}, Amount: {amount}", flush=True)
    
    # The bot should FOLD in this all-in scenario
    expected_action = ACTION_FOLD
    
    if action == expected_action:
        print(f"PASS: Correctly decided to {action} the all-in", flush=True)
    else:
        print(f"FAIL: Expected {expected_action}, but got {action}", flush=True)
        print("This was the exact scenario that caused the original issue!", flush=True)

except Exception as e:
    print(f"Error during test: {e}", flush=True)
    import traceback
    traceback.print_exc()

print("Test completed.", flush=True)
