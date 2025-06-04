import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from poker_bot import PokerBot
from decision_engine import ACTION_CALL, ACTION_RAISE, ACTION_CHECK, ACTION_FOLD
from hand_evaluator import HandEvaluator

class TestPreFlopScenariosNr3(unittest.TestCase):
    def setUp(self):
        """Set up for test methods."""
        self.config = {
            'big_blind': 0.02,
            'small_blind': 0.01,
        }
        self.bot = PokerBot(config=self.config)
        self.hand_evaluator = self.bot.hand_evaluator

    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self.bot, 'close_logger') and callable(self.bot.close_logger):
            self.bot.close_logger()

    # Helper methods (similar to other test files)
    def _create_mock_my_player_data(self, cards, stack, current_bet, bet_to_call, has_turn, game_stage, community_cards=None, position='UTG', name='TestBotNr3'):
        if community_cards is None:
            community_cards = []

        hand_evaluation_tuple = (0, "N/A", [])
        preflop_strength = 0.0 # DecisionEngine is expected to calculate this

        return {
            'hand': cards, 'stack': stack, 'current_bet': current_bet, 'bet_to_call': bet_to_call,
            'has_turn': has_turn, 'is_my_player': True, 'seat': '1', 'name': name,
            'hand_evaluation': hand_evaluation_tuple, 'id': 'player_bot', 'isActive': True, 'isFolded': False,
            'position': position, 'preflop_strength': preflop_strength,
            'available_actions': ['call', 'raise', 'fold', 'check', 'bet']
        }

    def _create_mock_table_data(self, community_cards, pot_size, game_stage, street=None):
        current_street = street if street else game_stage
        return {
            'community_cards': community_cards, 'pot_size': pot_size, 'street': current_street,
            'dealer_position': '2', 'hand_id': 'test_preflop_nr3_hand',
            'small_blind': self.bot.config['small_blind'], 'big_blind': self.bot.config['big_blind'], 'board': community_cards,
        }

    def _create_mock_opponent_data(self, seat, stack, current_bet, position, name=None, has_turn=False, is_active_player=True, isFolded=False):
        opponent_name = name if name else f'Opponent{seat}'
        return {
            'seat': seat, 'name': opponent_name, 'stack': stack, 'current_bet': current_bet,
            'has_turn': has_turn, 'is_my_player': False, 'hand': [], 'has_hidden_cards': True,
            'hand_evaluation': (0, "N/A", []), 'id': f'player_opp_{seat}', 'is_active_player': is_active_player,
            'isFolded': isFolded, 'position': position,
        }

    def _create_game_state(self, players, pot_size, community_cards, current_round, big_blind, small_blind, min_raise):
        # Ensure all player objects have the 'is_my_player' key
        for player in players:
            if 'is_my_player' not in player:
                player['is_my_player'] = False

        return {
            "players": players,
            "pot_size": pot_size,
            "community_cards": community_cards,
            "current_round": current_round,
            "big_blind": big_blind,
            "small_blind": small_blind,
            "min_raise": min_raise,
            "betting_history": [],
            "board": community_cards,
            "street": current_round,
        }

    # NEW TEST SCENARIOS - COVERING GAPS NOT IN EXISTING FILES

    def test_preflop_utg_fold_weak_ace_a2o(self):
        """Pre-Flop: Bot UTG with A2o, should fold weak ace in early position."""
        my_player_index = 0 # Bot is UTG
        bot_hand = ['Ad', '2c'] # Ace-Two offsuit

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='UTG', name='TestBot_UTG_FoldA2o'
        )
        opponent_mp = self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=0, position='MP', name='Opponent_MP')
        opponent_co = self._create_mock_opponent_data(seat='3', stack=1.0, current_bet=0, position='CO', name='Opponent_CO')
        opponent_btn = self._create_mock_opponent_data(seat='4', stack=1.0, current_bet=0, position='BTN', name='Opponent_BTN')
        opponent_sb = self._create_mock_opponent_data(seat='5', stack=0.99, current_bet=self.config['small_blind'], position='SB', name='Opponent_SB')
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB')

        all_players = [my_player_obj, opponent_mp, opponent_co, opponent_btn, opponent_sb, opponent_bb]
        
        table_pot_size = self.config['small_blind'] + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players,
                pot_size=table['pot_size'],
                community_cards=table['community_cards'],
                current_round="preflop",
                big_blind=self.config['big_blind'],
                small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ),
            my_player_index
        )
        self.assertEqual(action, ACTION_FOLD, "Action for A2o UTG should be FOLD.")

    def test_preflop_mp_open_a9s_6max(self):
        """Pre-Flop: Bot MP with A9s in 6-max, should open raise suited ace."""
        my_player_index = 1 # Bot is MP
        bot_hand = ['As', '9s'] # Ace-Nine suited

        opponent_utg = self._create_mock_opponent_data(seat='1', stack=1.0, current_bet=0, position='UTG', name='Opponent_UTG_Folded', is_active_player=False)
        opponent_utg['isFolded'] = True
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='MP', name='TestBot_MP_OpenA9s'
        )
        opponent_co = self._create_mock_opponent_data(seat='3', stack=1.0, current_bet=0, position='CO', name='Opponent_CO')
        opponent_btn = self._create_mock_opponent_data(seat='4', stack=1.0, current_bet=0, position='BTN', name='Opponent_BTN')
        opponent_sb = self._create_mock_opponent_data(seat='5', stack=0.99, current_bet=self.config['small_blind'], position='SB', name='Opponent_SB')
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB')

        all_players = [opponent_utg, my_player_obj, opponent_co, opponent_btn, opponent_sb, opponent_bb]
        
        table_pot_size = self.config['small_blind'] + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        expected_open_raise = self.config['big_blind'] * 3 # 0.06

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players,
                pot_size=table['pot_size'],
                community_cards=table['community_cards'],
                current_round="preflop",
                big_blind=self.config['big_blind'],
                small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ),
            my_player_index
        )
        self.assertEqual(action, ACTION_RAISE, "Action for A9s MP should be RAISE.")
        self.assertAlmostEqual(amount, expected_open_raise, delta=0.001, msg="Open raise amount for A9s MP is incorrect.")

    def test_preflop_co_fold_k8o_vs_utg_open(self):
        """Pre-Flop: Bot CO with K8o vs UTG open, should fold weak king."""
        my_player_index = 2 # Bot is CO
        bot_hand = ['Kh', '8c'] # King-Eight offsuit
        utg_open_amount = self.config['big_blind'] * 3 # 0.06

        opponent_utg = self._create_mock_opponent_data(seat='1', stack=0.94, current_bet=utg_open_amount, position='UTG', name='Opponent_UTG_Raiser')
        opponent_mp = self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=0, position='MP', name='Opponent_MP_Folded', is_active_player=False)
        opponent_mp['isFolded'] = True
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='CO', name='TestBot_CO_FoldK8o'
        )
        opponent_btn = self._create_mock_opponent_data(seat='4', stack=1.0, current_bet=0, position='BTN', name='Opponent_BTN')
        opponent_sb = self._create_mock_opponent_data(seat='5', stack=0.99, current_bet=self.config['small_blind'], position='SB', name='Opponent_SB')
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB')

        all_players = [opponent_utg, opponent_mp, my_player_obj, opponent_btn, opponent_sb, opponent_bb]
        
        table_pot_size = utg_open_amount + self.config['small_blind'] + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players,
                pot_size=table['pot_size'],
                community_cards=table['community_cards'],
                current_round="preflop",
                big_blind=self.config['big_blind'],
                small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ),
            my_player_index
        )
        self.assertEqual(action, ACTION_FOLD, "Action for K8o CO vs UTG open should be FOLD.")

    def test_preflop_btn_call_small_pp_55_vs_mp_open(self):
        """Pre-Flop: Bot BTN with 55 vs MP open, should call for set value."""
        my_player_index = 3 # Bot is BTN
        bot_hand = ['5h', '5c'] # Pocket fives
        mp_open_amount = self.config['big_blind'] * 3 # 0.06

        opponent_utg = self._create_mock_opponent_data(seat='1', stack=1.0, current_bet=0, position='UTG', name='Opponent_UTG_Folded', is_active_player=False)
        opponent_utg['isFolded'] = True
        opponent_mp = self._create_mock_opponent_data(seat='2', stack=0.94, current_bet=mp_open_amount, position='MP', name='Opponent_MP_Raiser')
        opponent_co = self._create_mock_opponent_data(seat='3', stack=1.0, current_bet=0, position='CO', name='Opponent_CO_Folded', is_active_player=False)
        opponent_co['isFolded'] = True
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='BTN', name='TestBot_BTN_Call55'
        )
        opponent_sb = self._create_mock_opponent_data(seat='5', stack=0.99, current_bet=self.config['small_blind'], position='SB', name='Opponent_SB')
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB')

        all_players = [opponent_utg, opponent_mp, opponent_co, my_player_obj, opponent_sb, opponent_bb]
        
        table_pot_size = mp_open_amount + self.config['small_blind'] + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players,
                pot_size=table['pot_size'],
                community_cards=table['community_cards'],
                current_round="preflop",
                big_blind=self.config['big_blind'],
                small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ),
            my_player_index
        )
        self.assertEqual(action, ACTION_CALL, "Action for 55 BTN vs MP open should be CALL.")
        self.assertAlmostEqual(amount, mp_open_amount, delta=0.001, msg="Call amount for 55 BTN is incorrect.")

    def test_preflop_sb_fold_j7s_vs_co_btn_action(self):
        """Pre-Flop: Bot SB with J7s, CO opens, BTN calls, should fold weak suited jack."""
        my_player_index = 1 # Bot is SB
        bot_hand = ['Js', '7s'] # Jack-Seven suited
        co_open_amount = self.config['big_blind'] * 3 # 0.06

        opponent_co = self._create_mock_opponent_data(seat='3', stack=0.94, current_bet=co_open_amount, position='CO', name='Opponent_CO_Raiser')
        opponent_btn = self._create_mock_opponent_data(seat='4', stack=0.94, current_bet=co_open_amount, position='BTN', name='Opponent_BTN_Caller')
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=0.99, current_bet=self.config['small_blind'], bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='SB', name='TestBot_SB_FoldJ7s'
        )
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB')

        all_players = [opponent_co, my_player_obj, opponent_bb, opponent_btn] # Reordered for logic
        
        table_pot_size = co_open_amount + co_open_amount + self.config['small_blind'] + self.config['big_blind'] # CO open + BTN call
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players,
                pot_size=table['pot_size'],
                community_cards=table['community_cards'],
                current_round="preflop",
                big_blind=self.config['big_blind'],
                small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ),
            my_player_index
        )
        self.assertEqual(action, ACTION_FOLD, "Action for J7s SB vs CO open + BTN call should be FOLD.")    
    def test_preflop_bb_3bet_aj_vs_btn_steal(self):
        """Pre-Flop: Bot BB with AJs vs BTN steal attempt, should 3-bet."""
        my_player_index = 1 # Bot is BB
        bot_hand = ['As', 'Js'] # Ace-Jack suited (fixed to be actually suited)
        btn_steal_amount = self.config['big_blind'] * 2.5 # 0.05

        opponent_btn = self._create_mock_opponent_data(seat='4', stack=0.95, current_bet=btn_steal_amount, position='BTN', name='Opponent_BTN_Stealer')
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=0.98, current_bet=self.config['big_blind'], bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='BB', name='TestBot_BB_3betAJs'
        )
        # SB folded
        all_players = [opponent_btn, my_player_obj]
        
        table_pot_size = btn_steal_amount + self.config['small_blind'] + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        expected_3bet_amount = self.config['big_blind'] * 9 # 0.18 (typical BB 3-bet vs steal)

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players,
                pot_size=table['pot_size'],
                community_cards=table['community_cards'],
                current_round="preflop",
                big_blind=self.config['big_blind'],
                small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ),
            my_player_index
        )
        self.assertEqual(action, ACTION_RAISE, "Action for AJs BB vs BTN steal should be 3-bet (RAISE).")
        self.assertAlmostEqual(amount, expected_3bet_amount, delta=0.005, msg="3-bet amount for AJs BB is incorrect.")

    def test_preflop_utg_open_ats_suited_ace(self):
        """Pre-Flop: Bot UTG with ATs, should open raise suited ace-ten."""
        my_player_index = 0 # Bot is UTG
        bot_hand = ['At', 'Ts'] # Ace-Ten suited

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='UTG', name='TestBot_UTG_OpenATs'
        )
        opponent_mp = self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=0, position='MP', name='Opponent_MP')
        opponent_co = self._create_mock_opponent_data(seat='3', stack=1.0, current_bet=0, position='CO', name='Opponent_CO')
        opponent_btn = self._create_mock_opponent_data(seat='4', stack=1.0, current_bet=0, position='BTN', name='Opponent_BTN')
        opponent_sb = self._create_mock_opponent_data(seat='5', stack=0.99, current_bet=self.config['small_blind'], position='SB', name='Opponent_SB')
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB')

        all_players = [my_player_obj, opponent_mp, opponent_co, opponent_btn, opponent_sb, opponent_bb]
        
        table_pot_size = self.config['small_blind'] + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        expected_open_raise = self.config['big_blind'] * 3 # 0.06

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players,
                pot_size=table['pot_size'],
                community_cards=table['community_cards'],
                current_round="preflop",
                big_blind=self.config['big_blind'],
                small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ),
            my_player_index
        )
        self.assertEqual(action, ACTION_RAISE, "Action for ATs UTG should be RAISE.")
        self.assertAlmostEqual(amount, expected_open_raise, delta=0.001, msg="Open raise amount for ATs UTG is incorrect.")

    def test_preflop_mp_fold_q9o_vs_utg_open(self):
        """Pre-Flop: Bot MP with Q9o vs UTG open, should fold weak queen."""
        my_player_index = 1 # Bot is MP
        bot_hand = ['Qc', '9h'] # Queen-Nine offsuit
        utg_open_amount = self.config['big_blind'] * 3 # 0.06

        opponent_utg = self._create_mock_opponent_data(seat='1', stack=0.94, current_bet=utg_open_amount, position='UTG', name='Opponent_UTG_Raiser')
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='MP', name='TestBot_MP_FoldQ9o'
        )
        opponent_co = self._create_mock_opponent_data(seat='3', stack=1.0, current_bet=0, position='CO', name='Opponent_CO')
        opponent_btn = self._create_mock_opponent_data(seat='4', stack=1.0, current_bet=0, position='BTN', name='Opponent_BTN')
        opponent_sb = self._create_mock_opponent_data(seat='5', stack=0.99, current_bet=self.config['small_blind'], position='SB', name='Opponent_SB')
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB')

        all_players = [opponent_utg, my_player_obj, opponent_co, opponent_btn, opponent_sb, opponent_bb]
        
        table_pot_size = utg_open_amount + self.config['small_blind'] + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players,
                pot_size=table['pot_size'],
                community_cards=table['community_cards'],
                current_round="preflop",
                big_blind=self.config['big_blind'],
                small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2            ),
            my_player_index
        )
        self.assertEqual(action, ACTION_FOLD, "Action for Q9o MP vs UTG open should be FOLD.")

    def test_preflop_btn_3bet_bluff_a4s_vs_co_open(self):
        """Pre-Flop: Bot BTN with A4s vs CO open, should 3-bet as bluff."""
        my_player_index = 1 # Bot is BTN
        bot_hand = ['As', '4s'] # Ace-Four suited (good bluff candidate)
        co_open_amount = self.config['big_blind'] * 3 # 0.06

        opponent_co = self._create_mock_opponent_data(seat='3', stack=0.94, current_bet=co_open_amount, position='CO', name='Opponent_CO_Raiser')
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='BTN', name='TestBot_BTN_3betBluffA4s'
        )
        opponent_sb = self._create_mock_opponent_data(seat='5', stack=0.99, current_bet=self.config['small_blind'], position='SB', name='Opponent_SB')
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB')

        all_players = [opponent_co, my_player_obj, opponent_sb, opponent_bb]
        
        table_pot_size = co_open_amount + self.config['small_blind'] + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        expected_3bet_amount = co_open_amount * 3 # 0.18 (3x the open)

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players,
                pot_size=table['pot_size'],
                community_cards=table['community_cards'],
                current_round="preflop",
                big_blind=self.config['big_blind'],
                small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ),
            my_player_index
        )
        self.assertEqual(action, ACTION_RAISE, "Action for A4s BTN vs CO open should be 3-bet (RAISE).")
        self.assertAlmostEqual(amount, expected_3bet_amount, delta=0.005, msg="3-bet amount for A4s BTN is incorrect.")

    def test_preflop_co_call_a8s_vs_utg_open(self):
        """Pre-Flop: Bot CO with A8s vs UTG open, should call suited ace."""
        my_player_index = 2 # Bot is CO
        bot_hand = ['As', '8s'] # Ace-Eight suited
        utg_open_amount = self.config['big_blind'] * 3 # 0.06

        opponent_utg = self._create_mock_opponent_data(seat='1', stack=0.94, current_bet=utg_open_amount, position='UTG', name='Opponent_UTG_Raiser')
        opponent_mp = self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=0, position='MP', name='Opponent_MP_Folded', is_active_player=False)
        opponent_mp['isFolded'] = True
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='CO', name='TestBot_CO_CallA8s'
        )
        opponent_btn = self._create_mock_opponent_data(seat='4', stack=1.0, current_bet=0, position='BTN', name='Opponent_BTN')
        opponent_sb = self._create_mock_opponent_data(seat='5', stack=0.99, current_bet=self.config['small_blind'], position='SB', name='Opponent_SB')
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB')

        all_players = [opponent_utg, opponent_mp, my_player_obj, opponent_btn, opponent_sb, opponent_bb]
        
        table_pot_size = utg_open_amount + self.config['small_blind'] + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players,
                pot_size=table['pot_size'],
                community_cards=table['community_cards'],
                current_round="preflop",
                big_blind=self.config['big_blind'],
                small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ),
            my_player_index
        )
        self.assertEqual(action, ACTION_CALL, "Action for A8s CO vs UTG open should be CALL.")
        self.assertAlmostEqual(amount, utg_open_amount, delta=0.001, msg="Call amount for A8s CO is incorrect.")

    def test_preflop_sb_3bet_ajo_vs_btn_open_heads_up(self):
        """Pre-Flop: Bot SB with AJo vs BTN open in heads-up, should 3-bet."""
        my_player_index = 0 # Bot is SB
        bot_hand = ['Ad', 'Jh'] # Ace-Jack offsuit
        btn_open_amount = self.config['big_blind'] * 2.5 # 0.05

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=0.99, current_bet=self.config['small_blind'], bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='SB', name='TestBot_SB_3betAJo'
        )
        opponent_btn = self._create_mock_opponent_data(seat='2', stack=0.95, current_bet=btn_open_amount, position='BTN', name='Opponent_BTN_Opener')

        all_players = [my_player_obj, opponent_btn]
        
        table_pot_size = btn_open_amount + self.config['small_blind'] + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        expected_3bet_amount = self.config['big_blind'] * 8 # 0.16 (heads-up 3-bet sizing)

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players,
                pot_size=table['pot_size'],
                community_cards=table['community_cards'],
                current_round="preflop",
                big_blind=self.config['big_blind'],
                small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ),
            my_player_index
        )
        self.assertEqual(action, ACTION_RAISE, "Action for AJo SB vs BTN open (HU) should be 3-bet (RAISE).")
        self.assertAlmostEqual(amount, expected_3bet_amount, delta=0.005, msg="3-bet amount for AJo SB (HU) is incorrect.")

    def test_preflop_bb_call_k9s_vs_multiple_limpers(self):
        """Pre-Flop: Bot BB with K9s vs 3 limpers, should call with decent hand."""
        my_player_index = 5 # Bot is BB
        bot_hand = ['Ks', '9s'] # King-Nine suited
        limp_amount = self.config['big_blind'] # 0.02

        opponent_utg = self._create_mock_opponent_data(seat='1', stack=0.98, current_bet=limp_amount, position='UTG', name='Opponent_UTG_Limper')
        opponent_mp = self._create_mock_opponent_data(seat='2', stack=0.98, current_bet=limp_amount, position='MP', name='Opponent_MP_Limper')
        opponent_co = self._create_mock_opponent_data(seat='3', stack=0.98, current_bet=limp_amount, position='CO', name='Opponent_CO_Limper')
        opponent_btn = self._create_mock_opponent_data(seat='4', stack=1.0, current_bet=0, position='BTN', name='Opponent_BTN_Folded', is_active_player=False)
        opponent_btn['isFolded'] = True
        opponent_sb = self._create_mock_opponent_data(seat='5', stack=0.99, current_bet=self.config['small_blind'], position='SB', name='Opponent_SB_Folded', is_active_player=False)
        opponent_sb['isFolded'] = True
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=0.98, current_bet=self.config['big_blind'], bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='BB', name='TestBot_BB_CallK9s'
        )

        all_players = [opponent_utg, opponent_mp, opponent_co, opponent_btn, opponent_sb, my_player_obj]
        
        table_pot_size = limp_amount * 3 + self.config['small_blind'] + self.config['big_blind'] # 3 limps + blinds
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players,
                pot_size=table['pot_size'],
                community_cards=table['community_cards'],
                current_round="preflop",
                big_blind=self.config['big_blind'],
                small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ),
            my_player_index
        )
        self.assertEqual(action, ACTION_CHECK, "Action for K9s BB vs 3 limpers should be CHECK.")
        self.assertEqual(amount, 0, "Check amount should be 0.")

    def test_preflop_mp_3bet_ak_vs_utg_open(self):
        """Pre-Flop: Bot MP with AKo vs UTG open, should 3-bet premium hand."""
        my_player_index = 1 # Bot is MP
        bot_hand = ['Ad', 'Kh'] # Ace-King offsuit
        utg_open_amount = self.config['big_blind'] * 3 # 0.06

        opponent_utg = self._create_mock_opponent_data(seat='1', stack=0.94, current_bet=utg_open_amount, position='UTG', name='Opponent_UTG_Raiser')
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='MP', name='TestBot_MP_3betAK'
        )
        opponent_co = self._create_mock_opponent_data(seat='3', stack=1.0, current_bet=0, position='CO', name='Opponent_CO')
        opponent_btn = self._create_mock_opponent_data(seat='4', stack=1.0, current_bet=0, position='BTN', name='Opponent_BTN')
        opponent_sb = self._create_mock_opponent_data(seat='5', stack=0.99, current_bet=self.config['small_blind'], position='SB', name='Opponent_SB')
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB')

        all_players = [opponent_utg, my_player_obj, opponent_co, opponent_btn, opponent_sb, opponent_bb]
        
        table_pot_size = utg_open_amount + self.config['small_blind'] + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        expected_3bet_amount = utg_open_amount * 3 # 0.18 (3x the open)

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players,
                pot_size=table['pot_size'],
                community_cards=table['community_cards'],
                current_round="preflop",
                big_blind=self.config['big_blind'],
                small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ),
            my_player_index
        )
        self.assertEqual(action, ACTION_RAISE, "Action for AKo MP vs UTG open should be 3-bet (RAISE).")
        self.assertAlmostEqual(amount, expected_3bet_amount, delta=0.005, msg="3-bet amount for AKo MP is incorrect.")

    def test_preflop_btn_fold_73s_vs_4bet(self):
        """Pre-Flop: Bot BTN with 73s faces 4-bet, should fold weak hand."""
        my_player_index = 3 # Bot is BTN
        bot_hand = ['7s', '3s'] # Seven-Three suited
        utg_open_amount = self.config['big_blind'] * 3 # 0.06
        mp_3bet_amount = self.config['big_blind'] * 9 # 0.18
        co_4bet_amount = self.config['big_blind'] * 24 # 0.48

        opponent_utg = self._create_mock_opponent_data(seat='1', stack=0.94, current_bet=utg_open_amount, position='UTG', name='Opponent_UTG_Opener')
        opponent_mp = self._create_mock_opponent_data(seat='2', stack=0.82, current_bet=mp_3bet_amount, position='MP', name='Opponent_MP_3bettor')
        opponent_co = self._create_mock_opponent_data(seat='3', stack=0.52, current_bet=co_4bet_amount, position='CO', name='Opponent_CO_4bettor')
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='BTN', name='TestBot_BTN_Fold73s'
        )
        opponent_sb = self._create_mock_opponent_data(seat='5', stack=0.99, current_bet=self.config['small_blind'], position='SB', name='Opponent_SB')
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB')

        all_players = [opponent_utg, opponent_mp, opponent_co, my_player_obj, opponent_sb, opponent_bb]
        
        table_pot_size = co_4bet_amount + self.config['small_blind'] + self.config['big_blind'] # Only the 4-bet amount in pot
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players,
                pot_size=table['pot_size'],
                community_cards=table['community_cards'],
                current_round="preflop",
                big_blind=self.config['big_blind'],
                small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ),
            my_player_index
        )
        self.assertEqual(action, ACTION_FOLD, "Action for 73s BTN vs 4-bet should be FOLD.")

    def test_preflop_co_open_kto_late_position(self):
        """Pre-Flop: Bot CO with KTo, folded to, should open raise in late position."""
        my_player_index = 2 # Bot is CO
        bot_hand = ['Kd', 'Tc'] # King-Ten offsuit

        opponent_utg = self._create_mock_opponent_data(seat='1', stack=1.0, current_bet=0, position='UTG', name='Opponent_UTG_Folded', is_active_player=False)
        opponent_utg['isFolded'] = True
        opponent_mp = self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=0, position='MP', name='Opponent_MP_Folded', is_active_player=False)
        opponent_mp['isFolded'] = True
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='CO', name='TestBot_CO_OpenKTo'
        )
        opponent_btn = self._create_mock_opponent_data(seat='4', stack=1.0, current_bet=0, position='BTN', name='Opponent_BTN')
        opponent_sb = self._create_mock_opponent_data(seat='5', stack=0.99, current_bet=self.config['small_blind'], position='SB', name='Opponent_SB')
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB')

        all_players = [opponent_utg, opponent_mp, my_player_obj, opponent_btn, opponent_sb, opponent_bb]
        
        table_pot_size = self.config['small_blind'] + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        expected_open_raise = self.config['big_blind'] * 3 # 0.06

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players,
                pot_size=table['pot_size'],
                community_cards=table['community_cards'],
                current_round="preflop",
                big_blind=self.config['big_blind'],
                small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ),
            my_player_index
        )
        self.assertEqual(action, ACTION_RAISE, "Action for KTo CO (folded to) should be RAISE.")
        self.assertAlmostEqual(amount, expected_open_raise, delta=0.001, msg="Open raise amount for KTo CO is incorrect.")

    def test_preflop_bb_fold_92o_vs_sb_open(self):
        """Pre-Flop: Bot BB with 92o vs SB open, should fold weak hand."""
        my_player_index = 1 # Bot is BB
        bot_hand = ['9h', '2c'] # Nine-Two offsuit
        sb_open_amount = self.config['big_blind'] * 3 # 0.06

        opponent_sb = self._create_mock_opponent_data(seat='1', stack=0.94, current_bet=sb_open_amount, position='SB', name='Opponent_SB_Opener')
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=0.98, current_bet=self.config['big_blind'], bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='BB', name='TestBot_BB_Fold92o'
        )

        all_players = [opponent_sb, my_player_obj]
        
        table_pot_size = sb_open_amount + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players,
                pot_size=table['pot_size'],
                community_cards=table['community_cards'],
                current_round="preflop",
                big_blind=self.config['big_blind'],
                small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ),
            my_player_index
        )
        self.assertEqual(action, ACTION_FOLD, "Action for 92o BB vs SB open should be FOLD.")

    def test_preflop_utg_fold_j8s_suited_but_weak(self):
        """Pre-Flop: Bot UTG with J8s, should fold weak suited hand in early position."""
        my_player_index = 0 # Bot is UTG
        bot_hand = ['Jh', '8h'] # Jack-Eight suited

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='UTG', name='TestBot_UTG_FoldJ8s'
        )
        opponent_mp = self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=0, position='MP', name='Opponent_MP')
        opponent_co = self._create_mock_opponent_data(seat='3', stack=1.0, current_bet=0, position='CO', name='Opponent_CO')
        opponent_btn = self._create_mock_opponent_data(seat='4', stack=1.0, current_bet=0, position='BTN', name='Opponent_BTN')
        opponent_sb = self._create_mock_opponent_data(seat='5', stack=0.99, current_bet=self.config['small_blind'], position='SB', name='Opponent_SB')
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB')

        all_players = [my_player_obj, opponent_mp, opponent_co, opponent_btn, opponent_sb, opponent_bb]
        
        table_pot_size = self.config['small_blind'] + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players,
                pot_size=table['pot_size'],
                community_cards=table['community_cards'],
                current_round="preflop",
                big_blind=self.config['big_blind'],
                small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ),
            my_player_index
        )
        self.assertEqual(action, ACTION_FOLD, "Action for J8s UTG should be FOLD.")

    def test_preflop_btn_open_k4s_steal_attempt(self):
        """Pre-Flop: Bot BTN with K4s, folded to, should attempt steal."""
        my_player_index = 3 # Bot is BTN
        bot_hand = ['Ks', '4s'] # King-Four suited

        opponent_utg = self._create_mock_opponent_data(seat='1', stack=1.0, current_bet=0, position='UTG', name='Opponent_UTG_Folded', is_active_player=False)
        opponent_utg['isFolded'] = True
        opponent_mp = self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=0, position='MP', name='Opponent_MP_Folded', is_active_player=False)
        opponent_mp['isFolded'] = True
        opponent_co = self._create_mock_opponent_data(seat='3', stack=1.0, current_bet=0, position='CO', name='Opponent_CO_Folded', is_active_player=False)
        opponent_co['isFolded'] = True
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='BTN', name='TestBot_BTN_StealK4s'
        )
        opponent_sb = self._create_mock_opponent_data(seat='5', stack=0.99, current_bet=self.config['small_blind'], position='SB', name='Opponent_SB')
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB')

        all_players = [opponent_utg, opponent_mp, opponent_co, my_player_obj, opponent_sb, opponent_bb]
        
        table_pot_size = self.config['small_blind'] + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        expected_steal_amount = self.config['big_blind'] * 2.5 # 0.05 (typical steal sizing)

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players,
                pot_size=table['pot_size'],
                community_cards=table['community_cards'],
                current_round="preflop",
                big_blind=self.config['big_blind'],
                small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ),
            my_player_index
        )
        self.assertEqual(action, ACTION_RAISE, "Action for K4s BTN (folded to) should be RAISE (steal).")
        self.assertAlmostEqual(amount, expected_steal_amount, delta=0.005, msg="Steal amount for K4s BTN is incorrect.")

if __name__ == '__main__':
    unittest.main()
