import sys
from equity_calculator import EquityCalculator
from ev_utils import calculate_expected_value, should_bluff, _estimate_fold_equity
from bet_utils import get_optimal_bet_size
from opponent_model_utils import update_opponent_model, get_opponent_tendencies
from opponent_tracking import OpponentTracker
from tournament_adjustments import get_tournament_adjustment_factor, adjust_preflop_range_for_tournament, adjust_bet_size_for_tournament
from hand_utils import get_hand_strength_value, calculate_stack_to_pot_ratio, get_preflop_hand_category, normalize_card_list
from preflop_decision_logic import make_preflop_decision
from postflop_decision_logic import make_postflop_decision
import logging

ACTION_FOLD = "fold"
ACTION_CHECK = "check"
ACTION_CALL = "call"
ACTION_RAISE = "raise"

logger = logging.getLogger(__name__)


def parse_monetary_value(value_str_or_float):
    if isinstance(value_str_or_float, (int, float)):
        return float(value_str_or_float)
    if value_str_or_float is None or str(value_str_or_float).strip() == "" or str(value_str_or_float).strip().upper() == "N/A": # Added N/A check
        logger.warning(f"Invalid monetary value received: '{value_str_or_float}'. Defaulting to 0.0.") # Log a warning
        return 0.0
    try:
        return float(str(value_str_or_float).replace('$', '').replace(',', '').replace('€', ''))
    except ValueError:
        logger.error(f"Could not convert monetary value '{value_str_or_float}' to float. Defaulting to 0.0.")
        return 0.0

class DecisionEngine:    
    def __init__(self, hand_evaluator, config=None): 
        self.hand_evaluator = hand_evaluator
        self.config = config if config is not None else {}
        self.big_blind_amount = self.config.get_setting('big_blind', 0.02) # Renamed for clarity
        self.small_blind_amount = self.config.get_setting('small_blind', 0.01) # Renamed for clarity
        
        # Get strategy settings with increased aggression defaults
        self.base_aggression_factor = self.config.get_setting('strategy', {}).get('base_aggression_factor_postflop', 1.8)
        self.preflop_aggression_factor = self.config.get_setting('strategy', {}).get('base_aggression_factor_preflop', 2.0)
        self.bluff_frequency = self.config.get_setting('strategy', {}).get('bluff_frequency', 0.25)
        self.semi_bluff_frequency = self.config.get_setting('strategy', {}).get('semi_bluff_frequency', 0.6)
        self.continuation_bet_frequency = self.config.get_setting('strategy', {}).get('continuation_bet_frequency', 0.8)
        
        logger.info(f"Decision Engine initialized with aggression factors - preflop: {self.preflop_aggression_factor}, postflop: {self.base_aggression_factor}")
        
        # Initialize equity calculator system
        self.equity_calculator = EquityCalculator()
        
        # Initialize opponent tracking system
        self.opponent_tracker = OpponentTracker()
        
        # Tournament settings (default to cash game)
        self.tournament_level = self.config.get_setting('tournament_level', 0)  # 0 = cash game, 1-3 = tournament levels
        
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

        # Use the bet_to_call from the parsed game state if available and seems reliable
        # This value is often directly provided by the poker client's UI or logs
        parsed_bet_to_call_str = my_player.get('bet_to_call')
        if parsed_bet_to_call_str is not None:
            bet_to_call = parse_monetary_value(parsed_bet_to_call_str)
            # Sanity check: if my_player's current_bet is already max_bet_on_table, bet_to_call should be 0
            my_current_bet = parse_monetary_value(my_player.get('current_bet', 0.0))
            if my_current_bet >= max_bet_on_table:
                 bet_to_call = 0.0
            # Further sanity check: bet_to_call shouldn't exceed max_bet_on_table
            # This also implies that if bet_to_call is positive, max_bet_on_table should be > my_current_bet
            # bet_to_call = max(0.0, min(bet_to_call, max_bet_on_table - my_current_bet)) # This could be too restrictive

        else:
            # Fallback to calculating from current bets if 'bet_to_call' is not in my_player data
            my_current_bet = parse_monetary_value(my_player.get('current_bet', 0.0))
            bet_to_call = max_bet_on_table - my_current_bet
          # Ensure bet_to_call is not negative
        bet_to_call = max(0.0, bet_to_call)        # logger.debug(f"_calculate_bet_to_call: my_player_bet={my_player.get('current_bet', 0.0)}, max_bet_on_table={max_bet_on_table}, initial_parsed_b2c={parsed_bet_to_call_str}, final_b2c={bet_to_call}")
        return bet_to_call, max_bet_on_table

    def make_decision(self, game_state, player_index):
        # Extract player and game state information
        my_player = game_state['players'][player_index]

        if not my_player.get('has_turn'):
            logger.info(f"Not player {player_index}'s turn. Returning (None, 0).")
            return None, 0
        
        all_players = game_state['players']
        current_round = game_state['current_round']
        action_history = game_state.get('action_history', []) # Extract action_history
        
        pot_value = game_state.get('pot_size', game_state.get('pot'))
        if pot_value is None:
            logger.warning("Pot size not found in game_state, defaulting to 0.0. Game state keys: %s", game_state.keys())
            pot_size = 0.0
        else:
            pot_size = parse_monetary_value(pot_value)

        # Ensure my_stack is a float
        my_stack_raw = my_player.get('stack')
        if my_stack_raw is None:
            logger.warning(f"Player stack not found for player {player_index}, defaulting to 0.0.")
            my_stack = 0.0
        else:            my_stack = parse_monetary_value(my_stack_raw)

        community_cards = game_state['community_cards']
        
        # Update opponent tracking before making decision
        self.update_opponents_from_game_state(game_state, player_index)

        # Determine if this player was the pre-flop aggressor
        # This needs to be tracked across streets. For now, we check if they made the last raise preflop.
        # A more robust solution would store this state in OpponentTracker or similar.
        was_preflop_aggressor = False
        if current_round != 'preflop': # Only relevant post-flop
            # Check preflop actions from game_state if available, or rely on opponent_tracker
            # This is a simplified check. A full implementation would look at the action history.
            # For now, we'll assume if the player is in `my_player` and has a specific flag or we can infer it.
            # This part needs to be properly implemented by tracking who made the last preflop raise.
            # Placeholder: Assume it's passed in my_player data or we can retrieve it.
            if hasattr(self.opponent_tracker, 'get_preflop_aggressor_info'):
                pfr_info = self.opponent_tracker.get_preflop_aggressor_info()
                if pfr_info and pfr_info.get('name') == my_player.get('name'):
                    was_preflop_aggressor = True
                    logger.debug(f"Player {my_player.get('name')} identified as pre-flop aggressor by opponent_tracker.")
            # If not available from tracker, it might be in my_player from a previous stage or log parsing
            elif my_player.get('was_preflop_aggressor') is True:
                 was_preflop_aggressor = True
                 logger.debug(f"Player {my_player.get('name')} has 'was_preflop_aggressor' flag set to True.")
            
            # Store this in my_player data for postflop_decision_logic to use
            my_player['was_preflop_aggressor'] = was_preflop_aggressor

        # Evaluate hand for the current player
        hand_eval_dict = self.hand_evaluator.evaluate_hand(my_player['hand'], community_cards)
        numerical_hand_rank = hand_eval_dict.get('rank_value', 0)
        hand_description = hand_eval_dict.get('description', "N/A")
        
        # Ensure win_probability is a float
        raw_win_probability = my_player.get('win_probability', hand_eval_dict.get('win_probability'))
        if raw_win_probability is None:
            # Use equity calculator to compute win probability when not available
            logger.info(f"win_probability not found for player {player_index}, calculating using equity calculator.")
            try:
                # Calculate number of active opponents
                num_opponents = len([p for p in all_players if p and p.get('is_active', False) and not p.get('is_my_player', False)])
                if num_opponents == 0:
                    num_opponents = 1  # Default to 1 opponent if none found
                
                # Use equity calculator to compute win probability
                win_probability = self.equity_calculator.calculate_win_probability(
                    my_player['hand'], 
                    community_cards, 
                    num_opponents
                )
                logger.info(f"Calculated win probability using equity calculator: {win_probability:.3f} ({win_probability*100:.1f}%) vs {num_opponents} opponents")
            except Exception as e:
                logger.error(f"Error calculating win probability with equity calculator: {e}")
                win_probability = 0.5 # Fallback to default
        else:
            try:
                win_probability = float(raw_win_probability)
            except (ValueError, TypeError):
                logger.warning(f"Could not convert win_probability '{raw_win_probability}' to float. Defaulting to 0.0.")
                win_probability = 0.0 # Default to a float if conversion fails
        
        # Calculate bet_to_call and max_bet_on_table
        # Pass game_state['big_blind'] directly
        # bet_to_call_calculated, max_bet_on_table = self._calculate_bet_to_call(my_player, all_players, player_index, self.big_blind_amount)

        # Use bet_to_call directly from my_player if available, otherwise calculate it.
        # max_bet_on_table is still useful for bet sizing logic.
        max_bet_on_table = 0.0
        logger.debug(f"  DEBUG ENGINE: Calculating max_bet_on_table. Raw all_players data used by decision_engine: {all_players}")
        for i, p_data in enumerate(all_players):
            if p_data:
                player_seat = p_data.get('seat', f'index {i}')
                # Prioritize 'current_bet' as test data often uses it, fallback to 'bet'
                raw_player_bet = p_data.get('current_bet', p_data.get('bet', 0.0))
                player_current_bet = parse_monetary_value(raw_player_bet)
                logger.debug(f"  DEBUG ENGINE: Player at seat/index {player_seat} - Raw bet: '{raw_player_bet}', Parsed bet: {player_current_bet}")
                if player_current_bet > max_bet_on_table:
                    max_bet_on_table = player_current_bet
                    logger.debug(f"  DEBUG ENGINE: New max_bet_on_table: {max_bet_on_table} from player at seat/index {player_seat}")
            else:
                logger.debug(f"  DEBUG ENGINE: Player data at index {i} is None or empty.")       
        logger.debug(f"  DEBUG ENGINE: Final calculated max_bet_on_table before use: {max_bet_on_table}")
        
        my_current_bet = parse_monetary_value(my_player.get('current_bet', 0.0))
        # Debug BB bet calculation issue
        logger.info(f"DEBUG ENGINE: BB bet calculation details:")
        logger.info(f"  my_player raw current_bet: {repr(my_player.get('current_bet'))}")
        logger.info(f"  my_current_bet parsed: {my_current_bet}")
        logger.info(f"  my_player position: {my_player.get('position')}")
        logger.info(f"  my_player name: {my_player.get('name')}")
        # This is the actual amount required to call the highest bet on the table.        
        bet_to_call_calculated = max(0.0, max_bet_on_table - my_current_bet)

        # Debug BB bet calculation issue
        logger.info(f"DEBUG ENGINE: BB bet calculation details:")
        logger.info(f"  my_player raw current_bet: {repr(my_player.get('current_bet'))}")
        logger.info(f"  my_current_bet parsed: {my_current_bet}")
        logger.info(f"  max_bet_on_table: {max_bet_on_table}")
        logger.info(f"  bet_to_call_calculated: {bet_to_call_calculated}")
        logger.info(f"  my_player position: {my_player.get('position')}")
        logger.info(f"  my_player name: {my_player.get('name')}")        
        bet_to_call_str = my_player.get('bet_to_call')
        parsed_ui_bet_to_call_for_log = "N/A" # Initialize for logging
        final_bet_to_call = bet_to_call_calculated  # Default to calculated value
        if bet_to_call_str is not None:
            parsed_ui_bet_to_call_for_log = parse_monetary_value(bet_to_call_str)
            # Use explicit bet_to_call when provided (especially important for test scenarios)
            # Always trust the UI bet_to_call value when it's provided (including 0.0 for BB check scenarios)
            if parsed_ui_bet_to_call_for_log >= 0:
                final_bet_to_call = parsed_ui_bet_to_call_for_log
                if parsed_ui_bet_to_call_for_log != bet_to_call_calculated and logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Make_decision: Using explicit bet_to_call ({parsed_ui_bet_to_call_for_log}) instead of calculated ({bet_to_call_calculated})")
            elif parsed_ui_bet_to_call_for_log != bet_to_call_calculated and logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Make_decision: UI bet_to_call ({parsed_ui_bet_to_call_for_log}) differs from calculated ({bet_to_call_calculated}). Using calculated.")
        logger.debug(f"Make_decision: UI_bet_to_call_val: {parsed_ui_bet_to_call_for_log}, Calculated_bet_to_call: {bet_to_call_calculated}, Final_bet_to_call: {final_bet_to_call}, Max_bet_on_table: {max_bet_on_table}, My_current_bet: {my_current_bet}")        
        can_check = final_bet_to_call == 0
        logger.info(f"DEBUG ENGINE: can_check calculation:")
        logger.info(f"  final_bet_to_call = {final_bet_to_call} (type: {type(final_bet_to_call)})")
        logger.info(f"  final_bet_to_call == 0 = {final_bet_to_call == 0}")
        logger.info(f"  final_bet_to_call == 0.0 = {final_bet_to_call == 0.0}")
        logger.info(f"  abs(final_bet_to_call) < 1e-10 = {abs(final_bet_to_call) < 1e-10}")
        logger.info(f"  can_check = {can_check}")
        active_opponents_count = sum(1 for i, p in enumerate(all_players) if p and p.get('is_active', False) and i != player_index)
        if current_round == 'preflop':
            logger.debug(f"  DEBUG ENGINE: PRE-CALL to make_preflop_decision: final_bet_to_call={final_bet_to_call}, max_bet_on_table={max_bet_on_table}")
            
            hand_category = get_preflop_hand_category(my_player['hand'], my_player['position'])
            
            is_sb = my_player['position'] == 'SB'
            is_bb = my_player['position'] == 'BB'            # Debug logging for BB check issue
            logger.info(f"DEBUG ENGINE: Calling make_preflop_decision with:")
            logger.info(f"  - position: {my_player['position']}")
            logger.info(f"  - bet_to_call: {final_bet_to_call}")
            logger.info(f"  - can_check: {can_check}")
            logger.info(f"  - is_bb: {is_bb}")
            logger.info(f"  - hand: {my_player['hand']}")
            
            action, amount = make_preflop_decision(
                my_player=my_player, 
                hand_category=hand_category,
                position=my_player['position'],
                bet_to_call=final_bet_to_call,
                can_check=can_check,
                my_stack=my_stack, # Pass converted float stack
                pot_size=pot_size,
                active_opponents_count=active_opponents_count,
                small_blind=self.small_blind_amount,
                big_blind=self.big_blind_amount,
                my_current_bet_this_street=parse_monetary_value(my_player.get('current_bet', 0)), # Ensure this is float too
                max_bet_on_table=max_bet_on_table, 
                min_raise=parse_monetary_value(game_state.get('min_raise', self.big_blind_amount * 2)), # Ensure this is float
                is_sb=is_sb,
                is_bb=is_bb,
                action_fold_const=ACTION_FOLD,
                action_check_const=ACTION_CHECK,
                action_call_const=ACTION_CALL,
                action_raise_const=ACTION_RAISE,
                action_history=action_history # Pass action_history
            )
            
            logger.info(f"DEBUG ENGINE: make_preflop_decision returned: action={action}, amount={amount}")
            
            # Apply tournament adjustments if in tournament mode
            if self.tournament_level > 0:
                tournament_adjustments = get_tournament_adjustment_factor(
                    my_stack, self.big_blind_amount, self.tournament_level
                )
                adjusted_action = adjust_preflop_range_for_tournament(action, hand_category, tournament_adjustments)
                if adjusted_action != action:
                    logger.debug(f"Tournament adjustment: Changed {action} to {adjusted_action} for {hand_category}")
                    action = adjusted_action
                    if action == ACTION_FOLD:
                        amount = 0
                    elif action == ACTION_CALL:
                        amount = final_bet_to_call
                  # Adjust bet size for tournament if raising
                if action == ACTION_RAISE and amount > 0:
                    amount = adjust_bet_size_for_tournament(amount, pot_size, tournament_adjustments)
            
        else: # postflop
            pot_odds_to_call = 0
            if (pot_size + final_bet_to_call) > 0: # Ensure denominator is not zero
                pot_odds_to_call = final_bet_to_call / (pot_size + final_bet_to_call)

            spr = 0
            if pot_size > 0:
                spr = my_stack / pot_size # Use converted float stack
            else:
                spr = float('inf') if my_stack > 0 else 0
            
            logger.debug(f"  DEBUG ENGINE: PRE-CALL to make_postflop_decision: final_bet_to_call={final_bet_to_call}, max_bet_on_table={max_bet_on_table}")
            
            action, amount = make_postflop_decision(
                decision_engine_instance=self,
                numerical_hand_rank=numerical_hand_rank,
                hand_description=hand_description,
                bet_to_call=final_bet_to_call,
                can_check=can_check,
                pot_size=pot_size,
                my_stack=my_stack, # Pass converted float stack
                win_probability=win_probability, # Pass converted float win_probability
                pot_odds_to_call=pot_odds_to_call,
                game_stage=current_round, 
                community_cards=community_cards, # Add community_cards argument
                spr=spr,
                action_fold_const=ACTION_FOLD,
                action_check_const=ACTION_CHECK,
                action_call_const=ACTION_CALL,
                action_raise_const=ACTION_RAISE,
                my_player_data=my_player,
                all_players_raw_data=all_players, # Add this line
                big_blind_amount=self.big_blind_amount,
                base_aggression_factor=self.base_aggression_factor,
                max_bet_on_table=max_bet_on_table,
                active_opponents_count=active_opponents_count,
                opponent_tracker=self.opponent_tracker,  # Pass opponent tracking data
                action_history=action_history # Pass action_history
            )
        
        # Ensure amount is a float before returning
        if isinstance(amount, (str)):
            try:
                amount = float(amount)
            except ValueError:
                logger.error(f"Could not convert action amount '{amount}' to float. Defaulting to 0.0.")
                amount = 0.0
        elif not isinstance(amount, (int, float)):
             logger.warning(f"Action amount '{amount}' is not int/float. Type: {type(amount)}. Defaulting to 0.0.")
             amount = 0.0        # Final safety check for amount if action is not fold or check
        if action not in [ACTION_FOLD, ACTION_CHECK] and amount <= 0 and action != ACTION_CALL: # Call can be 0 if already all-in and covered
            # Exception for call: if bet_to_call is 0 and it's a call action, amount 0 is fine.
            if not (action == ACTION_CALL and final_bet_to_call == 0):
                logger.warning(f"Action {action} has amount {amount}. This might be unintended. Overriding to check if possible, else fold.")
                if can_check:
                    action, amount = ACTION_CHECK, 0
                else:
                    # If it's a bet/raise that resolved to 0, it's problematic.
                    # If it was a call that resolved to 0 (and bet_to_call > 0), it's also problematic.
                    # This usually means an issue in bet sizing or decision logic.
                    # For safety, if we can't check, and we are supposed to bet/raise/call >0 but amount is 0, fold.
                    logger.error(f"Unsafe action {action} with amount {amount} when cannot check. Defaulting to FOLD.")
                    action, amount = ACTION_FOLD, 0


        return action, round(amount, 2)

    def update_opponents_from_game_state(self, game_state, player_index):
        """Update opponent tracking based on current game state and recent actions."""
        try:
            all_players = game_state.get('players', [])
            current_round = game_state.get('current_round', 'unknown')
            pot_size = parse_monetary_value(game_state.get('pot_size', game_state.get('pot', 0)))
            
            # Update opponent actions based on their current state
            for i, player in enumerate(all_players):
                if i == player_index or not player:  # Skip self and empty slots
                    continue
                    
                player_name = player.get('name', f'Player_{i}')
                position = player.get('position', 'unknown')
                
                # Check if player made an action this round
                if player.get('has_acted', False):
                    last_action = player.get('last_action', 'unknown')
                    bet_amount = parse_monetary_value(player.get('current_bet', 0))
                    
                    # Update opponent profile
                    self.opponent_tracker.update_opponent_action(
                        player_name=player_name,
                        action=last_action,
                        street=current_round.lower(),
                        position=position,
                        bet_size=bet_amount,
                        pot_size=pot_size
                    )
                    
                    logger.debug(f"Updated opponent {player_name}: {last_action} for {bet_amount} on {current_round}")
                    
        except Exception as e:
            logger.warning(f"Error updating opponent tracking: {e}")
