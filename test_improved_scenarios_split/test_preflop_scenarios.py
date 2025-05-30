#!/usr/bin/env py
"""
Improved comprehensive test script for the enhanced poker bot decision engine.
Tests Preflop scenarios with proper betting situations.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from html_parser import PokerPageParser
from decision_engine import DecisionEngine, ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE
from hand_evaluator import HandEvaluator
import unittest

class TestPreflopPokerScenarios(unittest.TestCase):
    def setUp(self):
        """Set up the test environment for each test method."""
        self.hand_evaluator = HandEvaluator()
        self.decision_engine = DecisionEngine(big_blind=0.02, small_blind=0.01)

    def test_scenario_1_pocket_aces_preflop_facing_raise(self):
        """Test Scenario 1: Pocket Aces Preflop - facing a raise"""
        my_player_1 = {
            'hole_cards': ['As', 'Ah'],
            'cards': ['As', 'Ah'],
            'stack': '14.96',
            'bet': '0.02',
            'chips': 14.96,
            'current_bet': 0.02,
            'is_active': True,
            'is_my_player': True,
            'has_turn': True,
            'hand_evaluation': (2, "Pair of Aces", [14, 14])
        }
        table_data_1 = {
            'community_cards': [],
            'pot_size': '0.13',
            'current_bet_level': 0.08,
            'game_stage': 'Preflop'
        }
        all_players_1 = [
            my_player_1,
            {'chips': 10.0, 'current_bet': 0.08, 'is_active': True, 'bet': '0.08'},
            {'chips': 8.5, 'current_bet': 0.01, 'is_active': True, 'bet': '0.01'}
        ]
        
        action, amount = self.decision_engine.make_decision(my_player_1, table_data_1, all_players_1)
        print(f"Scenario 1 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_RAISE, "Scenario 1: Should raise with pocket aces vs raise.")
        self.assertGreater(amount, table_data_1['current_bet_level'], "Scenario 1: Raise amount should be greater than current bet.")

    def test_scenario_6_marginal_hand_preflop_facing_3bet(self):
        """Test Scenario 6: Marginal Hand (e.g., KJs) Preflop, facing a 3-bet"""
        my_player_6 = {
            'hole_cards': ['Ks', 'Js'],
            'cards': ['Ks', 'Js'],
            'stack': '9.80',
            'bet': '0.08', 
            'chips': 9.80, 
            'current_bet': 0.08,
            'is_active': True,
            'is_my_player': True,
            'has_turn': True,
            'hand_evaluation': (0, "Suited Connectors", [13, 11])
        }
        table_data_6 = {
            'community_cards': [],
            'pot_size': '0.43',
            'current_bet_level': 0.24,
            'game_stage': 'Preflop'
        }
        all_players_6 = [
            my_player_6,
            {'chips': 10.0, 'current_bet': 0.08, 'is_active': False, 'bet': '0.08'}, 
            {'chips': 12.0, 'current_bet': 0.24, 'is_active': True, 'bet': '0.24'}
        ]
        
        action, amount = self.decision_engine.make_decision(my_player_6, table_data_6, all_players_6)
        print(f"Scenario 6 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_CALL, "Scenario 6: Should fold KJs to a preflop 3-bet in this context.")
        if action == ACTION_CALL:
            bet_to_call_expected = table_data_6['current_bet_level'] - my_player_6['current_bet']
            self.assertAlmostEqual(amount, bet_to_call_expected, places=7, msg="Scenario 6: Call amount should be the bet faced.")
        elif action == ACTION_FOLD:
            self.assertEqual(amount, 0, "Scenario 6: Fold amount should be 0.")

    def test_scenario_10_preflop_bb_vs_minraise_speculative_hand(self):
        """Test Scenario 10: Preflop, BB, speculative hand (76s) vs min-raise"""
        my_player_10 = {
            'hole_cards': ['7s', '6s'],
            'cards': ['7s', '6s'],
            'stack': '9.98',
            'bet': '0.02',
            'chips': 9.98,
            'current_bet': 0.02,
            'is_active': True,
            'is_my_player': True,
            'has_turn': True,
            'hand_evaluation': (0, "Suited Connectors", [7, 6])
        }
        table_data_10 = {
            'community_cards': [],
            'pot_size': '0.07',
            'current_bet_level': 0.04,
            'game_stage': 'Preflop'
        }
        all_players_10 = [
            {'chips': 10.0, 'current_bet': 0.01, 'is_active': False, 'bet': '0.01'}, 
            my_player_10,
            {'chips': 10.0, 'current_bet': 0.04, 'is_active': True, 'bet': '0.04'}
        ]
        action, amount = self.decision_engine.make_decision(my_player_10, table_data_10, all_players_10)
        print(f"Scenario 10 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_CALL, "Scenario 10: Should call with 76s in BB vs min-raise.")
        bet_to_call_expected = table_data_10['current_bet_level'] - my_player_10['current_bet']
        self.assertAlmostEqual(amount, bet_to_call_expected, places=7, msg="Scenario 10: Call amount should be correct.")

    def test_scenario_13_preflop_small_pocket_pair_vs_raise_and_call(self):
        """Test Scenario 13: Preflop, small pocket pair (44), facing raise and call (set mining odds)"""
        my_player_13 = {
            'hole_cards': ['4s', '4h'],
            'cards': ['4s', '4h'],
            'stack': '19.80', 
            'bet': '0.00', 
            'chips': 19.80,
            'current_bet': 0.00,
            'is_active': True,
            'is_my_player': True,
            'has_turn': True,
            'hand_evaluation': (2, "Pair of Fours", [4, 4])
        }
        table_data_13 = {
            'community_cards': [],
            'pot_size': '0.19',
            'current_bet_level': 0.08,
            'game_stage': 'Preflop'
        }
        all_players_13 = [
            {'chips': 20.0, 'current_bet': 0.01, 'is_active': True, 'bet': '0.01'}, 
            {'chips': 20.0, 'current_bet': 0.02, 'is_active': True, 'bet': '0.02'}, 
            {'chips': 20.0, 'current_bet': 0.08, 'is_active': True, 'bet': '0.08'}, 
            {'chips': 20.0, 'current_bet': 0.08, 'is_active': True, 'bet': '0.08'}, 
            my_player_13
        ]
        table_data_13['pot_size'] = str(sum(p['current_bet'] for p in all_players_13 if p != my_player_13) + my_player_13.get('current_bet',0))

        action, amount = self.decision_engine.make_decision(my_player_13, table_data_13, all_players_13)
        print(f"Scenario 13 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_CALL, "Scenario 13: Should call with 44 for set mining multiway.")
        bet_to_call_expected = table_data_13['current_bet_level'] - my_player_13['current_bet']
        self.assertAlmostEqual(amount, bet_to_call_expected, places=7, msg="Scenario 13: Call amount should be correct.")

    def test_scenario_16_preflop_squeeze_opportunity(self):
        """Test Scenario 16: Preflop, AQs on Button, UTG raises, MP calls. Hero should consider a 3-bet (squeeze)."""
        my_player_16 = {
            'hole_cards': ['As', 'Qs'], 'cards': ['As', 'Qs'], 'stack': '19.50', 'bet': '0.00', 
            'chips': 19.50, 'current_bet': 0.00, 'is_active': True, 'is_my_player': True, 'has_turn': True,
            'hand_evaluation': (0, "High Card Ace Queen Suited", [14, 12])
        }
        table_data_16 = {
            'community_cards': [], 'pot_size': '0.15', 
            'current_bet_level': 0.06, 
            'game_stage': 'Preflop'
        }
        all_players_16 = [
            {'name': 'SB', 'chips': 9.99, 'current_bet': 0.01, 'is_active': False, 'bet': '0.01'}, 
            {'name': 'BB', 'chips': 9.98, 'current_bet': 0.02, 'is_active': True, 'bet': '0.02'}, 
            {'name': 'UTG', 'chips': 19.94, 'current_bet': 0.06, 'is_active': True, 'bet': '0.06'}, 
            {'name': 'MP', 'chips': 19.94, 'current_bet': 0.06, 'is_active': True, 'bet': '0.06'}, 
            my_player_16
        ]
        table_data_16['pot_size'] = str(float(all_players_16[0]['bet']) + float(all_players_16[1]['bet']) + float(all_players_16[2]['bet']) + float(all_players_16[3]['bet']))

        action, amount = self.decision_engine.make_decision(my_player_16, table_data_16, all_players_16)
        print(f"Scenario 16 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_RAISE, "Scenario 16: Should 3-bet (squeeze) with AQs in position.")
        self.assertGreater(amount, table_data_16['current_bet_level'], "Scenario 16: Squeeze amount should be greater than current bet level.")

    def test_scenario_20_preflop_defend_bb_vs_steal(self):
        """Test Scenario 20: Preflop, Hero in BB with KTo, Button min-raises, SB folds."""
        my_player_20 = {
            'hole_cards': ['Kh', 'Td'], 'cards': ['Kh', 'Td'], 'stack': '9.98', 'bet': '0.02', 
            'chips': 9.98, 'current_bet': 0.02, 'is_active': True, 'is_my_player': True, 'has_turn': True,
            'hand_evaluation': (0, "High Card King Ten", [13, 10])
        }
        table_data_20 = {
            'community_cards': [], 'pot_size': '0.07', 
            'current_bet_level': 0.04, 
            'game_stage': 'Preflop'
        }
        all_players_20 = [
            {'name': 'SB', 'chips': 9.99, 'current_bet': 0.01, 'is_active': False, 'bet': '0.01'}, 
            my_player_20, 
            {'name': 'BTN', 'chips': 9.96, 'current_bet': 0.04, 'is_active': True, 'bet': '0.04'}
        ]
        action, amount = self.decision_engine.make_decision(my_player_20, table_data_20, all_players_20)
        print(f"Scenario 20 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_CALL, "Scenario 20: Should call with KTo in BB vs BTN min-raise for pot odds.")
        bet_to_call_expected = table_data_20['current_bet_level'] - my_player_20['current_bet']
        self.assertAlmostEqual(amount, bet_to_call_expected, places=7, msg="Scenario 20: Call amount should be correct.")

    def test_scenario_24_preflop_limp_reraise_trap_aa(self):
        """Test Scenario 24: Preflop, Hero limps with AA, CO raises, Hero re-raises."""
        my_player_24 = {
            'hole_cards': ['Ad', 'Ac'], 'cards': ['Ad', 'Ac'], 'stack': '19.98', 'bet': '0.02', 
            'chips': 19.98, 'current_bet': 0.02, 'is_active': True, 'is_my_player': True, 'has_turn': True,
            'hand_evaluation': (2, "Pair of Aces", [14, 14])
        }
        table_data_24 = {
            'community_cards': [], 'pot_size': '0.12', 
            'current_bet_level': 0.08, 
            'game_stage': 'Preflop'
        }
        all_players_24 = [
            {'name': 'BB', 'chips': 9.98, 'current_bet': 0.02, 'is_active': True, 'bet': '0.02'}, 
            my_player_24, 
            {'name': 'CO', 'chips': 19.92, 'current_bet': 0.08, 'is_active': True, 'bet': '0.08'}
        ]
        table_data_24['pot_size'] = str(float(all_players_24[0]['bet']) + float(my_player_24['bet']) + float(all_players_24[2]['bet']))

        action, amount = self.decision_engine.make_decision(my_player_24, table_data_24, all_players_24)
        print(f"Scenario 24 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_RAISE, "Scenario 24: Should re-raise (trap) with AA after limping.")
        self.assertGreater(amount, table_data_24['current_bet_level'], "Scenario 24: Re-raise amount must be > CO's bet.")
        self.assertGreaterEqual(amount, table_data_24['current_bet_level'] * 3, "Scenario 24: Re-raise should be substantial.")

    def test_scenario_28_preflop_all_in_short_stack(self):
        """Test Scenario 28: Preflop, Hero short stack (10BB) with AJs, UTG raises 2.5BB, Hero shoves."""
        my_player_28 = {
            'hole_cards': ['As', 'Js'], 'cards': ['As', 'Js'], 'stack': '1.00', 
            'bet': '0.00', 
            'chips': 1.00, 'current_bet': 0.00, 'is_active': True, 'is_my_player': True, 'has_turn': True,
            'hand_evaluation': (0, "Ace Jack Suited", [14, 11])
        }
        table_data_28 = {
            'community_cards': [], 'pot_size': '0.40', 
            'current_bet_level': 0.25, 
            'game_stage': 'Preflop'
        }
        all_players_28 = [
            {'name': 'SB', 'chips': 9.95, 'current_bet': 0.05, 'is_active': True, 'bet': '0.05'},
            {'name': 'BB', 'chips': 9.90, 'current_bet': 0.10, 'is_active': True, 'bet': '0.10'},
            {'name': 'UTG', 'chips': 9.75, 'current_bet': 0.25, 'is_active': True, 'bet': '0.25'}, 
            my_player_28
        ]
        action, amount = self.decision_engine.make_decision(my_player_28, table_data_28, all_players_28)
        print(f"Scenario 28 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_RAISE, "Scenario 28: Should shove AJs with 10BB stack facing a raise.")
        self.assertAlmostEqual(amount, float(my_player_28['stack']), places=7, msg="Scenario 28: Shove amount should be the entire stack.")

if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
