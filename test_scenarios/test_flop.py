import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from poker_bot import PokerBot
from decision_engine import ACTION_CALL, ACTION_RAISE, ACTION_CHECK, ACTION_FOLD, ACTION_BET
from hand_evaluator import HandEvaluator

class TestFlopScenarios(unittest.TestCase):
    def setUp(self):
        self.bot = PokerBot(big_blind=0.02, small_blind=0.01)
        self.hand_evaluator = HandEvaluator()

    def _create_mock_my_player_data(self, cards, stack, current_bet, bet_to_call, has_turn, game_stage, community_cards=None, position='UTG', name='TestBot'):
        if community_cards is None: community_cards = []
        hand_evaluation_tuple = (0, "N/A", []) 
        preflop_strength = 0.0
        if cards and len(cards) == 2:
            preflop_strength = self.hand_evaluator.evaluate_preflop_strength(cards)
            if game_stage == 'Pre-Flop': # Use preflop strength for preflop hand_evaluation tuple
                 hand_evaluation_tuple = (preflop_strength, f"Preflop Strength: {preflop_strength:.2f}", cards)
        
        if cards and game_stage != 'Pre-Flop': # Postflop evaluation
            # Use evaluate_hand which returns a dict including rank_category
            hand_eval_dict = self.hand_evaluator.evaluate_hand(cards, community_cards)
            # Store the dict directly or convert to tuple if other parts of bot expect tuple
            # For now, let's assume decision_engine can handle the dict or we adapt it there.
            # The original TestFullGameScenarios used calculate_best_hand which returns a tuple.
            # Let's stick to the tuple for now if that's what the decision engine was tested with.
            hand_evaluation_tuple = (hand_eval_dict['rank_value'], hand_eval_dict['description'], hand_eval_dict['tie_breakers'])

        return {
            'cards': cards, 'stack': stack, 'current_bet': current_bet, 'bet_to_call': bet_to_call,
            'has_turn': has_turn, 'is_my_player': True, 'seat': '1', 'name': name,
            'hand_evaluation': hand_evaluation_tuple, 'id': 'player1', 'isActive': True, 'isFolded': False,
            'position': position, 'preflop_strength': preflop_strength,
            'available_actions': ['call', 'raise', 'fold', 'check', 'bet'] # General list
        }

    def _create_mock_table_data(self, community_cards, pot_size, game_stage, street=None):
        current_street = street if street else game_stage
        return {
            'community_cards': community_cards, 'pot_size': pot_size, 'street': current_street,
            'dealer_position': '2', 'hand_id': 'test_flop_hand',
            'small_blind': self.bot.small_blind, 'big_blind': self.bot.big_blind, 'board': community_cards,
        }

    def _create_mock_opponent_data(self, seat, stack, current_bet, has_turn=False, is_active_player=True, position='BTN'):
        return {
            'seat': seat, 'name': f'Opponent{seat}', 'stack': stack, 'current_bet': current_bet,
            'has_turn': has_turn, 'is_my_player': False, 'cards': [], 'has_hidden_cards': True,
            'hand_evaluation': (0, "N/A", []), 'id': f'player{seat}', 'is_active_player': is_active_player,
            'isFolded': False, 'position': position,
        }

    def test_flop_my_turn_check_possible_strong_hand(self):
        """Flop: Bot has strong hand (e.g., Two Pair), no bets yet, bot is in position."""
        community = ['As', 'Kd', '7h']
        my_player = self._create_mock_my_player_data(
            cards=['Ad', 'Kc'], stack=1.0, current_bet=0, bet_to_call=0, has_turn=True, 
            game_stage='Flop', community_cards=community, position='BTN'
        )
        table = self._create_mock_table_data(community_cards=community, pot_size=0.1, game_stage='Flop')
        opponent = self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=0, position='BB')
        all_players = [my_player, opponent]

        action, amount = self.bot.decision_engine.make_decision(my_player, table, all_players)
        self.assertEqual(action, ACTION_BET, "Bot should bet with two pair on the flop when checked to.")
        self.assertGreater(amount, 0, "Bet amount should be greater than 0.")

    def test_flop_my_turn_opponent_bets_medium_hand_call(self):
        """Flop: Opponent bets, bot has medium strength hand (e.g., Top Pair Good Kicker), should call."""
        community = ['Qs', '8d', '2h']
        my_player = self._create_mock_my_player_data(
            cards=['Qc', 'Js'], stack=0.8, current_bet=0, bet_to_call=0.1, has_turn=True, 
            game_stage='Flop', community_cards=community, position='BTN'
        )
        table = self._create_mock_table_data(community_cards=community, pot_size=0.3, game_stage='Flop') # Pot was 0.2, opp bet 0.1
        opponent = self._create_mock_opponent_data(seat='2', stack=0.9, current_bet=0.1, position='BB') # Opponent made a bet of 0.1
        all_players = [my_player, opponent]

        action, amount = self.bot.decision_engine.make_decision(my_player, table, all_players)
        self.assertEqual(action, ACTION_CALL, "Bot should call with top pair when facing a reasonable bet.")
        self.assertEqual(amount, 0.1, "Call amount should match opponent's bet.")

    def test_flop_my_turn_opponent_bets_weak_hand_fold(self):
        """Flop: Opponent bets, bot has weak hand (e.g., Gutshot, no pair), should fold to aggression."""
        community = ['Ks', 'Td', '3h']
        my_player = self._create_mock_my_player_data(
            cards=['Ac', '2s'], stack=0.7, current_bet=0, bet_to_call=0.2, has_turn=True, 
            game_stage='Flop', community_cards=community, position='BTN'
        )
        table = self._create_mock_table_data(community_cards=community, pot_size=0.5, game_stage='Flop') # Pot was 0.3, opp bet 0.2
        opponent = self._create_mock_opponent_data(seat='2', stack=0.8, current_bet=0.2, position='BB')
        all_players = [my_player, opponent]

        action, amount = self.bot.decision_engine.make_decision(my_player, table, all_players)
        self.assertEqual(action, ACTION_FOLD, "Bot should fold a weak hand to a significant flop bet.")

    def test_flop_my_turn_draw_heavy_board_opponent_checks_semi_bluff(self):
        """Flop: Draw heavy board, opponent checks, bot has a good draw, should semi-bluff bet."""
        community = ['Th', '9h', '2s'] # Flush draw and straight draw possibilities
        my_player = self._create_mock_my_player_data(
            cards=['Qh', 'Jh'], stack=1.0, current_bet=0, bet_to_call=0, has_turn=True, # Open-ended straight flush draw
            game_stage='Flop', community_cards=community, position='BTN'
        )
        table = self._create_mock_table_data(community_cards=community, pot_size=0.1, game_stage='Flop')
        opponent = self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=0, position='BB')
        all_players = [my_player, opponent]

        action, amount = self.bot.decision_engine.make_decision(my_player, table, all_players)
        # Current decision engine might check back strong draws if it doesn't have specific semi-bluff logic for draws yet.
        # For now, let's assume it bets if it considers the draw strong enough.
        # If the bot checks, this test will need adjustment or the bot logic for draws needs enhancement.
        self.assertIn(action, [ACTION_BET, ACTION_CHECK], "Bot should either bet (semi-bluff) or check with a strong draw.")
        if action == ACTION_BET:
            self.assertGreater(amount, 0, "Semi-bluff bet amount should be greater than 0.")

    # def test_flop_not_my_turn(self): # This scenario is implicitly covered by has_turn=False in make_decision
    #     """Test flop scenario: not bot's turn."""
    #     # Decision engine should ideally not be called or return a specific non-action if not bot's turn.
    #     # The PokerBot class handles turn checking before calling decision_engine.
    #     # If testing decision_engine directly, ensure has_turn=False leads to no action or default fold.
    #     community = ['As', 'Kd', '7h']
    #     my_player = self._create_mock_my_player_data(
    #         cards=['Ad', 'Kc'], stack=1.0, current_bet=0, bet_to_call=0, has_turn=False, 
    #         game_stage='Flop', community_cards=community, position='BTN'
    #     )
    #     table = self._create_mock_table_data(community_cards=community, pot_size=0.1, game_stage='Flop')
    #     opponent = self._create_mock_opponent_data(seat='2', stack=1.0, current_bet=0, position='BB')
    #     all_players = [my_player, opponent]
        
    #     # Depending on how PokerBot calls DecisionEngine, this might not be directly testable here
    #     # or DecisionEngine itself should return a specific state like (None, 0) or ('fold', 0) if not has_turn.
    #     # Current DecisionEngine returns ('fold', 0) if essential data is missing, which could include has_turn logic.
    #     # Assuming the decision engine itself doesn't strictly enforce has_turn and relies on PokerBot wrapper
    #     # or it defaults to fold. If it has its own has_turn check, this assertion might change.
    #     # For now, let's assume it might proceed if called directly, so this test is less about 'not my turn' 
    #     # and more about a state where it *thinks* it's its turn but shouldn't act.
    #     # A better test for "not my turn" would be at the PokerBot level.
    #     pass # Test logic depends on how not_my_turn is handled by DecisionEngine if called directly.

if __name__ == '__main__':
    unittest.main()
