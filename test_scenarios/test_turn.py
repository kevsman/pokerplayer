import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from poker_bot import PokerBot
from decision_engine import ACTION_CALL, ACTION_RAISE, ACTION_CHECK, ACTION_FOLD, ACTION_BET # Added
from hand_evaluator import HandEvaluator # Added

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
        self.assertEqual(action, ACTION_BET, "Bot should bet with strong hand on the turn.") # Changed ACTION_RAISE to ACTION_BET
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

    # The test_turn_not_my_turn scenario is less about make_decision and more about game flow.
    # If make_decision is called when it's not the bot's turn, it might error or do nothing.
    # For this refactoring, we'll focus on tests where the bot *does* make a decision.
    # A "not my turn" test would typically verify that the bot *doesn't* try to act.
    # This might be better tested at a higher level or by ensuring make_decision isn't called.
    # If the goal is to ensure make_decision handles it gracefully (e.g. returns a specific "no action" or raises error):
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
        # If the engine is robust, it might return (None, 0) or similar.
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

if __name__ == '__main__':
    unittest.main()
