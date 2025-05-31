import sys
import os
import unittest # Add unittest import
import logging # Added logging

# Configure basic logging for the test run to see debug messages
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from poker_bot import PokerBot
from decision_engine import ACTION_CALL, ACTION_RAISE, ACTION_CHECK, ACTION_FOLD, ACTION_BET
from hand_evaluator import HandEvaluator

class TestRiverScenarios(unittest.TestCase):
    def setUp(self):
        """Set up for test methods."""
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

    # Helper methods adapted from test_turn.py
    def _create_mock_my_player_data(self, hand, stack, current_bet, bet_to_call, has_turn, game_stage, community_cards=None, position='UTG', name='TestBot', win_probability=None):
        hand_evaluation_result = (0, "N/A", []) # Default
        preflop_strength = 0.0 # Not directly used in river decisions but part of player data structure

        if hand and game_stage != 'Pre-Flop' and community_cards:
            hand_evaluation_result = self.hand_evaluator.evaluate_hand(hand, community_cards)
        # Pre-flop specific logic removed as this is for river scenarios primarily

        player_data = {
            'hand': hand, 'stack': stack, 'current_bet': current_bet, 'bet_to_call': bet_to_call,
            'has_turn': has_turn, 'is_my_player': True, 'seat': '1', # Default seat, can be overridden
            'name': name, 'hand_evaluation': hand_evaluation_result,
            'id': 'player1', # Default ID, can be overridden
            'isActive': True, 'isFolded': False,
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
            'dealer_position': '2', 'hand_id': 'test_river_hand',
            'small_blind': self.config['small_blind'], # Use self.config
            'big_blind': self.config['big_blind'],   # Use self.config
            'board': community_cards,
        }

    def _create_mock_opponent_data(self, seat, stack, current_bet, has_turn=False, is_active_player=True, position='BTN', name=None, hand=None):
        opponent_name = name if name else f'Opponent{seat}'
        return {
            'seat': seat, 'name': opponent_name, 'stack': stack, 'current_bet': current_bet,
            'has_turn': has_turn, 'is_my_player': False,
            'hand': hand if hand else [], 'has_hidden_cards': not bool(hand),
            'hand_evaluation': (0, "N/A", []), # Opponent hand evaluation not typically known by bot
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
                p_data['seat'] = str(i + 1) # Assign seat based on order if not present
            
            if 'hand' not in p_data: # Ensure hand key exists
                p_data['hand'] = p_data.pop('cards', []) 
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

    def test_river_my_turn_value_bet(self):
        """Test river scenario: bot has a strong hand, should value bet."""
        logging.critical("STARTING TEST: test_river_my_turn_value_bet - UNIQUE_MARKER_RIVER_VALUE_BET") # Unique marker
        my_player_index = 0
        # Bot has Royal Flush: Th with community Ah Kh Qh Jh
        bot_hand_val = ['Th', 'Ts'] 
        community_cards_val = ['Ah', 'Kh', 'Qh', 'Jh', '2c']

        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_val, stack=1.0, current_bet=0, bet_to_call=0.1, has_turn=True,
            game_stage='River', community_cards=community_cards_val, position='BTN', name='TestBot_BTN_ValueBet',
            win_probability=1.0 # Nuts
        )
        
        opponent_bet_amount = 0.1
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.9, current_bet=opponent_bet_amount, position='BB', name='Opponent_BB_RiverBet', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        
        table_pot_size = 0.20 + opponent_bet_amount
        table_data = self._create_mock_table_data(community_cards=community_cards_val, pot_size=table_pot_size, game_stage='River', street='River')

        game_state = self._create_game_state(
            players=all_players,
            pot_size=table_data['pot_size'],
            community_cards=table_data['community_cards'],
            current_round="river",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        self.assertIn(action, [ACTION_RAISE, ACTION_BET], "Expected a value RAISE (or BET if no prior bet) with a strong hand on the river.")
        self.assertGreater(amount, 0, "Value bet/raise amount should be greater than 0.")

    def test_river_my_turn_bluff_catch(self):
        """Test river scenario: opponent bets, bot has a medium strength hand, decide to call or fold."""
        my_player_index = 0
        bot_hand_bc = ['Ac', '7s'] # Top pair (Ace) with weak kicker
        community_cards_bc = ['Ah', 'Kd', '8c', '3h', '2s']

        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_bc, stack=1.0, current_bet=0, bet_to_call=0.2, has_turn=True,
            game_stage='River', community_cards=community_cards_bc, position='BB', name='TestBot_BB_BluffCatch',
            win_probability=0.35 # Medium strength, potential bluff catch
        )
        
        opponent_bet_amount = 0.20 # Pot-sized bet
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.8, current_bet=opponent_bet_amount, position='BTN', name='Opponent_BTN_RiverBetPot', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]

        table_pot_size = 0.20 + opponent_bet_amount 
        table_data = self._create_mock_table_data(community_cards=community_cards_bc, pot_size=table_pot_size, game_stage='River', street='River')

        game_state = self._create_game_state(
            players=all_players,
            pot_size=table_data['pot_size'],
            community_cards=table_data['community_cards'],
            current_round="river",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        
        self.assertIn(action, [ACTION_CALL, ACTION_FOLD], "Expected CALL or FOLD for bluff catch scenario.")
        if action == ACTION_CALL:
            self.assertAlmostEqual(amount, 0.2, delta=0.001, msg="Call amount incorrect.")

    def test_river_not_my_turn(self):
        """Test river scenario: not bot's turn."""
        my_player_index = 0 
        bot_hand_nmt = ['Ks', 'Qs']
        community_cards_nmt = ['Ah', 'Kd', 'Qc', '7h', '2s']

        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_nmt, stack=1.0, current_bet=0.1, bet_to_call=0, has_turn=False, # Not bot's turn
            game_stage='River', community_cards=community_cards_nmt, position='BTN', name='TestBot_BTN_NotTurn'
            # win_probability not crucial as it's not bot's turn
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.9, current_bet=0.1, position='BB', name='Opponent_BB_River', has_turn=True, hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]

        table_pot_size = 0.30 
        table_data = self._create_mock_table_data(community_cards=community_cards_nmt, pot_size=table_pot_size, game_stage='River', street='River')

        game_state = self._create_game_state(
            players=all_players,
            pot_size=table_data['pot_size'],
            community_cards=table_data['community_cards'],
            current_round="river",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        
        self.assertIsNone(action, "Action should be None when it's not the bot's turn.")
        self.assertEqual(amount, 0, "Amount should be 0 when it's not the bot's turn.")

    def test_river_thin_value_bet(self):
        """Test river scenario: bot has a good but not monster hand, opponent is passive, should bet for thin value."""
        my_player_index = 0
        bot_hand_tvb = ['Kc', 'Js'] # Second pair (Kings), good kicker.
        community_cards_tvb = ['Ah', 'Kd', '7c', '3h', '2s']

        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_tvb, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='River', community_cards=community_cards_tvb, position='BTN', name='TestBot_BTN_ThinValue',
            win_probability=0.65 # Good hand for thin value
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=0, position='BB', name='Opponent_BB_PassiveCheck', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]

        table_pot_size = 0.20
        table_data = self._create_mock_table_data(community_cards=community_cards_tvb, pot_size=table_pot_size, game_stage='River', street='River')

        game_state = self._create_game_state(
            players=all_players,
            pot_size=table_data['pot_size'],
            community_cards=table_data['community_cards'],
            current_round="river",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        
        self.assertEqual(action, ACTION_BET, "Expected a BET for thin value.")
        self.assertGreater(amount, 0, "Thin value bet amount should be > 0.")
        # self.assertLessEqual(amount, table_pot_size * 0.5, "Thin value bet should be reasonably sized.") # Optional check

    def test_river_bluff_opportunity(self):
        """Test river scenario: bot has a weak hand (busted draw), opportunity to bluff."""
        my_player_index = 0
        bot_hand_bo = ['7h', '8h'] # Busted flush draw
        community_cards_bo = ['As', 'Kd', '2h', '9c', '3s']

        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_bo, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='River', community_cards=community_cards_bo, position='BTN', name='TestBot_BTN_BluffOpp',
            win_probability=0.1 # Weak hand, for bluffing
        )

        opponents = [
            self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=0, position='BB', name='Opponent_BB_CheckFold', hand=[])
        ]

        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.10 # Small pot, good for bluff
        table_data = self._create_mock_table_data(community_cards=community_cards_bo, pot_size=table_pot_size, game_stage='River', street='River')

        game_state = self._create_game_state(
            players=all_players,
            pot_size=table_data['pot_size'],
            community_cards=table_data['community_cards'],
            current_round="river",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )

        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        # Depending on bluffing strategy, could be BET or CHECK
        self.assertIn(action, [ACTION_BET, ACTION_CHECK], "Expected BET (bluff) or CHECK with busted draw.")
        if action == ACTION_BET:
            self.assertGreater(amount, 0, "Bluff bet amount should be > 0.")
            # self.assertGreaterEqual(amount, table_pot_size * 0.5, "Bluff bet should be reasonably sized.") # Optional

    def test_river_check_fold_weak_hand_vs_bet(self):
        """Test river scenario: bot has weak hand, checks, opponent bets, bot should fold."""
        my_player_index = 0
        bot_hand_cf = ['7d', '2c'] # Weak hand
        community_cards_cf = ['Ah', 'Ks', 'Qh', 'Jc', '5s'] # Rainbow board, no obvious draws hit for bot

        opponent_bet_amount = 0.15
        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_cf, stack=1.0, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='River', community_cards=community_cards_cf, position='BB', name='TestBot_BB_CheckFold',
            win_probability=0.05 # Very weak hand
        )

        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.85, current_bet=opponent_bet_amount, position='BTN', name='Opponent_BTN_RiverBet', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.20 + opponent_bet_amount
        table_data = self._create_mock_table_data(community_cards=community_cards_cf, pot_size=table_pot_size, game_stage='River', street='River')

        game_state = self._create_game_state(
            players=all_players,
            pot_size=table_data['pot_size'],
            community_cards=table_data['community_cards'],
            current_round="river",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )

        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        self.assertEqual(action, ACTION_FOLD, "Expected FOLD with weak hand facing bet.")

    def test_river_check_call_medium_hand_vs_bet(self):
        """Test river scenario: bot has medium hand, checks (or is checked to), opponent bets, bot calls."""
        my_player_index = 0
        bot_hand_cc = ['Ac', 'Ts'] # Top pair, decent kicker
        community_cards_cc = ['Ah', 'Kd', '8c', '3h', '2s']

        opponent_bet_amount = 0.05 # Small bet from opponent
        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_cc, stack=1.0, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='River', community_cards=community_cards_cc, position='BB', name='TestBot_BB_MediumCall',
            win_probability=0.55 # Medium hand, good enough to call small bet
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.95, current_bet=opponent_bet_amount, position='BTN', name='Opponent_BTN_SmallRiverBet', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.20 + opponent_bet_amount
        table_data = self._create_mock_table_data(community_cards=community_cards_cc, pot_size=table_pot_size, game_stage='River', street='River')

        game_state = self._create_game_state(
            players=all_players,
            pot_size=table_data['pot_size'],
            community_cards=table_data['community_cards'],
            current_round="river",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        
        self.assertEqual(action, ACTION_CALL, "Expected CALL with medium hand facing a small bet.")
        self.assertAlmostEqual(amount, opponent_bet_amount, delta=0.001, msg="Call amount incorrect.")

    def test_river_facing_all_in_decision(self):
        """Test river scenario: bot faces an all-in bet from an opponent."""
        my_player_index = 0
        bot_hand_fai = ['Ks', 'Qh'] # Top two pair
        community_cards_fai = ['Kc', 'Qd', '7s', '2h', '3c']

        opponent_stack_before_all_in = 0.50
        opponent_all_in_bet = opponent_stack_before_all_in
        
        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_fai, stack=1.0, current_bet=0, bet_to_call=opponent_all_in_bet, has_turn=True,
            game_stage='River', community_cards=community_cards_fai, position='BTN', name='TestBot_BTN_FaceAllIn',
            win_probability=0.60 # Good hand, decision to call all-in
        )

        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0, current_bet=opponent_all_in_bet, position='BB', name='Opponent_BB_AllIn', hand=[])
        ]
        # opponents[0]['stack_before_bet'] = opponent_stack_before_all_in # For clarity, not used by engine

        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.30 + opponent_all_in_bet
        table_data = self._create_mock_table_data(community_cards=community_cards_fai, pot_size=table_pot_size, game_stage='River', street='River')

        game_state = self._create_game_state(
            players=all_players,
            pot_size=table_data['pot_size'],
            community_cards=table_data['community_cards'],
            current_round="river",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2 
        )
        
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        
        self.assertIn(action, [ACTION_CALL, ACTION_FOLD], "Expected CALL or FOLD when facing all-in.")
        if action == ACTION_CALL:
            self.assertAlmostEqual(amount, my_player_obj['bet_to_call'], delta=0.001, msg="Call amount for all-in incorrect.")

    def test_river_making_all_in_strong_hand(self):
        """Test river scenario: bot has a very strong hand (e.g., nuts) and decides to go all-in."""
        my_player_index = 0
        bot_hand_mai = ['Ah', 'Kh'] # Nuts (Royal Flush with Q J T on board)
        community_cards_mai = ['Qh', 'Jh', 'Th', '2c', '3d']

        bot_stack = 1.0
        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_mai, stack=bot_stack, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='River', community_cards=community_cards_mai, position='BTN', name='TestBot_BTN_MakeAllIn_Nuts',
            win_probability=0.99 # Nuts or near nuts
        )
        
        opponent_stack = 0.8
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=opponent_stack, current_bet=0, position='BB', name='Opponent_BB_CanCallAllIn', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.25 
        table_data = self._create_mock_table_data(community_cards=community_cards_mai, pot_size=table_pot_size, game_stage='River', street='River')

        game_state = self._create_game_state(
            players=all_players,
            pot_size=table_data['pot_size'],
            community_cards=table_data['community_cards'],
            current_round="river",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        
        self.assertIn(action, [ACTION_BET, ACTION_RAISE], "Expected BET or RAISE with the nuts.")
        self.assertGreater(amount, 0)
        # If bot goes all-in, amount should be its stack or opponent's effective stack
        effective_stack_to_bet = min(bot_stack, opponent_stack) # Max opponent can call if bot shoves
        # For this test, assume bot bets its stack if it's an all-in decision
        if action == ACTION_BET and amount == bot_stack: # Bot shoves
             self.assertAlmostEqual(amount, bot_stack, delta=0.001, msg="Expected bot to bet its entire stack (all-in).")
        # Or a large bet
        self.assertTrue((action == ACTION_BET and amount > 0) or (action == ACTION_RAISE and amount > 0), "Should make a substantial bet/raise with nuts.")


    def test_river_making_all_in_bluff(self):
        """Test river scenario: bot decides to go all-in as a bluff."""
        my_player_index = 0
        bot_hand_maib = ['7h', '2c'] # Complete air
        community_cards_maib = ['As', 'Ks', 'Qd', '3h', '4c']

        bot_stack = 0.75
        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_maib, stack=bot_stack, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='River', community_cards=community_cards_maib, position='BTN', name='TestBot_BTN_AllInBluff',
            win_probability=0.05 # Air, for bluffing
        )
        
        opponent_stack = 0.60
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=opponent_stack, current_bet=0, position='BB', name='Opponent_BB_CanFoldToBluff', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.10
        table_data = self._create_mock_table_data(community_cards=community_cards_maib, pot_size=table_pot_size, game_stage='River', street='River')

        game_state = self._create_game_state(
            players=all_players,
            pot_size=table_data['pot_size'],
            community_cards=table_data['community_cards'],
            current_round="river",
            big_blind=self.config['big_blind'],
            small_blind=self.config['small_blind'],
            min_raise=self.config['big_blind'] * 2
        )
        
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        
        self.assertIn(action, [ACTION_BET, ACTION_CHECK], "Expected BET (all-in bluff) or CHECK.")
        if action == ACTION_BET:
            self.assertGreater(amount, 0, "Bluff bet amount must be > 0.")
            # If bluffing all-in, amount could be bot_stack or effective_stack
            # self.assertAlmostEqual(amount, min(bot_stack, opponent_stack), delta=0.001, msg="Expected all-in bluff amount.")
            self.assertGreaterEqual(amount, table_pot_size, "All-in bluff should generally be at least pot sized if it's a bluff bet.")
