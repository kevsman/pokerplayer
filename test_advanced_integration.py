#!/usr/bin/env python3
"""
Test script to verify advanced poker features integration.
"""

import sys
import unittest
from unittest.mock import Mock, patch

# Import the modules we want to test
try:
    from postflop_decision_logic import (
        estimate_opponent_range, 
        calculate_fold_equity, 
        is_thin_value_spot, 
        should_call_bluff, 
        calculate_spr_adjustments
    )
    from opponent_tracking import OpponentTracker, OpponentProfile
    from decision_engine import DecisionEngine
    from hand_evaluator import HandEvaluator
    
    print("SUCCESS: All advanced modules imported successfully!")
    
except ImportError as e:
    print(f"IMPORT ERROR: {e}")
    sys.exit(1)

class TestAdvancedIntegration(unittest.TestCase):
    """Test the integration of advanced poker features."""
    
    def setUp(self):
        """Set up test environment."""
        self.hand_evaluator = HandEvaluator()
        self.config = {
            'big_blind': 0.02,
            'small_blind': 0.01
        }
        
    def test_opponent_range_estimation(self):
        """Test opponent range estimation function."""
        # Test tight UTG range
        range_result = estimate_opponent_range(
            position='UTG',
            preflop_action='raise',
            bet_size=0.06,
            pot_size=0.03,
            street='flop',
            board_texture='dry'
        )
        
        self.assertIn('tight', range_result)
        print(f"✓ Opponent range estimation working: {range_result}")
        
    def test_fold_equity_calculation(self):
        """Test fold equity calculation."""
        fold_equity = calculate_fold_equity(
            opponent_range='tight',
            board_texture='dry',
            bet_size=0.1,
            pot_size=0.2
        )
        
        self.assertGreater(fold_equity, 0)
        self.assertLess(fold_equity, 1)
        print(f"✓ Fold equity calculation working: {fold_equity:.2%}")
        
    def test_thin_value_detection(self):
        """Test thin value spot detection."""
        is_thin = is_thin_value_spot(
            hand_strength=2,  # One pair
            win_probability=0.58,
            opponent_range='weak',
            position='BTN'
        )
        
        self.assertIsInstance(is_thin, bool)
        print(f"✓ Thin value detection working: {is_thin}")
        
    def test_bluff_calling_logic(self):
        """Test bluff calling decision."""
        should_call = should_call_bluff(
            hand_strength=2,
            win_probability=0.45,
            pot_odds=0.25,
            opponent_range='polarized',
            bet_size=0.1,
            pot_size=0.2
        )
        
        self.assertIsInstance(should_call, bool)
        print(f"✓ Bluff calling logic working: {should_call}")
        
    def test_spr_adjustments(self):
        """Test SPR-based strategy adjustments."""
        spr_strategy = calculate_spr_adjustments(
            spr=1.5,  # Low SPR
            hand_strength=3,  # Two pair
            drawing_potential=False
        )
        
        self.assertIsInstance(spr_strategy, str)
        print(f"✓ SPR adjustments working: {spr_strategy}")
        
    def test_opponent_tracker_integration(self):
        """Test opponent tracking integration."""
        tracker = OpponentTracker()
        
        # Add some opponent data
        tracker.update_opponent_action("TestPlayer", "raise", "preflop", "BTN", 6.0, 2.0)
        
        self.assertEqual(len(tracker.opponents), 1)
        
        opponent = tracker.opponents["TestPlayer"]
        vpip = opponent.get_vpip()
        player_type = opponent.classify_player_type()
        
        print(f"✓ Opponent tracking working: VPIP={vpip:.1f}%, Type={player_type}")
        
    def test_decision_engine_integration(self):
        """Test that DecisionEngine can access opponent tracker."""
        decision_engine = DecisionEngine(self.hand_evaluator, self.config)
        
        # Verify opponent tracker exists
        self.assertIsNotNone(decision_engine.opponent_tracker)
        print(f"✓ DecisionEngine has opponent tracker: {type(decision_engine.opponent_tracker).__name__}")
        
        # Test that we can add opponents
        initial_count = len(decision_engine.opponent_tracker.opponents)
        decision_engine.opponent_tracker.update_opponent_action("TestPlayer", "call", "preflop", "CO", 2.0, 3.0)
        final_count = len(decision_engine.opponent_tracker.opponents)
        
        self.assertGreater(final_count, initial_count)
        print(f"✓ Can add opponents to DecisionEngine tracker: {initial_count} -> {final_count}")

if __name__ == '__main__':
    print("="*60)
    print("TESTING ADVANCED POKER FEATURES INTEGRATION")
    print("="*60)
    
    # Run the tests
    unittest.main(verbosity=2)
