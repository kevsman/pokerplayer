import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from poker_bot import PokerBot
from decision_engine import ACTION_CALL, ACTION_RAISE, ACTION_CHECK, ACTION_FOLD, ACTION_BET # Import actions
from hand_evaluator import HandEvaluator # For creating accurate hand evaluations in tests

class TestFullGameScenarios(unittest.TestCase):
    def setUp(self):
        self.bot = PokerBot(big_blind=0.02, small_blind=0.01)
        self.hand_evaluator = HandEvaluator() # Initialize hand evaluator
        # self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'examples')) # No longer needed for this test method

    # def _run_test_html_file(self, file_path): # This method can be kept for other tests or removed if all tests adopt simulation
    #     full_file_path = os.path.join(self.base_dir, file_path)
    #     if not os.path.exists(full_file_path):
    #         print(f"Warning: Test HTML file not found: {full_file_path}")
    #         self.skipTest(f"HTML file {file_path} not found") 
    #         return None, None 
    #     action, amount = self.bot.run_test_file(full_file_path) 
    #     return action, amount

    def _create_mock_my_player_data(self, cards, stack, current_bet, bet_to_call, has_turn, game_stage, community_cards=None, is_all_in_call_available=False, available_actions=None, position='UTG', name='TestBot'):
        if community_cards is None:
            community_cards = []
        if available_actions is None:
            available_actions = ['call', 'raise', 'fold']
        
        hand_evaluation_tuple = (0, "N/A", []) 
        preflop_strength = 0.0
        if cards and len(cards) == 2:
            preflop_strength = self.hand_evaluator.evaluate_preflop_strength(cards)
            # For the hand_evaluation tuple in preflop, we can use a simplified description or the strength score
            # The decision engine primarily uses preflop_strength for preflop, and hand_evaluation for postflop.
            hand_evaluation_tuple = (preflop_strength, f"Preflop Strength: {preflop_strength:.2f}", cards)

        if cards and game_stage != 'PREFLOP': # Postflop evaluation
            hand_evaluation_tuple = self.hand_evaluator.calculate_best_hand(cards, community_cards)
        

        return {
            'cards': cards,
            'stack': stack,
            'current_bet': current_bet, # Changed from 'bet' to 'current_bet'
            'bet_to_call': bet_to_call,
            'has_turn': has_turn,
            'is_my_player': True,
            'seat': '1', # Assuming bot is always seat 1 in these mocks for simplicity
            'name': name,
            'is_all_in_call_available': is_all_in_call_available,
            'available_actions': available_actions,
            'hand_evaluation': hand_evaluation_tuple, # Contains strength/rank, description, tiebreakers
            'id': 'player1', 
            'isActive': True, 
            'isFolded': False,
            'position': position, # Added position
            'preflop_strength': preflop_strength # Explicitly add preflop strength
        }

    def _create_mock_table_data(self, community_cards, pot_size, game_stage, dealer_position='2', hand_id='test_hand_123', street=None):
        # Ensure street and game_stage are consistent. Prefer 'street' as used by DecisionEngine.
        current_street = street if street else game_stage 
        return {
            'community_cards': community_cards,
            'pot_size': pot_size,
            'street': current_street, # Changed from 'game_stage' to 'street'
            'dealer_position': dealer_position,
            'hand_id': hand_id,
            'small_blind': self.bot.small_blind, 
            'big_blind': self.bot.big_blind, 
            'board': community_cards, 
            # 'game_stage': current_street # Keep for compatibility if other parts use it, but 'street' is primary
        }

    def _create_mock_opponent_data(self, seat, stack, current_bet, has_turn=False, is_active_player=True, is_folded=False, position='BTN'): # Renamed is_active to is_active_player for clarity
        return {
            'seat': seat,
            'name': f'Opponent{seat}',
            'stack': stack,
            'current_bet': current_bet, # Changed from 'bet' to 'current_bet'
            'has_turn': has_turn,
            'is_my_player': False,
            'cards': [], 
            'has_hidden_cards': True,
            'hand_evaluation': (0, "N/A", []),
            'id': f'player{seat}', 
            'is_active_player': is_active_player, # Changed from 'isActive' to 'is_active_player'
            'isFolded': is_folded, 
            'position': position, # Added position
        }

    def test_example_full_hand_scenario_simulated(self):
        """Simulate a full hand scenario using direct object inputs."""

        # --- Preflop --- 
        # Player is Small Blind (seat 1) with Ad Kh. BB is seat 2.
        # My initial current_bet is SB (0.01), Opponent initial current_bet is BB (0.02)
        # Pot = 0.03. My stack = 1.00 - 0.01 = 0.99. Opponent stack = 2.00 - 0.02 = 1.98
        # Bet to call for me is BB - SB = 0.01
        my_player_preflop = self._create_mock_my_player_data(
            cards=['Ad', 'Kh'], stack=0.99, current_bet=0.01, bet_to_call=0.01, has_turn=True, 
            game_stage='Pre-Flop', position='SB' # game_stage will be mapped to street, added position
        )
        table_preflop = self._create_mock_table_data(community_cards=[], pot_size=0.03, game_stage='Pre-Flop') # game_stage will be mapped to street
        opp1_preflop = self._create_mock_opponent_data(seat='2', stack=1.98, current_bet=0.02, position='BB') # BB
        all_players_preflop = [my_player_preflop, opp1_preflop]

        print("Simulating preflop (direct objects)... Bot has AdKh in SB")
        action, amount = self.bot.decision_engine.make_decision(my_player_preflop, table_preflop, all_players_preflop)
        
        self.assertIsNotNone(action, "Action should not be None preflop")
        # AKs is a strong hand, should at least call or raise. Let's assume a raise.
        self.assertEqual(action, ACTION_RAISE, f"Expected RAISE with AdKh preflop, got {action}")
        # Typical raise size might be 3-4x BB from SB. Pot is 0.03, BB is 0.02. Raise to ~0.06-0.08 total.
        # Amount returned by make_decision is the TOTAL bet amount for a raise.
        self.assertGreaterEqual(amount, 0.05, f"Raise amount {amount} too small for AdKh preflop") 
        self.assertLessEqual(amount, 0.10, f"Raise amount {amount} too large for AdKh preflop")
        print(f"Preflop action: {action}, Amount: {amount}")

        # Assume bot raises to 0.07 (amount = 0.07), opponent calls.
        # My new stack: 0.99 + 0.01 (SB back) - 0.07 = 0.93
        # Opponent new stack: 1.98 + 0.02 (BB back) - 0.07 = 1.93
        # Pot: 0.07 (my raise) + 0.07 (opponent call) = 0.14
        # My bet on flop is 0. Opponent bet on flop is 0. Bet to call is 0.
        current_pot = amount * 2 # Assuming opponent calls our raise
        my_stack_after_preflop = 0.99 - (amount - 0.01) # My stack - (my total preflop bet - my SB)
        opponent_stack_after_preflop = 1.98 - (amount - 0.02) # Opponent stack - (opponent total preflop call - their BB)

        # --- Flop --- 
        community_flop = ['Ac', 'Ks', 'Qh'] # Bot has top two pair
        my_player_flop = self._create_mock_my_player_data(
            cards=['Ad', 'Kh'], stack=my_stack_after_preflop, current_bet=0, bet_to_call=0, has_turn=True, 
            game_stage='Flop', community_cards=community_flop, position='SB'
        )
        table_flop = self._create_mock_table_data(community_cards=community_flop, pot_size=current_pot, game_stage='Flop')
        opp1_flop = self._create_mock_opponent_data(seat='2', stack=opponent_stack_after_preflop, current_bet=0, position='BB')
        all_players_flop = [my_player_flop, opp1_flop]

        print(f"Simulating flop (direct objects)... Pot: {current_pot:.2f}, My Stack: {my_stack_after_preflop:.2f}")
        action, amount = self.bot.decision_engine.make_decision(my_player_flop, table_flop, all_players_flop)
        
        self.assertIsNotNone(action, "Action should not be None on flop")
        # With top two pair, out of position, a bet is expected. 
        # DecisionEngine uses ACTION_BET for opening a round, ACTION_RAISE if facing a bet.
        self.assertEqual(action, ACTION_BET, f"Expected BET with top two pair on flop, got {action}")
        # Bet size could be 1/2 to 3/4 pot. Pot is current_pot.
        self.assertGreaterEqual(amount, current_pot * 0.4, f"Flop bet {amount} too small")
        self.assertLessEqual(amount, current_pot * 0.8, f"Flop bet {amount} too large")
        print(f"Flop action: {action}, Amount: {amount}")

        # Assume bot bets 0.10 (amount = 0.10), opponent calls.
        # My new stack: my_stack_after_preflop - 0.10
        # Opponent new stack: opponent_stack_after_preflop - 0.10
        # Pot: current_pot + 0.10 + 0.10
        my_stack_after_flop = my_stack_after_preflop - amount
        opponent_stack_after_flop = opponent_stack_after_preflop - amount
        current_pot += (amount * 2)

        # --- Turn --- 
        community_turn = community_flop + ['2s'] # No change to hand strength
        my_player_turn = self._create_mock_my_player_data(
            cards=['Ad', 'Kh'], stack=my_stack_after_flop, current_bet=0, bet_to_call=0, has_turn=True, 
            game_stage='Turn', community_cards=community_turn, position='SB'
        )
        table_turn = self._create_mock_table_data(community_cards=community_turn, pot_size=current_pot, game_stage='Turn')
        opp1_turn = self._create_mock_opponent_data(seat='2', stack=opponent_stack_after_flop, current_bet=0, position='BB')
        all_players_turn = [my_player_turn, opp1_turn]

        print(f"Simulating turn (direct objects)... Pot: {current_pot:.2f}, My Stack: {my_stack_after_flop:.2f}")
        action, amount = self.bot.decision_engine.make_decision(my_player_turn, table_turn, all_players_turn)

        self.assertIsNotNone(action, "Action should not be None on turn")
        # Continue betting with top two pair.
        self.assertEqual(action, ACTION_BET, f"Expected BET on turn, got {action}")
        self.assertGreaterEqual(amount, current_pot * 0.4)
        self.assertLessEqual(amount, current_pot * 0.8)
        print(f"Turn action: {action}, Amount: {amount}")

        # Assume bot bets 0.20 (amount = 0.20), opponent calls.
        my_stack_after_turn = my_stack_after_flop - amount
        opponent_stack_after_turn = opponent_stack_after_flop - amount
        current_pot += (amount * 2)

        # --- River ---
        community_river = community_turn + ['Js'] # Bot makes Broadway straight
        my_player_river = self._create_mock_my_player_data(
            cards=['Ad', 'Kh'], stack=my_stack_after_turn, current_bet=0, bet_to_call=0, has_turn=True, 
            game_stage='River', community_cards=community_river, position='SB'
        )
        table_river = self._create_mock_table_data(community_cards=community_river, pot_size=current_pot, game_stage='River')
        opp1_river = self._create_mock_opponent_data(seat='2', stack=opponent_stack_after_turn, current_bet=0, position='BB')
        all_players_river = [my_player_river, opp1_river]

        print(f"Simulating river (direct objects)... Pot: {current_pot:.2f}, My Stack: {my_stack_after_turn:.2f}")
        action, amount = self.bot.decision_engine.make_decision(my_player_river, table_river, all_players_river)
        
        self.assertIsNotNone(action, "Action should not be None on river")
        # Value bet the straight.
        self.assertEqual(action, ACTION_BET, f"Expected BET on river with a straight, got {action}")
        self.assertGreaterEqual(amount, current_pot * 0.4, "River bet too small for a straight")
        self.assertLessEqual(amount, current_pot * 0.8, "River bet too large for a straight")
        print(f"River action: {action}, Amount: {amount}")
        
    # Remove or comment out the old HTML-based test method
    # def test_example_full_hand_scenario(self):
    #     ...

if __name__ == '__main__':
    unittest.main()
