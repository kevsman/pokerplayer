#!/usr/bin/env py
"""
Improved comprehensive test script for the enhanced poker bot decision engine.
Tests various scenarios with proper betting situations.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from html_parser import PokerPageParser
from decision_engine import DecisionEngine, ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE
from hand_evaluator import HandEvaluator
import unittest

class TestImprovedPokerScenarios(unittest.TestCase):
    def setUp(self):
        """Set up the test environment for each test method."""
        self.hand_evaluator = HandEvaluator()
        self.decision_engine = DecisionEngine(big_blind=0.02, small_blind=0.01)
        # Note: The original script's DecisionEngine was initialized without hand_evaluator.
        # The DecisionEngine class seems to initialize its own EquityCalculator if one isn't provided.
        # For these tests, we are providing specific hand_evaluation, so direct equity calc might be bypassed.

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
            'hand_evaluation': (2, "Pair of Aces", [14, 14]) # Win prob will be derived if not explicitly set for decision logic
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
        print(f"Scenario 1 Decision: {action}, {amount}") # Keep for debugging during transition
        self.assertEqual(action, ACTION_RAISE, "Scenario 1: Should raise with pocket aces vs raise.")
        # Expected raise amount might be tricky to assert exactly without knowing the precise raise sizing logic
        # For now, let's assert it's a positive amount, greater than the current bet level.
        self.assertGreater(amount, table_data_1['current_bet_level'], "Scenario 1: Raise amount should be greater than current bet.")
        # A more specific assertion could be: self.assertAlmostEqual(amount, EXPECTED_3_BET_AMOUNT, places=2)

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
            'hand_evaluation': (1, "High Card", [7, 2]) # Explicitly setting low hand rank
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
        
        # For this test, we need to ensure win_probability is low.
        # The DecisionEngine's make_decision method calculates win_probability internally.
        # If the 'hand_evaluation' tuple doesn't directly set win_prob for the logic,
        # the internal equity calculator will run. Given 7s2h vs a random hand on KdQcJs,
        # actual win_prob would be very low. The output showed 1.000, which is the issue to fix.
        # For now, the test will reflect the *current* (potentially flawed) behavior if win_prob isn't correctly low.
        
        action, amount = self.decision_engine.make_decision(my_player_2, table_data_2, all_players_2)
        print(f"Scenario 2 Decision: {action}, {amount}") # Keep for debugging
        
        # Based on previous output, the bot decided ('check', 0) due to win_prob being 1.000
        # A correct decision with low win_prob should be FOLD.
        # We will assert FOLD, anticipating the win_prob issue will be fixed.
        # If it's not fixed, this test will fail, correctly indicating the problem.
        self.assertEqual(action, ACTION_FOLD, "Scenario 2: Should fold with 7-2o vs large flop bet.")
        self.assertEqual(amount, 0, "Scenario 2: Fold amount should be 0.")

    def test_scenario_3_strong_hand_river_facing_bet(self):
        """Test Scenario 3: Very strong hand (Full House) on the river, facing a bet"""
        my_player_3 = {
            'hole_cards': ['Ah', 'Kd'],
            'cards': ['Ah', 'Kd'], # For hand_eval, though equity uses hole_cards
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
            'current_bet_level': 5.00, # Opponent bets 5 into 15 (pot was 10 before their bet)
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

    def test_scenario_4_flush_draw_reasonable_bet_on_turn(self):
        """Test Scenario 4: Flush Draw on Turn, facing a reasonable bet"""
        my_player_4 = {
            'hole_cards': ['Ah', 'Kh'], # Nut flush draw
            'cards': ['Ah', 'Kh'],
            'stack': '15.00',
            'bet': '0.50',
            'chips': 15.00,
            'current_bet': 0.50,
            'is_active': True,
            'is_my_player': True,
            'has_turn': True,
            'hand_evaluation': (0, "Flush Draw", [14, 13]) # Placeholder, win_prob is key
        }
        table_data_4 = {
            'community_cards': ['Qh', '7h', '2s', 'Jd'], # Two hearts on board
            'pot_size': '6.00',
            'current_bet_level': 2.00, # Opponent bets 2 into 6 (pot was 4)
            'game_stage': 'Turn'
        }
        all_players_4 = [
            my_player_4,
            {'chips': 20.0, 'current_bet': 2.00, 'is_active': True, 'bet': '2.00'}
        ]
        action, amount = self.decision_engine.make_decision(my_player_4, table_data_4, all_players_4)
        print(f"Scenario 4 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_CALL, "Scenario 4: Should call with a flush draw facing a reasonable bet.")
        # Amount assertion should be flexible to the actual bet_to_call
        bet_to_call_expected = table_data_4['current_bet_level'] - my_player_4['current_bet']
        self.assertEqual(amount, bet_to_call_expected, "Scenario 4: Call amount should be the bet faced.")

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
            'community_cards': ['Ac', '5h', '2c', '7d', '8s'], # Player has Top Pair (Aces)
            'pot_size': '5.00',
            'current_bet_level': 0.00, # Can check
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
        # A more specific assertion could be: self.assertAlmostEqual(amount, POT_SIZE * 0.5, places=2)

    def test_scenario_6_marginal_hand_preflop_facing_3bet(self):
        """Test Scenario 6: Marginal Hand (e.g., KJs) Preflop, facing a 3-bet"""
        my_player_6 = {
            'hole_cards': ['Ks', 'Js'], # Suited King-Jack
            'cards': ['Ks', 'Js'],
            'stack': '9.80', # Initial stack 10, posted 0.02, opponent raised to 0.08, we called, now facing 0.24
            'bet': '0.08', # Our previous call
            'chips': 9.80, 
            'current_bet': 0.08,
            'is_active': True,
            'is_my_player': True,
            'has_turn': True,
            'hand_evaluation': (0, "Suited Connectors", [13, 11]) # Placeholder
        }
        table_data_6 = {
            'community_cards': [],
            'pot_size': '0.35', # SB (0.01) + BB (0.02) + P1_raise (0.08) + MyCall (0.08) + P2_3bet (0.24) = 0.43. Bet to call is 0.16. Pot before our action: 0.01+0.02+0.08+0.08+0.24 = 0.43. Current bet level is 0.24.
                               # Let's adjust pot to reflect state *before* our decision:
                               # Initial pot: SB (0.01) + BB (0.02) = 0.03
                               # Player A (Villain 1) raises to 0.08. Pot = 0.03 + 0.08 = 0.11
                               # Hero (MyPlayer) calls 0.08. Pot = 0.11 + 0.08 = 0.19
                               # Player B (Villain 2) 3-bets to 0.24. Pot = 0.19 + 0.24 = 0.43.
                               # Player A folds.
                               # Hero to act. Bet to call is 0.24 - 0.08 = 0.16.
                               # Pot size for decision: 0.43 (total in pot if we fold)
            'current_bet_level': 0.24, # Villain 2's 3-bet amount
            'game_stage': 'Preflop'
        }
        all_players_6 = [
            my_player_6,
            {'chips': 10.0, 'current_bet': 0.08, 'is_active': False, 'bet': '0.08'}, # Villain 1 (folded or already acted)
            {'chips': 12.0, 'current_bet': 0.24, 'is_active': True, 'bet': '0.24'}  # Villain 2 (3-bettor)
        ]
        
        # Original script expected FOLD. Bot decided RAISE. This is a key test for preflop logic.
        # KJs is often a fold to a 3-bet unless 3-bettor is very wide or stacks are deep.
        action, amount = self.decision_engine.make_decision(my_player_6, table_data_6, all_players_6)
        print(f"Scenario 6 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_FOLD, "Scenario 6: Should fold KJs to a preflop 3-bet in this context.")
        self.assertEqual(amount, 0, "Scenario 6: Fold amount should be 0.")

    def test_scenario_7_bluff_opportunity_river(self):
        """Test Scenario 7: Bluff opportunity on River with missed draw"""
        my_player_7 = {
            'hole_cards': ['Ah', 'Kh'], # Missed flush draw
            'cards': ['Ah', 'Kh'],
            'stack': '12.00',
            'bet': '0.00',
            'chips': 12.00,
            'current_bet': 0.00,
            'is_active': True,
            'is_my_player': True,
            'has_turn': True,
            'hand_evaluation': (1, "High Card Ace", [14]) # Missed draw
        }
        table_data_7 = {
            'community_cards': ['Qd', '7s', '2c', 'Js', 'Td'], # No flush
            'pot_size': '5.00', 
            'current_bet_level': 0.00, # Can check or bet
            'game_stage': 'River'
        }
        all_players_7 = [
            my_player_7,
            {'chips': 10.0, 'current_bet': 0.00, 'is_active': True, 'bet': '0.00'} # Opponent also checked
        ]
        # Original script expected a bluff (RAISE). Bot decided CHECK.
        # This depends on bluffing logic which considers win_prob (should be low).
        action, amount = self.decision_engine.make_decision(my_player_7, table_data_7, all_players_7)
        print(f"Scenario 7 Decision: {action}, {amount}")
        # Asserting a bluff (raise) if win_prob is correctly low and bluff logic is sound.
        # If it checks, it might be that bluff conditions aren't met or win_prob is still off.
        self.assertEqual(action, ACTION_RAISE, "Scenario 7: Should consider bluffing with a missed draw on the river.")
        self.assertGreater(amount, 0, "Scenario 7: Bluff bet amount should be greater than 0.")


    def test_scenario_8_medium_strength_hand_turn_facing_check(self):
        """Test Scenario 8: Medium strength hand (e.g. Second Pair) on Turn, facing a check"""
        my_player_8 = {
            'hole_cards': ['Ks', 'Qd'], # King-Queen offsuit
            'cards': ['Ks', 'Qd'],
            'stack': '17.50',
            'bet': '0.00',
            'chips': 17.50,
            'current_bet': 0.00,
            'is_active': True,
            'is_my_player': True,
            'has_turn': True,
            'hand_evaluation': (2, "Pair of Queens", [12, 13]) # Second pair
        }
        table_data_8 = {
            'community_cards': ['As', 'Qh', '7c', '2d'], # Ace on board, we have pair of Queens
            'pot_size': '3.50',
            'current_bet_level': 0.00, # Opponent checked
            'game_stage': 'Turn'
        }
        all_players_8 = [
            my_player_8,
            {'chips': 15.0, 'current_bet': 0.00, 'is_active': True, 'bet': '0.00'} # Opponent checked
        ]
        # Original script expected a BET (raise from 0). Bot decided CHECK.
        # With a medium strength hand and opponent checking, a bet for value/protection is often correct.
        action, amount = self.decision_engine.make_decision(my_player_8, table_data_8, all_players_8)
        print(f"Scenario 8 Decision: {action}, {amount}")
        self.assertEqual(action, ACTION_RAISE, "Scenario 8: Should bet with second pair on the turn when checked to.")
        self.assertGreater(amount, 0, "Scenario 8: Bet amount should be greater than 0.")

# Remove the old test_improved_scenarios function and its direct call
# def test_improved_scenarios():
#     ... (old content) ...

if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False) # exit=False for interactive environments
