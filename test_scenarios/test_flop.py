import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from poker_bot import PokerBot
from decision_engine import ACTION_CALL, ACTION_RAISE, ACTION_CHECK, ACTION_FOLD, ACTION_BET
from hand_evaluator import HandEvaluator

class TestFlopScenarios(unittest.TestCase):
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
        hand_evaluation_tuple = (0, "N/A", []) 
        preflop_strength = 0.0
        if hand and len(hand) == 2:
            preflop_strength = self.hand_evaluator.evaluate_preflop_strength(hand)
            if game_stage == 'Pre-Flop': # Use preflop strength for preflop hand_evaluation tuple
                 hand_evaluation_tuple = (preflop_strength, f"Preflop Strength: {preflop_strength:.2f}", hand)
        
        if hand and game_stage != 'Pre-Flop': # Postflop evaluation
            # Use evaluate_hand which returns a dict including rank_category
            hand_eval_dict = self.hand_evaluator.evaluate_hand(hand, community_cards)
            # Store the dict directly or convert to tuple if other parts of bot expect tuple
            # For now, let's assume decision_engine can handle the dict or we adapt it there.
            # The original TestFullGameScenarios used calculate_best_hand which returns a tuple.
            # Let's stick to the tuple for now if that's what the decision engine was tested with.
            hand_evaluation_tuple = (hand_eval_dict['rank_value'], hand_eval_dict['description'], hand_eval_dict['tie_breakers'])

        player_data = {
            'hand': hand, 'stack': stack, 'current_bet': current_bet, 'bet_to_call': bet_to_call,
            'has_turn': has_turn, 'is_my_player': True, 'seat': '1', 
            'name': name, 'hand_evaluation': hand_evaluation_tuple, 
            'id': 'player1', 'isActive': True, 'isFolded': False,
            'position': position, 'preflop_strength': preflop_strength,
            'available_actions': ['call', 'raise', 'fold', 'check', 'bet']
        }
        if win_probability is not None:
            player_data['win_probability'] = win_probability
        return player_data

    def _create_mock_table_data(self, community_cards, pot_size, game_stage, street=None):
        current_street = street if street else game_stage
        return {
            'community_cards': community_cards, 'pot_size': pot_size, 'street': current_street,
            'dealer_position': '2', 'hand_id': 'test_flop_hand',
            'small_blind': self.config['small_blind'], 
            'big_blind': self.config['big_blind'], 
            'board': community_cards,
        }

    def _create_mock_opponent_data(self, seat, stack, current_bet, has_turn=False, is_active_player=True, position='BTN', name=None, hand=None):
        opponent_name = name if name else f'Opponent{seat}'
        return {
            'seat': seat, 'name': opponent_name, 'stack': stack, 'current_bet': current_bet,
            'has_turn': has_turn, 'is_my_player': False,
            'hand': hand if hand else [], 'has_hidden_cards': not bool(hand),
            'hand_evaluation': (0, "N/A", []), 
            'id': f'player{seat}', 'is_active_player': is_active_player,
            'isFolded': False, 'position': position,
        }

    def _create_game_state(self, players, pot_size, community_cards, current_round, big_blind, small_blind, min_raise):
        processed_players = []
        for i, p_data_orig in enumerate(players):
            p_data = p_data_orig.copy()
            if 'id' not in p_data:
                p_data['id'] = f"player_gs_{i+1}_{p_data.get('name', 'unknown')}"
            if 'seat' not in p_data:
                p_data['seat'] = str(i + 1)
            # Ensure 'hand' key exists, mapping from 'cards' if necessary (as old tests might use 'cards')
            if 'hand' not in p_data and 'cards' in p_data:
                p_data['hand'] = p_data.pop('cards')
            elif 'hand' not in p_data:
                 p_data['hand'] = [] # Ensure hand key exists
            processed_players.append(p_data)

        return {
            "players": processed_players,
            "pot_size": pot_size,
            "community_cards": community_cards,
            "current_round": current_round, # This should map to 'street' e.g. 'Flop', 'Turn', 'River'
            "big_blind": big_blind,
            "small_blind": small_blind,
            "min_raise": min_raise,
            "board": community_cards, # board is often redundant with community_cards but good to have
        }

    def test_flop_my_turn_check_possible_strong_hand(self):
        """Flop: Bot has strong hand (e.g., Two Pair), no bets yet, bot is in position."""
        my_player_index = 0
        community = ['As', 'Kd', '7h']
        my_player_obj = self._create_mock_my_player_data(
            hand=['Ad', 'Kc'], stack=1.0, current_bet=0, bet_to_call=0, has_turn=True, 
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.85 # Example win_prob for strong hand
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=0, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.1,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2 
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_BET, "Bot should bet with two pair on the flop when checked to.")
        self.assertGreater(amount, 0, "Bet amount should be greater than 0.")

    def test_flop_my_turn_opponent_bets_medium_hand_call(self):
        """Flop: Opponent bets, bot has medium strength hand (e.g., Top Pair Good Kicker), should call."""
        my_player_index = 0
        community = ['Qs', '8d', '2h']
        opponent_bet_amount = 0.1
        my_player_obj = self._create_mock_my_player_data(
            hand=['Qc', 'Js'], stack=0.8, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True, 
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.6 # Example win_prob for medium hand
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.9, current_bet=opponent_bet_amount, position='BB') 
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.2 + opponent_bet_amount, # Initial pot + opponent's bet
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2 
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_CALL, "Bot should call with top pair when facing a reasonable bet.")
        self.assertEqual(amount, opponent_bet_amount, "Call amount should match opponent's bet.")

    def test_flop_my_turn_opponent_bets_weak_hand_fold(self):
        """Flop: Opponent bets, bot has weak hand (e.g., Gutshot, no pair), should fold to aggression."""
        my_player_index = 0
        community = ['Ks', 'Td', '3h']
        opponent_bet_amount = 0.2
        my_player_obj = self._create_mock_my_player_data(
            hand=['Ac', '2s'], stack=0.7, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True, 
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.15 # Example win_prob for weak hand
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.8, current_bet=opponent_bet_amount, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.3 + opponent_bet_amount, # Initial pot + opponent's bet
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_FOLD, "Bot should fold a weak hand to a significant flop bet.")

    def test_flop_my_turn_draw_heavy_board_opponent_checks_semi_bluff(self):
        """Flop: Draw heavy board, opponent checks, bot has a good draw, should semi-bluff bet."""
        my_player_index = 0
        community = ['Th', '9h', '2s'] # Flush draw and straight draw possibilities
        my_player_obj = self._create_mock_my_player_data(
            hand=['Qh', 'Jh'], stack=1.0, current_bet=0, bet_to_call=0, has_turn=True, # Open-ended straight flush draw
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.45 # Example win_prob for strong draw
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=0, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.1,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertIn(action, [ACTION_BET, ACTION_CHECK], "Bot should either bet (semi-bluff) or check with a strong draw.")
        if action == ACTION_BET:
            self.assertGreater(amount, 0, "Semi-bluff bet amount should be greater than 0.")

if __name__ == '__main__':
    unittest.main()
