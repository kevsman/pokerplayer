import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from poker_bot import PokerBot
from decision_engine import ACTION_CALL, ACTION_RAISE, ACTION_CHECK, ACTION_FOLD
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
        self.assertEqual(action, ACTION_RAISE, "Bot should bet with two pair on the flop when checked to.")
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
        self.assertIn(action, [ACTION_RAISE, ACTION_CHECK], "Bot should either bet (semi-bluff) or check with a strong draw.")
        if action == ACTION_RAISE:
            self.assertGreater(amount, 0, "Semi-bluff bet amount should be greater than 0.")

    def test_flop_set_versus_opponent_bet_raise(self):
        """Flop: Bot flops a set, opponent bets, should raise for value."""
        my_player_index = 0
        community = ['7c', '7s', 'Qh']
        opponent_bet_amount = 0.15
        my_player_obj = self._create_mock_my_player_data(
            hand=['7d', '7h'], stack=0.95, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.95
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.85, current_bet=opponent_bet_amount, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.3 + opponent_bet_amount,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_RAISE, "Bot should raise with quads for maximum value.")
        self.assertGreater(amount, opponent_bet_amount, "Raise amount should be greater than opponent's bet.")

    def test_flop_overpair_dry_board_bet(self):
        """Flop: Bot has overpair on dry board, should bet for value."""
        my_player_index = 0
        community = ['8c', '3d', '2s']
        my_player_obj = self._create_mock_my_player_data(
            hand=['Ac', 'As'], stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.88
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=0, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.15,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_RAISE, "Bot should bet overpair on dry board for value.")
        self.assertGreater(amount, 0, "Bet amount should be greater than 0.")

    def test_flop_flush_draw_opponent_bets_call(self):
        """Flop: Bot has flush draw, opponent bets reasonable amount, should call."""
        my_player_index = 0
        community = ['Kh', '9h', '4c']
        opponent_bet_amount = 0.08
        my_player_obj = self._create_mock_my_player_data(
            hand=['Ah', '6h'], stack=0.85, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.35
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.92, current_bet=opponent_bet_amount, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.2 + opponent_bet_amount,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_CALL, "Bot should call with nut flush draw at reasonable price.")
        self.assertEqual(amount, opponent_bet_amount, "Call amount should match opponent's bet.")

    def test_flop_open_ended_straight_draw_large_bet_fold(self):
        """Flop: Bot has open-ended straight draw, opponent makes large bet, should fold."""
        my_player_index = 0
        community = ['Jc', 'Td', '4h']
        opponent_bet_amount = 0.4  # Large bet relative to pot
        my_player_obj = self._create_mock_my_player_data(
            hand=['9s', '8c'], stack=0.6, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.32
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.6, current_bet=opponent_bet_amount, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.2 + opponent_bet_amount,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_FOLD, "Bot should fold open-ended straight draw to large bet.")

    def test_flop_top_pair_weak_kicker_versus_aggression_fold(self):
        """Flop: Bot has top pair weak kicker, faces significant aggression, should fold."""
        my_player_index = 0
        community = ['Ks', '9d', '3h']
        opponent_bet_amount = 0.25
        my_player_obj = self._create_mock_my_player_data(
            hand=['Kc', '2s'], stack=0.75, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True, # Corrected hand
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.35
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.75, current_bet=opponent_bet_amount, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.3 + opponent_bet_amount,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_FOLD, "Bot should fold top pair weak kicker to large bet.")

    def test_flop_bottom_two_pair_opponent_bets_call(self):
        """Flop: Bot has bottom two pair, opponent bets moderately, should call."""
        my_player_index = 0
        community = ['Kh', '9c', '5d']
        opponent_bet_amount = 0.12
        my_player_obj = self._create_mock_my_player_data(
            hand=['9s', '5h'], stack=0.88, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.72
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.88, current_bet=opponent_bet_amount, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.25 + opponent_bet_amount,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_CALL, "Bot should call with two pair against moderate bet.")
        self.assertEqual(amount, opponent_bet_amount, "Call amount should match opponent's bet.")

    def test_flop_pocket_pair_underpair_board_check_behind(self):
        """Flop: Bot has pocket pair that's an underpair to board, should check behind."""
        my_player_index = 0
        community = ['Ac', 'Kd', '7h']
        my_player_obj = self._create_mock_my_player_data(
            hand=['Jc', 'Js'], stack=0.95, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.25
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.95, current_bet=0, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.18,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_CHECK, "Bot should check behind with underpair on scary board.")

    def test_flop_gutshot_plus_overcards_call_small_bet(self):
        """Flop: Bot has gutshot + overcards, opponent makes small bet, should call."""
        my_player_index = 0
        community = ['9c', '8d', '2h']
        opponent_bet_amount = 0.06
        my_player_obj = self._create_mock_my_player_data(
            hand=['Ac', 'Jh'], stack=0.92, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.28
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.94, current_bet=opponent_bet_amount, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.15 + opponent_bet_amount,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_CALL, "Bot should call with gutshot + overcards to small bet.")
        self.assertEqual(amount, opponent_bet_amount, "Call amount should match opponent's bet.")

    def test_flop_air_versus_large_bet_fold(self):
        """Flop: Bot has complete air, opponent makes large bet, should fold."""
        my_player_index = 0
        community = ['Kh', 'Qc', '7s']
        opponent_bet_amount = 0.3
        my_player_obj = self._create_mock_my_player_data(
            hand=['4d', '2c'], stack=0.7, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.08
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.7, current_bet=opponent_bet_amount, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.2 + opponent_bet_amount,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_FOLD, "Bot should fold air to large bet.")

    def test_flop_multiway_pot_strong_hand_bet(self):
        """Flop: Multiway pot, bot has strong hand, should bet for value and protection."""
        my_player_index = 0
        community = ['As', 'Ah', '9c']
        my_player_obj = self._create_mock_my_player_data(
            hand=['Ad', 'Kc'], stack=0.9, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.92
        )
        opponent1 = self._create_mock_opponent_data(seat='2', stack=0.9, current_bet=0, position='BB')
        opponent2 = self._create_mock_opponent_data(seat='3', stack=0.9, current_bet=0, position='UTG')
        all_players = [my_player_obj, opponent1, opponent2]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.25,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_RAISE, "Bot should bet trips in multiway pot for value.")
        self.assertGreater(amount, 0, "Bet amount should be greater than 0.")

    def test_flop_pair_plus_flush_draw_versus_bet_raise(self):
        """Flop: Bot has pair + flush draw combo, opponent bets, should raise."""
        my_player_index = 0
        community = ['Tc', '8h', '3h']
        opponent_bet_amount = 0.1
        my_player_obj = self._create_mock_my_player_data(
            hand=['Th', '9h'], stack=0.85, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.65
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.9, current_bet=opponent_bet_amount, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.2 + opponent_bet_amount,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertIn(action, [ACTION_RAISE, ACTION_CALL], "Bot should raise or call with pair + flush draw.")
        if action == ACTION_RAISE:
            self.assertGreater(amount, opponent_bet_amount, "Raise should be greater than opponent's bet.")

    def test_flop_coordinated_board_overcards_fold_to_bet(self):
        """Flop: Highly coordinated board, bot has overcards only, should fold to bet."""
        my_player_index = 0
        community = ['9h', '8h', '7c']
        opponent_bet_amount = 0.15
        my_player_obj = self._create_mock_my_player_data(
            hand=['Ac', 'Kd'], stack=0.8, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.18
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.85, current_bet=opponent_bet_amount, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.25 + opponent_bet_amount,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_FOLD, "Bot should fold overcards on very coordinated board.")

    def test_flop_middle_pair_good_kicker_call_small_bet(self):
        """Flop: Bot has middle pair with good kicker, opponent makes small bet, should call."""
        my_player_index = 0
        community = ['Kc', '9s', '4d']
        opponent_bet_amount = 0.08
        my_player_obj = self._create_mock_my_player_data(
            hand=['9c', 'Ah'], stack=0.9, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.48
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.92, current_bet=opponent_bet_amount, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.18 + opponent_bet_amount,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_CALL, "Bot should call middle pair good kicker to small bet.")
        self.assertEqual(amount, opponent_bet_amount, "Call amount should match opponent's bet.")

    def test_flop_flopped_straight_slow_play(self):
        """Flop: Bot flops a straight, should consider slow playing or betting for value."""
        my_player_index = 0
        community = ['Jh', 'Tc', '9s']
        my_player_obj = self._create_mock_my_player_data(
            hand=['Qd', '8c'], stack=0.95, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.88
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.95, current_bet=0, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.16,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertIn(action, [ACTION_RAISE, ACTION_CHECK], "Bot should either bet for value or slow play with straight.")
        if action == ACTION_RAISE:
            self.assertGreater(amount, 0, "Bet amount should be greater than 0.")

    def test_flop_pocket_aces_wet_board_bet(self):
        """Flop: Bot has pocket aces on wet board, should bet for protection."""
        my_player_index = 0
        community = ['Kh', 'Qh', '7c']
        my_player_obj = self._create_mock_my_player_data(
            hand=['As', 'Ac'], stack=0.92, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.75
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.92, current_bet=0, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.2,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_RAISE, "Bot should bet pocket aces for protection on wet board.")
        self.assertGreater(amount, 0, "Bet amount should be greater than 0.")

    def test_flop_backdoor_draws_check_behind(self):
        """Flop: Bot has backdoor draws only, should check behind."""
        my_player_index = 0
        community = ['As', 'Jh', '5c']
        my_player_obj = self._create_mock_my_player_data(
            hand=['Kh', 'Qh'], stack=0.95, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.22
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.95, current_bet=0, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.14,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_CHECK, "Bot should check behind with only backdoor draws.")

    def test_flop_bottom_set_versus_aggression_raise(self):
        """Flop: Bot has bottom set, faces aggression, should raise for value."""
        my_player_index = 0
        community = ['Ah', 'Kc', '3s']
        opponent_bet_amount = 0.18
        my_player_obj = self._create_mock_my_player_data(
            hand=['3h', '3d'], stack=0.82, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.91
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.82, current_bet=opponent_bet_amount, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.3 + opponent_bet_amount,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_RAISE, "Bot should raise bottom set for maximum value.")
        self.assertGreater(amount, opponent_bet_amount, "Raise should be greater than opponent's bet.")

    def test_flop_weak_flush_draw_large_bet_fold(self):
        """Flop: Bot has weak flush draw, faces large bet, should fold."""
        my_player_index = 0
        community = ['Ks', '9s', '4h']
        opponent_bet_amount = 0.35
        my_player_obj = self._create_mock_my_player_data(
            hand=['6s', '2s'], stack=0.65, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.18
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.65, current_bet=opponent_bet_amount, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.25 + opponent_bet_amount,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_FOLD, "Bot should fold weak flush draw to large bet.")

    def test_flop_trips_slow_play_or_bet(self):
        """Flop: Bot has trips with kicker, should consider slow playing or betting."""
        my_player_index = 0
        community = ['Kh', 'Kd', '7s']
        my_player_obj = self._create_mock_my_player_data(
            hand=['Kc', 'Qs'], stack=0.9, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.94
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.9, current_bet=0, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.17,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertIn(action, [ACTION_RAISE, ACTION_CHECK], "Bot should either bet for value or slow play trips.")
        if action == ACTION_RAISE:
            self.assertGreater(amount, 0, "Bet amount should be greater than 0.")

    def test_flop_top_two_pair_versus_raise_reraise(self):
        """Flop: Bot has top two pair, faces a raise, should reraise."""
        my_player_index = 0
        community = ['As', 'Kh', '6c']
        opponent_bet_amount = 0.1
        opponent_raise_amount = 0.25
        my_player_obj = self._create_mock_my_player_data(
            hand=['Ac', 'Kd'], stack=0.75, current_bet=0, bet_to_call=opponent_raise_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.87
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.75, current_bet=opponent_raise_amount, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.3 + opponent_raise_amount,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_RAISE, "Bot should reraise with top two pair.")
        self.assertGreater(amount, opponent_raise_amount, "Reraise should be greater than opponent's raise.")

    def test_flop_straight_flush_draw_aggressive_play(self):
        """Flop: Bot has straight flush draw, should play aggressively."""
        my_player_index = 0
        community = ['9h', '8h', '2c']
        opponent_bet_amount = 0.12
        my_player_obj = self._create_mock_my_player_data(
            hand=['Th', '7h'], stack=0.88, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.54
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.88, current_bet=opponent_bet_amount, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.22 + opponent_bet_amount,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertIn(action, [ACTION_RAISE, ACTION_CALL], "Bot should raise or call with straight flush draw.")
        if action == ACTION_RAISE:
            self.assertGreater(amount, opponent_bet_amount, "Raise should be greater than opponent's bet.")

    def test_flop_monster_hand_extract_value(self):
        """Flop: Bot has monster hand (full house), should extract maximum value."""
        my_player_index = 0
        community = ['8h', '8c', '8d']
        opponent_bet_amount = 0.14
        my_player_obj = self._create_mock_my_player_data(
            hand=['As', '8s'], stack=0.86, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.99
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.86, current_bet=opponent_bet_amount, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.26 + opponent_bet_amount,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertIn(action, [ACTION_RAISE, ACTION_CALL], "Bot should raise or call to extract value with quads.")
        if action == ACTION_RAISE:
            self.assertGreater(amount, opponent_bet_amount, "Raise should be greater than opponent's bet.")

    def test_flop_position_matters_out_of_position(self):
        """Flop: Bot out of position with medium hand, should play more cautiously."""
        my_player_index = 0
        community = ['Qc', 'Jd', '5h']
        my_player_obj = self._create_mock_my_player_data(
            hand=['Qh', 'Td'], stack=0.9, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Flop', community_cards=community, position='BB', win_probability=0.58
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.9, current_bet=0, position='BTN')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.19,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertIn(action, [ACTION_CHECK, ACTION_RAISE], "Bot should check or make small bet out of position.")

    def test_flop_short_stack_play_conservatively(self):
        """Flop: Bot is short stacked, should play more conservatively."""
        my_player_index = 0
        community = ['Ac', '9s', '4h']
        opponent_bet_amount = 0.15
        my_player_obj = self._create_mock_my_player_data(
            hand=['Ad', 'Jc'], stack=0.25, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.68
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.85, current_bet=opponent_bet_amount, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.2 + opponent_bet_amount,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertIn(action, [ACTION_CALL, ACTION_RAISE], "Short stack should call or go all-in with top pair.")

    def test_flop_drawing_dead_fold_quickly(self):
        """Flop: Bot is drawing dead or nearly dead, should fold quickly."""
        my_player_index = 0
        community = ['Ah', 'As', 'Ac']
        opponent_bet_amount = 0.2
        my_player_obj = self._create_mock_my_player_data(
            hand=['7d', '2c'], stack=0.8, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.02
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.8, current_bet=opponent_bet_amount, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.3 + opponent_bet_amount,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_FOLD, "Bot should fold when drawing dead.")

    def test_flop_bluff_catcher_call_correctly(self):
        """Flop: Bot has bluff catcher, should call reasonable bets."""
        my_player_index = 0
        community = ['Ah', '7s', '2c']
        opponent_bet_amount = 0.09
        my_player_obj = self._create_mock_my_player_data(
            hand=['As', '6h'], stack=0.91, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.62
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.91, current_bet=opponent_bet_amount, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.18 + opponent_bet_amount,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_CALL, "Bot should call with top pair decent kicker as bluff catcher.")
        self.assertEqual(amount, opponent_bet_amount, "Call amount should match opponent's bet.")

    def test_flop_rainbow_board_continuation_bet(self):
        """Flop: Rainbow dry board, bot should continuation bet with any reasonable hand."""
        my_player_index = 0
        community = ['Kc', '6h', '2s']
        my_player_obj = self._create_mock_my_player_data(
            hand=['Ah', 'Qd'], stack=0.95, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.32
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.95, current_bet=0, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.16,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertIn(action, [ACTION_RAISE, ACTION_CHECK], "Bot should consider betting for fold equity on dry board.")

if __name__ == '__main__':
    unittest.main()
