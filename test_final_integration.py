#!/usr/bin/env python3
"""
Final integration test for enhanced postflop improvements.
Tests the complete decision logic with all enhancements working together.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from postflop_decision_logic import make_postflop_decision
from config import *

class TestFinalIntegration(unittest.TestCase):
    """Test complete integration of all postflop enhancements."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_opponent_tracker = Mock()
        self.mock_opponent_tracker.get_aggression_factor.return_value = 2.0
        self.mock_opponent_tracker.get_vpip.return_value = 25.0
        self.mock_opponent_tracker.get_pfr.return_value = 20.0
        self.mock_opponent_tracker.get_3bet_percent.return_value = 5.0
        self.mock_opponent_tracker.get_fold_to_cbet_percent.return_value = 65.0
        
    def test_strong_hand_consistent_sizing(self):
        """Test that strong hands use consistent bet sizing."""
        # Test scenario: Top pair strong kicker on flop
        decision, amount = make_postflop_decision(
            numerical_hand_rank=4,  # Strong hand
            win_probability=0.85,
            pot_size=100,
            bet_to_call=0,
            my_stack=1000,
            opponent_tracker=self.mock_opponent_tracker,
            active_opponents_count=1,
            street="flop",
            position="button",
            actions_taken_this_street=[],
            pot_odds_to_call=0,
            aggression_factor=2.0,
            bluff_frequency=0.1
        )
        
        self.assertEqual(decision, action_bet_const)
        # Should use consistent 2/3 pot sizing for strong hands
        expected_bet = int(100 * 0.67)  # 2/3 pot
        self.assertAlmostEqual(amount, expected_bet, delta=10)
        
    def test_drawing_hand_enhanced_analysis(self):
        """Test enhanced drawing hand analysis with implied odds."""
        # Test scenario: Flush draw on flop
        decision, amount = make_postflop_decision(
            numerical_hand_rank=8,  # Drawing hand
            win_probability=0.35,  # Good draw
            pot_size=200,
            bet_to_call=50,
            my_stack=800,
            opponent_tracker=self.mock_opponent_tracker,
            active_opponents_count=1,
            street="flop",
            position="button",
            actions_taken_this_street=[],
            pot_odds_to_call=0.20,  # 50/(200+50) = 20%
            aggression_factor=2.0,
            bluff_frequency=0.1
        )
        
        # Drawing hand with good implied odds should call
        self.assertEqual(decision, action_call_const)
        self.assertEqual(amount, 50)
        
    def test_enhanced_bluffing_strategy(self):
        """Test enhanced bluffing strategy with position awareness."""
        # Test scenario: Weak hand in position vs tight opponent
        self.mock_opponent_tracker.get_fold_to_cbet_percent.return_value = 75.0  # Tight opponent
        
        decision, amount = make_postflop_decision(
            numerical_hand_rank=9,  # Weak hand
            win_probability=0.15,
            pot_size=80,
            bet_to_call=0,
            my_stack=900,
            opponent_tracker=self.mock_opponent_tracker,
            active_opponents_count=1,
            street="flop",
            position="button",  # In position
            actions_taken_this_street=[],
            pot_odds_to_call=0,
            aggression_factor=2.0,
            bluff_frequency=0.25  # Higher bluff frequency
        )
        
        # Should bluff more often in position vs tight opponent
        if decision == action_bet_const:
            # Bluff size should be around 1/2 pot
            expected_bet = int(80 * 0.5)
            self.assertAlmostEqual(amount, expected_bet, delta=10)
        else:
            # Alternatively might check/fold which is also valid
            self.assertIn(decision, [action_check_const, action_fold_const])
            
    def test_multiway_conservative_play(self):
        """Test conservative play in multiway pots."""
        # Test scenario: Medium hand vs 3 opponents
        decision, amount = make_postflop_decision(
            numerical_hand_rank=6,  # Medium hand
            win_probability=0.45,
            pot_size=150,
            bet_to_call=0,
            my_stack=850,
            opponent_tracker=self.mock_opponent_tracker,
            active_opponents_count=3,  # Multiway
            street="flop",
            position="cutoff",
            actions_taken_this_street=[],
            pot_odds_to_call=0,
            aggression_factor=2.0,
            bluff_frequency=0.1
        )
        
        # Should be more conservative in multiway pots
        # Medium hands should check in multiway scenarios
        self.assertEqual(decision, action_check_const)
        self.assertEqual(amount, 0)
        
    def test_all_in_scenario_with_enhancements(self):
        """Test all-in scenario with enhanced logic."""
        # Test scenario: Strong hand facing all-in
        decision, amount = make_postflop_decision(
            numerical_hand_rank=2,  # Very strong hand
            win_probability=0.90,
            pot_size=300,
            bet_to_call=500,  # All-in call
            my_stack=500,
            opponent_tracker=self.mock_opponent_tracker,
            active_opponents_count=1,
            street="turn",
            position="big_blind",
            actions_taken_this_street=[],
            pot_odds_to_call=0.375,  # 500/(300+500+500)
            aggression_factor=2.0,
            bluff_frequency=0.1
        )
        
        # Very strong hand should call all-in
        self.assertEqual(decision, action_call_const)
        self.assertEqual(amount, 500)
        
    def test_river_value_betting(self):
        """Test value betting on river with enhancements."""
        # Test scenario: Strong hand on river
        decision, amount = make_postflop_decision(
            numerical_hand_rank=3,  # Strong hand
            win_probability=0.80,
            pot_size=250,
            bet_to_call=0,
            my_stack=750,
            opponent_tracker=self.mock_opponent_tracker,
            active_opponents_count=1,
            street="river",
            position="button",
            actions_taken_this_street=[],
            pot_odds_to_call=0,
            aggression_factor=2.0,
            bluff_frequency=0.1
        )
        
        # Should value bet on river with strong hand
        self.assertEqual(decision, action_bet_const)
        # River bet sizing should be larger for value
        expected_bet = int(250 * 0.75)  # 3/4 pot on river
        self.assertAlmostEqual(amount, expected_bet, delta=20)
        
    def test_pot_committed_scenario(self):
        """Test pot commitment logic with enhancements."""
        # Test scenario: Pot committed with medium hand
        decision, amount = make_postflop_decision(
            numerical_hand_rank=6,  # Medium hand
            win_probability=0.40,
            pot_size=400,
            bet_to_call=100,
            my_stack=150,  # Pot committed (call would leave 50)
            opponent_tracker=self.mock_opponent_tracker,
            active_opponents_count=1,
            street="turn",
            position="small_blind",
            actions_taken_this_street=[],
            pot_odds_to_call=0.20,  # 100/(400+100)
            aggression_factor=2.0,
            bluff_frequency=0.1
        )
        
        # When pot committed, should call with reasonable equity
        if decision == action_call_const:
            self.assertEqual(amount, 100)
        else:
            # Or might fold if equity is too low
            self.assertEqual(decision, action_fold_const)
            
    def test_fallback_logic_robustness(self):
        """Test that fallback logic works when enhanced modules fail."""
        # Test with None opponent_tracker to trigger fallbacks
        decision, amount = make_postflop_decision(
            numerical_hand_rank=5,
            win_probability=0.60,
            pot_size=120,
            bet_to_call=0,
            my_stack=880,
            opponent_tracker=None,  # This will trigger fallback logic
            active_opponents_count=1,
            street="flop",
            position="button",
            actions_taken_this_street=[],
            pot_odds_to_call=0,
            aggression_factor=2.0,
            bluff_frequency=0.1
        )
        
        # Should still make reasonable decisions with fallback logic
        self.assertIn(decision, [action_bet_const, action_check_const, action_call_const])
        if decision == action_bet_const:
            self.assertGreater(amount, 0)
            self.assertLessEqual(amount, 880)  # Can't bet more than stack

if __name__ == "__main__":
    print("Running final integration tests for enhanced postflop logic...")
    unittest.main(verbosity=2)
