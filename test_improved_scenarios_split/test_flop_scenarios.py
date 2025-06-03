#!/usr/bin/env py
"""
Improved comprehensive test script for the enhanced poker bot decision engine.
Tests Flop scenarios with proper betting situations.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from html_parser_original import PokerPageParser
from decision_engine import DecisionEngine, ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE
from hand_evaluator import HandEvaluator
import unittest

class TestFlopPokerScenarios(unittest.TestCase):
    def setUp(self):
        """Set up the test environment for each test method."""
        self.hand_evaluator = HandEvaluator()
        self.decision_engine = DecisionEngine(big_blind=0.02, small_blind=0.01)

    def test_scenario_2_weak_hand_facing_large_bet_on_flop(self):
        """Test Scenario 2: Weak hand (7-2 offsuit) facing large bet on flop"""
        my_player_2 = {
            'hole_cards': ['7s', '2h'],
            'cards': ['7s', '2h'],
            'stack': '10.00',
            'bet': '0.50', 
            'chips': 10.00,
            'current_bet': 0.50,
            'is_active': True,
            'is_my_player': True,
            'has_turn': True,
            'hand_evaluation': (1, "High Card", [7, 2])
        }
        table_data_2 = {
            'community_cards': ['Kd', 'Qc', 'Js'],
            'pot_size': '7.50',
            'current_bet_level': 5.00,
            'game_stage': 'Flop'
        }
        all_players_2 = [
            my_player_2,
            {'chips': 15.0, 'current_bet': 5.00, 'is_active': True, 'bet': '5.00'}
        ]
        
        action, amount = self.decision_engine.make_decision(my_player_2, table_data_2, all_players_2)
        print(f"Scenario 2 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_FOLD, "Scenario 2: Should fold with 7-2o vs large flop bet.")
        self.assertEqual(amount, 0, "Scenario 2: Fold amount should be 0.")

    def test_scenario_12_flop_bottom_pair_vs_cbet(self):
        """Test Scenario 12: Flop, bottom pair, facing a continuation bet"""
        my_player_12 = {
            'hole_cards': ['Ah', '5s'],
            'cards': ['Ah', '5s'],
            'stack': '14.50',
            'bet': '0.00',
            'chips': 14.50,
            'current_bet': 0.00,
            'is_active': True,
            'is_my_player': True,
            'has_turn': True,
            'hand_evaluation': (2, "Pair of Fives", [5, 14])
        }
        table_data_12 = {
            'community_cards': ['Kd', '8c', '5h'],
            'pot_size': '1.50',
            'current_bet_level': 0.75,
            'game_stage': 'Flop'
        }
        all_players_12 = [
            my_player_12,
            {'chips': 18.0, 'current_bet': 0.75, 'is_active': True, 'bet': '0.75'}
        ]
        action, amount = self.decision_engine.make_decision(my_player_12, table_data_12, all_players_12)
        print(f"Scenario 12 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_CALL, "Scenario 12: Should generally fold bottom pair to a flop c-bet.")
        if action == ACTION_CALL:
            bet_to_call_expected = table_data_12['current_bet_level'] - my_player_12['current_bet']
            self.assertAlmostEqual(amount, bet_to_call_expected, places=7, msg="Scenario 12: Call amount should be correct.")
        elif action == ACTION_FOLD:
            self.assertEqual(amount, 0, "Scenario 12: Fold amount should be 0.")

    def test_scenario_17_flop_set_vs_multiple_opponents_in_position(self):
        """Test Scenario 17: Flop, Hero has Set of 7s, in position, checked to by two opponents."""
        my_player_17 = {
            'hole_cards': ['7h', '7d'], 'cards': ['7h', '7d'], 'stack': '18.00', 'bet': '0.00',
            'chips': 18.00, 'current_bet': 0.00, 'is_active': True, 'is_my_player': True, 'has_turn': True,
            'hand_evaluation': (5, "Set of Sevens", [7, 7, 7, 13, 2])
        }
        table_data_17 = {
            'community_cards': ['7s', 'Kh', '2d'], 'pot_size': '1.50',
            'current_bet_level': 0.00,
            'game_stage': 'Flop'
        }
        all_players_17 = [
            {'name': 'Player1', 'chips': 19.00, 'current_bet': 0.00, 'is_active': True, 'bet': '0.00'},
            {'name': 'Player2', 'chips': 19.00, 'current_bet': 0.00, 'is_active': True, 'bet': '0.00'},
            my_player_17
        ]
        action, amount = self.decision_engine.make_decision(my_player_17, table_data_17, all_players_17)
        print(f"Scenario 17 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_RAISE, "Scenario 17: Should bet with a set when checked to multiway.")
        self.assertGreater(amount, 0, "Scenario 17: Bet amount should be greater than 0.")

    def test_scenario_21_flop_cbet_air_dry_board(self):
        """Test Scenario 21: Flop, Hero (preflop raiser) misses with AQs on J72r, c-bets as bluff."""
        my_player_21 = {
            'hole_cards': ['As', 'Qh'], 'cards': ['As', 'Qh'], 'stack': '19.00', 'bet': '0.00',
            'chips': 19.00, 'current_bet': 0.00, 'is_active': True, 'is_my_player': True, 'has_turn': True,
            'hand_evaluation': (1, "High Card Ace Queen", [14, 12])
        }
        table_data_21 = {
            'community_cards': ['Js', '7d', '2c'], 'pot_size': '0.75',
            'current_bet_level': 0.00,
            'game_stage': 'Flop'
        }
        all_players_21 = [
            {'name': 'Opponent', 'chips': 19.00, 'current_bet': 0.00, 'is_active': True, 'bet': '0.00'},
            my_player_21
        ]
        action, amount = self.decision_engine.make_decision(my_player_21, table_data_21, all_players_21)
        print(f"Scenario 21 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_RAISE, "Scenario 21: Should c-bet with air on a dry board as PFR.")
        self.assertGreater(amount, 0, "Scenario 21: C-bet amount should be positive.")
        self.assertLessEqual(amount, float(table_data_21['pot_size']) * 0.7, "Scenario 21: C-bet size reasonable.")

    def test_scenario_25_flop_float_oop_with_gutshot(self):
        """Test Scenario 25: Flop, Hero OOP with T9s (gutshot to J on KQ2r), calls opponent's c-bet."""
        my_player_25 = {
            'hole_cards': ['Ts', '9s'], 'cards': ['Ts', '9s'], 'stack': '18.00', 'bet': '0.00',
            'chips': 18.00, 'current_bet': 0.00, 'is_active': True, 'is_my_player': True, 'has_turn': True,
            'hand_evaluation': (0, "Gutshot Straight Draw", [10, 9])
        }
        table_data_25 = {
            'community_cards': ['Ks', 'Qd', '2c'], 'pot_size': '1.00',
            'current_bet_level': 0.50,
            'game_stage': 'Flop'
        }
        all_players_25 = [
            my_player_25,
            {'name': 'Opponent', 'chips': 17.50, 'current_bet': 0.50, 'is_active': True, 'bet': '0.50'}
        ]
        action, amount = self.decision_engine.make_decision(my_player_25, table_data_25, all_players_25)
        print(f"Scenario 25 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_CALL, "Scenario 25: Should call (float) with gutshot OOP facing a c-bet, good implied odds.")
        bet_to_call_expected = table_data_25['current_bet_level'] - my_player_25['current_bet']
        self.assertAlmostEqual(amount, bet_to_call_expected, places=7, msg="Scenario 25: Call amount should be correct.")

    def test_scenario_29_flop_donk_bet_bottom_pair(self):
        """Test Scenario 29: Flop, Hero (BB caller) hits bottom pair (76s on K87r) and donk bets."""
        my_player_29 = {
            'hole_cards': ['7s', '6s'], 'cards': ['7s', '6s'], 'stack': '9.70', 'bet': '0.00',
            'chips': 9.70, 'current_bet': 0.00, 'is_active': True, 'is_my_player': True, 'has_turn': True,
            'hand_evaluation': (2, "Pair of Sevens", [7, 6])
        }
        table_data_29 = {
            'community_cards': ['Kh', '8c', '7d'], 'pot_size': '0.60',
            'current_bet_level': 0.00,
            'game_stage': 'Flop'
        }
        all_players_29 = [
            my_player_29,
            {'name': 'PFR', 'chips': 9.70, 'current_bet': 0.00, 'is_active': True, 'bet': '0.00'}
        ]
        action, amount = self.decision_engine.make_decision(my_player_29, table_data_29, all_players_29)
        print(f"Scenario 29 Decision: {action}, {amount}")
        self.assertIn(action, [ACTION_RAISE, ACTION_CHECK], "Scenario 29: Could donk bet or check with bottom pair OOP.")
        if action == ACTION_RAISE:
            self.assertGreater(amount, 0, "Scenario 29: Donk bet amount should be positive.")
            self.assertLessEqual(amount, float(table_data_29['pot_size']) * 0.75, "Scenario 29: Donk bet size reasonable.")
        elif action == ACTION_CHECK:
            self.assertEqual(amount, 0, "Scenario 29: Check amount should be 0.")

if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
