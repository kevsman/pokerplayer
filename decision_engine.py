import sys
from equity_calculator import EquityCalculator
from ev_utils import calculate_expected_value, should_bluff, _estimate_fold_equity
from bet_utils import get_optimal_bet_size
from opponent_model_utils import update_opponent_model, get_opponent_tendencies
from hand_utils import get_hand_strength_value, calculate_stack_to_pot_ratio, get_preflop_hand_category, normalize_card_list
from preflop_decision_logic import make_preflop_decision
from postflop_decision_logic import make_postflop_decision
import logging

ACTION_FOLD = "fold"
ACTION_CHECK = "check"
ACTION_CALL = "call"
ACTION_RAISE = "raise"
ACTION_BET = "bet"
ACTION_ALL_IN = "all-in"

logger = logging.getLogger(__name__)


def parse_monetary_value(value_str_or_float):
    if isinstance(value_str_or_float, (int, float)):
        return float(value_str_or_float)
    if value_str_or_float is None or str(value_str_or_float).strip() == "":
        return 0.0
    return float(str(value_str_or_float).replace('$', '').replace(',', '').replace('€', ''))

class DecisionEngine:
    def __init__(self, hand_evaluator, config=None): 
        self.hand_evaluator = hand_evaluator
        self.config = config if config is not None else {}
        self.big_blind_amount = self.config.get('big_blind', 0.02) # Renamed for clarity
        self.small_blind_amount = self.config.get('small_blind', 0.01) # Renamed for clarity
        self.base_aggression_factor = self.config.get('base_aggression_factor_postflop', 1.0) # Renamed for clarity
        
        # Make helper functions available as instance methods or attributes
        self.get_optimal_bet_size_func = get_optimal_bet_size
        self.calculate_expected_value_func = calculate_expected_value
        self.should_bluff_func = should_bluff

    def _calculate_bet_to_call(self, my_player, all_players, player_index, big_blind_amount):
        """
        Calculates the amount the current player needs to call and the maximum bet currently on the table.
        Args:
            my_player (dict): The data for the current player.
            all_players (list): A list of data for all players.
            player_index (int): The index of the current player in all_players (currently unused).
            big_blind_amount (float): The amount of the big blind (currently unused).
        Returns:
            tuple: (bet_to_call, max_bet_on_table)
        """
        max_bet_on_table = 0.0
        for p in all_players:
            if p:  # Check if player data exists
                player_current_bet = parse_monetary_value(p.get('current_bet', 0.0))
                if player_current_bet > max_bet_on_table:
                    max_bet_on_table = player_current_bet

        my_current_bet = parse_monetary_value(my_player.get('current_bet', 0.0))
        
        bet_to_call = max_bet_on_table - my_current_bet
        
        # Ensure bet_to_call is not negative
        bet_to_call = max(0.0, bet_to_call)

        return bet_to_call, max_bet_on_table

    def make_decision(self, game_state, player_index):
        # Extract player and game state information
        my_player = game_state['players'][player_index]
        all_players = game_state['players']
        current_round = game_state['current_round']
        # Ensure pot_size is correctly retrieved and typed
        pot_value = game_state.get('pot_size', game_state.get('pot'))
        if pot_value is None:
            # Fallback if neither 'pot_size' nor 'pot' is found, though one should exist.
            # Log a warning or handle as an error if this case is not expected.
            logger.warning("Pot size not found in game_state, defaulting to 0.0. Game state keys: %s", game_state.keys())
            pot_size = 0.0
        else:
            pot_size = parse_monetary_value(pot_value) # Use existing parser

        community_cards = game_state['community_cards']

        # Evaluate hand for the current player
        # This needs to be done for both preflop (for win_probability if used) and postflop
        hand_eval_dict = self.hand_evaluator.evaluate_hand(my_player['hand'], community_cards)
        numerical_hand_rank = hand_eval_dict.get('rank_value', 0)
        hand_description = hand_eval_dict.get('description', "N/A")
        # win_probability might be calculated differently or be part of hand_eval_dict or a separate call
        # For now, let's assume it might come from hand_eval_dict or needs to be calculated
        # This is a placeholder, actual win_probability calculation might be more complex
        if 'win_probability' in my_player: # Check if win_probability is directly provided in player data (for testing)
            win_probability = my_player['win_probability']
        else:
            win_probability = hand_eval_dict.get('win_probability', 0.5) # Default if not in hand_eval_dict either
        
        # Calculate bet_to_call and max_bet_on_table
        # Pass game_state['big_blind'] directly
        bet_to_call_calculated, max_bet_on_table = self._calculate_bet_to_call(my_player, all_players, player_index, self.big_blind_amount)

        can_check = bet_to_call_calculated == 0
        active_opponents_count = sum(1 for i, p in enumerate(all_players) if p and not p.get('isFolded', False) and i != player_index)

        if current_round == 'preflop':
            print(f"  DEBUG ENGINE: PRE-CALL to make_preflop_decision: bet_to_call_calculated={bet_to_call_calculated}, max_bet_on_table={max_bet_on_table}", file=sys.stderr)
            sys.stderr.flush()
            
            # Calculate hand_category
            hand_category = get_preflop_hand_category(my_player['hand'], my_player['position'])
            
            # Determine if player is SB or BB
            is_sb = my_player['position'] == 'SB'
            is_bb = my_player['position'] == 'BB'

            action, amount = make_preflop_decision(
                my_player=my_player, 
                hand_category=hand_category,
                position=my_player['position'],
                bet_to_call=bet_to_call_calculated,
                can_check=can_check,
                my_stack=my_player['stack'],
                pot_size=pot_size,
                active_opponents_count=active_opponents_count,
                small_blind=self.small_blind_amount, # Use renamed attribute
                big_blind=self.big_blind_amount,    # Use renamed attribute
                my_current_bet_this_street=my_player.get('current_bet', 0),
                max_bet_on_table=max_bet_on_table, 
                min_raise=game_state.get('min_raise', self.big_blind_amount * 2), # Use renamed attribute
                is_sb=is_sb,
                is_bb=is_bb,
                action_fold_const=ACTION_FOLD,
                action_check_const=ACTION_CHECK,
                action_call_const=ACTION_CALL,
                action_raise_const=ACTION_RAISE
            )
        else: # postflop
            # numerical_hand_rank, hand_description, and win_probability are now in scope

            pot_odds_to_call = 0
            if (pot_size + bet_to_call_calculated) > 0:
                pot_odds_to_call = bet_to_call_calculated / (pot_size + bet_to_call_calculated)

            spr = 0
            if pot_size > 0:
                spr = my_player['stack'] / pot_size
            else: 
                spr = float('inf') if my_player['stack'] > 0 else 0
            
            print(f"  DEBUG ENGINE: PRE-CALL to make_postflop_decision: bet_to_call_calculated={bet_to_call_calculated}, max_bet_on_table={max_bet_on_table}", file=sys.stderr)
            sys.stderr.flush()
            
            action, amount = make_postflop_decision(
                decision_engine_instance=self, # Pass self to access helper funcs
                numerical_hand_rank=numerical_hand_rank, 
                hand_description=hand_description,     
                bet_to_call=bet_to_call_calculated,
                can_check=can_check,
                pot_size=pot_size,
                my_stack=my_player['stack'],
                win_probability=win_probability,       
                pot_odds_to_call=pot_odds_to_call,
                game_stage=current_round,
                spr=spr,
                action_fold_const=ACTION_FOLD,
                action_check_const=ACTION_CHECK,
                action_call_const=ACTION_CALL,
                action_raise_const=ACTION_RAISE,
                action_bet_const=ACTION_BET,
                my_player_data=my_player,
                big_blind_amount=self.big_blind_amount, # Pass renamed attribute
                base_aggression_factor=self.base_aggression_factor # Pass renamed attribute
                # Helper functions (get_optimal_bet_size_func, etc.) are now accessed via decision_engine_instance
            )
        
        amount = float(amount) if amount is not None else 0.0
        if action == ACTION_CHECK or action == ACTION_FOLD:
            amount = 0.0

        return action, amount
