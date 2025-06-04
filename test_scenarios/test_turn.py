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

    # Removed _run_test_html_file method

    def test_turn_my_turn_opportunity_to_bet(self):
        """Test turn scenario: bot's turn, can bet or check. Bot has a strong hand."""
        my_player_index = 0
        bot_hand = ['As', 'Ks'] # Strong hand
        community_cards = ['Ah', 'Kd', '7s', '2c'] # Turn card is 2c, bot has two pair

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='BTN', name='TestBot_BTN',
            win_probability=0.85 # Explicitly set high win probability
        )
        opponents = [
            self._create_mock_opponent_data(seat=2, stack=1.0, current_bet=0, position='BB', name='Opponent_BB')
        ]
        all_players = [my_player_obj] + opponents
        # Ensure player objects have necessary fields like 'id', 'seat' correctly set up if not done by helpers
        for i, p in enumerate(all_players):
            p['id'] = f'player{i+1}'
            p['seat'] = str(i + 1)
            if i == my_player_index:
                 p['is_my_player'] = True
            else:
                 p['is_my_player'] = False


        pot_after_flop_betting = 0.50 # Example pot size coming into the turn
        table_data = self._create_mock_table_data(
            community_cards=community_cards, pot_size=pot_after_flop_betting, game_stage='Turn'
        )
        game_state = self._create_game_state(all_players, table_data, my_player_index)

        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        # Assertion: With a strong hand (two pair) and opportunity to bet, bot should bet.
        # ACTION_BET was replaced with ACTION_RAISE as ACTION_BET is not defined in decision_engine
        self.assertEqual(action, ACTION_RAISE, "Bot should bet with strong hand on the turn.") 
        self.assertGreater(amount, 0, "Bet amount should be greater than 0.")

    def test_turn_my_turn_opportunity_to_check(self):
        """Test turn scenario: bot's turn, can check or raise. Bot has a weak hand."""
        my_player_index = 0
        bot_hand = ['7d', '2s'] # Weak hand
        community_cards = ['Ah', 'Kd', '8c', '3h'] # Turn card is 3h, bot missed everything

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='BTN', name='TestBot_BTN_WeakHand',
            win_probability=0.05 # Explicitly set low win probability
        )
        opponents = [
            self._create_mock_opponent_data(seat=2, stack=1.0, current_bet=0, position='BB', name='Opponent_BB')
        ]
        all_players = [my_player_obj] + opponents
        for i, p in enumerate(all_players):
            p['id'] = f'player{i+1}'
            p['seat'] = str(i + 1)
            if i == my_player_index:
                 p['is_my_player'] = True
            else:
                 p['is_my_player'] = False

        pot_after_flop_betting = 0.50
        table_data = self._create_mock_table_data(
            community_cards=community_cards, pot_size=pot_after_flop_betting, game_stage='Turn'
        )
        game_state = self._create_game_state(all_players, table_data, my_player_index)

        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        # Assertion: With a weak hand, bot should check (or fold, depending on aggression model).
        self.assertIn(action, [ACTION_CHECK, ACTION_FOLD], "Bot should check or fold with a weak hand on the turn.")

    def test_turn_opponent_bets_bot_to_call_strong_hand(self):
        """Test turn scenario: bot's turn, opponent has bet, bot has strong hand and should call or raise."""
        my_player_index = 1
        bot_hand = ['Qh', 'Qs'] # Strong hand (overpair to board)
        community_cards = ['Jd', '7s', '2c', '5h'] # Turn card is 5h

        opponent_bet_amount = 0.25
        pot_before_opponent_bet = 0.50
        current_pot_size = pot_before_opponent_bet + opponent_bet_amount

        # Player setup: Opponent (BTN) bets, Bot (BB) to act
        opponent_player = self._create_mock_opponent_data(
            seat=1, stack=1.0 - opponent_bet_amount, current_bet=opponent_bet_amount, position='BTN', name='Opponent_BTN_Bets'
        )
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='BB', name='TestBot_BB_FacesBet'
        )
        all_players = [opponent_player, my_player_obj]
        for i, p in enumerate(all_players):
            p['id'] = f'player{i+1}'
            p['seat'] = str(i + 1)
            if i == my_player_index:
                 p['is_my_player'] = True
            else:
                 p['is_my_player'] = False

        table_data = self._create_mock_table_data(
            community_cards=community_cards, pot_size=current_pot_size, game_stage='Turn'
        )
        game_state = self._create_game_state(all_players, table_data, my_player_index)

        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        # Assertion: With a strong hand facing a bet, bot might call or raise.
        # For this example, let's assume it calls.
        self.assertIn(action, [ACTION_CALL, ACTION_RAISE], "Bot should call or raise with a strong hand facing a bet.")
        if action == ACTION_CALL:
            self.assertEqual(amount, opponent_bet_amount, "Call amount is incorrect.")
        elif action == ACTION_RAISE:
            # Raise amount needs to be validated based on raise sizing logic
            # e.g., self.assertGreater(amount, opponent_bet_amount, "Raise amount should be greater than opponent's bet.")
            min_raise_value = opponent_bet_amount * 2 # Min raise is typically to double the bet
            self.assertGreaterEqual(amount, min_raise_value, f"Raise amount should be at least {min_raise_value}")

    def test_turn_opponent_bets_bot_to_fold_weak_hand(self):
        """Test turn scenario: bot's turn, opponent has bet, bot has weak hand and should fold."""
        my_player_index = 0
        bot_hand = ['7d', '2s'] # Weak hand, missed flop and turn
        community_cards = ['Ah', 'Ks', 'Qd', 'Jc'] # Board is very coordinated, dangerous for 72o

        opponent_bet_amount = 0.30
        pot_before_opponent_bet = 0.60
        current_pot_size = pot_before_opponent_bet + opponent_bet_amount # Pot after opponent's bet

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='SB', name='TestBot_SB_WeakHand',
            win_probability=0.02 # Explicitly set very low win probability for folding
        )
        opponent_player = self._create_mock_opponent_data(
            seat=2, stack=1.0 - opponent_bet_amount, current_bet=opponent_bet_amount, position='BB', name='Opponent_BB_Bets'
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
            community_cards=community_cards, pot_size=current_pot_size, game_stage='Turn'
        )
        game_state = self._create_game_state(all_players, table_data, my_player_index)

        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        self.assertEqual(action, ACTION_FOLD, "Bot should fold with a weak hand facing a bet on a dangerous turn.")
        # Amount for fold is typically 0
        self.assertEqual(amount, 0, "Amount for fold action should be 0.")

    def test_turn_bot_has_strong_draw(self):
        """Test turn scenario: bot has a strong draw (flush draw + straight draw)."""
        my_player_index = 0
        bot_hand = ['9h', '8h'] # Strong combo draw
        community_cards = ['7h', '6s', 'Th', '5c'] # Turn gives flush draw + open-ended straight draw

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0.20, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='CO', name='TestBot_CO_Draw',
            win_probability=0.65 # Strong draw has good equity
        )
        opponent_player = self._create_mock_opponent_data(
            seat=2, stack=0.8, current_bet=0.20, position='BTN', name='Opponent_BTN_Bets'
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
            community_cards=community_cards, pot_size=0.70, game_stage='Turn'
        )
        game_state = self._create_game_state(all_players, table_data, my_player_index)

        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        # With a strong draw, bot should call or raise
        self.assertIn(action, [ACTION_CALL, ACTION_RAISE], "Bot should call or raise with strong combo draw.")
        if action == ACTION_CALL:
            self.assertEqual(amount, 0.20, "Call amount should match the bet.")

    def test_turn_bot_has_weak_draw(self):
        """Test turn scenario: bot has a weak draw (gutshot)."""
        my_player_index = 0
        bot_hand = ['9c', '8d'] # Gutshot straight draw
        community_cards = ['Ah', 'Kh', '6s', '2c'] # Turn gives only gutshot to Jack

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0.30, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='UTG', name='TestBot_UTG_WeakDraw',
            win_probability=0.15 # Weak draw has low equity
        )
        opponent_player = self._create_mock_opponent_data(
            seat=2, stack=0.7, current_bet=0.30, position='BB', name='Opponent_BB_Bets'
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

        # With weak draw facing a large bet, bot should fold
        self.assertEqual(action, ACTION_FOLD, "Bot should fold weak draw facing large bet.")

    def test_turn_multiway_pot_strong_hand(self):
        """Test turn scenario: multiway pot with strong hand."""
        my_player_index = 1
        bot_hand = ['Ad', 'Ac'] # Premium pocket pair
        community_cards = ['8h', '7s', '2c', '3d'] # Safe board for overpair

        opponent1 = self._create_mock_opponent_data(
            seat=1, stack=0.9, current_bet=0.10, position='UTG', name='Opponent_UTG'
        )
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0.10, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='MP', name='TestBot_MP_Multiway'
        )
        opponent2 = self._create_mock_opponent_data(
            seat=3, stack=0.85, current_bet=0.10, position='CO', name='Opponent_CO'
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
            community_cards=community_cards, pot_size=0.80, game_stage='Turn'
        )
        game_state = self._create_game_state(all_players, table_data, my_player_index)

        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        # In multiway pot with strong hand, bot should call or raise
        self.assertIn(action, [ACTION_CALL, ACTION_RAISE], "Bot should call or raise with strong hand in multiway pot.")

    def test_turn_coordinated_board_bluff_opportunity(self):
        """Test turn scenario: coordinated board presents bluff opportunity."""
        my_player_index = 0
        bot_hand = ['As', '5d'] # Ace high, missed everything
        community_cards = ['9h', '8h', '7c', '6h'] # Very coordinated, scary turn card

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='BTN', name='TestBot_BTN_BluffSpot',
            win_probability=0.25 # Some fold equity due to scary board
        )
        opponent_player = self._create_mock_opponent_data(
            seat=2, stack=1.0, current_bet=0, position='BB', name='Opponent_BB_ChecksTo'
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

        # On scary coordinated board, bot might bluff or check
        self.assertIn(action, [ACTION_CHECK, ACTION_RAISE], "Bot should check or bluff on coordinated scary board.")

    def test_turn_made_straight_on_flush_board(self):
        """Test turn scenario: bot makes straight but board has flush potential."""
        my_player_index = 0
        bot_hand = ['Jc', 'Ts'] # Makes straight
        community_cards = ['9h', '8h', 'Qd', '7h'] # Straight but dangerous flush board

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0.25, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='SB', name='TestBot_SB_StraightFlushBoard',
            win_probability=0.55 # Good hand but vulnerable to flush
        )
        opponent_player = self._create_mock_opponent_data(
            seat=2, stack=0.75, current_bet=0.25, position='BB', name='Opponent_BB_BetsIntoFlushBoard'
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
            community_cards=community_cards, pot_size=0.75, game_stage='Turn'
        )
        game_state = self._create_game_state(all_players, table_data, my_player_index)

        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        # Made straight should call, but might be cautious due to flush board
        self.assertIn(action, [ACTION_CALL, ACTION_FOLD], "Bot should call or fold straight on dangerous flush board.")

    def test_turn_set_against_aggressive_opponent(self):
        """Test turn scenario: bot has set facing aggressive betting."""
        my_player_index = 1
        bot_hand = ['7h', '7s'] # Pocket sevens
        community_cards = ['7d', 'Kc', '3h', 'Qh'] # Flops set, turn brings flush draw

        opponent_player = self._create_mock_opponent_data(
            seat=1, stack=0.5, current_bet=0.50, position='BTN', name='Opponent_BTN_Aggressive'
        )
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0.50, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='BB', name='TestBot_BB_Set',
            win_probability=0.80 # Set is very strong
        )
        all_players = [opponent_player, my_player_obj]
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

        # With set, bot should call or raise against aggression
        self.assertIn(action, [ACTION_CALL, ACTION_RAISE], "Bot should call or raise set against aggressive betting.")

    def test_turn_short_stack_all_in_decision(self):
        """Test turn scenario: short stack faces all-in decision."""
        my_player_index = 0
        bot_hand = ['Kh', 'Qc'] # Decent but not premium hand
        community_cards = ['Ks', '9d', '4h', '2s'] # Top pair, weak kicker

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=0.30, current_bet=0, bet_to_call=0.30, has_turn=True, # All-in decision
            game_stage='Turn', community_cards=community_cards, position='SB', name='TestBot_SB_ShortStack',
            win_probability=0.45 # Marginal hand
        )
        opponent_player = self._create_mock_opponent_data(
            seat=2, stack=0.70, current_bet=0.30, position='BB', name='Opponent_BB_AllIn'
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
            community_cards=community_cards, pot_size=0.90, game_stage='Turn'
        )
        game_state = self._create_game_state(all_players, table_data, my_player_index)

        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        # Short stack with top pair should call all-in or fold depending on pot odds
        self.assertIn(action, [ACTION_CALL, ACTION_FOLD], "Short stack should call or fold all-in with marginal hand.")

    def test_turn_nut_flush_draw(self):
        """Test turn scenario: bot has nut flush draw."""
        my_player_index = 0
        bot_hand = ['Ah', 'Kh'] # Nut flush draw
        community_cards = ['9h', '5c', '2h', '7h'] # Turn completes flush draw

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0.35, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='CO', name='TestBot_CO_NutFlushDraw',
            win_probability=0.70 # Nut flush draw has excellent equity
        )
        opponent_player = self._create_mock_opponent_data(
            seat=2, stack=0.65, current_bet=0.35, position='BTN', name='Opponent_BTN_Bets'
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

        # With nut flush draw, bot should call or raise
        self.assertIn(action, [ACTION_CALL, ACTION_RAISE], "Bot should call or raise with nut flush draw.")

    def test_turn_two_pair_on_straight_board(self):
        """Test turn scenario: bot has two pair on straight-heavy board."""
        my_player_index = 0
        bot_hand = ['Kd', '9c'] # Two pair
        community_cards = ['Ks', '9h', '8s', '7c'] # Two pair but dangerous straight board

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0.40, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='MP', name='TestBot_MP_TwoPairStraightBoard',
            win_probability=0.35 # Two pair vulnerable to straights
        )
        opponent_player = self._create_mock_opponent_data(
            seat=2, stack=0.60, current_bet=0.40, position='CO', name='Opponent_CO_BetsIntoStraightBoard'
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

        # Two pair on straight board should be cautious
        self.assertIn(action, [ACTION_CALL, ACTION_FOLD], "Bot should be cautious with two pair on straight board.")

    def test_turn_check_raise_opportunity(self):
        """Test turn scenario: bot checks with intention to check-raise."""
        my_player_index = 0
        bot_hand = ['As', 'Ad'] # Premium hand
        community_cards = ['Ac', '6h', '3s', '2d'] # Top set

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='UTG', name='TestBot_UTG_CheckRaise',
            win_probability=0.90 # Monster hand
        )
        opponent_player = self._create_mock_opponent_data(
            seat=2, stack=1.0, current_bet=0, position='BTN', name='Opponent_BTN_Position'
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

        # With monster hand out of position, might check for deception or bet for value
        self.assertIn(action, [ACTION_CHECK, ACTION_RAISE], "Bot should check or bet with monster hand for value extraction.")

    def test_turn_not_my_turn_graceful_handling(self):
        """Test turn scenario: not bot's turn. Ensure make_decision handles this if called."""
        my_player_index = 0 # Bot
        opponent_player_index = 1 # Opponent whose turn it is

        bot_hand = ['Ac', 'Kc']
        community_cards = ['Ah', 'Kd', '7s', '2c']

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=False, # Key: has_turn=False
            game_stage='Turn', community_cards=community_cards, position='SB', name='TestBot_SB_NotTurn'
        )
        opponent_player = self._create_mock_opponent_data(
            seat=2, stack=1.0, current_bet=0, has_turn=True, # Opponent's turn
            position='BB', name='Opponent_BB_IsTurn'
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

        # Depending on how decision_engine is supposed to behave:
        # Option 1: It should not be called if not bot's turn (test this at a higher integration level).
        # Option 2: If called, it returns a specific "no action" or default.
        # Option 3: It raises an error.
        # For this example, let's assume it should return a "no action" (e.g., None, None or specific constants)
        # or perhaps the engine itself has a check.
        # This test depends heavily on the expected behavior of `make_decision` when `my_player['has_turn']` is False.
        # Let's assume for now the decision engine's `make_decision` has a guard or returns a non-action.
        try:
            action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
            # If it's designed to return a non-action:
            self.assertIsNone(action, "Action should be None if it's not the bot's turn.")
            self.assertEqual(amount, 0, "Amount should be 0 if it's not the bot's turn.")
        except Exception as e:
            # Or, if it's designed to raise an error:
            self.fail(f"make_decision raised an unexpected exception when not bot's turn: {e}")
        # A more robust test would mock `make_decision` or check a state flag in the bot
        # to ensure it wasn't called inappropriately by a higher-level game loop.
        # For now, this tests a possible graceful return from make_decision itself.

    def test_turn_pot_committed_decision(self):
        """Test turn scenario: bot is pot committed and must call."""
        my_player_index = 0
        bot_hand = ['Jd', '9s'] # Marginal hand
        community_cards = ['Jh', '8c', '3d', '2h'] # Top pair weak kicker

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=0.15, current_bet=0, bet_to_call=0.15, has_turn=True, # Pot committed
            game_stage='Turn', community_cards=community_cards, position='BB', name='TestBot_BB_PotCommitted',
            win_probability=0.35 # Marginal but pot committed
        )
        opponent_player = self._create_mock_opponent_data(
            seat=2, stack=0.85, current_bet=0.15, position='BTN', name='Opponent_BTN_PutsAllIn'
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
            community_cards=community_cards, pot_size=1.50, game_stage='Turn' # Large pot relative to remaining stack
        )
        game_state = self._create_game_state(all_players, table_data, my_player_index)

        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        # When pot committed, bot should call even with marginal hand
        self.assertEqual(action, ACTION_CALL, "Bot should call when pot committed.")
        self.assertEqual(amount, 0.15, "Call amount should be remaining stack.")

    def test_turn_paired_board_full_house_potential(self):
        """Test turn scenario: board pairs on turn, creating full house potential."""
        my_player_index = 0
        bot_hand = ['Ks', 'Kd'] # Pocket kings
        community_cards = ['Kh', '9c', '4s', '9d'] # Turn pairs the board, gives full house

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='CO', name='TestBot_CO_FullHouse',
            win_probability=0.95 # Full house is very strong
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
            community_cards=community_cards, pot_size=0.50, game_stage='Turn'
        )
        game_state = self._create_game_state(all_players, table_data, my_player_index)

        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        # With full house, bot should bet for value
        self.assertEqual(action, ACTION_RAISE, "Bot should bet full house for value.")
        self.assertGreater(amount, 0, "Bet amount should be greater than 0.")

    def test_turn_overcards_to_board(self):
        """Test turn scenario: bot has overcards to low board."""
        my_player_index = 0
        bot_hand = ['Ac', 'Kd'] # Big cards
        community_cards = ['8h', '6s', '3c', '2d'] # Low board, overcards

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0.20, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='SB', name='TestBot_SB_Overcards',
            win_probability=0.30 # Overcards have some equity
        )
        opponent_player = self._create_mock_opponent_data(
            seat=2, stack=0.80, current_bet=0.20, position='BB', name='Opponent_BB_CBet'
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

        # Overcards might call or fold depending on pot odds and position
        self.assertIn(action, [ACTION_CALL, ACTION_FOLD], "Bot should call or fold with overcards.")

    def test_turn_blocking_bet_opportunity(self):
        """Test turn scenario: bot makes blocking bet with marginal hand."""
        my_player_index = 0
        bot_hand = ['Ah', '9c'] # Top pair weak kicker
        community_cards = ['As', '7h', '4d', '2s'] # Dry board

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='SB', name='TestBot_SB_BlockingBet',
            win_probability=0.55 # Marginal hand that might benefit from blocking bet
        )
        opponent_player = self._create_mock_opponent_data(
            seat=2, stack=1.0, current_bet=0, position='BTN', name='Opponent_BTN_Position'
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

        # With marginal hand out of position, might bet small (blocking bet) or check
        self.assertIn(action, [ACTION_CHECK, ACTION_RAISE], "Bot should check or make blocking bet with marginal hand.")

    def test_turn_runner_runner_flush_draw(self):
        """Test turn scenario: turn gives runner-runner flush draw."""
        my_player_index = 0
        bot_hand = ['Kh', 'Qc'] # High cards
        community_cards = ['Jd', '8h', '5c', 'Qh'] # Turn gives backdoor flush draw and pair

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0.15, has_turn=True,
            game_stage='Turn', community_cards=community_cards, position='MP', name='TestBot_MP_BackdoorFlush',
            win_probability=0.40 # Pair + backdoor draws
        )
        opponent_player = self._create_mock_opponent_data(
            seat=2, stack=0.85, current_bet=0.15, position='CO', name='Opponent_CO_Bets'
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
            community_cards=community_cards, pot_size=0.65, game_stage='Turn'
        )
        game_state = self._create_game_state(all_players, table_data, my_player_index)

        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        # With pair and backdoor draws, might call or fold
        self.assertIn(action, [ACTION_CALL, ACTION_FOLD], "Bot should call or fold with pair and backdoor draws.")

if __name__ == '__main__':
    unittest.main()
