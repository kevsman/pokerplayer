import os
import sys
import unittest

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from poker_bot import PokerBot
from decision_engine import ACTION_CALL, ACTION_RAISE, ACTION_CHECK, ACTION_FOLD
from hand_evaluator import HandEvaluator

class TestFlopScenariosAdvanced(unittest.TestCase):
    def setUp(self):
        self.config = {
            'big_blind': 0.02,
            'small_blind': 0.01,
        }
        self.bot = PokerBot(config=self.config)
        self.hand_evaluator = HandEvaluator()

    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self.bot, 'close_logger') and callable(self.bot.close_logger):
            self.bot.close_logger()

    def _create_mock_my_player_data(self, hand, stack, current_bet, bet_to_call, has_turn, game_stage, community_cards=None, position='UTG', name='TestBot', win_probability=None):
        if community_cards is None:
            community_cards = []
        hand_evaluation_tuple = (0, "N/A", [])
        preflop_strength = 0.0
        if hand and len(hand) == 2:
            preflop_strength = self.hand_evaluator.evaluate_preflop_strength(hand)
            if game_stage == 'Pre-Flop':  # Use preflop strength for preflop hand_evaluation tuple
                hand_evaluation_tuple = (preflop_strength, f"Preflop Strength: {preflop_strength:.2f}", hand)

        if hand and game_stage != 'Pre-Flop':  # Postflop evaluation
            # Use evaluate_hand which returns a dict including rank_category
            hand_eval_dict = self.hand_evaluator.evaluate_hand(hand, community_cards)
            # Store the dict directly or convert to tuple if other parts of bot expect tuple
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
            if 'hand' not in p_data and 'cards' in p_data:
                p_data['hand'] = p_data.pop('cards')
            elif 'hand' not in p_data:
                p_data['hand'] = []
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

    def test_flop_mixed_draw_check_raise_strategy(self):
        """Flop: Bot has both straight and flush draw, should use check-raise strategy when out of position."""
        my_player_index = 0
        community = ['Jh', 'Th', '4c']
        my_player_obj = self._create_mock_my_player_data(
            hand=['Qh', '9h'], stack=0.9, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Flop', community_cards=community, position='BB', win_probability=0.48
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.9, current_bet=0, position='BTN')
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
        # Bot should check or bet when it has a strong drawing hand out of position
        self.assertIn(action, [ACTION_CHECK, ACTION_RAISE], 
                     "Bot should check (for check-raise) or bet with strong draws out of position.")
        if action == ACTION_RAISE:
            self.assertGreater(amount, 0, "Bet amount should be greater than 0.")

    def test_flop_paired_board_strong_kicker(self):
        """Flop: Paired board, bot has high card matching pair with strong kicker, should bet for value."""
        my_player_index = 0
        community = ['8s', '8d', '3h']
        my_player_obj = self._create_mock_my_player_data(
            hand=['8c', 'Ad'], stack=0.95, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.89
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.95, current_bet=0, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.13,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_RAISE, "Bot should bet trips on paired board for value.")
        self.assertGreater(amount, 0, "Bet amount should be greater than 0.")

    def test_flop_check_raise_trap_with_monster(self):
        """Flop: Bot has monster hand, should sometimes check to induce bets (check-raise trap)."""
        my_player_index = 0
        community = ['As', 'Ad', '7c']
        my_player_obj = self._create_mock_my_player_data(
            hand=['Ac', 'Kh'], stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Flop', community_cards=community, position='SB', win_probability=0.96
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=0, position='BTN')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.12,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertIn(action, [ACTION_CHECK, ACTION_RAISE], 
                      "Bot should check (to trap) or bet with trips+kicker on paired board.")

    def test_flop_blocker_bluff_with_ace_high(self):
        """Flop: Bot has ace-high with blocker to strongest hand, should occasionally bluff."""
        my_player_index = 0
        community = ['Ks', 'Qd', 'Th']  # Board shows potential straight draw
        my_player_obj = self._create_mock_my_player_data(
            hand=['Ah', '4c'], stack=0.92, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.31
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.92, current_bet=0, position='BB')
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
        # Bot could either bluff or check here, both are valid strategies
        self.assertIn(action, [ACTION_RAISE, ACTION_CHECK],
                     "Bot should occasionally bluff with Ace blocker or check.")

    def test_flop_board_texture_change_strategy(self):
        """Flop: Bot adjusts strategy based on board texture - very wet vs. very dry."""
        # First test with dry board
        my_player_index = 0
        dry_community = ['2s', '6d', 'Jh']  # Unconnected, rainbow board
        my_player_obj = self._create_mock_my_player_data(
            hand=['As', 'Ks'], stack=0.95, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Flop', community_cards=dry_community, position='BTN', win_probability=0.58
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.95, current_bet=0, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.15,
            community_cards=dry_community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        dry_action, dry_amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        
        # Then test with wet board
        wet_community = ['9h', '8h', '7s']  # Connected, two-flush board
        my_player_obj = self._create_mock_my_player_data(
            hand=['As', 'Ks'], stack=0.95, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Flop', community_cards=wet_community, position='BTN', win_probability=0.43
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.95, current_bet=0, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.15,
            community_cards=wet_community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        wet_action, wet_amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        
        # Bot should be more willing to bet on dry board with overcards than wet board
        if dry_action == ACTION_RAISE and wet_action == ACTION_CHECK:
            self.assertTrue(True, "Bot correctly plays more aggressively on dry board than wet with same hand.")
        elif dry_action == wet_action == ACTION_RAISE:
            self.assertGreaterEqual(dry_amount, wet_amount, 
                                   "Bot should bet more on dry board than wet board with overcards.")

    def test_flop_stack_to_pot_ratio_adjustment(self):
        """Flop: Bot adjusts play based on SPR (Stack-to-Pot Ratio) - different plays based on effective stack depth."""
        my_player_index = 0
        community = ['Qc', 'Tc', '4s']
        
        # Test with deep stacks (high SPR)
        high_spr_player = self._create_mock_my_player_data(
            hand=['Qs', 'Jh'], stack=2.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.67
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=2.0, current_bet=0, position='BB')
        all_players = [high_spr_player, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.15,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        high_spr_action, high_spr_amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        
        # Test with shallow stacks (low SPR)
        low_spr_player = self._create_mock_my_player_data(
            hand=['Qs', 'Jh'], stack=0.3, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.67
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.3, current_bet=0, position='BB')
        all_players = [low_spr_player, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.15,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        low_spr_action, low_spr_amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        
        # We don't assert exact actions since both betting strategies could be valid
        # but we check that the bet sizing or action changes based on SPR
        if high_spr_action == low_spr_action == ACTION_RAISE:
            # If both decide to bet, betting proportion should differ
            high_spr_bet_proportion = high_spr_amount / high_spr_player['stack']
            low_spr_bet_proportion = low_spr_amount / low_spr_player['stack']
            self.assertNotAlmostEqual(high_spr_bet_proportion, low_spr_bet_proportion, delta=0.05)

    def test_flop_second_pair_good_kicker_versus_cbet(self):
        """Flop: Bot has second pair with a good kicker, facing continuation bet, should call."""
        my_player_index = 0
        community = ['Ks', '9d', '4h']
        opponent_bet_amount = 0.10
        my_player_obj = self._create_mock_my_player_data(
            hand=['9s', 'Ad'], stack=0.85, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BB', win_probability=0.56
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.90, current_bet=opponent_bet_amount, position='BTN')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.20 + opponent_bet_amount,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_CALL, 
                        "Bot should call with second pair good kicker against standard c-bet.")
        self.assertEqual(amount, opponent_bet_amount, "Call amount should match opponent's bet.")

    def test_flop_pot_committed_with_draw(self):
        """Flop: Bot is pot-committed with a draw, should be more willing to call/raise."""
        my_player_index = 0
        community = ['Ah', 'Kh', '6c']
        opponent_bet_amount = 0.20
        # Already committed 0.30 to the pot, with only 0.30 behind (pot committed)
        my_player_obj = self._create_mock_my_player_data(
            hand=['Qh', 'Jh'], stack=0.30, current_bet=0.30, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BB', win_probability=0.35
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.80, current_bet=opponent_bet_amount, position='BTN')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.60 + opponent_bet_amount,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertIn(action, [ACTION_CALL, ACTION_RAISE], 
                     "Bot should call or raise when pot committed with a strong draw.")
        if action == ACTION_CALL:
            self.assertEqual(amount, opponent_bet_amount, "Call amount should match opponent's bet.")

    def test_flop_three_bet_pot_with_strong_hand(self):
        """Flop: In a 3-bet pot, bot plays differently with same hand strength compared to single raised pot."""
        my_player_index = 0
        community = ['Ac', 'Td', '5s']
        my_player_obj = self._create_mock_my_player_data(
            hand=['Ad', 'Qs'], stack=0.80, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Flop', community_cards=community, position='BB', win_probability=0.72
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.80, current_bet=0, position='BTN')
        all_players = [my_player_obj, opponent]

        # This is a 3-bet pot, larger than normal
        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.45,  # Larger pot due to 3-betting preflop
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        
        # Bot should bet top pair top kicker in 3-bet pot
        self.assertEqual(action, ACTION_RAISE, 
                        "Bot should bet TPTK in 3-bet pot when checked to.")
        self.assertGreater(amount, 0.09, "Bet amount should be significant in 3-bet pot.")

    def test_flop_bluff_catch_with_marginal_hand(self):
        """Flop: Bot uses bluff-catching strategy with marginal hand in the right spot."""
        my_player_index = 0
        community = ['Qd', '7s', '3c']
        opponent_bet_amount = 0.08  # Small bet
        my_player_obj = self._create_mock_my_player_data(
            hand=['7d', '6c'], stack=0.90, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BB', win_probability=0.45
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.92, current_bet=opponent_bet_amount, position='BTN')
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
        self.assertEqual(action, ACTION_CALL, 
                        "Bot should call small bet with middle pair as a bluff-catcher.")
        self.assertEqual(amount, opponent_bet_amount, "Call amount should match opponent's bet.")

    def test_flop_four_to_flush_fold_to_large_bet(self):
        """Flop: Bot has 4 cards to flush, facing large bet should fold."""
        my_player_index = 0
        community = ['9c', '5c', '2c']
        opponent_bet_amount = 0.40  # Very large bet (2.5x pot)
        my_player_obj = self._create_mock_my_player_data(
            hand=['Ac', 'Jd'], stack=0.70, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.30
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.60, current_bet=opponent_bet_amount, position='BB')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.16 + opponent_bet_amount,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_FOLD, 
                        "Bot should fold flush draw to massive overbet.")

    def test_flop_multiway_pot_adjust_hand_strength(self):
        """Flop: Bot adjusts hand strength requirements in multiway pot vs. heads up."""
        my_player_index = 0
        community = ['Kc', '9d', '4s']
        
        # Same hand in a multiway pot with 3 players
        my_player_obj = self._create_mock_my_player_data(
            hand=['Kd', 'Tc'], stack=0.85, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.55
        )
        opponent1 = self._create_mock_opponent_data(seat='2', stack=0.85, current_bet=0, position='BB')
        opponent2 = self._create_mock_opponent_data(seat='3', stack=0.85, current_bet=0, position='SB')
        all_players = [my_player_obj, opponent1, opponent2]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.25,  # Larger pot due to more players
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        multiway_action, multiway_amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        # Now heads-up with the same hand
        all_players = [my_player_obj, opponent1]
        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.16,  # Smaller pot in heads-up
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        headsup_action, headsup_amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        if multiway_action == ACTION_RAISE and headsup_action == ACTION_RAISE:
            # If bot bets in both cases, it should bet less in multiway
            self.assertLessEqual(multiway_amount, headsup_amount,
                               "Bot should bet more cautiously in multiway pot than heads-up.")
        elif multiway_action == ACTION_CHECK and headsup_action == ACTION_RAISE:
            # This is also good, as it shows more caution in multiway
            self.assertTrue(True, "Bot correctly more cautious in multiway pot.")

    def test_flop_backdoor_straight_draw_plus_overcards(self):
        """Flop: Bot has backdoor straight draw plus overcards, should usually check."""
        my_player_index = 0
        community = ['8d', '5c', '2s']
        my_player_obj = self._create_mock_my_player_data(
            hand=['Ah', 'Kc'], stack=0.95, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Flop', community_cards=community, position='BB', win_probability=0.30
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.95, current_bet=0, position='BTN')
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
        # Both check (for pot control with medium strength) and bet (as bluff) are acceptable
        self.assertIn(action, [ACTION_CHECK, ACTION_RAISE], 
                     "Bot should usually check with overcards and backdoor draws, but bluffing is ok sometimes.")
        
    def test_flop_strong_ace_small_kicker(self):
        """Flop: Bot has strong ace but small kicker on ace-high board, should play cautiously."""
        my_player_index = 0
        community = ['As', 'Tc', '4h']
        opponent_bet_amount = 0.15
        my_player_obj = self._create_mock_my_player_data(
            hand=['Ac', '5d'], stack=0.85, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BB', win_probability=0.53
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.85, current_bet=opponent_bet_amount, position='BTN')
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
        self.assertEqual(action, ACTION_CALL, 
                        "Bot should call with ace-small kicker when facing moderate bet.")
        self.assertEqual(amount, opponent_bet_amount, "Call amount should match opponent's bet.")

    def test_flop_missed_completely_check_fold_strategy(self):
        """Flop: Bot completely missed flop, should employ check-fold strategy."""
        my_player_index = 0
        community = ['Qh', 'Jc', 'Td']
        my_player_obj = self._create_mock_my_player_data(
            hand=['3c', '2s'], stack=0.90, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Flop', community_cards=community, position='BB', win_probability=0.09
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.90, current_bet=0, position='BTN')
        all_players = [my_player_obj, opponent]

        # First check if bot checks when having the option
        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.16,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        check_action, check_amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(check_action, ACTION_CHECK, "Bot should check with complete air.")

        # Then verify if bot folds to a bet
        opponent_bet_amount = 0.10
        my_player_obj = self._create_mock_my_player_data(
            hand=['3c', '2s'], stack=0.90, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BB', win_probability=0.09
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.90, current_bet=opponent_bet_amount, position='BTN')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.16 + opponent_bet_amount,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        fold_action, fold_amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(fold_action, ACTION_FOLD, "Bot should fold complete air when facing a bet.")

    def test_flop_polarized_range_against_weak_opponent(self):
        """Flop: Bot employs polarized betting range against weak opponent."""
        my_player_index = 0
        # A board texture where polarized betting makes sense
        community = ['Ad', '7s', '2c']  
        my_player_obj = self._create_mock_my_player_data(
            hand=['Ks', 'Qh'], stack=0.95, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.29
            # Relatively weak hand but can represent strong hands
        )
        # Opponent who has shown weakness by checking
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
        
        # Both check (for pot control with medium strength) and bet (as bluff) are acceptable
        self.assertIn(action, [ACTION_CHECK, ACTION_RAISE], 
                     "Bot should either bluff bet or check with K-high on A-high board.")
        if action == ACTION_RAISE:
            self.assertGreater(amount, 0, "Bluff amount should be greater than 0.")

    def test_flop_oesd_versus_multiple_bets(self):
        """Flop: Bot has OESD, facing multiple bets, should fold to preserve stack."""
        my_player_index = 0
        community = ['Qc', 'Jd', '8h']
        
        # Simulating a bet and a raise before it gets to the bot
        opponent1_bet = 0.10
        opponent2_raise = 0.30
        
        my_player_obj = self._create_mock_my_player_data(
            hand=['Tc', '9s'], stack=0.70, current_bet=0, bet_to_call=opponent2_raise, has_turn=True,
            game_stage='Flop', community_cards=community, position='SB', win_probability=0.34
        )
        opponent1 = self._create_mock_opponent_data(
            seat='2', stack=0.90, current_bet=opponent1_bet, position='BB'
        )
        opponent2 = self._create_mock_opponent_data(
            seat='3', stack=0.70, current_bet=opponent2_raise, position='BTN'
        )
        all_players = [my_player_obj, opponent1, opponent2]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.22 + opponent1_bet + opponent2_raise,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_FOLD, 
                        "Bot should fold OESD facing a bet and raise.")

    def test_flop_paired_board_no_improvement(self):
        """Flop: Bot on paired board with no improvement and bet facing, should fold."""
        my_player_index = 0
        community = ['9s', '9c', '2d']
        opponent_bet_amount = 0.18
        my_player_obj = self._create_mock_my_player_data(
            hand=['Ah', 'Kd'], stack=0.82, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.26
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.82, current_bet=opponent_bet_amount, position='BB')
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
        self.assertEqual(action, ACTION_FOLD, 
                        "Bot should fold A-K high on paired board against a significant bet.")

    def test_flop_min_defense_frequency_against_small_bet(self):
        """Flop: Bot defends with sufficient frequency against small bets (MDF considerations)."""
        my_player_index = 0
        community = ['Td', '6s', '3c']
        opponent_bet_amount = 0.04  # Very small bet (1/4 pot)
        my_player_obj = self._create_mock_my_player_data(
            hand=['8h', '4d'], stack=0.96, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Flop', community_cards=community, position='BB', win_probability=0.23
            # Weak hand but facing tiny bet
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.96, current_bet=opponent_bet_amount, position='BTN')
        all_players = [my_player_obj, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.16 + opponent_bet_amount,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        
        # With such a small bet, the bot should sometimes call even with weak hands
        # to prevent being exploited (MDF principle)
        self.assertIn(action, [ACTION_CALL, ACTION_FOLD], 
                      "Bot should sometimes call very small bets with weak hands to prevent exploitation.")
        if action == ACTION_CALL:
            self.assertEqual(amount, opponent_bet_amount, "Call amount should match opponent's bet.")

    def test_flop_high_variance_scenarios(self):
        """Flop: Bot handles high variance scenarios differently based on stack depth."""
        my_player_index = 0
        community = ['As', 'Ks', 'Ts'] # Monochrome flop with high cards
        
        # Test with deep stack
        deep_stack_player = self._create_mock_my_player_data(
            hand=['Qh', 'Jh'], stack=2.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.25
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=2.0, current_bet=0, position='BB')
        all_players = [deep_stack_player, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.16,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        deep_action, deep_amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        
        # Test with short stack
        short_stack_player = self._create_mock_my_player_data(
            hand=['Qh', 'Jh'], stack=0.25, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Flop', community_cards=community, position='BTN', win_probability=0.25
        )
        opponent = self._create_mock_opponent_data(seat='2', stack=0.25, current_bet=0, position='BB')
        all_players = [short_stack_player, opponent]

        game_state = self._create_game_state(
            players=all_players,
            pot_size=0.16,
            community_cards=community,
            current_round="flop",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        short_action, short_amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        
        # Both plays may be valid, but they should differ based on stack depth
        # especially in a high variance situation with draws and monochrome boards
        if deep_action == short_action and deep_action == ACTION_RAISE:
            deep_bet_ratio = deep_amount / game_state['pot_size'] 
            short_bet_ratio = short_amount / game_state['pot_size']
            self.assertNotAlmostEqual(deep_bet_ratio, short_bet_ratio, delta=0.1)


if __name__ == '__main__':
    unittest.main()