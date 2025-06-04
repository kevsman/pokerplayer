import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from poker_bot import PokerBot
from decision_engine import ACTION_CALL, ACTION_RAISE, ACTION_CHECK, ACTION_FOLD 
from hand_evaluator import HandEvaluator

class TestTurnScenarios(unittest.TestCase):
    def setUp(self):
        """Set up for test methods."""
        self.config = {
            'big_blind': 0.02,
            'small_blind': 0.01,
            # Add other necessary config parameters if PokerBot or DecisionEngine expects them
        }
        # Initialize PokerBot with individual config values if it does not take a config dict
        self.bot = PokerBot(config=self.config) # Pass config object
        # If DecisionEngine is not created by PokerBot or needs specific setup for tests:
        # from decision_engine import DecisionEngine # Ensure DecisionEngine is imported
        # self.decision_engine_instance = DecisionEngine(hand_evaluator=HandEvaluator(), config=self.config)
        # self.bot.decision_engine = self.decision_engine_instance
        self.hand_evaluator = HandEvaluator() # Initialize HandEvaluator

    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self.bot, 'close_logger') and callable(self.bot.close_logger):
            self.bot.close_logger()

    # Helper methods (adapted from test_preflop.py and test_flop.py)
    def _create_mock_my_player_data(self, cards, stack, current_bet, bet_to_call, has_turn, game_stage, community_cards=None, position='UTG', name='TestBot', win_probability=None):
        """Creates mock data for the bot's player."""
        hand_evaluation_tuple = (0, "N/A", []) # Default for preflop or if evaluation fails
        preflop_strength = 0.0
        hand_strength = 0
        hand_name = "N/A"
        best_hand_cards = []

        if cards and community_cards and game_stage != 'Pre-Flop':
            hand_eval_dict = self.hand_evaluator.evaluate_hand(cards, community_cards)
            hand_strength = hand_eval_dict.get('rank_value', 0)
            hand_name = hand_eval_dict.get('description', "N/A")
            best_hand_cards = hand_eval_dict.get('tie_breakers', [])
            hand_evaluation_tuple = (hand_strength, hand_name, best_hand_cards)
        elif cards and len(cards) == 2 and game_stage == 'Pre-Flop':
            # Placeholder for preflop strength calculation if needed later
            pass

        player_data = {
            'hand': cards, 'stack': stack, 'current_bet': current_bet, 'bet_to_call': bet_to_call,
            'has_turn': has_turn, 'is_my_player': True, 'seat': '1', 'name': name,
            'hand_evaluation': hand_evaluation_tuple, 'id': 'player1', 'isActive': True, 'isFolded': False,
            'position': position, 'preflop_strength': preflop_strength,
            'available_actions': ['call', 'raise', 'fold', 'check', 'bet']
        }
        if win_probability is not None:
            player_data['win_probability'] = win_probability
        return player_data

    def _create_mock_opponent_data(self, seat, stack, current_bet, has_turn=False, is_active_player=True, position='BTN', name=None, cards=None, is_folded=False, win_probability=None):
        """Creates mock data for an opponent player."""
        opponent_name = name if name else f'Opponent{seat}'
        opponent_cards = cards if cards else []
        has_hidden_cards = not bool(cards)

        opponent_data = {
            'seat': str(seat), 'name': opponent_name, 'stack': stack, 'current_bet': current_bet,
            'has_turn': has_turn, 'is_my_player': False, 'hand': opponent_cards, 'has_hidden_cards': has_hidden_cards,
            'hand_evaluation': (0, "N/A", []), 'id': f'player{seat}', 'is_active_player': is_active_player,
            'isFolded': is_folded, 'position': position,
            'preflop_strength': 0.0, 
            'available_actions': ['call', 'raise', 'fold', 'check', 'bet']
        }
        if win_probability is not None:
            opponent_data['win_probability'] = win_probability
        return opponent_data

    def _create_mock_table_data(self, community_cards, pot_size, game_stage, street=None):
        """Creates mock data for the table."""
        current_street = street if street else game_stage # game_stage could be 'Turn'
        return {
            'community_cards': community_cards, 'pot_size': pot_size, 'street': current_street,
            'dealer_position': '2', 'hand_id': f'test_{current_street.lower()}_hand',
            'small_blind': self.config['small_blind'], 'big_blind': self.config['big_blind'],
            'board': community_cards, # 'board' is often used synonymously with community_cards
        }

    def _create_game_state(self, players, table_data, my_player_index):
        """Creates a mock game state dictionary."""
        # Ensure 'bet_to_call' is correctly calculated for the bot before passing to make_decision
        # The decision engine itself might do this, or it might expect it to be pre-calculated.
        # For these tests, we set it in _create_mock_my_player_data.

        # The game_state structure expected by make_decision needs to be matched.
        # Based on test_preflop.py, it seems to be a flat dictionary.
        # However, PokerBot.py's process_game_state might create a more structured one.
        # For direct calls to decision_engine.make_decision, the structure from test_preflop is:
        # { "players": all_players, "pot_size": ..., "community_cards": ..., "current_round": ..., etc. }

        return {
            "players": players,
            "pot_size": table_data['pot_size'],
            "community_cards": table_data['community_cards'],
            "current_round": table_data['street'].lower(), # e.g., "turn"
            "big_blind": self.config['big_blind'],
            "small_blind": self.config['small_blind'],
            "min_raise": self.config['big_blind'] * 2, # A common default, adjust if engine calculates differently
            "board": table_data['board'], # Redundant with community_cards but often present
            "street": table_data['street'], # Explicit street
            # Add any other keys expected by the decision engine for the turn
        }

    def test_turn_completed_flush_vs_full_house(self):
        """Test turn scenario: turn completes flush but board pairs giving full house potential."""
        my_player_index = 0
        bot_hand = ['8h', '6h'] # Made flush
        community_cards = ['9h', 'Jh', '9c', 'Ah'] # Flush completed but board pairs

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0.45, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='BTN', name='TestBot_BTN_FlushVsFullHouse',
            win_probability=0.60 # Flush but vulnerable to full house
        )
        opponent_player = self._create_mock_opponent_data(
            seat=2, stack=0.55, current_bet=0.45, position='BB', name='Opponent_BB_BigBet'
        )
        all_players = [my_player_obj, opponent_player]
        for i, p in enumerate(all_players):
            p['id'] = f'player{i+1}'
            p['seat'] = str(i + 1)
            if i == my_player_index:
                 p['is_my_player'] = True
            else:
                 p['is_my_player'] = False

        table_data = self._create_mock_table_data(
            community_cards=community_cards, pot_size=1.20, game_stage='Turn'
        )
        game_state = self._create_game_state(all_players, table_data, my_player_index)

        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        # Flush on paired board should be cautious against big bet
        self.assertIn(action, [ACTION_CALL, ACTION_FOLD], "Bot should be cautious with flush on paired board.")

    def test_turn_dry_board_becomes_wet(self):
        """Test turn scenario: dry flop becomes wet turn."""
        my_player_index = 0
        bot_hand = ['As', 'Ks'] # Strong hand
        community_cards = ['Ad', '6h', '2c', '5d'] # Dry flop, turn brings straight possibilities

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='CO', name='TestBot_CO_DryToWet',
            win_probability=0.75 # Top pair top kicker still strong
        )
        opponent_player = self._create_mock_opponent_data(
            seat=2, stack=1.0, current_bet=0, position='BTN', name='Opponent_BTN_Checks'
        )
        all_players = [my_player_obj, opponent_player]
        for i, p in enumerate(all_players):
            p['id'] = f'player{i+1}'
            p['seat'] = str(i + 1)
            if i == my_player_index:
                 p['is_my_player'] = True
            else:
                 p['is_my_player'] = False

        table_data = self._create_mock_table_data(
            community_cards=community_cards, pot_size=0.60, game_stage='Turn'
        )
        game_state = self._create_game_state(all_players, table_data, my_player_index)

        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        # Should still bet for value despite board getting more connected
        self.assertIn(action, [ACTION_RAISE, ACTION_CHECK], "Bot should bet or check based on opponent tendencies.")

    def test_turn_middle_pair_multiway(self):
        """Test turn scenario: middle pair in multiway pot."""
        my_player_index = 1
        bot_hand = ['8c', '8d'] # Pocket eights
        community_cards = ['Kh', '8s', '5c', 'Qd'] # Middle set but dangerous turn

        opponent1 = self._create_mock_opponent_data(
            seat=1, stack=0.8, current_bet=0.20, position='UTG', name='Opponent_UTG_Bets'
        )
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0.20, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='MP', name='TestBot_MP_MiddleSet'
        )
        opponent2 = self._create_mock_opponent_data(
            seat=3, stack=0.9, current_bet=0, has_turn=False, position='CO', name='Opponent_CO_Calls'
        )
        all_players = [opponent1, my_player_obj, opponent2]
        for i, p in enumerate(all_players):
            p['id'] = f'player{i+1}'
            p['seat'] = str(i + 1)
            if i == my_player_index:
                 p['is_my_player'] = True
            else:
                 p['is_my_player'] = False

        table_data = self._create_mock_table_data(
            community_cards=community_cards, pot_size=1.10, game_stage='Turn'
        )
        game_state = self._create_game_state(all_players, table_data, my_player_index)

        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        # Middle set should call or raise in multiway pot
        self.assertIn(action, [ACTION_CALL, ACTION_RAISE], "Bot should call or raise middle set in multiway pot.")

    def test_turn_big_bet_sizing_decision(self):
        """Test turn scenario: facing unusually large bet."""
        my_player_index = 0
        bot_hand = ['Ac', 'Jd'] # Top pair decent kicker
        community_cards = ['As', '9h', '4c', '2s'] # Safe board

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0.80, has_turn=True, # Very large bet
            game_stage='Turn', community_cards=community_cards, position='BB', name='TestBot_BB_BigBet',
            win_probability=0.45 # Good hand but facing overbet
        )
        opponent_player = self._create_mock_opponent_data(
            seat=2, stack=0.20, current_bet=0.80, position='BTN', name='Opponent_BTN_Overbet'
        )
        all_players = [my_player_obj, opponent_player]
        for i, p in enumerate(all_players):
            p['id'] = f'player{i+1}'
            p['seat'] = str(i + 1)
            if i == my_player_index:
                 p['is_my_player'] = True
            else:
                 p['is_my_player'] = False

        table_data = self._create_mock_table_data(
            community_cards=community_cards, pot_size=1.40, game_stage='Turn'
        )
        game_state = self._create_game_state(all_players, table_data, my_player_index)

        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        # Facing overbet with top pair, might call or fold
        self.assertIn(action, [ACTION_CALL, ACTION_FOLD], "Bot should be cautious facing overbet with top pair.")

    def test_turn_protection_bet_vs_draws(self):
        """Test turn scenario: betting to protect against draws."""
        my_player_index = 0
        bot_hand = ['Kd', 'Ks'] # Overpair
        community_cards = ['9h', '8h', '7c', '6h'] # Very wet board with multiple draws

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='SB', name='TestBot_SB_Protection',
            win_probability=0.50 # Overpair but many bad rivers
        )
        opponent_player = self._create_mock_opponent_data(
            seat=2, stack=1.0, current_bet=0, position='BB', name='Opponent_BB_DrawHeavy'
        )
        all_players = [my_player_obj, opponent_player]
        for i, p in enumerate(all_players):
            p['id'] = f'player{i+1}'
            p['seat'] = str(i + 1)
            if i == my_player_index:
                 p['is_my_player'] = True
            else:
                 p['is_my_player'] = False

        table_data = self._create_mock_table_data(
            community_cards=community_cards, pot_size=0.50, game_stage='Turn'
        )
        game_state = self._create_game_state(all_players, table_data, my_player_index)

        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        # Should bet to charge draws or check/fold on dangerous board
        self.assertIn(action, [ACTION_RAISE, ACTION_CHECK], "Bot should bet for protection or check on dangerous board.")

    def test_turn_small_stack_preservation(self):
        """Test turn scenario: small stack needs to preserve chips."""
        my_player_index = 0
        bot_hand = ['Qd', 'Jc'] # Decent but not premium
        community_cards = ['Qs', '9h', '5d', '3c'] # Top pair weak kicker

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=0.40, current_bet=0, bet_to_call=0.25, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='UTG', name='TestBot_UTG_SmallStack',
            win_probability=0.40 # Marginal hand, small stack
        )
        opponent_player = self._create_mock_opponent_data(
            seat=2, stack=1.5, current_bet=0.25, position='BTN', name='Opponent_BTN_BigStack'
        )
        all_players = [my_player_obj, opponent_player]
        for i, p in enumerate(all_players):
            p['id'] = f'player{i+1}'
            p['seat'] = str(i + 1)
            if i == my_player_index:
                 p['is_my_player'] = True
            else:
                 p['is_my_player'] = False

        table_data = self._create_mock_table_data(
            community_cards=community_cards, pot_size=0.80, game_stage='Turn'
        )
        game_state = self._create_game_state(all_players, table_data, my_player_index)

        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        # Small stack with marginal hand should be cautious
        self.assertIn(action, [ACTION_CALL, ACTION_FOLD], "Small stack should preserve chips with marginal hand.")

    def test_turn_slowplay_monster(self):
        """Test turn scenario: slowplaying monster hand."""
        my_player_index = 0
        bot_hand = ['9s', '9d'] # Pocket nines
        community_cards = ['9h', '9c', '4s', '2d'] # Quads

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='MP', name='TestBot_MP_Quads',
            win_probability=0.99 # Virtual nuts
        )
        opponent_player = self._create_mock_opponent_data(
            seat=2, stack=1.0, current_bet=0, position='CO', name='Opponent_CO_Checks'
        )
        all_players = [my_player_obj, opponent_player]
        for i, p in enumerate(all_players):
            p['id'] = f'player{i+1}'
            p['seat'] = str(i + 1)
            if i == my_player_index:
                 p['is_my_player'] = True
            else:
                 p['is_my_player'] = False

        table_data = self._create_mock_table_data(
            community_cards=community_cards, pot_size=0.40, game_stage='Turn'
        )
        game_state = self._create_game_state(all_players, table_data, my_player_index)

        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        # With quads might slowplay or bet small for value
        self.assertIn(action, [ACTION_CHECK, ACTION_RAISE], "Bot should check or bet small with quads.")

    def test_turn_implied_odds_call(self):
        """Test turn scenario: calling with implied odds."""
        my_player_index = 0
        bot_hand = ['Td', '9d'] # Open-ended straight draw
        community_cards = ['8s', '7h', '2c', 'Ac'] # Straight draw

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0.30, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='BTN', name='TestBot_BTN_ImpliedOdds',
            win_probability=0.25 # Draw with implied odds
        )
        opponent_player = self._create_mock_opponent_data(
            seat=2, stack=1.5, current_bet=0.30, position='BB', name='Opponent_BB_DeepStack'
        )
        all_players = [my_player_obj, opponent_player]
        for i, p in enumerate(all_players):
            p['id'] = f'player{i+1}'
            p['seat'] = str(i + 1)
            if i == my_player_index:
                 p['is_my_player'] = True
            else:
                 p['is_my_player'] = False

        table_data = self._create_mock_table_data(
            community_cards=community_cards, pot_size=1.00, game_stage='Turn'
        )
        game_state = self._create_game_state(all_players, table_data, my_player_index)

        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        # Draw with good implied odds might call
        self.assertIn(action, [ACTION_CALL, ACTION_FOLD], "Bot should consider implied odds with straight draw.")

    def test_turn_reverse_implied_odds(self):
        """Test turn scenario: facing reverse implied odds."""
        my_player_index = 0
        bot_hand = ['As', '2s'] # Weak flush draw
        community_cards = ['Ks', 'Qs', '9h', '8s'] # Weak flush draw on dangerous board

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0.40, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='SB', name='TestBot_SB_ReverseOdds',
            win_probability=0.20 # Weak draw with reverse implied odds
        )
        opponent_player = self._create_mock_opponent_data(
            seat=2, stack=1.0, current_bet=0.40, position='BTN', name='Opponent_BTN_AggressiveBet'
        )
        all_players = [my_player_obj, opponent_player]
        for i, p in enumerate(all_players):
            p['id'] = f'player{i+1}'
            p['seat'] = str(i + 1)
            if i == my_player_index:
                 p['is_my_player'] = True
            else:
                 p['is_my_player'] = False

        table_data = self._create_mock_table_data(
            community_cards=community_cards, pot_size=1.20, game_stage='Turn'
        )
        game_state = self._create_game_state(all_players, table_data, my_player_index)

        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        # Weak flush draw should fold due to reverse implied odds
        self.assertEqual(action, ACTION_FOLD, "Bot should fold weak flush draw with reverse implied odds.")

    def test_turn_thin_value_bet(self):
        """Test turn scenario: thin value betting opportunity."""
        my_player_index = 0
        bot_hand = ['Ah', 'Tc'] # Top pair weak kicker
        community_cards = ['Ad', '8h', '5c', '2s'] # Dry board

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='CO', name='TestBot_CO_ThinValue',
            win_probability=0.60 # Marginal value hand
        )
        opponent_player = self._create_mock_opponent_data(
            seat=2, stack=1.0, current_bet=0, position='BTN', name='Opponent_BTN_Passive'
        )
        all_players = [my_player_obj, opponent_player]
        for i, p in enumerate(all_players):
            p['id'] = f'player{i+1}'
            p['seat'] = str(i + 1)
            if i == my_player_index:
                 p['is_my_player'] = True
            else:
                 p['is_my_player'] = False

        table_data = self._create_mock_table_data(
            community_cards=community_cards, pot_size=0.50, game_stage='Turn'
        )
        game_state = self._create_game_state(all_players, table_data, my_player_index)

        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        # Against passive opponent might bet thinly for value
        self.assertIn(action, [ACTION_RAISE, ACTION_CHECK], "Bot might bet thin or check with marginal value hand.")

    def test_turn_board_texture_analysis(self):
        """Test turn scenario: complex board texture requiring careful analysis."""
        my_player_index = 0
        bot_hand = ['Jd', 'Jc'] # Pocket jacks
        community_cards = ['Tc', '9s', '8h', 'Qd'] # Very coordinated board

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0.35, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='BB', name='TestBot_BB_ComplexBoard',
            win_probability=0.35 # Overpair but board very coordinated
        )
        opponent_player = self._create_mock_opponent_data(
            seat=2, stack=0.65, current_bet=0.35, position='SB', name='Opponent_SB_Bets'
        )
        all_players = [my_player_obj, opponent_player]
        for i, p in enumerate(all_players):
            p['id'] = f'player{i+1}'
            p['seat'] = str(i + 1)
            if i == my_player_index:
                 p['is_my_player'] = True
            else:
                 p['is_my_player'] = False

        table_data = self._create_mock_table_data(
            community_cards=community_cards, pot_size=1.05, game_stage='Turn'
        )
        game_state = self._create_game_state(all_players, table_data, my_player_index)

        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        # Overpair on very coordinated board should be very cautious
        self.assertIn(action, [ACTION_CALL, ACTION_FOLD], "Bot should be cautious with overpair on coordinated board.")

if __name__ == '__main__':
    unittest.main()
