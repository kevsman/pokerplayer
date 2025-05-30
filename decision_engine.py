# filepath: c:\\GitRepositories\\pokerplayer\\decision_engine.py
from equity_calculator import EquityCalculator
# Import new utility functions
from ev_utils import calculate_expected_value, should_bluff, _estimate_fold_equity
from bet_utils import get_optimal_bet_size
from opponent_model_utils import update_opponent_model, get_opponent_tendencies
from hand_utils import get_hand_strength_value, calculate_stack_to_pot_ratio, get_preflop_hand_category, normalize_card_list
from preflop_decision_logic import make_preflop_decision
from postflop_decision_logic import make_postflop_decision
import logging

# Define action constants (if not already defined globally or imported)
ACTION_FOLD = "fold"
ACTION_CHECK = "check"
ACTION_CALL = "call"
ACTION_RAISE = "raise"
ACTION_BET = "bet" # Added ACTION_BET definition
ACTION_ALL_IN = "all-in" # Added for completeness, though not directly tested yet

logger = logging.getLogger(__name__)

def parse_monetary_value(value_str_or_float):
    if isinstance(value_str_or_float, (int, float)):
        return float(value_str_or_float)
    if value_str_or_float is None or str(value_str_or_float).strip() == "":
        return 0.0
    return float(str(value_str_or_float).replace('$', '').replace(',', '').replace('€', ''))

class DecisionEngine:
    def __init__(self, hand_evaluator, config=None): # Ensure config is a dictionary
        self.hand_evaluator = hand_evaluator
        self.config = config if config is not None else {} # Initialize config as dict if None
        self.big_blind = self.config.get('big_blind', 0.02)
        self.small_blind = self.config.get('small_blind', 0.01)
        self.equity_calculator = EquityCalculator()
        self.opponent_models = {} 
        self.HAND_RANK_STRENGTH = {
            "Royal Flush": 10, "Straight Flush": 9, "Four of a Kind": 8,
            "Full House": 7, "Flush": 6, "Straight": 5,
            "Three of a Kind": 4, "Two Pair": 3, "One Pair": 2,            "High Card": 1, "N/A": 0
        }
        self.base_aggression_factor = 1.4 
        self.base_aggression_factor_postflop = 1.0

    # Wrapper methods to call the imported functions, maintaining the class structure if needed
    # or directly use the imported functions in make_decision, _make_preflop_decision, etc.

    def _calculate_ev_wrapper(self, action, amount, pot_size, win_probability, bet_to_call=0):
        return calculate_expected_value(action, amount, pot_size, win_probability,
                                        ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE,
                                        bet_to_call)

    def _get_optimal_bet_size_wrapper(self, hand_strength, pot_size, stack_size, game_stage, bluff=False):
        return get_optimal_bet_size(hand_strength, pot_size, stack_size, game_stage, self.big_blind, bluff)

    def _update_opponent_model_wrapper(self, player_name, action, amount, game_stage, pot_size, num_active_opponents_in_hand):
        update_opponent_model(self.opponent_models, player_name, action, amount, game_stage, pot_size, num_active_opponents_in_hand,
                              ACTION_CALL, ACTION_RAISE) 

    def _get_opponent_tendencies_wrapper(self, player_name):
        return get_opponent_tendencies(self.opponent_models, player_name)


    def make_decision(self, my_player, table_data, all_players_data):
        action = ACTION_FOLD  # Default action
        amount = 0

        if not my_player or not table_data:
            logger.warning("Missing my_player or table_data in make_decision")
            return ACTION_FOLD, 0

        my_cards = my_player.get('cards') 
        community_cards = table_data.get('community_cards', [])
        street = table_data.get('street', 'Pre-Flop') 

        if not my_cards:
            logger.warning("Missing my_cards in make_decision")
            return ACTION_FOLD, 0

        pot_size = parse_monetary_value(table_data.get('pot_size', "0"))
        my_stack = parse_monetary_value(my_player.get('stack', '0'))
        my_current_bet = parse_monetary_value(my_player.get('current_bet', '0'))
        
        active_opponents_count = 0
        max_opponent_bet_this_street = 0.0
        opponent_bets = []

        for p_data in all_players_data:
            if p_data.get('name') != my_player.get('name') and p_data.get('is_active_player', False):
                active_opponents_count += 1
                opponent_bet_val = parse_monetary_value(p_data.get('current_bet', '0')) # Renamed to avoid conflict
                opponent_bets.append(opponent_bet_val)
                if opponent_bet_val > max_opponent_bet_this_street:
                    max_opponent_bet_this_street = opponent_bet_val
        
        amount_to_call = max(0, max_opponent_bet_this_street - my_current_bet)

        if street == 'Pre-Flop':
            strength = self.hand_evaluator.evaluate_preflop_strength(my_cards)
            position = my_player.get('position', 'Unknown')
            
            if strength > 0.8:
                if max_opponent_bet_this_street == 0: action = ACTION_BET; amount = min(my_stack, pot_size * 0.75)
                elif amount_to_call > 0: action = ACTION_RAISE; amount = min(my_stack, max_opponent_bet_this_street * 3 + pot_size)
                else: action = ACTION_CHECK
            elif strength > 0.6:
                if max_opponent_bet_this_street == 0: action = ACTION_BET; amount = min(my_stack, pot_size * 0.5)
                elif amount_to_call > 0 and amount_to_call <= my_stack * 0.1: action = ACTION_CALL; amount = amount_to_call
                else: action = ACTION_CHECK
            elif strength > 0.4:
                if max_opponent_bet_this_street == 0 and position in ['CO', 'BTN']: action = ACTION_BET; amount = min(my_stack, pot_size * 0.5)
                elif amount_to_call == 0: action = ACTION_CHECK
                elif amount_to_call > 0 and amount_to_call <= my_stack * 0.05 and position == 'BB': action = ACTION_CALL; amount = amount_to_call
                else: action = ACTION_FOLD
            else:
                if amount_to_call == 0: action = ACTION_CHECK
                else: action = ACTION_FOLD
        else: # Post-flop
            hand_strength_info = self.hand_evaluator.evaluate_hand(my_cards, community_cards)
            hand_rank_category = hand_strength_info['rank_category']

            if hand_rank_category in ["Straight Flush", "Four of a Kind", "Full House", "Flush", "Straight"]:
                if max_opponent_bet_this_street == 0: action = ACTION_BET; amount = min(my_stack, pot_size * 0.75)
                else: action = ACTION_RAISE; amount = min(my_stack, max_opponent_bet_this_street * 2.5 + pot_size)
            elif hand_rank_category in ["Three of a Kind", "Two Pair"]:
                if max_opponent_bet_this_street == 0: action = ACTION_BET; amount = min(my_stack, pot_size * 0.6)
                elif amount_to_call > 0 and amount_to_call <= my_stack * 0.2: action = ACTION_CALL; amount = amount_to_call
                elif amount_to_call == 0: action = ACTION_CHECK
                else: action = ACTION_FOLD
            elif hand_rank_category == "One Pair":
                if max_opponent_bet_this_street == 0: action = ACTION_CHECK 
                elif amount_to_call > 0 and amount_to_call <= my_stack * 0.25: action = ACTION_CALL; amount = amount_to_call # Increased threshold from 0.1 to 0.25
                else: action = ACTION_FOLD
            else: # High Card or less
                if max_opponent_bet_this_street == 0: action = ACTION_CHECK
                else: action = ACTION_FOLD

        # Validate action and amount
        if action in [ACTION_BET, ACTION_RAISE]:
            if amount <= 0:
                if action == ACTION_RAISE and amount_to_call > 0: action = ACTION_CALL; amount = amount_to_call
                else: action = ACTION_CHECK; amount = 0
            elif amount > my_stack: amount = my_stack 
        elif action == ACTION_CALL:
            if amount_to_call == 0 and max_opponent_bet_this_street > 0: 
                 if my_current_bet < max_opponent_bet_this_street: amount = amount_to_call
                 else: action = ACTION_CHECK; amount = 0
            elif amount_to_call > my_stack: amount = my_stack 
            else: amount = amount_to_call
        elif action == ACTION_CHECK and amount_to_call > 0: 
            action = ACTION_FOLD; amount = 0 

        if action not in [ACTION_FOLD, ACTION_CHECK] and (amount is None or amount < 0):
            logger.warning(f"Invalid amount {amount} for action {action}. Defaulting.")
            if amount_to_call > 0 : action = ACTION_FOLD
            else: action = ACTION_CHECK
            amount = 0
        
        if action in [ACTION_BET, ACTION_RAISE, ACTION_CALL] and amount == my_stack:
            action = ACTION_ALL_IN 

        # logger.info(f"Final decision: {action}, Amount: {amount}")
        return action, amount

    def _get_player_info(self, player_id, game_state):
        """
        Extract and normalize player information from the game state.
        """
        player_info = game_state.get('players', {}).get(player_id, {})
        if not player_info:
            return None

        # Normalize hole_cards using the imported function
        if 'hole_cards' in player_info and player_info['hole_cards']:
            original_hole_cards = player_info['hole_cards']
            player_info['hole_cards'] = normalize_card_list(player_info['hole_cards'])
            logger.debug(f"Normalized hole_cards for {player_id}: {original_hole_cards} -> {player_info['hole_cards']}")
        
        return player_info
