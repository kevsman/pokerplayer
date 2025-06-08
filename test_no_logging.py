#!/usr/bin/env python3
"""
Very simple test to check basic functionality without logging.
"""

import sys
import os
from unittest.mock import Mock, patch

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock the logger to prevent any logging issues
import logging
logging.disable(logging.CRITICAL)

def simple_test():
    """Run a simple test without complex logging."""
    print("Starting simple postflop test...")
    
    try:
        # Import after disabling logging
        print("Importing config...")
        from config import *
        
        print("Importing postflop logic...")
        
        # Patch any potential logger calls
        with patch('postflop_decision_logic.logger') as mock_logger:
            mock_logger.info.return_value = None
            mock_logger.debug.return_value = None
            mock_logger.warning.return_value = None
            mock_logger.error.return_value = None
            
            from postflop_decision_logic import make_postflop_decision
            
            print("Creating mock opponent tracker...")
            mock_opponent_tracker = Mock()
            mock_opponent_tracker.get_aggression_factor.return_value = 2.0
            mock_opponent_tracker.get_vpip.return_value = 25.0
            mock_opponent_tracker.get_pfr.return_value = 20.0
            mock_opponent_tracker.get_3bet_percent.return_value = 5.0
            mock_opponent_tracker.get_fold_to_cbet_percent.return_value = 65.0
            
            print("Testing simple decision...")
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
            
            print(f"✓ Decision: {decision}, Amount: {amount}")
            
            # Test enhanced bet sizing
            print("Testing strong hand decision...")
            decision2, amount2 = make_postflop_decision(
                numerical_hand_rank=4,  # Strong hand
                win_probability=0.85,
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
            
            print(f"✓ Strong hand decision: {decision2}, Amount: {amount2}")
            
            # Test multiway pot
            print("Testing multiway pot...")
            decision3, amount3 = make_postflop_decision(
                numerical_hand_rank=6,  # Medium hand
                win_probability=0.45,
                pot_size=150,
                bet_to_call=0,
                my_stack=850,
                opponent_tracker=mock_opponent_tracker,
                active_opponents_count=3,  # Multiway
                street="flop",
                position="cutoff",
                actions_taken_this_street=[],
                pot_odds_to_call=0,
                aggression_factor=2.0,
                bluff_frequency=0.1
            )
            
            print(f"✓ Multiway decision: {decision3}, Amount: {amount3}")
            
            print("🎉 All simple tests completed successfully!")
            return True
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = simple_test()
    print(f"Test result: {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)
