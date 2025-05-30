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
        # Potentially add big_blind, small_blind to self.config if not already there
        # self.big_blind = self.config.get('big_blind', 0.02) 
        # self.small_blind = self.config.get('small_blind', 0.01)

    def make_decision(self, game_state, player_index):
        all_players = game_state['players']
        my_player = all_players[player_index]
        pot_size = game_state['pot_size']
        current_round = game_state['current_round']
        
        print(f"DEBUG ENGINE: make_decision for player_index: {player_index}, name: {my_player.get('name')}", file=sys.stderr)
        print(f"DEBUG ENGINE: pot_size: {pot_size}, my_current_bet: {my_player.get('current_bet', 0)}", file=sys.stderr)
        print(f"DEBUG ENGINE: Player states at entry (from all_players as received by make_decision):", file=sys.stderr)
        for p_idx, p_state in enumerate(all_players):
            if p_state:
                print(f"    - Player {p_idx} ({p_state.get('name', 'N/A')}): current_bet={p_state.get('current_bet', 0)}, isFolded={p_state.get('isFolded', False)}", file=sys.stderr)
            else:
                print(f"    - Player {p_idx}: None", file=sys.stderr)
        sys.stderr.flush()

        max_bet_on_table = 0
        active_player_bets = [p.get('current_bet', 0) for p in all_players if p and not p.get('isFolded', False)]
        if active_player_bets:
            max_bet_on_table = max(active_player_bets)
        
        print(f"DEBUG ENGINE: max_bet_on_table calculated as: {max_bet_on_table}", file=sys.stderr)

        bet_to_call_calculated = max_bet_on_table - my_player.get('current_bet', 0)
        bet_to_call_calculated = max(0, bet_to_call_calculated)

        print(f"DEBUG ENGINE: bet_to_call_calculated: {bet_to_call_calculated} (max_bet: {max_bet_on_table} - my_bet: {my_player.get('current_bet', 0)})", file=sys.stderr)
        sys.stderr.flush()

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
                my_player=my_player, # Pass the whole my_player object
                hand_category=hand_category,
                position=my_player['position'],
                bet_to_call=bet_to_call_calculated,
                can_check=can_check,
                my_stack=my_player['stack'],
                pot_size=pot_size,
                active_opponents_count=active_opponents_count,
                small_blind=game_state['small_blind'],
                big_blind=game_state['big_blind'],
                my_current_bet_this_street=my_player.get('current_bet', 0),
                max_bet_on_table=max_bet_on_table, # Renamed from max_opponent_bet for clarity in preflop_logic
                min_raise=game_state.get('min_raise', game_state['big_blind'] * 2),
                is_sb=is_sb,
                is_bb=is_bb,
                action_fold_const=ACTION_FOLD,
                action_check_const=ACTION_CHECK,
                action_call_const=ACTION_CALL,
                action_raise_const=ACTION_RAISE
            )
        else: # postflop
            print(f"  DEBUG ENGINE: PRE-CALL to make_postflop_decision: bet_to_call_calculated={bet_to_call_calculated}, max_bet_on_table={max_bet_on_table}", file=sys.stderr)
            sys.stderr.flush()
            action, amount = make_postflop_decision(
                hand=my_player['hand'],
                community_cards=game_state['community_cards'],
                position=my_player['position'],
                bet_to_call=bet_to_call_calculated,
                can_check=can_check,
                my_stack=my_player['stack'],
                pot_size=pot_size,
                active_opponents_count=active_opponents_count,
                big_blind=game_state['big_blind'],
                my_current_bet=my_player.get('current_bet', 0),
                max_opponent_bet=max_bet_on_table,
                min_raise=game_state.get('min_raise', game_state['big_blind'] * 2)
            )
        
        amount = float(amount) if amount is not None else 0.0
        if action == ACTION_CHECK or action == ACTION_FOLD:
            amount = 0.0

        return action, amount
