import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from poker_bot import PokerBot
from decision_engine import ACTION_CALL, ACTION_RAISE, ACTION_CHECK, ACTION_FOLD, ACTION_BET
from hand_evaluator import HandEvaluator

class TestFullGameScenarios(unittest.TestCase):
    def setUp(self):
        self.config = {
            'big_blind': 0.02,
            'small_blind': 0.01,
        }
        self.bot = PokerBot(config=self.config) # Pass config object
        self.hand_evaluator = HandEvaluator()

    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self.bot, 'close_logger') and callable(self.bot.close_logger):
            self.bot.close_logger()

    def _create_mock_my_player_data(self, hand, stack, current_bet, bet_to_call, has_turn, game_stage, community_cards=None, position='UTG', name='TestBot', win_probability=None):
        if community_cards is None: community_cards = []
        
        hand_evaluation_result = (0, "N/A", []) 
        preflop_strength = 0.0
        if hand and len(hand) == 2:
            # Simplified preflop strength for testing, actual preflop logic is more complex
            # For full game tests, win_probability might be more directly useful if known for the scenario
            preflop_strength = self.hand_evaluator.evaluate_preflop_strength(hand) 
            if game_stage == 'Pre-Flop':
                 hand_evaluation_result = (preflop_strength, f"Preflop Strength: {preflop_strength:.2f}", hand)
        
        if hand and game_stage != 'Pre-Flop' and community_cards:
            hand_evaluation_result = self.hand_evaluator.evaluate_hand(hand, community_cards)

        player_data = {
            'hand': hand, # Changed from 'cards'
            'stack': stack,
            'current_bet': current_bet,
            'bet_to_call': bet_to_call,
            'has_turn': has_turn,
            'is_my_player': True,
            'seat': '1',
            'name': name,
            'hand_evaluation': hand_evaluation_result, 
            'id': 'player1', 
            'isActive': True, 
            'isFolded': False,
            'position': position,
            'preflop_strength': preflop_strength,
            'available_actions': ['call', 'raise', 'fold', 'check', 'bet']
        }
        if win_probability is not None:
            player_data['win_probability'] = win_probability
        return player_data

    def _create_mock_table_data(self, community_cards, pot_size, game_stage, street=None):
        current_street = street if street else game_stage
        return {
            'community_cards': community_cards,
            'pot_size': pot_size,
            'street': current_street,
            'dealer_position': '2', 
            'hand_id': 'test_hand_123',
            'small_blind': self.config['small_blind'], 
            'big_blind': self.config['big_blind'], 
            'board': community_cards,
        }

    def _create_mock_opponent_data(self, seat, stack, current_bet, has_turn=False, is_active_player=True, is_folded=False, position='BTN', name=None, hand=None):
        opponent_name = name if name else f'Opponent{seat}'
        return {
            'seat': seat, 'name': opponent_name, 'stack': stack, 'current_bet': current_bet,
            'has_turn': has_turn, 'is_my_player': False,
            'hand': hand if hand else [], 'has_hidden_cards': not bool(hand),
            'hand_evaluation': (0, "N/A", []),
            'id': f'player{seat}', 'is_active_player': is_active_player,
            'isFolded': is_folded, 'position': position,
        }

    def _create_game_state(self, players, pot_size, community_cards, current_round, big_blind, small_blind, min_raise):
        processed_players = []
        for i, p_data_orig in enumerate(players):
            p_data = p_data_orig.copy()
            if 'id' not in p_data:
                p_data['id'] = f"player_gs_{i+1}_{p_data.get('name', 'unknown')}"
            if 'seat' not in p_data:
                p_data['seat'] = str(i + 1)
            if 'hand' not in p_data and 'cards' in p_data: # Map 'cards' to 'hand' for backward compatibility
                p_data['hand'] = p_data.pop('cards')
            elif 'hand' not in p_data:
                 p_data['hand'] = [] # Ensure hand key exists
            processed_players.append(p_data)

        return {
            "players": processed_players,
            "pot_size": pot_size,
            "community_cards": community_cards,
            "current_round": current_round,
            "big_blind": big_blind,
            "small_blind": small_blind,
            "min_raise": min_raise,
            "board": community_cards,
        }

    def test_example_full_hand_scenario_simulated(self):
        """Simulate a full hand scenario using direct object inputs."""
        my_player_index = 0 # Bot is the first player in the list for these scenarios

        # --- Preflop --- 
        my_player_preflop_obj = self._create_mock_my_player_data(
            hand=['Ad', 'Kh'], stack=0.99, current_bet=0.01, bet_to_call=0.01, has_turn=True, 
            game_stage='Pre-Flop', position='SB', win_probability=0.66 # Approx for AKs
        )
        opp1_preflop = self._create_mock_opponent_data(seat='2', stack=1.98, current_bet=0.02, position='BB')
        all_players_preflop = [my_player_preflop_obj, opp1_preflop]

        game_state_preflop = self._create_game_state(
            players=all_players_preflop,
            pot_size=0.03,
            community_cards=[],
            current_round="preflop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )

        print("Simulating preflop (direct objects)... Bot has AdKh in SB")
        action, amount = self.bot.decision_engine.make_decision(game_state_preflop, my_player_index)
        
        self.assertIsNotNone(action, "Action should not be None preflop")
        self.assertEqual(action, ACTION_RAISE, f"Expected RAISE with AdKh preflop, got {action}")
        self.assertGreaterEqual(amount, 0.05, f"Raise amount {amount} too small for AdKh preflop") 
        self.assertLessEqual(amount, 0.10, f"Raise amount {amount} too large for AdKh preflop")
        print(f"Preflop action: {action}, Amount: {amount}")

        # Assume bot raises to 0.07 (amount = 0.07), opponent calls.
        # Update player stacks and pot for the next street
        # Player making the action is game_state_preflop["players"][my_player_index]
        # Opponent is game_state_preflop["players"][1-my_player_index] (assuming 2 players)
        
        # Bot's total bet was 'amount', initial bet was SB (0.01). Additional amount = amount - 0.01
        # Opponent's total call was 'amount', initial bet was BB (0.02). Additional amount to call = amount - 0.02
        
        my_stack_after_preflop = my_player_preflop_obj['stack'] - (amount - my_player_preflop_obj['current_bet'])
        opponent_stack_after_preflop = opp1_preflop['stack'] - (amount - opp1_preflop['current_bet'])
        current_pot = game_state_preflop['pot_size'] + (amount - my_player_preflop_obj['current_bet']) + (amount - opp1_preflop['current_bet'])

        # --- Flop --- 
        community_flop = ['Ac', 'Ks', 'Qh'] # Bot has top two pair
        my_player_flop_obj = self._create_mock_my_player_data(
            hand=['Ad', 'Kh'], stack=my_stack_after_preflop, current_bet=0, bet_to_call=0, has_turn=True, 
            game_stage='Flop', community_cards=community_flop, position='SB', win_probability=0.85 # Example for top two
        )
        opp1_flop = self._create_mock_opponent_data(seat='2', stack=opponent_stack_after_preflop, current_bet=0, position='BB')
        all_players_flop = [my_player_flop_obj, opp1_flop]

        game_state_flop = self._create_game_state(
            players=all_players_flop,
            pot_size=current_pot,
            community_cards=community_flop,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )

        print(f"Simulating flop (direct objects)... Pot: {current_pot:.2f}, My Stack: {my_stack_after_preflop:.2f}")
        action, amount = self.bot.decision_engine.make_decision(game_state_flop, my_player_index)
        
        self.assertIsNotNone(action, "Action should not be None on flop")
        self.assertEqual(action, ACTION_BET, f"Expected BET with top two pair on flop, got {action}")
        self.assertGreaterEqual(amount, current_pot * 0.4, f"Flop bet {amount} too small")
        self.assertLessEqual(amount, current_pot * 0.8, f"Flop bet {amount} too large")
        print(f"Flop action: {action}, Amount: {amount}")

        # Assume bot bets 0.10 (amount = 0.10), opponent calls.
        my_stack_after_flop = my_stack_after_preflop - amount
        opponent_stack_after_flop = opponent_stack_after_preflop - amount
        current_pot += (amount * 2)

        # --- Turn --- 
        community_turn = community_flop + ['2s'] # No change to hand strength
        my_player_turn_obj = self._create_mock_my_player_data(
            hand=['Ad', 'Kh'], stack=my_stack_after_flop, current_bet=0, bet_to_call=0, has_turn=True, 
            game_stage='Turn', community_cards=community_turn, position='SB', win_probability=0.80 # Slight drop due to more cards
        )
        opp1_turn = self._create_mock_opponent_data(seat='2', stack=opponent_stack_after_flop, current_bet=0, position='BB')
        all_players_turn = [my_player_turn_obj, opp1_turn]

        game_state_turn = self._create_game_state(
            players=all_players_turn,
            pot_size=current_pot,
            community_cards=community_turn,
            current_round="turn",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )

        print(f"Simulating turn (direct objects)... Pot: {current_pot:.2f}, My Stack: {my_stack_after_flop:.2f}")
        action, amount = self.bot.decision_engine.make_decision(game_state_turn, my_player_index)

        self.assertIsNotNone(action, "Action should not be None on turn")
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
        my_player_river_obj = self._create_mock_my_player_data(
            hand=['Ad', 'Kh'], stack=my_stack_after_turn, current_bet=0, bet_to_call=0, has_turn=True, 
            game_stage='River', community_cards=community_river, position='SB', win_probability=1.0 # Nuts!
        )
        opp1_river = self._create_mock_opponent_data(seat='2', stack=opponent_stack_after_turn, current_bet=0, position='BB')
        all_players_river = [my_player_river_obj, opp1_river]

        game_state_river = self._create_game_state(
            players=all_players_river,
            pot_size=current_pot,
            community_cards=community_river,
            current_round="river",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )

        print(f"Simulating river (direct objects)... Pot: {current_pot:.2f}, My Stack: {my_stack_after_turn:.2f}")
        action, amount = self.bot.decision_engine.make_decision(game_state_river, my_player_index)
        
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
