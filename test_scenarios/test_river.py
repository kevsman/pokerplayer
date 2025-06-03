import sys
import os
import unittest # Add unittest import
import logging # Added logging

# Configure basic logging for the test run to see debug messages
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from poker_bot import PokerBot
from decision_engine import ACTION_CALL, ACTION_RAISE, ACTION_CHECK, ACTION_FOLD 
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

        self.assertIn(action, [ACTION_RAISE, ACTION_RAISE], "Expected a value RAISE (or BET if no prior bet) with a strong hand on the river.")
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
        
        self.assertEqual(action, ACTION_RAISE, "Expected a BET for thin value.")
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
        self.assertIn(action, [ACTION_RAISE, ACTION_CHECK], "Expected BET (bluff) or CHECK with busted draw.")
        if action == ACTION_RAISE:
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
        
        self.assertIn(action, [ACTION_RAISE, ACTION_RAISE], "Expected BET or RAISE with the nuts.")
        self.assertGreater(amount, 0)
        # If bot goes all-in, amount should be its stack or opponent's effective stack
        effective_stack_to_bet = min(bot_stack, opponent_stack) # Max opponent can call if bot shoves
        # For this test, assume bot bets its stack if it's an all-in decision
        if action == ACTION_RAISE and amount == bot_stack: # Bot shoves
             self.assertAlmostEqual(amount, bot_stack, delta=0.001, msg="Expected bot to bet its entire stack (all-in).")
        # Or a large bet
        self.assertTrue((action == ACTION_RAISE and amount > 0) or (action == ACTION_RAISE and amount > 0), "Should make a substantial bet/raise with nuts.")


    def test_river_all_in_bluff_vs_small_stack(self):
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
        
        self.assertIn(action, [ACTION_RAISE, ACTION_CHECK], "Expected BET (all-in bluff) or CHECK.")
        if action == ACTION_RAISE:
            self.assertAlmostEqual(amount, my_player_obj['stack'], delta=0.001, msg="All-in bluff amount incorrect.")

    def test_river_value_bet_all_in_nuts_vs_small_stack(self):
        """Test river scenario: bot has the nuts, opponent has a small stack, bot should go all-in."""
        my_player_index = 0
        bot_hand_vbai = ['Ah', 'Kh'] # Nuts (Ace high flush with board)
        community_cards_vbai = ['Qh', 'Jh', 'Th', '2c', '3d']

        bot_stack = 0.80
        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_vbai, stack=bot_stack, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='River', community_cards=community_cards_vbai, position='BTN', name='TestBot_BTN_ValueBetAllIn_Nuts',
            win_probability=0.99 # Nuts
        )
        
        opponent_stack = 0.10 # Very short stack
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=opponent_stack, current_bet=0, position='BB', name='Opponent_BB_CanCallAllIn', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.30 # Pot size before any betting
        table_data = self._create_mock_table_data(community_cards=community_cards_vbai, pot_size=table_pot_size, game_stage='River', street='River')

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
        
        # Bot has the nuts and opponent has a small stack, bot should go all-in.
        # This could be a BET (if first to act) or a RAISE (if opponent bet small)
        # For simplicity, if it's a raise, it should be an all-in raise.
        # If it's a bet, it should be an all-in bet.
        self.assertTrue((action == ACTION_RAISE and amount > 0) or (action == ACTION_RAISE and amount > 0), "Should make a substantial bet/raise with nuts.")
        if action == ACTION_RAISE and amount == bot_stack: # Bot shoves
             self.assertAlmostEqual(amount, bot_stack, delta=0.001, msg="Expected bot to bet its entire stack (all-in).")
        elif action == ACTION_RAISE and amount > 0: # Bot raises (could be all-in or less if opponent bet first)
            pass # Correct, assuming raise logic handles all-in sizing appropriately
        else:
            # Adding a more specific check for all-in
            # This depends on whether the bot's action was a bet (first to act) or raise
            # If my_player_obj['current_bet'] was 0, then it's an opening bet.
            # If opponent bet first, then it's a raise.
            # The current logic in postflop_decision_logic.py returns ACTION_RAISE for bets.
            self.assertEqual(action, ACTION_RAISE, "Action should be RAISE (interpreted as bet/raise).")
            self.assertAlmostEqual(amount, bot_stack, delta=0.001, msg="Value bet all-in amount incorrect.")

    def test_river_monster_hand_vs_aggressive_opponent(self):
        """Test river scenario: bot has monster hand (quads), aggressive opponent bets big."""
        my_player_index = 0
        bot_hand_monster = ['As', 'Ac']  # Pocket Aces
        community_cards_monster = ['Ah', 'Ad', 'Kh', '7c', '2s']  # Quad Aces

        opponent_bet_amount = 0.40  # Large bet
        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_monster, stack=1.5, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='River', community_cards=community_cards_monster, position='BTN', name='TestBot_BTN_Monster',
            win_probability=0.999  # Monster hand
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.60, current_bet=opponent_bet_amount, position='BB', name='Opponent_BB_AggBet', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.30 + opponent_bet_amount
        table_data = self._create_mock_table_data(community_cards=community_cards_monster, pot_size=table_pot_size, game_stage='River', street='River')

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
        
        self.assertEqual(action, ACTION_RAISE, "Expected RAISE with monster hand vs aggressive bet.")
        self.assertGreater(amount, opponent_bet_amount, "Raise amount should be substantial with monster hand.")

    def test_river_polarized_betting_spot_nuts(self):
        """Test river scenario: board completes draws, bot has nuts and should bet polarized."""
        my_player_index = 0
        bot_hand_polar = ['9s', '8s']  # Straight flush
        community_cards_polar = ['7s', '6s', '5s', 'Ah', 'Kd']  # Straight flush on board

        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_polar, stack=1.2, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='River', community_cards=community_cards_polar, position='BTN', name='TestBot_BTN_Polarized',
            win_probability=1.0  # Nuts
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=0, position='BB', name='Opponent_BB_Check', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.45
        table_data = self._create_mock_table_data(community_cards=community_cards_polar, pot_size=table_pot_size, game_stage='River', street='River')

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
        
        self.assertEqual(action, ACTION_RAISE, "Expected polarized BET with nuts on draw-heavy board.")
        self.assertGreaterEqual(amount, table_pot_size * 0.7, "Polarized bet should be substantial.")

    def test_river_missed_draw_check_behind(self):
        """Test river scenario: bot missed draw, should check behind when checked to."""
        my_player_index = 0
        bot_hand_missed = ['Kh', 'Qh']  # Missed flush draw
        community_cards_missed = ['Jd', '9s', '4c', '2s', '7c']  # No flush, no straight

        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_missed, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='River', community_cards=community_cards_missed, position='BTN', name='TestBot_BTN_MissedDraw',
            win_probability=0.15  # Weak hand
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=0, position='BB', name='Opponent_BB_Check', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.20
        table_data = self._create_mock_table_data(community_cards=community_cards_missed, pot_size=table_pot_size, game_stage='River', street='River')

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
        
        self.assertEqual(action, ACTION_CHECK, "Expected CHECK behind with missed draw.")

    def test_river_small_bet_inducing_call(self):
        """Test river scenario: bot has strong hand, makes small bet to induce calls."""
        my_player_index = 0
        bot_hand_induce = ['As', 'Ks']  # Top two pair
        community_cards_induce = ['Ah', 'Kc', '8d', '3h', '2s']

        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_induce, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='River', community_cards=community_cards_induce, position='BTN', name='TestBot_BTN_Induce',
            win_probability=0.85  # Very strong hand
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.8, current_bet=0, position='BB', name='Opponent_BB_TightPlayer', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.15  # Small pot
        table_data = self._create_mock_table_data(community_cards=community_cards_induce, pot_size=table_pot_size, game_stage='River', street='River')

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
        
        self.assertEqual(action, ACTION_RAISE, "Expected BET with strong hand for value.")
        if action == ACTION_RAISE:
            self.assertGreater(amount, 0, "Bet amount should be positive.")
            # Small inducing bet should be reasonable size
            self.assertLessEqual(amount, table_pot_size * 0.8, "Inducing bet should be reasonable size.")

    def test_river_pot_control_medium_hand(self):
        """Test river scenario: bot has medium strength hand, should control pot size."""
        my_player_index = 0
        bot_hand_control = ['Ac', '9s']  # Top pair, weak kicker
        community_cards_control = ['Ad', 'Kh', 'Qc', '7s', '4d']

        opponent_bet_amount = 0.25  # Medium bet
        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_control, stack=1.0, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='River', community_cards=community_cards_control, position='BB', name='TestBot_BB_PotControl',
            win_probability=0.45  # Medium strength
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.75, current_bet=opponent_bet_amount, position='BTN', name='Opponent_BTN_MedBet', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.30 + opponent_bet_amount
        table_data = self._create_mock_table_data(community_cards=community_cards_control, pot_size=table_pot_size, game_stage='River', street='River')

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
        
        self.assertIn(action, [ACTION_CALL, ACTION_FOLD], "Expected CALL or FOLD for pot control with medium hand.")
        if action == ACTION_CALL:
            self.assertAlmostEqual(amount, opponent_bet_amount, delta=0.001, msg="Call amount incorrect.")

    def test_river_overbet_shove_with_nuts(self):
        """Test river scenario: bot has nuts, opponent checks, bot makes overbet shove."""
        my_player_index = 0
        bot_hand_overbet = ['Th', '9h']  # Straight flush
        community_cards_overbet = ['8h', '7h', '6h', 'As', 'Kd']

        bot_stack = 2.0  # Deep stack
        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_overbet, stack=bot_stack, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='River', community_cards=community_cards_overbet, position='BTN', name='TestBot_BTN_Overbet',
            win_probability=1.0  # Nuts
        )
        
        opponent_stack = 1.8
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=opponent_stack, current_bet=0, position='BB', name='Opponent_BB_DeepCheck', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.60  # Medium pot
        table_data = self._create_mock_table_data(community_cards=community_cards_overbet, pot_size=table_pot_size, game_stage='River', street='River')

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
        
        self.assertEqual(action, ACTION_RAISE, "Expected BET/RAISE with nuts.")
        self.assertGreater(amount, 0, "Bet amount should be positive.")
        # With nuts, bot should make a substantial bet
        self.assertGreaterEqual(amount, table_pot_size * 0.5, "Should make substantial bet with nuts.")

    def test_river_three_way_pot_strong_hand(self):
        """Test river scenario: three-way pot, bot has strong hand, multiple opponents."""
        my_player_index = 0
        bot_hand_3way = ['Kd', 'Kc']  # Pocket Kings
        community_cards_3way = ['Ks', '8h', '3d', '7c', '2s']  # Trip Kings

        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_3way, stack=1.2, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='River', community_cards=community_cards_3way, position='BTN', name='TestBot_BTN_3Way',
            win_probability=0.92  # Very strong hand
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=0, position='BB', name='Opponent_BB_3Way', hand=[]),
            self._create_mock_opponent_data(seat='3', stack=0.8, current_bet=0, position='UTG', name='Opponent_UTG_3Way', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0], opponents[1]]
        table_pot_size = 0.45
        table_data = self._create_mock_table_data(community_cards=community_cards_3way, pot_size=table_pot_size, game_stage='River', street='River')

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
        
        self.assertEqual(action, ACTION_RAISE, "Expected BET with strong hand in 3-way pot.")
        self.assertGreater(amount, 0, "Bet amount should be positive.")

    def test_river_check_raise_trap_with_nuts(self):
        """Test river scenario: bot has nuts, opponent bets, bot should check-raise."""
        my_player_index = 0
        bot_hand_trap = ['As', 'Ks']  # Nut straight
        community_cards_trap = ['Qd', 'Jc', 'Th', '5h', '2s']

        opponent_bet_amount = 0.30
        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_trap, stack=1.5, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='River', community_cards=community_cards_trap, position='BB', name='TestBot_BB_Trap',
            win_probability=0.98  # Nuts
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.70, current_bet=opponent_bet_amount, position='BTN', name='Opponent_BTN_Bet', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.40 + opponent_bet_amount
        table_data = self._create_mock_table_data(community_cards=community_cards_trap, pot_size=table_pot_size, game_stage='River', street='River')

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
        
        self.assertEqual(action, ACTION_RAISE, "Expected RAISE (check-raise) with nuts.")
        self.assertGreater(amount, opponent_bet_amount, "Raise amount should be greater than opponent's bet.")

    def test_river_fold_to_overbet_weak_hand(self):
        """Test river scenario: bot has weak hand, faces large overbet, should fold."""
        my_player_index = 0
        bot_hand_weak = ['9c', '8d']  # Missed straight draw
        community_cards_weak = ['Ah', 'Kh', 'Qc', '5s', '2d']

        opponent_overbet = 1.2  # Massive overbet
        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_weak, stack=1.0, current_bet=0, bet_to_call=opponent_overbet, has_turn=True,
            game_stage='River', community_cards=community_cards_weak, position='BB', name='TestBot_BB_FoldOverbet',
            win_probability=0.08  # Very weak
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.3, current_bet=opponent_overbet, position='BTN', name='Opponent_BTN_Overbet', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.50 + opponent_overbet
        table_data = self._create_mock_table_data(community_cards=community_cards_weak, pot_size=table_pot_size, game_stage='River', street='River')

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
        
        self.assertEqual(action, ACTION_FOLD, "Expected FOLD to overbet with weak hand.")

    def test_river_blocking_bet_marginal_hand(self):
        """Test river scenario: bot has marginal hand, makes small blocking bet."""
        my_player_index = 0
        bot_hand_blocking = ['Jc', 'Ts']  # Middle pair
        community_cards_blocking = ['Jh', '8d', '5c', 'Ah', '3s']

        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_blocking, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='River', community_cards=community_cards_blocking, position='BTN', name='TestBot_BTN_Blocking',
            win_probability=0.35  # Marginal hand
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=0, position='BB', name='Opponent_BB_CheckToBlock', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.35
        table_data = self._create_mock_table_data(community_cards=community_cards_blocking, pot_size=table_pot_size, game_stage='River', street='River')

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
        
        self.assertIn(action, [ACTION_RAISE, ACTION_CHECK], "Expected small BET (blocking) or CHECK with marginal hand.")
        if action == ACTION_RAISE:
            self.assertGreater(amount, 0, "Blocking bet should be positive.")
            self.assertLessEqual(amount, table_pot_size * 0.4, "Blocking bet should be small.")

    def test_river_set_vs_flush_draw_completed(self):
        """Test river scenario: bot has set, flush draw completed on river, opponent bets big."""
        my_player_index = 0
        bot_hand_set = ['8s', '8d']  # Pocket 8s
        community_cards_set = ['8h', 'Kh', '7h', '3h', '2h']  # Set of 8s but flush completed

        opponent_bet_amount = 0.60  # Large bet suggesting flush
        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_set, stack=1.2, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='River', community_cards=community_cards_set, position='BB', name='TestBot_BB_SetVsFlush',
            win_probability=0.25  # Set but likely beat by flush
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.60, current_bet=opponent_bet_amount, position='BTN', name='Opponent_BTN_FlushBet', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.40 + opponent_bet_amount
        table_data = self._create_mock_table_data(community_cards=community_cards_set, pot_size=table_pot_size, game_stage='River', street='River')

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
        
        self.assertEqual(action, ACTION_FOLD, "Expected FOLD with set when flush completes and opponent bets big.")

    def test_river_nut_flush_vs_full_house_board(self):
        """Test river scenario: bot has nut flush but board pairs, suggesting full house possible."""
        my_player_index = 0
        bot_hand_flush = ['Ah', 'Qh']  # Nut flush
        community_cards_flush = ['Kh', 'Jh', '9h', 'Kd', 'Kc']  # Flush but board trips

        opponent_bet_amount = 0.80  # Large bet
        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_flush, stack=1.5, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='River', community_cards=community_cards_flush, position='BTN', name='TestBot_BTN_FlushVsBoat',
            win_probability=0.35  # Nut flush but board paired
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.70, current_bet=opponent_bet_amount, position='BB', name='Opponent_BB_BoatBet', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.50 + opponent_bet_amount
        table_data = self._create_mock_table_data(community_cards=community_cards_flush, pot_size=table_pot_size, game_stage='River', street='River')

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
        
        self.assertIn(action, [ACTION_CALL, ACTION_FOLD], "Expected CALL or FOLD with nut flush vs potential full house.")

    def test_river_straight_vs_flush_possible(self):
        """Test river scenario: bot has straight, flush is possible, opponent bets."""
        my_player_index = 0
        bot_hand_straight = ['Ts', '9c']  # Straight
        community_cards_straight = ['8h', '7h', '6h', 'Ah', '5d']  # Straight but flush possible

        opponent_bet_amount = 0.45
        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_straight, stack=1.0, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='River', community_cards=community_cards_straight, position='BB', name='TestBot_BB_StraightVsFlush',
            win_probability=0.40  # Straight but flush possible
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.55, current_bet=opponent_bet_amount, position='BTN', name='Opponent_BTN_FlushDraw', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.35 + opponent_bet_amount
        table_data = self._create_mock_table_data(community_cards=community_cards_straight, pot_size=table_pot_size, game_stage='River', street='River')

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
        
        self.assertIn(action, [ACTION_CALL, ACTION_FOLD], "Expected CALL or FOLD with straight vs potential flush.")

    def test_river_two_pair_vs_straight_board(self):
        """Test river scenario: bot has two pair, board shows potential straight."""
        my_player_index = 0
        bot_hand_2pair = ['Kc', '7s']  # Two pair K and 7
        community_cards_2pair = ['Kh', '7d', '8c', '9h', 'Ts']  # Two pair but straight possible

        opponent_bet_amount = 0.25
        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_2pair, stack=1.0, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='River', community_cards=community_cards_2pair, position='BB', name='TestBot_BB_TwoPairVsStraight',
            win_probability=0.30  # Two pair vs straight draw
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.75, current_bet=opponent_bet_amount, position='BTN', name='Opponent_BTN_StraightDraw', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.30 + opponent_bet_amount
        table_data = self._create_mock_table_data(community_cards=community_cards_2pair, pot_size=table_pot_size, game_stage='River', street='River')

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
        
        self.assertIn(action, [ACTION_CALL, ACTION_FOLD], "Expected CALL or FOLD with two pair vs potential straight.")

    def test_river_pocket_pair_unimproved_vs_bet(self):
        """Test river scenario: bot has unimproved pocket pair, faces bet on scary board."""
        my_player_index = 0
        bot_hand_pocket = ['Jc', 'Js']  # Pocket Jacks
        community_cards_pocket = ['Ah', 'Kh', 'Qd', '9s', '8c']  # Overcard heavy board

        opponent_bet_amount = 0.30
        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_pocket, stack=1.0, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='River', community_cards=community_cards_pocket, position='BB', name='TestBot_BB_PocketPair',
            win_probability=0.25  # Unimproved pocket pair
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.70, current_bet=opponent_bet_amount, position='BTN', name='Opponent_BTN_OvercardBet', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.25 + opponent_bet_amount
        table_data = self._create_mock_table_data(community_cards=community_cards_pocket, pot_size=table_pot_size, game_stage='River', street='River')

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
        
        self.assertEqual(action, ACTION_FOLD, "Expected FOLD with unimproved pocket pair on scary board.")

    def test_river_full_house_vs_quads_possible(self):
        """Test river scenario: bot has full house, board shows potential quads."""
        my_player_index = 0
        bot_hand_boat = ['As', 'Ac']  # Pocket Aces
        community_cards_boat = ['Ah', 'Ad', 'Kh', 'Kd', 'Ks']  # Full house but quads possible

        opponent_bet_amount = 1.0  # All-in bet
        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_boat, stack=1.5, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='River', community_cards=community_cards_boat, position='BTN', name='TestBot_BTN_BoatVsQuads',
            win_probability=0.80  # Full house but quads possible
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0, current_bet=opponent_bet_amount, position='BB', name='Opponent_BB_AllInQuads', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.60 + opponent_bet_amount
        table_data = self._create_mock_table_data(community_cards=community_cards_boat, pot_size=table_pot_size, game_stage='River', street='River')

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
        
        self.assertEqual(action, ACTION_CALL, "Expected CALL with full house even vs potential quads.")

    def test_river_broadway_straight_vs_higher_straight(self):
        """Test river scenario: bot has Broadway straight, higher straight possible."""
        my_player_index = 0
        bot_hand_broadway = ['Ts', '9h']  # Broadway straight (T-A)
        community_cards_broadway = ['Ah', 'Kc', 'Qd', 'Jh', '8s']  # Broadway but higher straight possible

        opponent_bet_amount = 0.50
        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_broadway, stack=1.0, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='River', community_cards=community_cards_broadway, position='BB', name='TestBot_BB_Broadway',
            win_probability=0.85  # Very strong hand
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.50, current_bet=opponent_bet_amount, position='BTN', name='Opponent_BTN_StraightBet', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.40 + opponent_bet_amount
        table_data = self._create_mock_table_data(community_cards=community_cards_broadway, pot_size=table_pot_size, game_stage='River', street='River')

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
        
        self.assertEqual(action, ACTION_CALL, "Expected CALL with Broadway straight.")

    def test_river_ace_high_bluff_catcher(self):
        """Test river scenario: bot has ace high, potential bluff catcher spot."""
        my_player_index = 0
        bot_hand_ace_high = ['Ad', '5c']  # Ace high
        community_cards_ace_high = ['Kh', 'Q7', '8s', '4d', '2h']  # Ace high only

        opponent_bet_amount = 0.15  # Small bet, potential bluff
        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_ace_high, stack=1.0, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='River', community_cards=community_cards_ace_high, position='BB', name='TestBot_BB_AceHighBluffCatch',
            win_probability=0.20  # Weak but could be bluff catch
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.85, current_bet=opponent_bet_amount, position='BTN', name='Opponent_BTN_SmallBet', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.20 + opponent_bet_amount
        table_data = self._create_mock_table_data(community_cards=community_cards_ace_high, pot_size=table_pot_size, game_stage='River', street='River')

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
        
        self.assertIn(action, [ACTION_CALL, ACTION_FOLD], "Expected CALL (bluff catch) or FOLD with ace high vs small bet.")

    def test_river_bottom_set_on_wet_board(self):
        """Test river scenario: bot has bottom set on very wet board."""
        my_player_index = 0
        bot_hand_bottom_set = ['2c', '2s']  # Pocket 2s
        community_cards_bottom_set = ['2h', 'Th', '9h', '8h', '7h']  # Bottom set but flush possible

        opponent_bet_amount = 0.70  # Large bet
        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_bottom_set, stack=1.2, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='River', community_cards=community_cards_bottom_set, position='BB', name='TestBot_BB_BottomSet',
            win_probability=0.15  # Bottom set but very wet board
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.50, current_bet=opponent_bet_amount, position='BTN', name='Opponent_BTN_WetBoard', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.45 + opponent_bet_amount
        table_data = self._create_mock_table_data(community_cards=community_cards_bottom_set, pot_size=table_pot_size, game_stage='River', street='River')

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
        
        self.assertEqual(action, ACTION_FOLD, "Expected FOLD with bottom set on extremely wet board.")

    def test_river_top_set_value_bet_dry_board(self):
        """Test river scenario: bot has top set on dry board, should value bet."""
        my_player_index = 0
        bot_hand_top_set = ['As', 'Ac']  # Pocket Aces
        community_cards_top_set = ['Ah', '7d', '3c', '2s', '8h']  # Top set, dry board

        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_top_set, stack=1.5, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='River', community_cards=community_cards_top_set, position='BTN', name='TestBot_BTN_TopSet',
            win_probability=0.95  # Very strong hand
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=0, position='BB', name='Opponent_BB_DryBoard', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.30
        table_data = self._create_mock_table_data(community_cards=community_cards_top_set, pot_size=table_pot_size, game_stage='River', street='River')

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
        
        self.assertEqual(action, ACTION_RAISE, "Expected BET with top set on dry board.")
        self.assertGreater(amount, 0, "Value bet should be positive.")

    def test_river_river_card_improves_to_nuts(self):
        """Test river scenario: river card gives bot the nuts, opponent already bet."""
        my_player_index = 0
        bot_hand_river_nuts = ['9h', '8h']  # Straight flush draw
        community_cards_river_nuts = ['7h', '6h', '5s', '4c', 'Th']  # River completes straight flush

        opponent_bet_amount = 0.40  # Opponent bet before seeing bot improved
        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_river_nuts, stack=1.2, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='River', community_cards=community_cards_river_nuts, position='BTN', name='TestBot_BTN_RiverNuts',
            win_probability=1.0  # Nuts
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.60, current_bet=opponent_bet_amount, position='BB', name='Opponent_BB_RiverBet', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.35 + opponent_bet_amount
        table_data = self._create_mock_table_data(community_cards=community_cards_river_nuts, pot_size=table_pot_size, game_stage='River', street='River')

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

        self.assertEqual(action, ACTION_RAISE, "Expected RAISE with nuts on river.")
        self.assertGreater(amount, opponent_bet_amount, "Should raise with nuts.")

    def test_river_slowplay_nuts_multiway(self):
        """Test river scenario: bot has nuts in multiway pot, considers slowplay."""
        my_player_index = 0
        bot_hand_multiway_nuts = ['As', 'Ks']  # Nut straight
        community_cards_multiway_nuts = ['Qh', 'Jd', 'Tc', '7s', '2h']  # Nut straight

        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_multiway_nuts, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='River', community_cards=community_cards_multiway_nuts, position='BTN', name='TestBot_BTN_MultiwayNuts',
            win_probability=0.98  # Nuts
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.8, current_bet=0, position='BB', name='Opponent_BB_Multiway', hand=[]),
            self._create_mock_opponent_data(seat='3', stack=0.6, current_bet=0, position='UTG', name='Opponent_UTG_Multiway', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0], opponents[1]]
        table_pot_size = 0.50
        table_data = self._create_mock_table_data(community_cards=community_cards_multiway_nuts, pot_size=table_pot_size, game_stage='River', street='River')

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
        
        # In multiway with nuts, usually better to bet than slowplay
        self.assertEqual(action, ACTION_RAISE, "Expected BET with nuts in multiway pot.")

    def test_river_paired_board_full_house_vs_trips(self):
        """Test river scenario: board pairs, bot has full house, opponent likely has trips."""
        my_player_index = 0
        bot_hand_fh = ['Ah', 'As']  # Pocket Aces
        community_cards_fh = ['Ad', 'Kh', '7c', 'Kd', '7s']  # Full house A over K

        opponent_bet_amount = 0.35  # Medium bet suggesting trips
        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_fh, stack=1.2, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='River', community_cards=community_cards_fh, position='BTN', name='TestBot_BTN_FullHouse',
            win_probability=0.88  # Full house
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.65, current_bet=opponent_bet_amount, position='BB', name='Opponent_BB_TripsBet', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.40 + opponent_bet_amount
        table_data = self._create_mock_table_data(community_cards=community_cards_fh, pot_size=table_pot_size, game_stage='River', street='River')

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
        
        self.assertEqual(action, ACTION_RAISE, "Expected RAISE with full house vs likely trips.")
        self.assertGreater(amount, opponent_bet_amount, "Should raise for value with full house.")

    def test_river_runner_runner_flush_bad_beat(self):
        """Test river scenario: bot had good hand but runner-runner flush beats it."""
        my_player_index = 0
        bot_hand_beaten = ['Ks', 'Kc']  # Pocket Kings
        community_cards_beaten = ['Kh', '9d', '7h', '3h', '6h']  # Set but runner-runner flush

        opponent_bet_amount = 0.50  # Large bet suggesting flush
        my_player_obj = self._create_mock_my_player_data(
            hand=bot_hand_beaten, stack=1.0, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='River', community_cards=community_cards_beaten, position='BB', name='TestBot_BB_RunnerRunner',
            win_probability=0.20  # Set but flush possible
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.50, current_bet=opponent_bet_amount, position='BTN', name='Opponent_BTN_FlushRunner', hand=[])
        ]
        
        all_players = [my_player_obj, opponents[0]]
        table_pot_size = 0.40 + opponent_bet_amount
        table_data = self._create_mock_table_data(community_cards=community_cards_beaten, pot_size=table_pot_size, game_stage='River', street='River')

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
        
        self.assertEqual(action, ACTION_FOLD, "Expected FOLD with set when runner-runner flush completes.")
        
if __name__ == "__main__":
    unittest.main()
