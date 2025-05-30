import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from poker_bot import PokerBot
from decision_engine import ACTION_CALL, ACTION_RAISE, ACTION_CHECK, ACTION_FOLD, ACTION_BET # Added
from hand_evaluator import HandEvaluator # Added

class TestRiverScenarios(unittest.TestCase):
    def setUp(self):
        """Set up for test methods."""
        self.config = {
            'big_blind': 0.02,
            'small_blind': 0.01,
            # Add other necessary config items if your bot uses them
        }
        self.bot = PokerBot(config=self.config)
        self.hand_evaluator = HandEvaluator() # Added

    # Helper methods adapted from test_preflop.py
    def _create_mock_my_player_data(self, cards, stack, current_bet, bet_to_call, has_turn, game_stage, community_cards=None, position='UTG', name='TestBot'):
        if community_cards is None: community_cards = []
        hand_evaluation_tuple = (0, "N/A", [])
        preflop_strength = 0.0 # Not used in river, but part of the structure

        if cards and game_stage != 'Pre-Flop' and community_cards: # Ensure community_cards for post-flop
            hand_eval_dict = self.hand_evaluator.evaluate_hand(cards, community_cards)
            hand_evaluation_tuple = (hand_eval_dict['rank_value'], hand_eval_dict['description'], hand_eval_dict['tie_breakers'])
        elif cards and len(cards) == 2 and game_stage == 'Pre-Flop': # For consistency if ever needed
            preflop_strength = self.hand_evaluator.evaluate_preflop_strength(cards)
            hand_evaluation_tuple = (preflop_strength, f"Preflop Strength: {preflop_strength:.2f}", cards)


        return {
            'cards': cards, 'stack': stack, 'current_bet': current_bet, 'bet_to_call': bet_to_call,
            'has_turn': has_turn, 'is_my_player': True, 'seat': '1', 'name': name,
            'hand_evaluation': hand_evaluation_tuple, 'id': 'player1', 'isActive': True, 'isFolded': False,
            'position': position, 'preflop_strength': preflop_strength,
            'available_actions': ['call', 'raise', 'fold', 'check', 'bet']
        }

    def _create_mock_table_data(self, community_cards, pot_size, game_stage, street=None):
        current_street = street if street else game_stage
        return {
            'community_cards': community_cards, 'pot_size': pot_size, 'street': current_street,
            'dealer_position': '2', 'hand_id': 'test_river_hand',
            'small_blind': self.bot.config['small_blind'], 'big_blind': self.bot.config['big_blind'], 'board': community_cards,
        }

    def _create_mock_opponent_data(self, seat, stack, current_bet, has_turn=False, is_active_player=True, position='BTN', name=None, cards=None):
        opponent_name = name if name else f'Opponent{seat}'
        # For river tests, opponent cards might be known for specific scenarios, but usually hidden.
        # If cards are provided, it implies they are known (e.g. for equity calculation against a specific hand)
        # but the bot's decision should still be based on 'has_hidden_cards' unless it's a known showdown.
        # For decision making, bot doesn't know opponent cards.
        return {
            'seat': seat, 'name': opponent_name, 'stack': stack, 'current_bet': current_bet,
            'has_turn': has_turn, 'is_my_player': False, 'cards': cards if cards else [], 'has_hidden_cards': not bool(cards),
            'hand_evaluation': (0, "N/A", []), 'id': f'player{seat}', 'is_active_player': is_active_player,
            'isFolded': False, 'position': position,
        }

    def _create_game_state(self, players, pot_size, community_cards, current_round, big_blind, small_blind, min_raise):
        # Ensure all player objects have 'hand' and 'seat' keys
        for i, p in enumerate(players):
            if 'hand' not in p:
                p['hand'] = [] # Default to empty hand if not specified
            if 'seat' not in p:
                p['seat'] = str(i + 1) # Default seat based on index
            if 'is_my_player' not in p:
                p['is_my_player'] = False # Default
            if p.get('is_my_player', False) and 'cards' in p: # Ensure 'cards' matches 'hand' for my_player
                p['hand'] = p['cards']


        return {
            "players": players,
            "pot_size": pot_size,
            "community_cards": community_cards,
            "current_round": current_round, # e.g., "river"
            "big_blind": big_blind,
            "small_blind": small_blind,
            "min_raise": min_raise,
            "board": community_cards, # Ensure board is also present
            # Add any other keys make_decision might expect from game_state
        }

    def test_river_my_turn_value_bet(self):
        """Test river scenario: bot has a strong hand, should value bet."""
        # Scenario: Bot has nuts (e.g., Straight Flush), 1 opponent. Bot is in position (BTN).
        # Community cards: Ah Kh Qh Jh (Royal Flush possible with Th)
        # Bot hand: Th Ts (Bot has Royal Flush)
        # Opponent bets half pot on river. Bot should raise (all-in if appropriate, or substantial raise).
        
        my_player_index = 0
        bot_hand = ['Th', 'Ts'] # Example: Bot has Ten-high straight flush with community cards
        community_cards = ['Ah', 'Kh', 'Qh', 'Jh', '2c'] # River card is 2c, board gives flush draw

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0.1, has_turn=True, # Opponent bet 0.1
            game_stage='River', community_cards=community_cards, position='BTN', name='TestBot_BTN_ValueBet'
        )
        
        opponent_bet_amount = 0.1
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.9, current_bet=opponent_bet_amount, position='BB', name='Opponent_BB_RiverBet')
        ]
        
        all_players = [my_player_obj, opponents[0]]
        # Ensure 'hand' and 'seat' are correctly assigned
        for i, p_data in enumerate(all_players):
            p_data['seat'] = str(i + 1)
            if p_data.get('name') == 'TestBot_BTN_ValueBet':
                p_data['hand'] = bot_hand # Ensure bot's hand is set in the player object
                p_data['cards'] = bot_hand # Ensure 'cards' matches 'hand'
                p_data['is_my_player'] = True
            else:
                p_data['is_my_player'] = False
                if 'hand' not in p_data or not p_data['hand']:
                    p_data['hand'] = []


        # Pot size: Assume some betting on previous streets + opponent's river bet
        # Let's say pot was 0.2 before opponent's river bet of 0.1. So, current pot is 0.3.
        # Bot needs to call 0.1 first.
        # The decision engine should calculate bet_to_call based on max_bet_on_table and my_player.current_bet
        # For this setup, my_player_obj.bet_to_call is already set to 0.1.
        
        table_pot_size = 0.20 + opponent_bet_amount # Pot before bot's action, including opponent's bet
        table = self._create_mock_table_data(community_cards=community_cards, pot_size=table_pot_size, game_stage='River', street='River')

        game_state = self._create_game_state(
            players=all_players,
            pot_size=table['pot_size'],
            community_cards=table['community_cards'],
            current_round="river",
            big_blind=self.bot.config['big_blind'],
            small_blind=self.bot.config['small_blind'],
            min_raise=self.bot.config['big_blind'] * 2 # Standard min raise
        )
        
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)

        self.assertIn(action, [ACTION_RAISE, ACTION_BET], "Expected a value RAISEx (or BET if no prior bet) with a strong hand on the river.")
        self.assertGreater(amount, 0, "Value bet/raise amount should be greater than 0.")
        # More specific assertion for raise amount could be added if sizing logic is known
        # e.g. self.assertAlmostEqual(amount, expected_raise_amount, delta=0.001)


    def test_river_my_turn_bluff_catch(self):
        """Test river scenario: opponent bets, bot has a medium strength hand, decide to call or fold."""
        # Scenario: Bot has top pair, weak kicker. Opponent makes a pot-sized bet.
        my_player_index = 0
        bot_hand = ['Ac', '7s'] # Top pair (Ace) with weak kicker
        community_cards = ['Ah', 'Kd', '8c', '3h', '2s'] # Ace on board

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0.2, has_turn=True, # Opponent bet 0.2 (pot size)
            game_stage='River', community_cards=community_cards, position='BB', name='TestBot_BB_BluffCatch'
        )
        
        opponent_bet_amount = 0.20 # Pot-sized bet
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.8, current_bet=opponent_bet_amount, position='BTN', name='Opponent_BTN_RiverBetPot')
        ]
        
        all_players = [my_player_obj, opponents[0]]
        for i, p_data in enumerate(all_players):
            p_data['seat'] = str(i + 1)
            if p_data.get('name') == 'TestBot_BB_BluffCatch':
                p_data['hand'] = bot_hand
                p_data['cards'] = bot_hand
                p_data['is_my_player'] = True
            else:
                p_data['is_my_player'] = False
                if 'hand' not in p_data or not p_data['hand']:
                    p_data['hand'] = []

        # Pot size before opponent's bet was 0.2. Opponent bets 0.2. Total pot before bot action = 0.4
        table_pot_size = 0.20 + opponent_bet_amount 
        table = self._create_mock_table_data(community_cards=community_cards, pot_size=table_pot_size, game_stage='River', street='River')

        game_state = self._create_game_state(
            players=all_players,
            pot_size=table['pot_size'],
            community_cards=table['community_cards'],
            current_round="river",
            big_blind=self.bot.config['big_blind'],
            small_blind=self.bot.config['small_blind'],
            min_raise=self.bot.config['big_blind'] * 2
        )
        
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        
        self.assertIn(action, [ACTION_CALL, ACTION_FOLD], "Expected CALL or FOLD for bluff catch scenario.")
        if action == ACTION_CALL:
            self.assertAlmostEqual(amount, opponent_bet_amount, delta=0.001, msg="Call amount incorrect.")


    def test_river_not_my_turn(self):
        """Test river scenario: not bot's turn."""
        my_player_index = 0 # Bot is player 0
        bot_hand = ['Ks', 'Qs']
        community_cards = ['Ah', 'Kd', 'Qc', '7h', '2s'] # Bot has two pair

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0.1, bet_to_call=0, has_turn=False, # Not bot's turn
            game_stage='River', community_cards=community_cards, position='BTN', name='TestBot_BTN_NotTurn'
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.9, current_bet=0.1, position='BB', name='Opponent_BB_River', has_turn=True) # Opponent's turn
        ]
        
        all_players = [my_player_obj, opponents[0]]
        for i, p_data in enumerate(all_players):
            p_data['seat'] = str(i + 1)
            if p_data.get('name') == 'TestBot_BTN_NotTurn':
                p_data['hand'] = bot_hand
                p_data['cards'] = bot_hand
                p_data['is_my_player'] = True
            else:
                p_data['is_my_player'] = False
                if 'hand' not in p_data or not p_data['hand']:
                    p_data['hand'] = []

        table_pot_size = 0.30 
        table = self._create_mock_table_data(community_cards=community_cards, pot_size=table_pot_size, game_stage='River', street='River')

        game_state = self._create_game_state(
            players=all_players,
            pot_size=table['pot_size'],
            community_cards=table['community_cards'],
            current_round="river",
            big_blind=self.bot.config['big_blind'],
            small_blind=self.bot.config['small_blind'],
            min_raise=self.bot.config['big_blind'] * 2
        )
        
        # When it's not the bot's turn, make_decision might return a specific "no action"
        # or the test setup should ensure it's not called, or it handles it gracefully.
        # Assuming make_decision is robust enough or returns a clear "no action" indicator.
        # For this test, we expect the decision engine to perhaps return ('None', 0) or similar if not its turn.
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        
        # This assertion depends on how `make_decision` or the bot handles "not my turn".
        # It might return (None, 0), ('no_action', 0), or raise an error.
        # For now, let's assume it returns a non-standard action or (None, 0)
        # A common pattern is to return (None, 0) or a specific constant like NO_ACTION
        self.assertIsNone(action, "Action should be None when it's not the bot's turn.")
        self.assertEqual(amount, 0, "Amount should be 0 when it's not the bot's turn.")


    def test_river_thin_value_bet(self):
        """Test river scenario: bot has a good but not monster hand, opponent is passive, should bet for thin value."""
        # Scenario: Bot has second pair, good kicker. Checked to bot on river. Opponent is passive.
        my_player_index = 0
        bot_hand = ['Kc', 'Js'] # King high, J kicker.
        community_cards = ['Ah', 'Kd', '7c', '3h', '2s'] # Bot has second pair (Kings)

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True, # Checked to bot
            game_stage='River', community_cards=community_cards, position='BTN', name='TestBot_BTN_ThinValue'
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=0, position='BB', name='Opponent_BB_PassiveCheck') # Opponent checked
        ]
        
        all_players = [my_player_obj, opponents[0]]
        for i, p_data in enumerate(all_players):
            p_data['seat'] = str(i + 1)
            if p_data.get('name') == 'TestBot_BTN_ThinValue':
                p_data['hand'] = bot_hand
                p_data['cards'] = bot_hand
                p_data['is_my_player'] = True
            else:
                p_data['is_my_player'] = False
                if 'hand' not in p_data or not p_data['hand']:
                    p_data['hand'] = []

        table_pot_size = 0.20 # Assume some pot from previous streets
        table = self._create_mock_table_data(community_cards=community_cards, pot_size=table_pot_size, game_stage='River', street='River')

        game_state = self._create_game_state(
            players=all_players,
            pot_size=table['pot_size'],
            community_cards=table['community_cards'],
            current_round="river",
            big_blind=self.bot.config['big_blind'],
            small_blind=self.bot.config['small_blind'],
            min_raise=self.bot.config['big_blind'] * 2
        )
        
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        
        self.assertEqual(action, ACTION_BET, "Expected a BET for thin value.")
        self.assertGreater(amount, 0, "Thin value bet amount should be > 0.")
        # Bet sizing for thin value is often smaller, e.g., 1/3 to 1/2 pot.
        # self.assertLessEqual(amount, table_pot_size * 0.5, "Thin value bet should be reasonably sized.")


    def test_river_bluff_opportunity(self):
        """Test river scenario: bot has a weak hand (busted draw), opportunity to bluff."""
        # Scenario: Bot missed flush draw. Board is not scary. Opponent checked.
        my_player_index = 0
        bot_hand = ['7h', '8h'] # Busted flush draw
        community_cards = ['As', 'Kd', '2h', '9c', '3s'] # No flush, no obvious straight for bot.

        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=0, has_turn=True, # Checked to bot
            game_stage='River', community_cards=community_cards, position='BTN', name='TestBot_BTN_Bluff'
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=0, position='BB', name='Opponent_BB_CheckRiver') # Opponent checked
        ]
        
        all_players = [my_player_obj, opponents[0]]
        for i, p_data in enumerate(all_players):
            p_data['seat'] = str(i + 1)
            if p_data.get('name') == 'TestBot_BTN_Bluff':
                p_data['hand'] = bot_hand
                p_data['cards'] = bot_hand
                p_data['is_my_player'] = True
            else:
                p_data['is_my_player'] = False
                if 'hand' not in p_data or not p_data['hand']:
                    p_data['hand'] = []

        table_pot_size = 0.15 # Small pot
        table = self._create_mock_table_data(community_cards=community_cards, pot_size=table_pot_size, game_stage='River', street='River')

        game_state = self._create_game_state(
            players=all_players,
            pot_size=table['pot_size'],
            community_cards=table['community_cards'],
            current_round="river",
            big_blind=self.bot.config['big_blind'],
            small_blind=self.bot.config['small_blind'],
            min_raise=self.bot.config['big_blind'] * 2
        )
        
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        
        # Bot might check back or bluff. For this test, let's assume bluff is viable.
        self.assertIn(action, [ACTION_BET, ACTION_CHECK], "Expected a BET (bluff) or CHECK with a busted draw.")
        if action == ACTION_BET:
            self.assertGreater(amount, 0, "Bluff amount should be > 0.")
            # Bluff sizing can vary, e.g., 2/3 pot to pot size.
            # self.assertGreaterEqual(amount, table_pot_size * 0.66, "Bluff bet should be reasonably sized.")


    def test_river_check_fold_weak_hand_vs_bet(self):
        """Test river scenario: bot has weak hand, checks (or is checked to), opponent bets, bot should fold."""
        my_player_index = 0
        bot_hand = ['7d', '2c'] # Weakest possible hand
        community_cards = ['Ah', 'Ks', 'Qd', 'Jc', 'Ts'] # Straight on board, bot has nothing.

        # Opponent bets, bot to act.
        opponent_bet_amount = 0.10
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='River', community_cards=community_cards, position='BB', name='TestBot_BB_WeakFold'
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.9, current_bet=opponent_bet_amount, position='BTN', name='Opponent_BTN_BetRiver')
        ]
        
        all_players = [my_player_obj, opponents[0]]
        for i, p_data in enumerate(all_players):
            p_data['seat'] = str(i + 1)
            if p_data.get('name') == 'TestBot_BB_WeakFold':
                p_data['hand'] = bot_hand
                p_data['cards'] = bot_hand
                p_data['is_my_player'] = True
            else:
                p_data['is_my_player'] = False
                if 'hand' not in p_data or not p_data['hand']:
                    p_data['hand'] = []

        table_pot_size = 0.15 + opponent_bet_amount # Pot before bot's action
        table = self._create_mock_table_data(community_cards=community_cards, pot_size=table_pot_size, game_stage='River', street='River')

        game_state = self._create_game_state(
            players=all_players,
            pot_size=table['pot_size'],
            community_cards=table['community_cards'],
            current_round="river",
            big_blind=self.bot.config['big_blind'],
            small_blind=self.bot.config['small_blind'],
            min_raise=self.bot.config['big_blind'] * 2
        )
        
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        
        self.assertEqual(action, ACTION_FOLD, "Expected FOLD with weak hand facing bet.")


    def test_river_check_call_medium_hand_vs_bet(self):
        """Test river scenario: bot has medium hand, checks (or is checked to), opponent bets, bot calls."""
        my_player_index = 0
        bot_hand = ['Ac', 'Ts'] # Top pair, decent kicker
        community_cards = ['Ah', 'Kd', '8c', '3h', '2s'] # Ace on board

        opponent_bet_amount = 0.05 # Small bet from opponent
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0, bet_to_call=opponent_bet_amount, has_turn=True,
            game_stage='River', community_cards=community_cards, position='BB', name='TestBot_BB_MediumCall'
        )
        
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0.95, current_bet=opponent_bet_amount, position='BTN', name='Opponent_BTN_SmallRiverBet')
        ]
        
        all_players = [my_player_obj, opponents[0]]
        for i, p_data in enumerate(all_players):
            p_data['seat'] = str(i + 1)
            if p_data.get('name') == 'TestBot_BB_MediumCall':
                p_data['hand'] = bot_hand
                p_data['cards'] = bot_hand
                p_data['is_my_player'] = True
            else:
                p_data['is_my_player'] = False
                if 'hand' not in p_data or not p_data['hand']:
                    p_data['hand'] = []

        table_pot_size = 0.20 + opponent_bet_amount # Pot before bot's action
        table = self._create_mock_table_data(community_cards=community_cards, pot_size=table_pot_size, game_stage='River', street='River')

        game_state = self._create_game_state(
            players=all_players,
            pot_size=table['pot_size'],
            community_cards=table['community_cards'],
            current_round="river",
            big_blind=self.bot.config['big_blind'],
            small_blind=self.bot.config['small_blind'],
            min_raise=self.bot.config['big_blind'] * 2
        )
        
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        
        self.assertEqual(action, ACTION_CALL, "Expected CALL with medium hand facing a small bet.")
        self.assertAlmostEqual(amount, opponent_bet_amount, delta=0.001, msg="Call amount incorrect.")


    def test_river_facing_all_in_decision(self):
        """Test river scenario: bot faces an all-in bet from an opponent."""
        my_player_index = 0
        # Bot has a good hand (e.g., two pair), but not the nuts. Opponent shoves.
        bot_hand = ['Ks', 'Qh'] 
        community_cards = ['Kc', 'Qd', '7s', '2h', '3c'] # Bot has top two pair

        opponent_stack_before_all_in = 0.50
        opponent_all_in_bet = opponent_stack_before_all_in # Opponent shoves for 0.50
        
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=1.0, current_bet=0.1, bet_to_call=opponent_all_in_bet, has_turn=True, # Bot already has 0.1 in pot this street
            game_stage='River', community_cards=community_cards, position='BTN', name='TestBot_BTN_FaceAllIn'
        )
        # Opponent's current_bet should be their total bet for the street
        # If opponent had 0.1 in, then shoves remaining 0.4, total bet is 0.5
        # bet_to_call for bot is opponent_total_bet - bot_current_bet_this_street
        # Let's simplify: opponent shoves, bot has 0 current_bet this street.
        my_player_obj['current_bet'] = 0 
        my_player_obj['bet_to_call'] = opponent_all_in_bet


        opponents = [
            self._create_mock_opponent_data(seat='2', stack=0, current_bet=opponent_all_in_bet, position='BB', name='Opponent_BB_AllIn', cards=[]) # Stack is 0 after all-in
        ]
        opponents[0]['stack_before_bet'] = opponent_stack_before_all_in # For clarity if needed

        all_players = [my_player_obj, opponents[0]]
        for i, p_data in enumerate(all_players):
            p_data['seat'] = str(i + 1)
            if p_data.get('name') == 'TestBot_BTN_FaceAllIn':
                p_data['hand'] = bot_hand
                p_data['cards'] = bot_hand
                p_data['is_my_player'] = True
            else:
                p_data['is_my_player'] = False
                if 'hand' not in p_data or not p_data['hand']:
                    p_data['hand'] = []


        # Pot before opponent's all-in: e.g., 0.30. Opponent shoves 0.50. Pot becomes 0.30 + 0.50 = 0.80
        table_pot_size = 0.30 + opponent_all_in_bet
        table = self._create_mock_table_data(community_cards=community_cards, pot_size=table_pot_size, game_stage='River', street='River')

        game_state = self._create_game_state(
            players=all_players,
            pot_size=table['pot_size'],
            community_cards=table['community_cards'],
            current_round="river",
            big_blind=self.bot.config['big_blind'],
            small_blind=self.bot.config['small_blind'],
            min_raise=self.bot.config['big_blind'] * 2 
        )
        
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        
        self.assertIn(action, [ACTION_CALL, ACTION_FOLD], "Expected CALL or FOLD when facing all-in.")
        if action == ACTION_CALL:
            # Call amount should be the opponent's bet amount that bot needs to match
            # which is my_player_obj['bet_to_call']
            self.assertAlmostEqual(amount, my_player_obj['bet_to_call'], delta=0.001, msg="Call amount for all-in incorrect.")


    def test_river_making_all_in_strong_hand(self):
        """Test river scenario: bot has a very strong hand (e.g., nuts) and decides to go all-in."""
        my_player_index = 0
        bot_hand = ['Ah', 'Kh'] # Nuts (Royal Flush with Q J T on board)
        community_cards = ['Qh', 'Jh', 'Th', '2c', '3d']

        bot_stack = 1.0
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=bot_stack, current_bet=0, bet_to_call=0, has_turn=True, # Checked to bot, or bot opens
            game_stage='River', community_cards=community_cards, position='BTN', name='TestBot_BTN_MakeAllIn_Nuts'
        )
        
        opponent_stack = 0.8
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=opponent_stack, current_bet=0, position='BB', name='Opponent_BB_CanCallAllIn')
        ]
        
        all_players = [my_player_obj, opponents[0]]
        for i, p_data in enumerate(all_players):
            p_data['seat'] = str(i + 1)
            if p_data.get('name') == 'TestBot_BTN_MakeAllIn_Nuts':
                p_data['hand'] = bot_hand
                p_data['cards'] = bot_hand
                p_data['is_my_player'] = True
            else:
                p_data['is_my_player'] = False
                if 'hand' not in p_data or not p_data['hand']:
                    p_data['hand'] = []

        table_pot_size = 0.25 
        table = self._create_mock_table_data(community_cards=community_cards, pot_size=table_pot_size, game_stage='River', street='River')

        game_state = self._create_game_state(
            players=all_players,
            pot_size=table['pot_size'],
            community_cards=table['community_cards'],
            current_round="river",
            big_blind=self.bot.config['big_blind'],
            small_blind=self.bot.config['small_blind'],
            min_raise=self.bot.config['big_blind'] * 2
        )
        
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        
        # Expecting a BET. If opponent stack is smaller, it's an effective all-in for opponent.
        # If bot stack is smaller, it's an all-in for bot.
        # The decision engine should determine the bet amount. If it's all-in, amount should be its stack (or opponent's stack if less)
        self.assertIn(action, [ACTION_BET, ACTION_RAISE], "Expected BET or RAISE with the nuts.")
        # If the bot decides to go all-in, the amount should be its stack (or opponent's stack if less)
        # This depends on the bot's betting strategy with the nuts.
        # For simplicity, let's assume it bets at least a significant portion of the pot or stack.
        self.assertGreater(amount, 0)
        if bot_stack <= opponent_stack : # Bot is all-in
             if action == ACTION_BET or action == ACTION_RAISE: # Assuming all-in is a type of bet/raise
                self.assertAlmostEqual(amount, bot_stack, delta=0.001, msg="Expected bot to bet its entire stack (all-in).")
        # else: # Opponent is all-in if they call
            # self.assertAlmostEqual(amount, opponent_stack, delta=0.001, msg="Expected bot to bet opponent's stack (all-in for opponent).")
        # The above stack comparison for amount is tricky; decision engine might just bet pot or a multiple.
        # A more general check:
        self.assertTrue((action == ACTION_BET and amount > 0) or (action == ACTION_RAISE and amount > 0), "Should make a substantial bet/raise with nuts.")


    def test_river_making_all_in_bluff(self):
        """Test river scenario: bot decides to go all-in as a bluff."""
        my_player_index = 0
        bot_hand = ['7h', '2c'] # Complete air
        community_cards = ['As', 'Ks', 'Qd', '3h', '4c'] # Scary board for some hands, but bot has nothing.

        bot_stack = 0.75 # Bot has a stack to bluff with
        my_player_obj = self._create_mock_my_player_data(
            cards=bot_hand, stack=bot_stack, current_bet=0, bet_to_call=0, has_turn=True, # Checked to bot
            game_stage='River', community_cards=community_cards, position='BTN', name='TestBot_BTN_AllInBluff'
        )
        
        opponent_stack = 0.60 # Opponent has a stack that might fold
        opponents = [
            self._create_mock_opponent_data(seat='2', stack=opponent_stack, current_bet=0, position='BB', name='Opponent_BB_CanFoldToBluff')
        ]
        
        all_players = [my_player_obj, opponents[0]]
        for i, p_data in enumerate(all_players):
            p_data['seat'] = str(i + 1)
            if p_data.get('name') == 'TestBot_BTN_AllInBluff':
                p_data['hand'] = bot_hand
                p_data['cards'] = bot_hand
                p_data['is_my_player'] = True
            else:
                p_data['is_my_player'] = False
                if 'hand' not in p_data or not p_data['hand']:
                    p_data['hand'] = []

        table_pot_size = 0.10 # Small pot, making a bluff potentially effective
        table = self._create_mock_table_data(community_cards=community_cards, pot_size=table_pot_size, game_stage='River', street='River')

        game_state = self._create_game_state(
            players=all_players,
            pot_size=table['pot_size'],
            community_cards=table['community_cards'],
            current_round="river",
            big_blind=self.bot.config['big_blind'],
            small_blind=self.bot.config['small_blind'],
            min_raise=self.bot.config['big_blind'] * 2
        )
        
        action, amount = self.bot.decision_engine.make_decision(game_state, my_player_index)
        
        # Bot might check or bluff. If bluffing all-in is a strategy:
        self.assertIn(action, [ACTION_BET, ACTION_CHECK], "Expected BET (all-in bluff) or CHECK.")
        if action == ACTION_BET:
            # If bluffing all-in, amount should be bot's stack or opponent's effective stack
            effective_stack = min(bot_stack, opponent_stack)
            # The bot might not always go all-in; it might choose a large bluff bet.
            # For this test, if it bets, we assume it's a significant bluff.
            self.assertGreater(amount, 0, "Bluff bet amount must be > 0.")
            # If the strategy is specifically "all-in bluff", then:
            # self.assertAlmostEqual(amount, effective_stack, delta=0.001, msg=f"Expected all-in bluff amount to be effective stack {effective_stack}.")
            # A more general check for a large bluff:
            self.assertGreaterEqual(amount, table_pot_size, "All-in bluff should generally be at least pot sized.")


if __name__ == '__main__':
    unittest.main()
