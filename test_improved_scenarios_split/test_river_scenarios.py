#!/usr/bin/env py
"""
Improved comprehensive test script for the enhanced poker bot decision engine.
Tests River scenarios with proper betting situations.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from html_parser import PokerPageParser
from decision_engine import DecisionEngine, ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE
from hand_evaluator import HandEvaluator
import unittest

class TestRiverPokerScenarios(unittest.TestCase):
    def setUp(self):
        """Set up the test environment for each test method."""
        self.hand_evaluator = HandEvaluator()
        self.decision_engine = DecisionEngine(big_blind=0.02, small_blind=0.01)

    def test_scenario_3_strong_hand_river_facing_bet(self):
        """Test Scenario 3: Very strong hand (Full House) on the river, facing a bet"""
        my_player_3 = {
            'hole_cards': ['Ah', 'Kd'],
            'cards': ['Ah', 'Kd'],
            'stack': '20.00',
            'bet': '1.00',
            'chips': 20.00,
            'current_bet': 1.00,
            'is_active': True,
            'is_my_player': True,
            'has_turn': True,
            'hand_evaluation': (7, "Full House, Aces full of Kings", [14, 14, 14, 13, 13])
        }
        table_data_3 = {
            'community_cards': ['As', 'Ac', 'Kh', 'Ks', '2d'],
            'pot_size': '15.00',
            'current_bet_level': 5.00,
            'game_stage': 'River'
        }
        all_players_3 = [
            my_player_3,
            {'chips': 25.0, 'current_bet': 5.00, 'is_active': True, 'bet': '5.00'}
        ]
        action, amount = self.decision_engine.make_decision(my_player_3, table_data_3, all_players_3)
        print(f"Scenario 3 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_RAISE, "Scenario 3: Should raise with a full house on the river facing a bet.")
        self.assertGreater(amount, table_data_3['current_bet_level'], "Scenario 3: Raise amount should be greater than opponent's bet.")

    def test_scenario_5_top_pair_river_can_check_value_bet(self):
        """Test Scenario 5: Top Pair on River, can check, should value bet"""
        my_player_5 = {
            'hole_cards': ['Ad', 'Ts'],
            'cards': ['Ad', 'Ts'],
            'stack': '18.00',
            'bet': '0.00',
            'chips': 18.00,
            'current_bet': 0.00,
            'is_active': True,
            'is_my_player': True,
            'has_turn': True,
            'hand_evaluation': (2, "Pair of Aces", [14, 10]) 
        }
        table_data_5 = {
            'community_cards': ['Ac', '5h', '2c', '7d', '8s'],
            'pot_size': '5.00',
            'current_bet_level': 0.00,
            'game_stage': 'River'
        }
        all_players_5 = [
            my_player_5,
            {'chips': 10.0, 'current_bet': 0.00, 'is_active': True, 'bet': '0.00'}
        ]
        action, amount = self.decision_engine.make_decision(my_player_5, table_data_5, all_players_5)
        print(f"Scenario 5 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_RAISE, "Scenario 5: Should bet (raise from 0) for value with top pair on river.")
        self.assertGreater(amount, 0, "Scenario 5: Value bet amount should be greater than 0.")

    def test_scenario_7_bluff_opportunity_river(self):
        """Test Scenario 7: Bluff opportunity on River with missed draw"""
        my_player_7 = {
            'hole_cards': ['Ah', 'Kh'],
            'cards': ['Ah', 'Kh'],
            'stack': '12.00',
            'bet': '0.00',
            'chips': 12.00,
            'current_bet': 0.00,
            'is_active': True,
            'is_my_player': True,
            'has_turn': True,
            'hand_evaluation': (1, "High Card Ace", [14])
        }
        table_data_7 = {
            'community_cards': ['Qd', '7s', '2c', 'Js', 'Td'],
            'pot_size': '5.00', 
            'current_bet_level': 0.00,
            'game_stage': 'River'
        }
        all_players_7 = [
            my_player_7,
            {'chips': 10.0, 'current_bet': 0.00, 'is_active': True, 'bet': '0.00'}
        ]
        action, amount = self.decision_engine.make_decision(my_player_7, table_data_7, all_players_7)
        print(f"Scenario 7 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_CHECK, "Scenario 7: Should consider bluffing with a missed draw on the river.")
        if action == ACTION_CHECK:
            self.assertEqual(amount, 0, "Scenario 7: Check amount should be 0.")
        elif action == ACTION_RAISE:
            self.assertGreater(amount, 0, "Scenario 7: Bluff bet amount should be greater than 0.")

    def test_scenario_9_river_bluff_catcher_small_bet(self):
        """Test Scenario 9: River, medium strength hand (bluff catcher), facing a small bet"""
        my_player_9 = {
            'hole_cards': ['As', 'Ts'],
            'cards': ['As', 'Ts'],
            'stack': '15.00',
            'bet': '0.00',
            'chips': 15.00,
            'current_bet': 0.00,
            'is_active': True,
            'is_my_player': True,
            'has_turn': True,
            'hand_evaluation': (2, "Pair of Tens", [10, 14])
        }
        table_data_9 = {
            'community_cards': ['Kd', 'Tc', '7h', '2s', '3d'],
            'pot_size': '8.00',
            'current_bet_level': 2.00,
            'game_stage': 'River'
        }
        all_players_9 = [
            my_player_9,
            {'chips': 20.0, 'current_bet': 2.00, 'is_active': True, 'bet': '2.00'}
        ]
        action, amount = self.decision_engine.make_decision(my_player_9, table_data_9, all_players_9)
        print(f"Scenario 9 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_CALL, "Scenario 9: Should call with a bluff catcher facing a small river bet.")
        bet_to_call_expected = table_data_9['current_bet_level'] - my_player_9['current_bet']
        self.assertEqual(amount, bet_to_call_expected, "Scenario 9: Call amount should be the bet faced.")

    def test_scenario_14_river_missed_draw_vs_large_bet(self):
        """Test Scenario 14: River, missed all draws, opponent bets large"""
        my_player_14 = {
            'hole_cards': ['Ah', 'Kh'],
            'cards': ['Ah', 'Kh'],
            'stack': '10.00',
            'bet': '0.00',
            'chips': 10.00,
            'current_bet': 0.00,
            'is_active': True,
            'is_my_player': True,
            'has_turn': True,
            'hand_evaluation': (1, "High Card Ace", [14])
        }
        table_data_14 = {
            'community_cards': ['Qd', '7s', '2c', 'Js', 'Td'],
            'pot_size': '5.00',
            'current_bet_level': 4.00,
            'game_stage': 'River'
        }
        all_players_14 = [
            my_player_14,
            {'chips': 15.0, 'current_bet': 4.00, 'is_active': True, 'bet': '4.00'}
        ]
        action, amount = self.decision_engine.make_decision(my_player_14, table_data_14, all_players_14)
        print(f"Scenario 14 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_FOLD, "Scenario 14: Should fold with a missed draw facing a large river bet.")
        self.assertEqual(amount, 0, "Scenario 14: Fold amount should be 0.")

    def test_scenario_19_river_thin_value_bet(self):
        """Test Scenario 19: River, Hero has Pair of Kings (KJs), opponent checks. Thin value bet opportunity."""
        my_player_19 = {
            'hole_cards': ['Ks', 'Js'], 'cards': ['Ks', 'Js'], 'stack': '12.00', 'bet': '0.00',
            'chips': 12.00, 'current_bet': 0.00, 'is_active': True, 'is_my_player': True, 'has_turn': True,
            'hand_evaluation': (2, "Pair of Kings", [13, 11]) 
        }
        table_data_19 = {
            'community_cards': ['Kc', 'Ts', '7d', '2h', '4s'], 'pot_size': '8.00',
            'current_bet_level': 0.00,
            'game_stage': 'River'
        }
        all_players_19 = [
            my_player_19,
            {'name': 'Opponent', 'chips': 10.00, 'current_bet': 0.00, 'is_active': True, 'bet': '0.00'}
        ]
        action, amount = self.decision_engine.make_decision(my_player_19, table_data_19, all_players_19)
        print(f"Scenario 19 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_RAISE, "Scenario 19: Should make a thin value bet with top pair.")
        self.assertGreater(amount, 0, "Scenario 19: Value bet amount should be positive.")
        self.assertLessEqual(amount, float(table_data_19['pot_size']) * 0.5, "Scenario 19: Thin value bet should be reasonably sized (e.g., <= 1/2 pot).")

    def test_scenario_23_river_blocking_bet_oop(self):
        """Test Scenario 23: River, Hero OOP with medium pair (QJ on AQ725), wants to see showdown cheaply."""
        my_player_23 = {
            'hole_cards': ['Qs', 'Js'], 'cards': ['Qs', 'Js'], 'stack': '10.00', 'bet': '0.00',
            'chips': 10.00, 'current_bet': 0.00, 'is_active': True, 'is_my_player': True, 'has_turn': True,
            'hand_evaluation': (2, "Pair of Queens", [12, 11]) 
        }
        table_data_23 = {
            'community_cards': ['Ah', 'Qc', '7d', '2c', '5h'], 'pot_size': '9.00',
            'current_bet_level': 0.00,
            'game_stage': 'River'
        }
        all_players_23 = [
            my_player_23,
            {'name': 'Opponent', 'chips': 12.00, 'current_bet': 0.00, 'is_active': True, 'bet': '0.00'}
        ]
        action, amount = self.decision_engine.make_decision(my_player_23, table_data_23, all_players_23)
        print(f"Scenario 23 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_RAISE, "Scenario 23: Should make a small blocking bet.")
        self.assertGreater(amount, 0, "Scenario 23: Bet amount must be positive.")
        self.assertLessEqual(amount, float(table_data_23['pot_size']) * 0.35, "Scenario 23: Blocking bet should be small.")

    def test_scenario_27_river_cooler_nut_flush_vs_king_flush(self):
        """Test Scenario 27: River, Hero AdKd (Nut Flush on Td7d2dQd4d), opponent (KQdd - King Flush) bets, Hero re-raises for value."""
        my_player_27 = {
            'hole_cards': ['Ad', 'Kd'], 'cards': ['Ad', 'Kd'], 'stack': '25.00', 'bet': '0.00',
            'chips': 25.00, 'current_bet': 0.00, 'is_active': True, 'is_my_player': True, 'has_turn': True,
            'hand_evaluation': (6, "Ace High Flush", [14, 13, 10, 7, 4])
        }
        table_data_27 = {
            'community_cards': ['Td', '7d', '2d', 'Qs', '4d'], 'pot_size': '10.00',
            'current_bet_level': 5.00,
            'game_stage': 'River'
        }
        all_players_27 = [
            my_player_27,
            {'name': 'Opponent', 'chips': 30.00, 'current_bet': 5.00, 'is_active': True, 'bet': '5.00', 'hole_cards': ['Kh', 'Qd']}
        ]
        action, amount = self.decision_engine.make_decision(my_player_27, table_data_27, all_players_27)
        print(f"Scenario 27 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_RAISE, "Scenario 27: Should re-raise for value with nut flush vs likely second best.")
        self.assertGreater(amount, table_data_27['current_bet_level'], "Scenario 27: Re-raise amount must be > opponent's bet.")
        self.assertGreaterEqual(amount, table_data_27['current_bet_level'] * 2.5, "Scenario 27: Re-raise should be substantial.")

if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
