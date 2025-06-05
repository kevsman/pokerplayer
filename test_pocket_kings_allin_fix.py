#!/usr/bin/env python3
"""
Test script to validate the fix for pocket kings folding to all-in bets preflop.
This test reproduces the exact scenario from the poker bot log where KK should call an all-in.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from decision_engine import DecisionEngine, ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE
from hand_evaluator import HandEvaluator
import unittest

class TestPocketKingsAllInFix(unittest.TestCase):
    def setUp(self):
        """Set up the test environment for each test method."""
        self.hand_evaluator = HandEvaluator()
        self.decision_engine = DecisionEngine(big_blind=0.02, small_blind=0.01)

    def test_pocket_kings_should_call_allin_after_raising(self):
        """
        Test the exact scenario from the log: Hero has KK, raises twice, 
        then faces an all-in bet. Should call, not fold.
        
        From log: Hero has K♣K♥, raises to €0.12, re-raises to €0.84, 
        then faces all-in of €2.59 (entire remaining stack).
        """
        # Simulate the final decision point where bot has already raised twice
        # and now faces an all-in for the remaining stack
        my_player = {
            'hole_cards': ['Kc', 'Kh'],  # Pocket Kings
            'cards': ['Kc', 'Kh'],
            'stack': '2.59',  # Remaining stack from log
            'bet': '0.84',    # Already committed €0.84
            'chips': 2.59,
            'current_bet': 0.84,
            'is_active': True,
            'is_my_player': True,
            'has_turn': True,
            'hand_evaluation': (2, "Pair of Kings", [13, 13]),
            'position': 'UTG'  # Position from log
        }
        
        table_data = {
            'community_cards': [],
            'pot_size': '3.43',  # Pot from log (€0.84 + €2.59)
            'current_bet_level': 2.59,  # Opponent's all-in amount
            'game_stage': 'Preflop'
        }
        
        # Opponent who went all-in
        all_players = [
            my_player,
            {
                'chips': 0.0,  # All-in
                'current_bet': 2.59,  # All-in amount
                'is_active': True, 
                'bet': '2.59',
                'name': 'Opponent'
            }
        ]
        
        action, amount = self.decision_engine.make_decision(my_player, table_data, all_players)
        
        print(f"Pocket Kings vs All-in Decision: {action}, Amount: {amount}")
        print(f"Stack: {my_player['stack']}, Bet to call: {2.59 - 0.84}")
        
        # KK should CALL the all-in, not fold
        self.assertEqual(action, ACTION_CALL, 
                        "Pocket Kings should call an all-in preflop, not fold!")
        
        # Should call for the remaining stack amount
        expected_call_amount = 2.59 - 0.84  # All-in amount minus already committed
        self.assertAlmostEqual(amount, expected_call_amount, places=2,
                              msg=f"Call amount should be {expected_call_amount}")

    def test_pocket_kings_vs_smaller_allin(self):
        """
        Test pocket kings against a smaller all-in (not full stack).
        Should definitely call in this scenario too.
        """
        my_player = {
            'hole_cards': ['Ks', 'Kd'],
            'cards': ['Ks', 'Kd'],
            'stack': '10.00',
            'bet': '0.12',
            'chips': 10.00,
            'current_bet': 0.12,
            'is_active': True,
            'is_my_player': True,
            'has_turn': True,
            'hand_evaluation': (2, "Pair of Kings", [13, 13]),
            'position': 'BTN'
        }
        
        table_data = {
            'community_cards': [],
            'pot_size': '1.62',  # Small pot
            'current_bet_level': 1.50,  # Smaller all-in
            'game_stage': 'Preflop'
        }
        
        all_players = [
            my_player,
            {
                'chips': 0.0,
                'current_bet': 1.50,
                'is_active': True,
                'bet': '1.50'
            }
        ]
        
        action, amount = self.decision_engine.make_decision(my_player, table_data, all_players)
        
        print(f"KK vs Smaller All-in Decision: {action}, Amount: {amount}")
        
        # Should call or raise (but definitely not fold)
        self.assertIn(action, [ACTION_CALL, ACTION_RAISE], 
                     "KK should call or raise against smaller all-in, never fold")
        
        if action == ACTION_CALL:
            expected_call = 1.50 - 0.12
            self.assertAlmostEqual(amount, expected_call, places=2)

    def test_pocket_aces_vs_allin_should_also_call(self):
        """
        Test that pocket aces also call all-ins (should work with same logic).
        """
        my_player = {
            'hole_cards': ['As', 'Ah'],
            'cards': ['As', 'Ah'],
            'stack': '5.00',
            'bet': '0.20',
            'chips': 5.00,
            'current_bet': 0.20,
            'is_active': True,
            'is_my_player': True,
            'has_turn': True,
            'hand_evaluation': (2, "Pair of Aces", [14, 14]),
            'position': 'MP'
        }
        
        table_data = {
            'community_cards': [],
            'pot_size': '5.20',
            'current_bet_level': 5.00,  # Big all-in
            'game_stage': 'Preflop'
        }
        
        all_players = [
            my_player,
            {
                'chips': 0.0,
                'current_bet': 5.00,
                'is_active': True,
                'bet': '5.00'
            }
        ]
        
        action, amount = self.decision_engine.make_decision(my_player, table_data, all_players)
        
        print(f"AA vs Big All-in Decision: {action}, Amount: {amount}")
        
        # Aces should definitely call
        self.assertEqual(action, ACTION_CALL, "Pocket Aces must call all-ins preflop")
        
        expected_call = 5.00 - 0.20
        self.assertAlmostEqual(amount, expected_call, places=2)

    def test_pocket_queens_vs_allin_should_call(self):
        """
        Test that pocket queens also call all-ins (premium pair logic).
        """
        my_player = {
            'hole_cards': ['Qs', 'Qh'],
            'cards': ['Qs', 'Qh'],
            'stack': '8.00',
            'bet': '0.50',
            'chips': 8.00,
            'current_bet': 0.50,
            'is_active': True,
            'is_my_player': True,
            'has_turn': True,
            'hand_evaluation': (2, "Pair of Queens", [12, 12]),
            'position': 'CO'
        }
        
        table_data = {
            'community_cards': [],
            'pot_size': '4.50',
            'current_bet_level': 4.00,
            'game_stage': 'Preflop'
        }
        
        all_players = [
            my_player,
            {
                'chips': 0.0,
                'current_bet': 4.00,
                'is_active': True,
                'bet': '4.00'
            }
        ]
        
        action, amount = self.decision_engine.make_decision(my_player, table_data, all_players)
        
        print(f"QQ vs All-in Decision: {action}, Amount: {amount}")
        
        # Queens should call (premium pair)
        self.assertEqual(action, ACTION_CALL, "Pocket Queens should call all-ins preflop")
        
        expected_call = 4.00 - 0.50
        self.assertAlmostEqual(amount, expected_call, places=2)

if __name__ == '__main__':
    print("Testing Pocket Kings All-In Fix...")
    print("=" * 50)
    
    unittest.main(verbosity=2)
