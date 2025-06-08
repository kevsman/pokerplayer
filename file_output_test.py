#!/usr/bin/env python3
"""
Comprehensive validation of the KQ pair of 9s fix - with file output
"""
from postflop_decision_logic import make_postflop_decision
from unittest.mock import Mock

# Open output file
with open("test_results.txt", "w") as f:
    f.write("=== COMPREHENSIVE FIX VALIDATION ===\n")
    f.write("\n")
    
    decision_engine = Mock()
    decision_engine.should_bluff_func = Mock(return_value=False)
    
    # Scenario 1: Original first bet (0.24 call)
    f.write("1. Original scenario - KQ pair of 9s, 0.24 bet:\n")
    action1, amount1 = make_postflop_decision(
        decision_engine_instance=decision_engine,
        numerical_hand_rank=2,
        hand_description="One Pair, 9s",
        bet_to_call=0.24,
        can_check=False,
        pot_size=0.48,
        my_stack=0.74,
        win_probability=0.35,
        pot_odds_to_call=0.333,
        game_stage="turn",
        spr=1.54,
        action_fold_const="fold",
        action_check_const="check",
        action_call_const="call",
        action_raise_const="raise",
        my_player_data={"current_bet": 0.0, "hand": ["QS", "KH"], "community_cards": ["9C", "9D", "7D", "5S"], "is_all_in_call_available": False},
        big_blind_amount=0.02,
        base_aggression_factor=1.0,
        max_bet_on_table=0.24,
        active_opponents_count=1,
        opponent_tracker=None
    )
    f.write(f"   Decision: {action1} (Expected: fold)\n")
    
    # Scenario 2: All-in scenario
    f.write("2. All-in scenario - KQ pair of 9s, 0.50 all-in:\n")
    action2, amount2 = make_postflop_decision(
        decision_engine_instance=decision_engine,
        numerical_hand_rank=2,
        hand_description="One Pair, 9s",
        bet_to_call=0.50,
        can_check=False,
        pot_size=1.55,
        my_stack=0.50,
        win_probability=0.35,
        pot_odds_to_call=0.244,
        game_stage="turn",
        spr=0.32,
        action_fold_const="fold",
        action_check_const="check",
        action_call_const="call",
        action_raise_const="raise",
        my_player_data={"current_bet": 0.24, "hand": ["QS", "KH"], "community_cards": ["9C", "9D", "7D", "5S"], "is_all_in_call_available": True},
        big_blind_amount=0.02,
        base_aggression_factor=1.0,
        max_bet_on_table=0.50,
        active_opponents_count=1,
        opponent_tracker=None
    )
    f.write(f"   Decision: {action2} (Expected: fold)\n")
    
    f.write("\n")
    if action1 == "fold" and action2 == "fold":
        f.write("✅ SUCCESS: Both problematic scenarios now fold correctly!\n")
        f.write("✅ The poker bot KQ pair of 9s issue has been FIXED!\n")
    else:
        f.write("❌ FAILURE: Fix incomplete\n")
        f.write(f"   Scenario 1: {action1} (should be fold)\n")
        f.write(f"   Scenario 2: {action2} (should be fold)\n")

print("Test completed. Results written to test_results.txt")
