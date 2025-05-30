#!/usr/bin/env py
"""
Improved comprehensive test script for the enhanced poker bot decision engine.
Tests Turn scenarios with proper betting situations.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from html_parser import PokerPageParser
from decision_engine import DecisionEngine, ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE
from hand_evaluator import HandEvaluator
import unittest

class TestTurnPokerScenarios(unittest.TestCase):
    def setUp(self):
        """Set up the test environment for each test method."""
        self.hand_evaluator = HandEvaluator()
        self.decision_engine = DecisionEngine(big_blind=0.02, small_blind=0.01)

    def test_scenario_4_flush_draw_reasonable_bet_on_turn(self):
        """Test Scenario 4: Flush Draw on Turn, facing a reasonable bet"""
        my_player_4 = {
            'hole_cards': ['Ah', 'Kh'],
            'cards': ['Ah', 'Kh'],
            'stack': '15.00',
            'bet': '0.50',
            'chips': 15.00,
            'current_bet': 0.50,
            'is_active': True,
            'is_my_player': True,
            'has_turn': True,
            'hand_evaluation': (0, "Flush Draw", [14, 13])
        }
        table_data_4 = {
            'community_cards': ['Qh', '7h', '2s', 'Jd'],
            'pot_size': '6.00',
            'current_bet_level': 2.00,
            'game_stage': 'Turn'
        }
        all_players_4 = [
            my_player_4,
            {'chips': 20.0, 'current_bet': 2.00, 'is_active': True, 'bet': '2.00'}
        ]
        action, amount = self.decision_engine.make_decision(my_player_4, table_data_4, all_players_4)
        print(f"Scenario 4 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_CALL, "Scenario 4: Should call with a flush draw facing a reasonable bet.")
        bet_to_call_expected = table_data_4['current_bet_level'] - my_player_4['current_bet']
        self.assertEqual(amount, bet_to_call_expected, "Scenario 4: Call amount should be the bet faced.")

    def test_scenario_8_medium_strength_hand_turn_facing_check(self):
        """Test Scenario 8: Medium strength hand (e.g. Second Pair) on Turn, facing a check"""
        my_player_8 = {
            'hole_cards': ['Ks', 'Qd'],
            'cards': ['Ks', 'Qd'],
            'stack': '17.50',
            'bet': '0.00',
            'chips': 17.50,
            'current_bet': 0.00,
            'is_active': True,
            'is_my_player': True,
            'has_turn': True,
            'hand_evaluation': (2, "Pair of Queens", [12, 13])
        }
        table_data_8 = {
            'community_cards': ['As', 'Qh', '7c', '2d'],
            'pot_size': '3.50',
            'current_bet_level': 0.00,
            'game_stage': 'Turn'
        }
        all_players_8 = [
            my_player_8,
            {'chips': 15.0, 'current_bet': 0.00, 'is_active': True, 'bet': '0.00'}
        ]
        action, amount = self.decision_engine.make_decision(my_player_8, table_data_8, all_players_8)
        print(f"Scenario 8 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_RAISE, "Scenario 8: Should bet with second pair on the turn when checked to.")
        self.assertGreater(amount, 0, "Scenario 8: Bet amount should be greater than 0.")

    def test_scenario_11_turn_made_straight_opponent_checks(self):
        """Test Scenario 11: Turn, made a straight, opponent checks"""
        my_player_11 = {
            'hole_cards': ['8h', '7d'],
            'cards': ['8h', '7d'],
            'stack': '16.00',
            'bet': '0.00',
            'chips': 16.00,
            'current_bet': 0.00,
            'is_active': True,
            'is_my_player': True,
            'has_turn': True,
            'hand_evaluation': (4, "Straight", [10, 9, 8, 7, 6])
        }
        table_data_11 = {
            'community_cards': ['Ts', '9c', '6h', 'Jd'],
            'pot_size': '4.50',
            'current_bet_level': 0.00,
            'game_stage': 'Turn'
        }
        all_players_11 = [
            my_player_11,
            {'chips': 15.0, 'current_bet': 0.00, 'is_active': True, 'bet': '0.00'}
        ]
        action, amount = self.decision_engine.make_decision(my_player_11, table_data_11, all_players_11)
        print(f"Scenario 11 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_CHECK, "Scenario 11: Should bet for value with a straight when checked to on turn.")
        if action == ACTION_CHECK:
            self.assertEqual(amount, 0, "Scenario 11: Check amount should be 0.")
        elif action == ACTION_RAISE:
            self.assertGreater(amount, 0, "Scenario 11: Value bet amount should be greater than 0.")

    def test_scenario_15_turn_strong_combo_draw_vs_bet(self):
        """Test Scenario 15: Turn, strong combo draw (flush + straight), facing a reasonable bet"""
        my_player_15 = {
            'hole_cards': ['Ah', 'Kh'],
            'cards': ['Ah', 'Kh'],
            'stack': '18.00',
            'bet': '0.00',
            'chips': 18.00,
            'current_bet': 0.00,
            'is_active': True,
            'is_my_player': True,
            'has_turn': True,
            'hand_evaluation': (0, "Flush Draw + Gutshot", [14, 13])
        }
        table_data_15 = {
            'community_cards': ['Qh', 'Jh', '7s', '2d'],
            'pot_size': '7.00',
            'current_bet_level': 3.00,
            'game_stage': 'Turn'
        }
        all_players_15 = [
            my_player_15,
            {'chips': 25.0, 'current_bet': 3.00, 'is_active': True, 'bet': '3.00'}
        ]
        action, amount = self.decision_engine.make_decision(my_player_15, table_data_15, all_players_15)
        print(f"Scenario 15 Decision: {action}, {amount}")
        self.assertIn(action, [ACTION_CALL, ACTION_RAISE], "Scenario 15: Should at least call with a strong combo draw.")
        if action == ACTION_CALL:
            bet_to_call_expected = table_data_15['current_bet_level'] - my_player_15['current_bet']
            self.assertAlmostEqual(amount, bet_to_call_expected, places=7, msg="Scenario 15: Call amount should be correct.")
        elif action == ACTION_RAISE:
            self.assertGreater(amount, table_data_15['current_bet_level'], "Scenario 15: Raise amount should be greater than current bet.")

    def test_scenario_18_turn_overbet_bluff_opportunity(self):
        """Test Scenario 18: Turn, Hero missed flush draw (Ace high), board is scary, opponent checks. Opportunity for overbet bluff."""
        my_player_18 = {
            'hole_cards': ['Ah', 'Kh'], 'cards': ['Ah', 'Kh'], 'stack': '15.00', 'bet': '0.00',
            'chips': 15.00, 'current_bet': 0.00, 'is_active': True, 'is_my_player': True, 'has_turn': True,
            'hand_evaluation': (1, "High Card Ace", [14])
        }
        table_data_18 = {
            'community_cards': ['Qd', 'Jd', '2s', '3c'],
            'pot_size': '6.00',
            'current_bet_level': 0.00,
            'game_stage': 'Turn'
        }
        all_players_18 = [
            my_player_18,
            {'name': 'Opponent', 'chips': 15.00, 'current_bet': 0.00, 'is_active': True, 'bet': '0.00'}
        ]
        action, amount = self.decision_engine.make_decision(my_player_18, table_data_18, all_players_18)
        print(f"Scenario 18 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_RAISE, "Scenario 18: Should consider an overbet bluff.")
        self.assertGreater(amount, float(table_data_18['pot_size']), "Scenario 18: Overbet bluff amount should be greater than pot size.")

    def test_scenario_22_turn_check_raise_strong_made_hand(self):
        """Test Scenario 22: Turn, Hero has Two Pair (T9s on Th 9c 2d Ks), checks, opponent bets, Hero check-raises."""
        my_player_22 = {
            'hole_cards': ['Ts', '9s'], 'cards': ['Ts', '9s'], 'stack': '16.00', 'bet': '0.00',
            'chips': 16.00, 'current_bet': 0.00, 'is_active': True, 'is_my_player': True, 'has_turn': True,
            'hand_evaluation': (3, "Two Pair, Tens and Nines", [10, 10, 9, 9, 13])
        }
        table_data_22 = {
            'community_cards': ['Th', '9c', '2d', 'Ks'], 'pot_size': '5.00',
            'current_bet_level': 2.50,
            'game_stage': 'Turn'
        }
        all_players_22 = [
            my_player_22,
            {'name': 'Opponent', 'chips': 17.50, 'current_bet': 2.50, 'is_active': True, 'bet': '2.50'}
        ]
        action, amount = self.decision_engine.make_decision(my_player_22, table_data_22, all_players_22)
        print(f"Scenario 22 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_RAISE, "Scenario 22: Should check-raise with two pair on the turn.")
        self.assertGreater(amount, table_data_22['current_bet_level'], "Scenario 22: Check-raise amount must be > opponent's bet.")
        self.assertGreaterEqual(amount, table_data_22['current_bet_level'] * 2.5, "Scenario 22: Check-raise size substantial.")

    def test_scenario_26_turn_semibluff_raise_combo_draw(self):
        """Test Scenario 26: Turn, Hero has 8s7s on 6s5sKd2c (Flush Draw + OESD), opponent bets, Hero semi-bluff raises."""
        my_player_26 = {
            'hole_cards': ['8s', '7s'], 'cards': ['8s', '7s'], 'stack': '15.00', 'bet': '0.00',
            'chips': 15.00, 'current_bet': 0.00, 'is_active': True, 'is_my_player': True, 'has_turn': True,
            'hand_evaluation': (0, "Flush Draw + OESD", [8, 7])
        }
        table_data_26 = {
            'community_cards': ['6s', '5s', 'Kd', '2c'], 'pot_size': '7.00',
            'current_bet_level': 3.00,
            'game_stage': 'Turn'
        }
        all_players_26 = [
            my_player_26,
            {'name': 'Opponent', 'chips': 17.00, 'current_bet': 3.00, 'is_active': True, 'bet': '3.00'}
        ]
        action, amount = self.decision_engine.make_decision(my_player_26, table_data_26, all_players_26)
        print(f"Scenario 26 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_RAISE, "Scenario 26: Should semi-bluff raise with a strong combo draw.")
        self.assertGreater(amount, table_data_26['current_bet_level'], "Scenario 26: Semi-bluff raise amount must be > opponent's bet.")

    def test_scenario_30_turn_probe_bet_after_pfr_checks_back_flop(self):
        """Test Scenario 30: Turn, PFR checked back flop. Hero (BB) has mid pair (T9 on QT2 flop, turn 4) and probe bets turn."""
        my_player_30 = {
            'hole_cards': ['Ts', '9d'], 'cards': ['Ts', '9d'], 'stack': '17.00', 'bet': '0.00',
            'chips': 17.00, 'current_bet': 0.00, 'is_active': True, 'is_my_player': True, 'has_turn': True,
            'hand_evaluation': (2, "Pair of Tens", [10, 9])
        }
        table_data_30 = {
            'community_cards': ['Qh', 'Tc', '2s', '4d'],
            'pot_size': '1.20',
            'current_bet_level': 0.00,
            'game_stage': 'Turn'
        }
        all_players_30 = [
            my_player_30,
            {'name': 'PFR', 'chips': 17.00, 'current_bet': 0.00, 'is_active': True, 'bet': '0.00'}
        ]
        action, amount = self.decision_engine.make_decision(my_player_30, table_data_30, all_players_30)
        print(f"Scenario 30 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_RAISE, "Scenario 30: Should probe bet turn with medium strength hand after PFR checked flop.")
        self.assertGreater(amount, 0, "Scenario 30: Probe bet amount should be positive.")
        self.assertGreaterEqual(amount, float(table_data_30['pot_size']) * 0.4, "Scenario 30: Probe bet size reasonable lower bound.")
        self.assertLessEqual(amount, float(table_data_30['pot_size']) * 0.75, "Scenario 30: Probe bet size reasonable upper bound.")

if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
