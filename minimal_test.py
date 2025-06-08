#!/usr/bin/env python3
"""
Minimal test to check postflop decision logic functionality.
"""

import sys
import os
from unittest.mock import Mock

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Importing config...")
from config import *

print("Importing postflop decision logic...")
from postflop_decision_logic import make_postflop_decision

print("Creating mock opponent tracker...")
mock_opponent_tracker = Mock()
mock_opponent_tracker.get_aggression_factor.return_value = 2.0
mock_opponent_tracker.get_vpip.return_value = 25.0
mock_opponent_tracker.get_pfr.return_value = 20.0
mock_opponent_tracker.get_3bet_percent.return_value = 5.0
mock_opponent_tracker.get_fold_to_cbet_percent.return_value = 65.0

print("Testing simple decision...")
try:
    decision, amount = make_postflop_decision(
        numerical_hand_rank=5,
        win_probability=0.60,
        pot_size=100,
        bet_to_call=0,
        my_stack=1000,
        opponent_tracker=mock_opponent_tracker,
        active_opponents_count=1,
        street="flop",
        position="button",
        actions_taken_this_street=[],
        pot_odds_to_call=0,
        aggression_factor=2.0,
        bluff_frequency=0.1
    )
    print(f"Decision: {decision}, Amount: {amount}")
    print("✓ Test completed successfully!")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("Test finished.")
