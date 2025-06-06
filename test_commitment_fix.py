#!/usr/bin/env python3
"""Test the fixed postflop_decision_logic with a minimal scenario."""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from postflop_decision_logic import make_postflop_decision
    from decision_engine import DecisionEngine
    print("✓ Successfully imported postflop_decision_logic")
    
    # Test that the commitment_threshold variable is properly defined
    # Create a minimal DecisionEngine instance
    class MockDecisionEngine:
        def should_bluff_func(self, *args, **kwargs):
            return False
    
    decision_engine = MockDecisionEngine()
    
    # Test parameters that should trigger the commitment_threshold logic
    result = make_postflop_decision(
        decision_engine_instance=decision_engine,
        numerical_hand_rank=5,  # Medium hand
        hand_description="One Pair",
        bet_to_call=0.0,
        can_check=True,
        pot_size=0.05,
        my_stack=1.98,
        win_probability=0.45,  # Medium probability
        pot_odds_to_call=0.0,
        game_stage="flop",
        spr=39.6,
        action_fold_const="fold",
        action_check_const="check",
        action_call_const="call",
        action_raise_const="raise",
        my_player_data={'seat': '4', 'current_bet': 0},
        big_blind_amount=0.02,
        base_aggression_factor=1.0,
        max_bet_on_table=0.0,
        active_opponents_count=5,
        opponent_tracker=None
    )
    
    print(f"✓ Successfully executed make_postflop_decision: {result}")
    print("✓ All tests passed - the UnboundLocalError has been fixed!")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
