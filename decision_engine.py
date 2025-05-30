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

logger = logging.getLogger(__name__)

class DecisionEngine:
    def __init__(self, big_blind=0.02, small_blind=0.01):
        self.big_blind = big_blind
        self.small_blind = small_blind
        self.equity_calculator = EquityCalculator()
        self.opponent_models = {} 
        self.HAND_RANK_STRENGTH = {
            "Royal Flush": 10, "Straight Flush": 9, "Four of a Kind": 8,
            "Full House": 7, "Flush": 6, "Straight": 5,
            "Three of a Kind": 4, "Two Pair": 3, "One Pair": 2,            "High Card": 1, "N/A": 0
        }
        self.base_aggression_factor = 1.4  # Increased from 1.3
        self.base_aggression_factor_postflop = 1.0  # Increased from 0.8

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
                              ACTION_CALL, ACTION_RAISE) # Pass action constants

    def _get_opponent_tendencies_wrapper(self, player_name):
        return get_opponent_tendencies(self.opponent_models, player_name)


    def make_decision(self, my_player, table_data, all_players_data):
        """
        Enhanced decision making with EV calculations, win probability, and proper pot odds
        """
        pot_odds_to_call = 0.0
        if not my_player or not my_player.get('has_turn'):
            return "Not my turn or player data missing."

        aggression_factor = self.base_aggression_factor

        hand_evaluation_tuple = my_player.get('hand_evaluation') 
        if not hand_evaluation_tuple or not isinstance(hand_evaluation_tuple, tuple) or len(hand_evaluation_tuple) < 3:
            return ACTION_FOLD, 0

        numerical_hand_rank = get_hand_strength_value(hand_evaluation_tuple) # from hand_utils
        hand_description = hand_evaluation_tuple[1]
        my_hole_cards_str_list = my_player.get('hole_cards', []) # Ensure we get actual hole cards

        pot_size_str = table_data.get('pot_size', "0").replace('$', '').replace(',', '').replace('€', '')
        try:
            pot_size = float(pot_size_str)
        except ValueError:
            pot_size = 0.0
        
        my_stack_str = my_player.get('stack', '0').replace('$', '').replace(',', '').replace('€', '')
        try:
            my_stack = float(my_stack_str)
        except ValueError:
            my_stack = self.big_blind * 100

        active_opponents_count = 0
        max_bet_on_table = 0.0 # Max bet from other players
        
        for p in all_players_data:
            if p.get('is_empty', False): # Skip empty seats
                continue
            
            if p.get('is_my_player', False): # Skip myself
                continue
            
            # p is an opponent.
            # Count them if they are active and haven't folded.
            # is_active should be True if they are in the hand.
            # bet != 'folded' is an additional check.
            if p.get('is_active', False) and str(p.get('bet', '0')).lower() != 'folded':
                active_opponents_count += 1
            
            # Update max_bet_on_table with this opponent's bet if it's numeric
            try:
                player_bet_str = str(p.get('bet', '0')).replace('$', '').replace(',', '').replace('€', '')
                if player_bet_str.lower() != 'folded':
                    player_bet_value = float(player_bet_str)
                    max_bet_on_table = max(max_bet_on_table, player_bet_value)
            except ValueError:
                pass # Non-numeric bet string that isn't 'folded'
        
        my_current_bet_str = my_player.get('bet', '0').replace('$', '').replace(',', '').replace('€', '')
        try:
            my_current_bet = float(my_current_bet_str)
        except ValueError:
            my_current_bet = 0.0
            
        bet_to_call = round(max(0, max_bet_on_table - my_current_bet), 2)
        
        parsed_bet_to_call = my_player.get('bet_to_call', 0)
        if parsed_bet_to_call > 0:
            bet_to_call = parsed_bet_to_call

        can_check = (bet_to_call == 0)
        game_stage = table_data.get('game_stage', 'Preflop')
        community_cards = table_data.get('community_cards', [])

        win_probability = 0.0
        if my_hole_cards_str_list and len(my_hole_cards_str_list) == 2:
            win_prob, tie_prob, ev_multiplier = self.equity_calculator.calculate_equity_monte_carlo(
                my_hole_cards_str_list, community_cards, active_opponents_count, simulations=500
            )
            win_probability = win_prob
            print(f"DecisionEngine: Win probability: {win_probability:.3f}, Tie probability: {tie_prob:.3f}")

        if bet_to_call > 0:
            pot_odds_to_call = bet_to_call / (pot_size + bet_to_call) if (pot_size + bet_to_call) > 0 else 0
        else:
            pot_odds_to_call = 0

        print(f"DecisionEngine: Pot odds: {pot_odds_to_call:.3f}, Bet to call: {bet_to_call}, Pot size: {pot_size}")

        spr = calculate_stack_to_pot_ratio(my_stack, pot_size) # from hand_utils
        print(f"DecisionEngine: SPR: {spr:.2f}")

        # << NEW SECTION: Apply potential overrides from table_data to my_player >>
        # This assumes a convention where table_data might hold overrides for the current player.
        # The key 'player_context_overrides' is hypothetical.
        if 'player_context_overrides' in table_data and isinstance(table_data['player_context_overrides'], dict):
            print(f"DecisionEngine: Applying player_context_overrides from table_data: {table_data['player_context_overrides']}") # Debug
            my_player.update(table_data['player_context_overrides'])
        # << END NEW SECTION >>

        is_facing_all_in = (bet_to_call >= my_stack * 0.9)
        
        if is_facing_all_in:
            print(f"DecisionEngine: Facing all-in situation. Hand rank: {numerical_hand_rank}, Win prob: {win_probability:.3f}")
            
            ev_call = self._calculate_ev_wrapper(ACTION_CALL, bet_to_call, pot_size, win_probability, bet_to_call)
            ev_fold = 0.0
            
            print(f"DecisionEngine: EV of calling all-in: {ev_call:.2f}, EV of folding: {ev_fold:.2f}")
            
            # More aggressive all-in calling, especially with pairs and good aces
            min_win_prob_allin = 0.25  # Reduced from 0.3
            if numerical_hand_rank >= 2:  # Any pair
                min_win_prob_allin = 0.22  # Even more aggressive with pairs
            elif "A" in str(my_hole_cards_str_list):  # Ace high
                min_win_prob_allin = 0.28
            
            if ev_call > ev_fold and win_probability > min_win_prob_allin:
                return ACTION_CALL, min(my_stack, bet_to_call)
            else:
                return ACTION_FOLD, 0

        if game_stage == 'Preflop':
            # Pass the DecisionEngine instance itself for access to blinds, aggression factor
            return make_preflop_decision( 
                self, # Pass instance of DecisionEngine
                my_player, hand_evaluation_tuple, my_hole_cards_str_list, bet_to_call, 
                can_check, pot_size, my_stack, active_opponents_count, win_probability, pot_odds_to_call,
                max_bet_on_table, game_stage, hand_description,
                ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE, # Pass action constants
                get_preflop_hand_category, # Pass function from hand_utils
                self._calculate_ev_wrapper # Pass wrapper for EV calculation
            )

        # Post-flop decision making
        return make_postflop_decision(
            self, # Pass instance of DecisionEngine
            numerical_hand_rank, hand_description, bet_to_call, can_check, 
            pot_size, my_stack, win_probability, pot_odds_to_call, game_stage, spr,
            ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE, # Pass action constants
            self._get_optimal_bet_size_wrapper, # Pass wrapper for bet sizing
            self._calculate_ev_wrapper, # Pass wrapper for EV
            should_bluff, # Pass function from ev_utils
            my_player # Pass my_player data for context like hand_notes
        )

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
