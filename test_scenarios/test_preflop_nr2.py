import sys
import os
import unittest

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from poker_bot import PokerBot
from decision_engine import ACTION_CALL, ACTION_RAISE, ACTION_CHECK, ACTION_FOLD
from hand_evaluator import HandEvaluator

class TestPreFlopScenariosNr2(unittest.TestCase):
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

    # Helper methods (copied from test_preflop.py)
    def _create_mock_my_player_data(self, cards, stack, current_bet, bet_to_call, has_turn, game_stage, community_cards=None, position='UTG', name='TestBotNr2'):
        if community_cards is None:
            community_cards = []

        hand_evaluation_tuple = (0, "N/A", [])
        preflop_strength = 0.0 # DecisionEngine is expected to calculate this

        return {
            'hand': cards, 'stack': stack, 'current_bet': current_bet, 'bet_to_call': bet_to_call, # bet_to_call here is initial, engine recalculates
            'has_turn': has_turn, 'is_my_player': True, 'seat': '1', 'name': name,
            'hand_evaluation': hand_evaluation_tuple, 'id': 'player_bot', 'isActive': True, 'isFolded': False,
            'position': position, 'preflop_strength': preflop_strength,
            'available_actions': ['call', 'raise', 'fold', 'check', 'bet'] # 'bet' might be filtered by engine preflop
        }

    def _create_mock_table_data(self, community_cards, pot_size, game_stage, street=None):
        current_street = street if street else game_stage
        return {
            'community_cards': community_cards, 'pot_size': pot_size, 'street': current_street,
            'dealer_position': '2', 'hand_id': 'test_preflop_nr2_hand',
            'small_blind': self.bot.config['small_blind'], 'big_blind': self.bot.config['big_blind'], 'board': community_cards,
        }

    def _create_mock_opponent_data(self, seat, stack, current_bet, position, name=None, has_turn=False, is_active_player=True, isFolded=False):
        opponent_name = name if name else f'Opponent{seat}'
        return {
            'seat': seat, 'name': opponent_name, 'stack': stack, 'current_bet': current_bet,
            'has_turn': has_turn, 'is_my_player': False, 'hand': [], 'has_hidden_cards': True, # Changed 'cards' to 'hand'
            'hand_evaluation': (0, "N/A", []), 'id': f'player_opp_{seat}', 'is_active_player': is_active_player,
            'isFolded': isFolded, 'position': position,
        }

    def _create_game_state(self, players, pot_size, community_cards, current_round, big_blind, small_blind, min_raise):
        # Ensure all player objects have the 'is_my_player' key
        for player in players:
            if 'is_my_player' not in player:
                player['is_my_player'] = False # Default to False if not specified
            if 'hand' not in player: # Ensure 'hand' key for opponents if not set by helper
                 player['hand'] = []
            if 'preflop_strength' not in player: # Ensure 'preflop_strength' key
                 player['preflop_strength'] = 0.0


        return {
            "players": players,
            "pot_size": pot_size,
            "community_cards": community_cards,
            "current_round": current_round,
            "big_blind": big_blind,
            "small_blind": small_blind,
            "min_raise": min_raise, # This is min additional raise amount
            "betting_history": [], # Add empty betting history
            "board": community_cards, # Ensure board is present
            "street": current_round, # Ensure street is present
        }

    # New Test Scenarios
    def test_preflop_utg_marginal_hand_fold(self):
        """Pre-Flop: Bot has a marginal hand (JTs) UTG (3-handed), should fold."""
        my_player_index = 0 # Bot is UTG
        bot_hand = ['Js', 'Ts'] # Jack-Ten suited

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='UTG', name='TestBot_UTG_Fold'
        )
        opponent_sb = self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=self.config['small_blind'], position='SB', name='Opponent_SB')
        opponent_bb = self._create_mock_opponent_data(seat='3', stack=1.0, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB')

        all_players = [my_player_obj, opponent_sb, opponent_bb]
        
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
        self.assertEqual(action, ACTION_FOLD, "Action for JTs UTG should be FOLD.")

    def test_preflop_btn_call_co_open_speculative_hand(self):
        """Pre-Flop: Bot on BTN with 87s faces a CO open-raise, should call."""
        my_player_index = 1 # Bot is BTN
        bot_hand = ['8s', '7s'] # Eight-Seven suited
        co_raise_amount = self.config['big_blind'] * 3 # e.g., 0.06

        opponent_co = self._create_mock_opponent_data(seat='1', stack=1.0, current_bet=co_raise_amount, position='CO', name='Opponent_CO_Raiser')
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True, # bet_to_call will be calculated by engine
            game_stage='Pre-Flop', position='BTN', name='TestBot_BTN_Call'
        )
        opponent_sb = self._create_mock_opponent_data(seat='3', stack=0.99, current_bet=self.config['small_blind'], position='SB', name='Opponent_SB_Post')
        opponent_bb = self._create_mock_opponent_data(seat='4', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB_Post')

        all_players = [opponent_co, my_player_obj, opponent_sb, opponent_bb]
        
        table_pot_size = co_raise_amount + self.config['small_blind'] + self.config['big_blind']
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
        self.assertEqual(action, ACTION_CALL, "Action for 87s on BTN vs CO raise should be CALL.")
        self.assertAlmostEqual(amount, co_raise_amount, delta=0.001, msg="Call amount for 87s on BTN is incorrect.")


    def test_preflop_sb_open_raise_decent_hand(self):
        """Pre-Flop: Bot in SB with A9s, folded to, should open-raise."""
        my_player_index = 0 # Bot is SB in a 2-handed scenario (SB, BB) after folds
        bot_hand = ['As', '9s'] # Ace-Nine suited

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=self.config['small_blind'], bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='SB', name='TestBot_SB_Open'
        )
        opponent_bb = self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB')
        
        # Simulate folded players for correct pot and context if necessary, but for SB vs BB, this is simpler:
        all_players = [my_player_obj, opponent_bb]
        
        table_pot_size = self.config['small_blind'] + self.config['big_blind'] # Pot before SB action
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        # Expected raise: e.g., 3xBB = 0.06
        expected_raise_total_bet = self.config['big_blind'] * 3 

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
        self.assertEqual(action, ACTION_RAISE, "Action for A9s in SB (open) should be RAISE.")
        self.assertAlmostEqual(amount, expected_raise_total_bet, delta=0.001, msg="Raise amount for A9s SB open is incorrect.")

    def test_preflop_bb_raise_vs_sb_limp_strong_hand(self):
        """Pre-Flop: Bot in BB with KQs, SB limps, Bot should raise."""
        my_player_index = 1 # Bot is BB
        bot_hand = ['Ks', 'Qd'] # King-Queen suited

        # SB posts SB (0.01), then limps by adding 0.01 to call BB. SB's total current_bet = 0.02.
        opponent_sb_limper = self._create_mock_opponent_data(
            seat='1', stack=0.98, current_bet=self.config['big_blind'], position='SB', name='Opponent_SB_Limp'
        )
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=0.98, current_bet=self.config['big_blind'], bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='BB', name='TestBot_BB_RaiseLimp'
        )
        
        all_players = [opponent_sb_limper, my_player_obj]
        
        # Pot: SB (0.01) + BB (0.02) + SB's limp call (0.01) = 0.04. Or SB (0.02) + BB (0.02) = 0.04
        table_pot_size = self.config['big_blind'] + self.config['big_blind'] # SB matched BB
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        # Expected raise: e.g., Pot (0.04) + 3xBB (0.06) = 0.10 total bet. Or 4xBB = 0.08.
        # Let's assume a raise to 4*BB = 0.08.
        expected_raise_total_bet = self.config['big_blind'] * 4 

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
        self.assertEqual(action, ACTION_RAISE, "Action for KQs in BB vs SB limp should be RAISE.")
        self.assertAlmostEqual(amount, expected_raise_total_bet, delta=0.001, msg="Raise amount for KQs BB vs SB limp is incorrect.")

    # START OF 16 NEW TEST SCENARIOS

    def test_preflop_co_open_raise_aqs_6max(self):
        """Pre-Flop: Bot on CO with AQs (6-max), UTG/MP fold, should open-raise."""
        my_player_index = 0 # Bot is CO after UTG/MP fold
        bot_hand = ['As', 'Qh'] # Ace-Queen suited

        # Players: CO (Bot), BTN, SB, BB
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='CO', name='TestBot_CO_OpenAQ'
        )
        opponent_btn = self._create_mock_opponent_data(seat='4', stack=1.0, current_bet=0, position='BTN', name='Opponent_BTN')
        opponent_sb = self._create_mock_opponent_data(seat='5', stack=0.99, current_bet=self.config['small_blind'], position='SB', name='Opponent_SB')
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB')

        all_players = [my_player_obj, opponent_btn, opponent_sb, opponent_bb]
        
        table_pot_size = self.config['small_blind'] + self.config['big_blind'] # Blinds posted
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        expected_raise_total_bet = self.config['big_blind'] * 3 # Standard open to 3BB (0.06)

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players, pot_size=table['pot_size'], community_cards=table['community_cards'],
                current_round="preflop", big_blind=self.config['big_blind'], small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ), my_player_index
        )
        self.assertEqual(action, ACTION_RAISE, "Action for AQs CO open should be RAISE.")
        self.assertAlmostEqual(amount, expected_raise_total_bet, delta=0.001, msg="Raise amount for AQs CO open is incorrect.")

    def test_preflop_btn_open_raise_t9s_6max(self):
        """Pre-Flop: Bot on BTN with T9s (6-max), folds to BTN, should open-raise."""
        my_player_index = 0 # Bot is BTN after folds
        bot_hand = ['Ts', '9s'] # Ten-Nine suited

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='BTN', name='TestBot_BTN_OpenT9s'
        )
        opponent_sb = self._create_mock_opponent_data(seat='5', stack=0.99, current_bet=self.config['small_blind'], position='SB', name='Opponent_SB')
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB')

        all_players = [my_player_obj, opponent_sb, opponent_bb]
        
        table_pot_size = self.config['small_blind'] + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        expected_raise_total_bet = self.config['big_blind'] * 2.5 # BTN open to 2.5BB (0.05)

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players, pot_size=table['pot_size'], community_cards=table['community_cards'],
                current_round="preflop", big_blind=self.config['big_blind'], small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ), my_player_index
        )
        self.assertEqual(action, ACTION_RAISE, "Action for T9s BTN open should be RAISE.")
        self.assertAlmostEqual(amount, expected_raise_total_bet, delta=0.001, msg="Raise amount for T9s BTN open is incorrect.")

    def test_preflop_mp_open_raise_99_6max(self):
        """Pre-Flop: Bot in MP with 99 (6-max), UTG folds, should open-raise."""
        my_player_index = 0 # Bot is MP after UTG folds
        bot_hand = ['9h', '9d'] # Pocket Nines

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='MP', name='TestBot_MP_Open99'
        )
        # Assuming MP is followed by CO, BTN, SB, BB in a 6-max game
        opponent_co = self._create_mock_opponent_data(seat='3', stack=1.0, current_bet=0, position='CO', name='Opponent_CO')
        opponent_btn = self._create_mock_opponent_data(seat='4', stack=1.0, current_bet=0, position='BTN', name='Opponent_BTN')
        opponent_sb = self._create_mock_opponent_data(seat='5', stack=0.99, current_bet=self.config['small_blind'], position='SB', name='Opponent_SB')
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB')

        all_players = [my_player_obj, opponent_co, opponent_btn, opponent_sb, opponent_bb]
        
        table_pot_size = self.config['small_blind'] + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        expected_raise_total_bet = self.config['big_blind'] * 3 # MP open to 3BB (0.06)

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players, pot_size=table['pot_size'], community_cards=table['community_cards'],
                current_round="preflop", big_blind=self.config['big_blind'], small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ), my_player_index
        )
        self.assertEqual(action, ACTION_RAISE, "Action for 99 MP open should be RAISE.")
        self.assertAlmostEqual(amount, expected_raise_total_bet, delta=0.001, msg="Raise amount for 99 MP open is incorrect.")

    def test_preflop_sb_3bet_a5s_vs_btn_open_3handed(self):
        """Pre-Flop: Bot in SB with A5s (3-handed), BTN opens, SB should 3-bet."""
        my_player_index = 1 # BTN, SB (Bot), BB
        bot_hand = ['As', '5s'] # Ace-Five suited (bluff 3-bet candidate)
        btn_open_amount = self.config['big_blind'] * 2.5 # BTN opens to 0.05

        opponent_btn = self._create_mock_opponent_data(
            seat='4', stack=0.95, current_bet=btn_open_amount, position='BTN', name='Opponent_BTN_Raiser', has_turn=False
        )
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=0.99, current_bet=self.config['small_blind'], bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='SB', name='TestBot_SB_3betA5s'
        )
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB')

        all_players = [opponent_btn, my_player_obj, opponent_bb]
        
        # Pot: BTN's raise (0.05) + SB (0.01) + BB (0.02) = 0.08
        table_pot_size = btn_open_amount + self.config['small_blind'] + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        # Expected 3-bet: ~3x OOP raise -> 3 * 0.05 = 0.15. Or Pot (0.08) + BTN raise (0.05) = 0.13.
        # Let's go with a common sizing: 3.5x the open, so 3.5 * 0.05 = 0.175. Or fixed 9BB (0.18)
        expected_3bet_total_bet = self.config['big_blind'] * 9 # 9BB = 0.18

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players, pot_size=table['pot_size'], community_cards=table['community_cards'],
                current_round="preflop", big_blind=self.config['big_blind'], small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ), my_player_index
        )
        self.assertEqual(action, ACTION_RAISE, "Action for A5s SB vs BTN open should be 3-bet (RAISE).")
        self.assertAlmostEqual(amount, expected_3bet_total_bet, delta=0.005, msg="3-bet amount for A5s SB is incorrect.") # Increased delta for sizing variations

    def test_preflop_bb_call_kjo_vs_sb_open_hu(self):
        """Pre-Flop: Bot in BB with KJo (Heads-Up), SB opens, BB should call."""
        my_player_index = 1 # SB, BB (Bot)
        bot_hand = ['Kh', 'Jd'] # King-Jack offsuit
        sb_open_amount = self.config['big_blind'] * 3 # SB opens to 3BB (0.06)

        opponent_sb = self._create_mock_opponent_data(
            seat='5', stack=0.93, current_bet=sb_open_amount, position='SB', name='Opponent_SB_Raiser', has_turn=False # SB already includes its blind in raise
        )
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=0.98, current_bet=self.config['big_blind'], bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='BB', name='TestBot_BB_CallKJo'
        )
        all_players = [opponent_sb, my_player_obj]
        
        # Pot: SB's raise (0.06) + BB's blind (0.02) = 0.08. (SB's original 0.01 is part of their 0.06 raise)
        # Or more simply: SB (0.06) + BB (0.02) = 0.08.
        # The SB's current_bet is their total bet. The pot before BB acts is SB_total_bet + BB_blind.
        table_pot_size = sb_open_amount + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        expected_call_amount = sb_open_amount - self.config['big_blind'] # BB needs to call the difference

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players, pot_size=table['pot_size'], community_cards=table['community_cards'],
                current_round="preflop", big_blind=self.config['big_blind'], small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ), my_player_index
        )
        self.assertEqual(action, ACTION_CALL, "Action for KJo BB vs SB open (HU) should be CALL.")
        self.assertAlmostEqual(amount, expected_call_amount, delta=0.001, msg="Call amount for KJo BB is incorrect.")

    def test_preflop_utg_fold_ajo_vs_mp_3bet_6max(self):
        """Pre-Flop: Bot UTG opens AJo, MP 3-bets, Bot should fold."""
        my_player_index = 0 # UTG (Bot), MP, CO, BTN, SB, BB
        bot_hand = ['Ad', 'Jo'] # Ace-Jack offsuit
        utg_open_amount = self.config['big_blind'] * 3 # UTG opens to 0.06
        mp_3bet_amount = utg_open_amount * 3 # MP 3-bets to 0.18

        # Bot (UTG) has opened, MP has 3-bet. Action is back on Bot.
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0 - utg_open_amount, current_bet=utg_open_amount, bet_to_call=0, has_turn=True, # bet_to_call calculated by engine
            game_stage='Pre-Flop', position='UTG', name='TestBot_UTG_FoldTo3Bet'
        )
        opponent_mp = self._create_mock_opponent_data(
            seat='2', stack=1.0 - mp_3bet_amount, current_bet=mp_3bet_amount, position='MP', name='Opponent_MP_3bettor', has_turn=False
        )
        # Other players folded or yet to act, for simplicity focus on UTG and MP
        opponent_co = self._create_mock_opponent_data(seat='3', stack=1.0, current_bet=0, position='CO', name='Opponent_CO', isFolded=True) # Assume CO,BTN folded
        opponent_btn = self._create_mock_opponent_data(seat='4', stack=1.0, current_bet=0, position='BTN', name='Opponent_BTN', isFolded=True)
        opponent_sb = self._create_mock_opponent_data(seat='5', stack=0.99, current_bet=self.config['small_blind'], position='SB', name='Opponent_SB', isFolded=True) # SB folded original blind
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB', isFolded=True) # BB folded original blind

        all_players = [my_player_obj, opponent_mp, opponent_co, opponent_btn, opponent_sb, opponent_bb] # Include folded for pot calc if needed
        
        # Pot: UTG open (0.06) + MP 3bet (0.18) + SB (0.01) + BB (0.02) = 0.27 (assuming SB/BB folded their blinds)
        table_pot_size = utg_open_amount + mp_3bet_amount + self.config['small_blind'] + self.config['big_blind']
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
        self.assertEqual(action, ACTION_FOLD, "Action for AJo UTG vs MP 3-bet should be FOLD.")

    def test_preflop_co_call_3bet_kqs_vs_btn_6max(self):
        """Pre-Flop: Bot CO opens KQs, BTN 3-bets, Bot should call."""
        my_player_index = 0 # CO (Bot), BTN, SB, BB (UTG/MP folded implicitly)
        bot_hand = ['Ks', 'Qs'] # King-Queen suited
        co_open_amount = self.config['big_blind'] * 3 # CO opens to 0.06
        btn_3bet_amount = co_open_amount * 3 # BTN 3-bets to 0.18

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0 - co_open_amount, current_bet=co_open_amount, bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='CO', name='TestBot_CO_Call3Bet'
        )
        opponent_btn = self._create_mock_opponent_data(
            seat='4', stack=1.0 - btn_3bet_amount, current_bet=btn_3bet_amount, position='BTN', name='Opponent_BTN_3bettor', has_turn=False
        )
        opponent_sb = self._create_mock_opponent_data(seat='5', stack=0.99, current_bet=self.config['small_blind'], position='SB', name='Opponent_SB', isFolded=True)
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB', isFolded=True)

        all_players = [my_player_obj, opponent_btn, opponent_sb, opponent_bb]
        
        # Pot: CO open (0.06) + BTN 3bet (0.18) + SB (0.01) + BB (0.02) = 0.27
        table_pot_size = co_open_amount + btn_3bet_amount + self.config['small_blind'] + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        expected_call_amount = btn_3bet_amount - co_open_amount # Call additional amount needed (0.18 - 0.06 = 0.12)

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players, pot_size=table['pot_size'], community_cards=table['community_cards'],
                current_round="preflop", big_blind=self.config['big_blind'], small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ), my_player_index
        )
        self.assertEqual(action, ACTION_CALL, "Action for KQs CO vs BTN 3-bet should be CALL.")
        self.assertAlmostEqual(amount, expected_call_amount, delta=0.001, msg="Call amount for KQs CO vs BTN 3-bet is incorrect.")

    def test_preflop_btn_4bet_kk_vs_sb_3bet_6max(self):
        """Pre-Flop: Bot BTN opens KK, SB 3-bets, Bot should 4-bet."""
        my_player_index = 0 # BTN (Bot), SB, BB (others folded)
        bot_hand = ['Kc', 'Kh'] # Pocket Kings
        btn_open_amount = self.config['big_blind'] * 2.5 # BTN opens to 0.05
        sb_3bet_amount = btn_open_amount * 3.6 # SB 3-bets to 0.18 (9BB)

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0 - btn_open_amount, current_bet=btn_open_amount, bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='BTN', name='TestBot_BTN_4BetKK'
        )
        opponent_sb = self._create_mock_opponent_data(
            seat='5', stack=1.0 - sb_3bet_amount, current_bet=sb_3bet_amount, position='SB', name='Opponent_SB_3bettor', has_turn=False
        )
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB', isFolded=True) # BB folds to 3bet

        all_players = [my_player_obj, opponent_sb, opponent_bb]
        
        # Pot: BTN open (0.05) + SB 3bet (0.18) + BB blind (0.02, folded) = 0.25
        table_pot_size = btn_open_amount + sb_3bet_amount + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        # Expected 4-bet: ~2.2x to 2.5x the 3-bet total. 2.3 * 0.18 = 0.414. Let's say 0.42 (21BB)
        expected_4bet_total_bet = self.config['big_blind'] * 21 # 0.42

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players, pot_size=table['pot_size'], community_cards=table['community_cards'],
                current_round="preflop", big_blind=self.config['big_blind'], small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ), my_player_index
        )
        self.assertEqual(action, ACTION_RAISE, "Action for KK BTN vs SB 3-bet should be 4-bet (RAISE).")
        self.assertAlmostEqual(amount, expected_4bet_total_bet, delta=0.01, msg="4-bet amount for KK BTN is incorrect.") # Higher delta for larger bets

    def test_preflop_sb_call_66_vs_btn_open_6max(self):
        """Pre-Flop: Bot SB with 66, BTN opens, Bot should call (set-mining)."""
        my_player_index = 1 # BTN, SB (Bot), BB
        bot_hand = ['6s', '6h'] # Pocket Sixes
        btn_open_amount = self.config['big_blind'] * 2.5 # BTN opens to 0.05

        opponent_btn = self._create_mock_opponent_data(
            seat='4', stack=0.95, current_bet=btn_open_amount, position='BTN', name='Opponent_BTN_Raiser', has_turn=False
        )
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=0.99, current_bet=self.config['small_blind'], bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='SB', name='TestBot_SB_Call66'
        )
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB')

        all_players = [opponent_btn, my_player_obj, opponent_bb]
        
        table_pot_size = btn_open_amount + self.config['small_blind'] + self.config['big_blind'] # 0.05 + 0.01 + 0.02 = 0.08
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        expected_call_amount = btn_open_amount - self.config['small_blind'] # Call additional amount needed (0.05 - 0.01 = 0.04)

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players, pot_size=table['pot_size'], community_cards=table['community_cards'],
                current_round="preflop", big_blind=self.config['big_blind'], small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ), my_player_index
        )
        self.assertEqual(action, ACTION_CALL, "Action for 66 SB vs BTN open should be CALL.")
        self.assertAlmostEqual(amount, expected_call_amount, delta=0.001, msg="Call amount for 66 SB is incorrect.")

    def test_preflop_bb_fold_94o_vs_utg_open_6max(self):
        """Pre-Flop: Bot BB with 94o, UTG opens, folds to BB, Bot should fold."""
        my_player_index = 1 # UTG, BB (Bot) - others folded
        bot_hand = ['9c', '4d'] # Nine-Four offsuit
        utg_open_amount = self.config['big_blind'] * 3 # UTG opens to 0.06

        opponent_utg = self._create_mock_opponent_data(
            seat='1', stack=0.94, current_bet=utg_open_amount, position='UTG', name='Opponent_UTG_Raiser', has_turn=False
        )
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=0.98, current_bet=self.config['big_blind'], bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='BB', name='TestBot_BB_Fold94o'
        )
        # Assume MP, CO, BTN, SB folded. SB's blind is in the pot.
        all_players = [opponent_utg, my_player_obj] # Simplified for direct confrontation
        
        # Pot: UTG open (0.06) + SB blind (0.01) + BB blind (0.02) = 0.09
        table_pot_size = utg_open_amount + self.config['small_blind'] + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players, pot_size=table['pot_size'], community_cards=table['community_cards'],
                current_round="preflop", big_blind=self.config['big_blind'], small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ), my_player_index
        )
        self.assertEqual(action, ACTION_FOLD, "Action for 94o BB vs UTG open should be FOLD.")

    def test_preflop_mp_call_t9s_vs_utg_open_6max(self):
        """Pre-Flop: Bot MP with T9s, UTG opens, Bot should call."""
        my_player_index = 1 # UTG, MP (Bot), CO, BTN, SB, BB
        bot_hand = ['Ts', '9s'] # Ten-Nine suited
        utg_open_amount = self.config['big_blind'] * 3 # UTG opens to 0.06

        opponent_utg = self._create_mock_opponent_data(
            seat='1', stack=0.94, current_bet=utg_open_amount, position='UTG', name='Opponent_UTG_Raiser', has_turn=False
        )
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='MP', name='TestBot_MP_CallT9s'
        )
        opponent_co = self._create_mock_opponent_data(seat='3', stack=1.0, current_bet=0, position='CO', name='Opponent_CO')
        opponent_btn = self._create_mock_opponent_data(seat='4', stack=1.0, current_bet=0, position='BTN', name='Opponent_BTN')
        opponent_sb = self._create_mock_opponent_data(seat='5', stack=0.99, current_bet=self.config['small_blind'], position='SB', name='Opponent_SB')
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB')

        all_players = [opponent_utg, my_player_obj, opponent_co, opponent_btn, opponent_sb, opponent_bb]
        
        # Pot: UTG open (0.06) + SB (0.01) + BB (0.02) = 0.09
        table_pot_size = utg_open_amount + self.config['small_blind'] + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        expected_call_amount = utg_open_amount

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players, pot_size=table['pot_size'], community_cards=table['community_cards'],
                current_round="preflop", big_blind=self.config['big_blind'], small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ), my_player_index
        )
        self.assertEqual(action, ACTION_CALL, "Action for T9s MP vs UTG open should be CALL.")
        self.assertAlmostEqual(amount, expected_call_amount, delta=0.001, msg="Call amount for T9s MP is incorrect.")

    def test_preflop_btn_squeeze_jj_vs_utg_open_mp_3bet_6max(self):
        """Pre-Flop: Bot BTN with JJ, UTG opens, MP calls, Bot should squeeze."""
        my_player_index = 2 # UTG, MP, BTN (Bot), SB, BB
        bot_hand = ['Jc', 'Jh'] # Pocket Jacks
        utg_open_amount = self.config['big_blind'] * 3 # UTG opens to 0.06
        mp_call_amount = utg_open_amount # MP calls 0.06

        opponent_utg = self._create_mock_opponent_data(
            seat='1', stack=0.94, current_bet=utg_open_amount, position='UTG', name='Opponent_UTG_Raiser', has_turn=False
        )
        opponent_mp = self._create_mock_opponent_data(
            seat='2', stack=0.94, current_bet=mp_call_amount, position='MP', name='Opponent_MP_Caller', has_turn=False
        )
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='BTN', name='TestBot_BTN_SqueezeJJ'
        )
        opponent_sb = self._create_mock_opponent_data(seat='5', stack=0.99, current_bet=self.config['small_blind'], position='SB', name='Opponent_SB')
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB')

        all_players = [opponent_utg, opponent_mp, my_player_obj, opponent_sb, opponent_bb]
        
        # Pot: UTG open (0.06) + MP call (0.06) + SB (0.01) + BB (0.02) = 0.15
        table_pot_size = utg_open_amount + mp_call_amount + self.config['small_blind'] + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        # Expected squeeze: Pot (0.15) + 2*OriginalRaise (2*0.06=0.12) = 0.27. Or 4-5x original raise. 4.5 * 0.06 = 0.27 (13.5BB)
        expected_squeeze_total_bet = self.config['big_blind'] * 13.5 # 0.27

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players, pot_size=table['pot_size'], community_cards=table['community_cards'],
                current_round="preflop", big_blind=self.config['big_blind'], small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ), my_player_index
        )
        self.assertEqual(action, ACTION_RAISE, "Action for JJ BTN squeeze should be RAISE.")
        self.assertAlmostEqual(amount, expected_squeeze_total_bet, delta=0.01, msg="Squeeze amount for JJ BTN is incorrect.")

    def test_preflop_sb_fold_kto_vs_co_open_6max(self):
        """Pre-Flop: Bot SB with KTo, CO opens, Bot should fold."""
        my_player_index = 1 # CO, SB (Bot), BB
        bot_hand = ['Kd', 'Tc'] # King-Ten offsuit
        co_open_amount = self.config['big_blind'] * 3 # CO opens to 0.06

        opponent_co = self._create_mock_opponent_data(
            seat='3', stack=0.94, current_bet=co_open_amount, position='CO', name='Opponent_CO_Raiser', has_turn=False
        )
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=0.99, current_bet=self.config['small_blind'], bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='SB', name='TestBot_SB_FoldKTo'
        )
        opponent_bb = self._create_mock_opponent_data(seat='6', stack=0.98, current_bet=self.config['big_blind'], position='BB', name='Opponent_BB')

        all_players = [opponent_co, my_player_obj, opponent_bb]
        
        # Pot: CO open (0.06) + SB (0.01) + BB (0.02) = 0.09
        table_pot_size = co_open_amount + self.config['small_blind'] + self.config['big_blind']
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
        self.assertEqual(action, ACTION_FOLD, "Action for KTo SB vs CO open should be FOLD.")

    def test_preflop_bb_3bet_ako_vs_co_open_6max(self):
        """Pre-Flop: Bot BB with AKo, CO opens, folds to BB, Bot should 3-bet."""
        my_player_index = 1 # CO, BB (Bot) - SB folded
        bot_hand = ['Ad', 'Kc'] # Ace-King offsuit
        co_open_amount = self.config['big_blind'] * 3 # CO opens to 0.06

        opponent_co = self._create_mock_opponent_data(
            seat='3', stack=0.94, current_bet=co_open_amount, position='CO', name='Opponent_CO_Raiser', has_turn=False
        )
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=0.98, current_bet=self.config['big_blind'], bet_to_call=0, has_turn=True,
            game_stage='Pre-Flop', position='BB', name='TestBot_BB_3betAKo'
        )
        # SB folded, their blind is in the pot.
        all_players = [opponent_co, my_player_obj] # Simplified
        
        # Pot: CO open (0.06) + SB blind (0.01) + BB blind (0.02) = 0.09
        table_pot_size = co_open_amount + self.config['small_blind'] + self.config['big_blind']
        table = self._create_mock_table_data(community_cards=[], pot_size=table_pot_size, game_stage='Pre-Flop')

        # Expected 3-bet OOP: ~4x open raise. 4 * 0.06 = 0.24 (12BB)
        expected_3bet_total_bet = self.config['big_blind'] * 12 # 0.24

        action, amount = self.bot.decision_engine.make_decision(
            self._create_game_state(
                players=all_players, pot_size=table['pot_size'], community_cards=table['community_cards'],
                current_round="preflop", big_blind=self.config['big_blind'], small_blind=self.config['small_blind'],
                min_raise=self.config['big_blind'] * 2
            ), my_player_index
        )
        self.assertEqual(action, ACTION_RAISE, "Action for AKo BB vs CO open should be 3-bet (RAISE).")
        self.assertAlmostEqual(amount, expected_3bet_total_bet, delta=0.005, msg="3-bet amount for AKo BB is incorrect.")

if __name__ == '__main__':
    unittest.main()