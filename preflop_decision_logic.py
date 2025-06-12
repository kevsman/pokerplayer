# preflop_decision_logic.py
import math # For round
from hand_utils import get_preflop_hand_category # Ensure this is imported
import logging

# Assuming OpponentTracker is in a module named opponent_tracking
# from opponent_tracking import OpponentTracker # Import if type hinting or direct instantiation needed here

logger = logging.getLogger(__name__) # Use module's name for the logger

# Constants for actions (consider moving to a shared constants file)
ACTION_FOLD = 'fold'
ACTION_CHECK = 'check'
ACTION_CALL = 'call'
ACTION_RAISE = 'raise'

# Add action_history and opponent_tracker as parameters
def make_preflop_decision(
    my_player, hand_category, position, bet_to_call, can_check,
    my_stack, pot_size, active_opponents_count,
    small_blind, big_blind, my_current_bet_this_street, max_bet_on_table, min_raise,
    is_sb, is_bb,
    action_fold_const, action_check_const, action_call_const, action_raise_const,
    action_history=None,  # Add action_history here
    opponent_tracker=None # Add opponent_tracker here
    ):
    """Enhanced pre-flop decision making, now considering action_history and opponent_tracker."""
    
    if action_history is None:
        action_history = [] 
    
    # It's crucial that opponent_tracker is available if we intend to use it.
    # For now, we'll proceed cautiously if it's None, but ideally, it should always be passed.
    if opponent_tracker is None:
        logger.warning("Opponent tracker not provided to preflop logic. Decisions will be less informed.")
        # Fallback: create a dummy tracker or operate with limited info
        # For simplicity in this step, we'll just check for its existence before use.

    logger.debug(f"Preflop decision with action_history: {action_history}, opponent_tracker available: {opponent_tracker is not None}")

    # --- Helper function to analyze action history for current street ---
    def analyze_street_actions(history, current_street):
        raisers = []
        callers = []
        num_raises = 0
        last_raiser_info = None
        bet_levels = [0] # Start with 0 for initial blind posts

        for action_item in history:
            if action_item.get('street', '').lower() == current_street:
                action_type = action_item.get('action_type', '').upper()
                player_name = action_item.get('player_name')
                amount = action_item.get('amount', 0) # This is the total bet amount by the player in that action.

                if action_type == 'RAISE':
                    num_raises += 1
                    raisers.append(player_name)
                    last_raiser_info = action_item
                    bet_levels.append(amount)
                elif action_type == 'CALL':
                    callers.append(player_name)
                elif action_type == 'BET': # Could be an open bet
                    num_raises +=1 # Treat an initial bet as the first "raise" over blinds
                    raisers.append(player_name)
                    last_raiser_info = action_item
                    bet_levels.append(amount)
        
        # Determine the facing bet amount and the player who made it
        facing_bet_amount = 0
        last_aggressor_name = None
        if last_raiser_info:
            facing_bet_amount = last_raiser_info.get('amount', 0) 
            last_aggressor_name = last_raiser_info.get('player_name')
            
        return num_raises, raisers, callers, last_raiser_info, facing_bet_amount, last_aggressor_name, sorted(list(set(bet_levels))) # Ensure bet_levels is sorted and unique

    num_raises_this_street, raisers_on_street, callers_on_street, last_raiser_action_info, facing_bet_from_history, last_aggressor_name_from_history, bet_levels_from_history = analyze_street_actions(action_history, 'preflop')
    
    logger.debug(f"Preflop History Analysis: Num Raises={num_raises_this_street}, Last Raiser Info={last_raiser_action_info}, Last Aggressor Name={last_aggressor_name_from_history}, Bet Levels: {bet_levels_from_history}")

    # --- Opponent Profiling ---
    last_aggressor_profile = None
    if opponent_tracker and last_aggressor_name_from_history:
        last_aggressor_profile = opponent_tracker.get_opponent_profile(last_aggressor_name_from_history)
        logger.debug(f"Last aggressor ({last_aggressor_name_from_history}) profile: {last_aggressor_profile}")

    table_dynamics = None
    if opponent_tracker:
        table_dynamics = opponent_tracker.get_table_dynamics()
        logger.debug(f"Table dynamics: {table_dynamics}")

    # --- Limper Calculation (using action_history for more accuracy if available) ---
    num_limpers = 0
    limper_names = []
    # A raise is any 'RAISE' action, or a 'BET' action if it's the first bet beyond blinds.
    # Check if any action in history for preflop is a raise or a bet that isn't just posting a blind.
    has_been_raised_or_opened = False
    for action in action_history:
        if action.get('street') == 'preflop':
            action_type = action.get('action_type','').upper()
            amount = action.get('amount',0)
            if action_type == 'RAISE':
                has_been_raised_or_opened = True
                break
            if action_type == 'BET' and amount > big_blind : # A bet larger than BB is an open
                has_been_raised_or_opened = True
                break
    
    if not has_been_raised_or_opened:
        for action in action_history:
            if action.get('street') == 'preflop' and \
               action.get('action_type', '').upper() == 'CALL' and \
               action.get('amount') == big_blind and \
               action.get('player_name') != my_player.get('name'): 
                player_actions_before_call = [
                    a for a in action_history 
                    if a.get('player_name') == action.get('player_name') and 
                       a.get('street') == 'preflop' and 
                       action_history.index(a) < action_history.index(action)
                ]
                is_blind_post = any(prev_a.get('action_type','').upper() == 'POST' for prev_a in player_actions_before_call if prev_a.get('amount',0) == big_blind)

                if not any(prev_a.get('action_type','').upper() in ['BET', 'RAISE'] for prev_a in player_actions_before_call) and not is_blind_post:
                    if action.get('player_name') not in limper_names:
                         num_limpers += 1
                         limper_names.append(action.get('player_name'))
    logger.debug(f"Number of limpers calculated from history: {num_limpers}, Names: {limper_names}")


    # --- Raise Amount Calculation (Revised and using history) ---
    base_for_raise_calc = big_blind # Default if no prior raises
    size_of_last_raise_increment = big_blind # Default if first raise is ours

    if last_raiser_action_info: # There has been at least one bet/raise
        last_raise_total_bet = last_raiser_action_info.get('amount', 0)
        base_for_raise_calc = last_raise_total_bet # The total amount of the last bet/raise

        # Find the bet level before the last_raise_total_bet
        previous_bet_level_idx = -1
        for i, level in enumerate(bet_levels_from_history):
            if level < last_raise_total_bet:
                previous_bet_level_idx = i
            else:
                break 
        
        previous_bet_level = 0
        if previous_bet_level_idx != -1 and previous_bet_level_idx < len(bet_levels_from_history):
             previous_bet_level = bet_levels_from_history[previous_bet_level_idx]
        
        size_of_last_raise_increment = last_raise_total_bet - previous_bet_level
        if size_of_last_raise_increment <=0 : # Should not happen if bet_levels are correct
            size_of_last_raise_increment = big_blind # Fallback
    
    open_raise_multiplier_bb = 3.0 # Multiplier of Big Blind for open raise
    if position == 'BTN' and num_limpers == 0: open_raise_multiplier_bb = 2.5
    if position == 'SB' and num_limpers == 0: open_raise_multiplier_bb = 3.0

    if table_dynamics:
        if 'loose' in table_dynamics.get('table_type', ''):
            open_raise_multiplier_bb += 0.5 
        elif 'tight' in table_dynamics.get('table_type', ''):
            open_raise_multiplier_bb = max(2.0, open_raise_multiplier_bb - 0.25)


    if num_raises_this_street == 0: # This is an opening raise or isolation raise.
        # Standard open: X * BB. Isolation: X * BB + Y * BB for each limper.
        raise_amount_calculated = (open_raise_multiplier_bb * big_blind) + (num_limpers * big_blind)
    else: # Facing a bet/raise (re-raise situation: 3-bet, 4-bet, etc.)
        # Standard re-raise: current total bet + K * (size of last raise increment)
        # Or: K * (total amount of previous bet)
        reraise_multiplier_of_total_bet = 3.0
        if position not in ['SB', 'BB']: # IP
            reraise_multiplier_of_total_bet = 2.7
        
        if num_raises_this_street >= 2: # Facing a 3-bet (we consider 4-bet) or more
            reraise_multiplier_of_total_bet = 2.3 
            if position not in ['SB', 'BB']: reraise_multiplier_of_total_bet = 2.2

        # Calculate raise based on the total amount of the previous bet/raise
        raise_amount_calculated = reraise_multiplier_of_total_bet * base_for_raise_calc
        
        # Alternative: Pot-sized raise logic for re-raises
        # Amount to call = bet_to_call
        # Pot after call = pot_size + bet_to_call
        # Raise size = Pot after call
        # Total bet = bet_to_call + Pot after call = bet_to_call + pot_size + bet_to_call
        # pot_sized_raise_total = bet_to_call + pot_size + bet_to_call 
        # if num_raises_this_street >=1: # If re-raising
        #     raise_amount_calculated = pot_sized_raise_total


        # Add extra for callers between the last raise and us (if any)
        # This is complex; for now, the multiplier approach is simpler.
        # If there were callers after the last raise, our re-raise should be larger.
        # Example: UTG raises to 3BB. MP calls. CO (Hero) wants to 3-bet.
        # Pot is SB+BB + 3BB (UTG) + 3BB (MP) = ~7.5BB before Hero. Call is 3BB.
        # Standard 3-bet over UTG raise might be 9-10BB. Over UTG+caller, maybe 12-15BB.
        # Our current `raise_amount_calculated` is based on `base_for_raise_calc` (UTG's 3BB total).
        # So, e.g., 2.7 * 3BB = 8.1BB. We need to add for the caller.
        # Add 1x the size of the original raise for each caller.
        
        callers_after_last_raise_count = 0
        if last_raiser_action_info and action_history:
            try:
                # Find the index of the last raiser's action
                last_raiser_index = -1
                # This direct object comparison might fail if objects are not identical
                # A robust way is to use a unique ID if actions have one, or compare key fields.
                # For now, assume last_raiser_action_info is the actual dict from action_history
                if last_raiser_action_info in action_history:
                     last_raiser_index = action_history.index(last_raiser_action_info)
                
                if last_raiser_index != -1:
                    for i in range(last_raiser_index + 1, len(action_history)):
                        action_after_raiser = action_history[i]
                        if action_after_raiser.get('street','').lower() == 'preflop':
                            if action_after_raiser.get('action_type','').upper() == 'CALL' and \
                               action_after_raiser.get('amount',0) == base_for_raise_calc: # Called the last raise amount
                                callers_after_last_raise_count +=1
            except ValueError: # If last_raiser_action_info is not in action_history (e.g. it was a copy)
                logger.warning("Could not find last_raiser_action_info in action_history for caller counting.")


        if callers_after_last_raise_count > 0:
            raise_amount_calculated += (callers_after_last_raise_count * size_of_last_raise_increment)


    # Final adjustments to raise_amount_calculated
    # Ensure raise is at least min_raise (total amount)
    # min_raise is the total bet amount for a valid minimum raise.
    # If we are opening (num_raises_this_street == 0), min_raise is typically 2*BB.
    # If we are re-raising, min_raise is (last_bet_total + last_raise_increment).
    
    # If our calculated raise is less than the legal min_raise, use min_raise.
    # min_raise should be the *total* bet amount.
    if raise_amount_calculated < min_raise and min_raise > bet_to_call : # bet_to_call is what we owe
         raise_amount_calculated = min_raise
    
    # If calculated amount is not actually a raise over current bet_to_call (i.e. <= bet_to_call),
    # but min_raise is a valid raise (min_raise > bet_to_call), then use min_raise.
    if raise_amount_calculated <= bet_to_call and min_raise > bet_to_call:
        raise_amount_calculated = min_raise

    # Ensure raise amount is not more than our stack
    raise_amount_calculated = round(min(raise_amount_calculated, my_stack), 2)

    # If, after all calculations, the raise_amount_calculated is not greater than what we need to call,
    # it means we cannot make a "standard" sized raise.
    # The decision to raise will then consider if an all-in is appropriate or if min_raise is the only option.
    
    logger.info(f"Preflop Logic: Pos: {position}, Cat: {hand_category}, B2Call: {bet_to_call}, CanChk: {can_check}, CalcRaise: {raise_amount_calculated}, MyStack: {my_stack}, MyBet: {my_current_bet_this_street}, MaxOppBet: {max_bet_on_table}, MinRaise: {min_raise}, Pot: {pot_size}, Opps: {active_opponents_count}, BB: {big_blind}, is_bb: {is_bb}, NumLimpers: {num_limpers}, NumRaises: {num_raises_this_street}")
    if last_aggressor_profile:
        logger.info(f"Last Aggressor ({last_aggressor_name_from_history}): VPIP={last_aggressor_profile.get_vpip():.1f}, PFR={last_aggressor_profile.get_pfr():.1f}, Type={last_aggressor_profile.classify_player_type()}")


    # --- Decision Logic (incorporating opponent tendencies) ---

    # General principle: If last aggressor is very tight, be more cautious. If very loose, be more aggressive.
    # These thresholds would ideally come from OpponentProfile methods like get_fold_to_3bet_percentage()
    fold_to_3bet_threshold_tight = 55 # Folds to 3bet > 55% of the time
    fold_to_3bet_threshold_loose = 35 # Folds to 3bet < 35% (calls/4bets more)
    
    # --- PREMIUM PAIRS (AA, KK, QQ) ---
    if hand_category == "Premium Pair":
        # Always aim to raise or re-raise.
        actual_raise_amount = raise_amount_calculated
        
        # If calculated raise is not valid (e.g. <= bet_to_call) but we can go all-in or make min_raise
        if actual_raise_amount <= bet_to_call:
            if my_stack > bet_to_call: # We can raise more than just calling
                actual_raise_amount = my_stack # Default to all-in if standard calc failed
                if min_raise > bet_to_call and min_raise < my_stack: # If min_raise is a valid option
                    actual_raise_amount = min_raise 
            # If actual_raise_amount is still <= bet_to_call, it means only call or fold is possible.
        
        can_make_valid_raise = actual_raise_amount > bet_to_call or \
                               (actual_raise_amount == my_stack and my_stack > bet_to_call)

        if can_make_valid_raise:
            # QQ facing a 3-bet or 4-bet from a very tight player might consider calling if deep.
            if num_raises_this_street >= 2 and "Q" in str(my_player.get('hand', ['','']))[1]: # Simplified QQ check
                if last_aggressor_profile and last_aggressor_profile.classify_player_type() in ["tight_aggressive", "tight_passive"] and last_aggressor_profile.get_pfr() < 10:
                    logger.info("QQ facing 3bet+ from tight player.")
                    # Effective stack for calling decision
                    effective_stack_for_call = min(my_stack, last_raiser_action_info.get('stack_before_action', my_stack) if last_raiser_action_info else my_stack)
                    if bet_to_call < effective_stack_for_call * 0.33: 
                         logger.info(f"Premium Pair (QQ) vs tight 3bettor/4bettor, calling. Action: CALL, Amount: {bet_to_call}")
                         return action_call_const, bet_to_call
            
            logger.info(f"Premium Pair. Action: RAISE, Amount: {actual_raise_amount}")
            return action_raise_const, actual_raise_amount
        
        # If cannot make a valid raise, call if possible.
        if bet_to_call > 0 and bet_to_call < my_stack:
            logger.info(f"Premium Pair, cannot make standard raise, calling. Action: CALL, Amount: {bet_to_call}")
            return action_call_const, bet_to_call
        elif bet_to_call >= my_stack and bet_to_call > 0: # All-in call
             logger.info(f"Premium Pair, cannot make standard raise, calling ALL-IN. Action: CALL, Amount: {my_stack}")
             return action_call_const, my_stack
        elif can_check: 
            logger.info(f"Premium Pair, can check (unusual). Action: CHECK") 
            return action_check_const, 0
        else: 
            logger.warning(f"Premium Pair in unexpected fold situation. B2C:{bet_to_call}, MyStack:{my_stack} Action: FOLD")
            return action_fold_const, 0


    # --- STRONG HANDS (AKs, AKo, AQs, JJ, TT) ---
    is_strong_hand = hand_category in ["Strong Pair"] or \
                     (hand_category == "Suited Ace" and any(h in str(my_player.get('hand','')) for h in ["AKs", "AQs"])) or \
                     (hand_category == "Offsuit Ace" and "AKo" in str(my_player.get('hand','')))

    if is_strong_hand:
        actual_raise_amount = raise_amount_calculated
        can_make_valid_raise = actual_raise_amount > bet_to_call or \
                               (actual_raise_amount == my_stack and my_stack > bet_to_call)

        if num_raises_this_street == 0: # Opening
            if can_make_valid_raise:
                logger.info(f"Strong hand ({hand_category}), opening. Action: RAISE, Amount: {actual_raise_amount}")
                return action_raise_const, actual_raise_amount
            elif can_check: # BB, checked to. Still raise.
                 logger.info(f"Strong hand ({hand_category}), BB can check, but raising. Action: RAISE, Amount: {actual_raise_amount if actual_raise_amount > 0 else min_raise}")
                 return action_raise_const, actual_raise_amount if actual_raise_amount > 0 else min_raise
            else: 
                 logger.info(f"Strong hand ({hand_category}), cannot open raise effectively. Folding. (Review this state)")
                 return action_fold_const, 0

        elif num_raises_this_street == 1: # Facing an open raise, consider 3-betting
            is_jj_tt = hand_category == "Strong Pair" and any(h in str(my_player.get('hand','')) for h in ["JJ", "TT"])
            
            if is_jj_tt and last_aggressor_profile and last_aggressor_profile.get_pfr() < 10 and position not in ['BTN', 'CO']: # JJ/TT vs tight opener, not in LP
                effective_stack_for_call = min(my_stack, last_raiser_action_info.get('stack_before_action', my_stack) if last_raiser_action_info else my_stack)
                if bet_to_call < effective_stack_for_call * 0.20 : 
                    logger.info(f"Strong Pair (JJ/TT) vs tight opener. Action: CALL, Amount: {bet_to_call}")
                    return action_call_const, bet_to_call
            
            # Standard 3-bet with strong hands
            if can_make_valid_raise:
                logger.info(f"Strong hand ({hand_category}), 3-betting. Action: RAISE, Amount: {actual_raise_amount}")
                return action_raise_const, actual_raise_amount
            elif bet_to_call < my_stack: 
                logger.info(f"Strong hand ({hand_category}), cannot 3-bet effectively, calling. Action: CALL, Amount: {bet_to_call}")
                return action_call_const, bet_to_call
            elif bet_to_call >= my_stack and bet_to_call > 0 : # All-in call
                 logger.info(f"Strong hand ({hand_category}), cannot 3-bet/call. Action: CALL ALL-IN, Amount: {my_stack}")
                 return action_call_const, my_stack
            else:
                logger.info(f"Strong hand ({hand_category}), cannot 3-bet/call, folding. Action: FOLD")
                return action_fold_const, 0


        elif num_raises_this_street >= 2: # Facing a 3-bet or 4-bet
            is_ak = "AK" in str(my_player.get('hand',''))
            if is_ak: # AK continues (4-bet or call 4-bet/5-bet)
                if can_make_valid_raise: 
                    logger.info(f"AK facing 3bet+, re-raising. Action: RAISE, Amount: {actual_raise_amount}")
                    return action_raise_const, actual_raise_amount
                elif bet_to_call < my_stack: 
                    logger.info(f"AK facing 3bet+, calling. Action: CALL, Amount: {bet_to_call}")
                    return action_call_const, bet_to_call
                elif bet_to_call >= my_stack and bet_to_call > 0: 
                    logger.info(f"AK facing 3bet+, calling ALL-IN. Action: CALL, Amount: {my_stack}")
                    return action_call_const, my_stack
                else:
                    logger.info(f"AK facing 3bet+, folding. Action: FOLD")
                    return action_fold_const, 0
            else: # AQs, JJ, TT facing 3-bet+
                effective_stack = min(my_stack, last_raiser_action_info.get('stack_before_action', my_stack) if last_raiser_action_info else my_stack)
                # Adjust threshold based on aggressor type
                call_threshold_multiplier = 0.30
                if last_aggressor_profile and last_aggressor_profile.classify_player_type() in ["loose_aggressive", "maniac"]:
                    call_threshold_multiplier = 0.40 # Call wider vs LAGs/Maniacs
                
                if bet_to_call < effective_stack * call_threshold_multiplier:
                    logger.info(f"AQs/JJ/TT facing 3bet+, calling. Action: CALL, Amount: {bet_to_call}")
                    return action_call_const, bet_to_call
                else:
                    logger.info(f"AQs/JJ/TT facing 3bet+, folding to large bet or vs tight player. Action: FOLD")
                    return action_fold_const, 0
        
        # Fallback for strong hands
        if bet_to_call == 0 and can_check: return action_check_const, 0
        if bet_to_call > 0 and bet_to_call < my_stack: return action_call_const, bet_to_call
        if bet_to_call >= my_stack and bet_to_call > 0 : return action_call_const, my_stack 
        return action_fold_const, 0


    # --- MEDIUM STRENGTH HANDS (AQo, AJs, KQs, ATs, KJs, QJs, 99, 88, 77) ---
    is_medium_hand = hand_category in ["Medium Pair", "Suited Playable"] or \
                     (hand_category == "Offsuit Ace" and "AQo" in str(my_player.get('hand',''))) or \
                     (hand_category == "Suited Ace" and any(h in str(my_player.get('hand','')) for h in ["AJs", "ATs"])) or \
                     (hand_category == "Suited King" and any(h in str(my_player.get('hand','')) for h in ["KQs", "KJs"])) or \
                     (hand_category == "Playable Broadway" and "QJs" in str(my_player.get('hand','')))


    if is_medium_hand:
        actual_raise_amount = raise_amount_calculated
        can_make_valid_raise = actual_raise_amount > bet_to_call or \
                               (actual_raise_amount == my_stack and my_stack > bet_to_call)

        if num_raises_this_street == 0: # Opening
            can_open = True
            # Tighten up opening ranges from UTG/MP for some medium hands
            if position in ['UTG', 'MP']:
                if hand_category == "Medium Pair" and not any(p in str(my_player.get('hand','')) for p in ["99"]): # 77,88 from UTG/MP
                    can_open = False
                if hand_category == "Suited Ace" and "ATs" in str(my_player.get('hand','')) and position == 'UTG': 
                    can_open = False
                if hand_category == "Offsuit Ace" and "AQo" in str(my_player.get('hand','')) and position == 'UTG': # AQo UTG is borderline, consider table
                    if table_dynamics and 'tight' not in table_dynamics.get('table_type',''): can_open = False # Fold AQo UTG unless table is tight

            if not can_open:
                logger.info(f"Medium hand ({hand_category}) too weak to open from {position}. Action: FOLD")
                return action_fold_const, 0

            if can_make_valid_raise:
                logger.info(f"Medium hand ({hand_category}), opening. Action: RAISE, Amount: {actual_raise_amount}")
                return action_raise_const, actual_raise_amount
            elif can_check: # BB, checked to
                 logger.info(f"Medium hand ({hand_category}), BB can check, but raising. Action: RAISE, Amount: {actual_raise_amount if actual_raise_amount > 0 else min_raise}")
                 return action_raise_const, actual_raise_amount if actual_raise_amount > 0 else min_raise
            else:
                 logger.info(f"Medium hand ({hand_category}), cannot open effectively. Folding.")
                 return action_fold_const, 0

        elif num_raises_this_street == 1: # Facing an open raise
            should_3bet_bluff = False
            fold_to_3bet_stat = None
            pfr_stat = None
            raiser_player_type = "unknown"

            if last_aggressor_profile:
                fold_to_3bet_stat = last_aggressor_profile.get_fold_to_3bet_percentage()
                pfr_stat = last_aggressor_profile.get_pfr()
                raiser_player_type = last_aggressor_profile.classify_player_type()
                logger.debug(f"Aggressor {last_aggressor_name_from_history} stats: FoldTo3Bet={fold_to_3bet_stat}, PFR={pfr_stat}, Type={raiser_player_type}")

            # Conditions for 3-betting as a semi-bluff
            # More likely if raiser folds often to 3-bets, or is opening very wide (high PFR)
            # Also consider position: more 3-bet bluffs from LP (BTN, CO) or Blinds.
            if fold_to_3bet_stat is not None and fold_to_3bet_stat > 50: # Folds >50% to 3bets
                should_3bet_bluff = True
            elif pfr_stat is not None and pfr_stat > 25 and position in ['CO', 'BTN', 'SB', 'BB']:
                should_3bet_bluff = True
            elif raiser_player_type in ["loose_aggressive", "maniac"] and position in ['CO', 'BTN', 'SB', 'BB']:
                should_3bet_bluff = True
            
            # Specific hands good for semi-bluff 3-betting (blockers, playability)
            can_semi_bluff_3bet_hand = hand_category in ["Suited Ace", "Suited King"] or \
                                      (hand_category == "Medium Pair" and any(p in str(my_player.get('hand','')) for p in ["99","88","77"])) or \
                                      (hand_category == "Suited Playable" and any(h in str(my_player.get('hand','')) for h in ["KQs", "QJs"])) 

            if should_3bet_bluff and can_semi_bluff_3bet_hand and can_make_valid_raise:
                logger.info(f"Medium hand ({hand_category}), 3-betting as semi-bluff vs {last_aggressor_name_from_history} (F3B:{fold_to_3bet_stat}, PFR:{pfr_stat}). Action: RAISE, Amount: {actual_raise_amount}")
                return action_raise_const, actual_raise_amount

            # Default to call if not 3-betting and price is right
            effective_stack_for_call = min(my_stack, last_raiser_action_info.get('stack_before_action', my_stack) if last_raiser_action_info else my_stack)
            call_cost_percentage_of_stack = (bet_to_call / effective_stack_for_call) if effective_stack_for_call > 0 else 1
            
            # Call with medium pairs (set mining) or good suited broadways/aces if price is good.
            # Max 10-12% of stack for these calls usually, adjust based on opponent type
            max_call_percentage = 0.10 # Default
            if hand_category == "Medium Pair": max_call_percentage = 0.12 # For setmining
            if raiser_player_type in ["loose_passive", "whale"]: # Call wider vs fishy players
                max_call_percentage += 0.05
            if position == 'BB': # Defend BB a bit wider
                max_call_percentage += 0.03

            if call_cost_percentage_of_stack < max_call_percentage:
                logger.info(f"Medium hand ({hand_category}), calling raise from {last_aggressor_name_from_history}. Cost: {call_cost_percentage_of_stack*100:.0f}% of stack. Action: CALL, Amount: {bet_to_call}")
                return action_call_const, bet_to_call
            else:
                logger.info(f"Medium hand ({hand_category}), raise from {last_aggressor_name_from_history} too expensive to call ({call_cost_percentage_of_stack*100:.0f}% of stack). Action: FOLD")
                return action_fold_const, 0

        else: # Facing 3-bet or more
            # Generally fold medium hands to 3-bets unless specific conditions are met
            # e.g. AQ, 99 vs a known loose 3-bettor and good stack depth/position.
            can_call_3bet = False
            if last_aggressor_profile and bet_to_call < my_stack * 0.25: # Not committing too much
                fold_to_4bet_stat = last_aggressor_profile.get_fold_to_4bet_percentage() # Assuming this stat exists
                three_bet_stat = last_aggressor_profile.get_3bet_percentage() # Assuming this stat exists

                # If opponent 3-bets wide (high 3Bet%) and folds to 4-bets often, consider a 4-bet bluff with AQs/AJs/KQs or even 99/88
                if can_make_valid_raise and (hand_category in ["Suited Ace", "Suited King"] or (hand_category == "Medium Pair" and "99" in str(my_player.get('hand','')))):
                    if three_bet_stat is not None and three_bet_stat > 10 and fold_to_4bet_stat is not None and fold_to_4bet_stat > 50:
                        logger.info(f"Medium hand ({hand_category}) 4-bet bluffing vs {last_aggressor_name_from_history} (3B:{three_bet_stat}, F4B:{fold_to_4bet_stat}). Action: RAISE, Amount: {actual_raise_amount}")
                        return action_raise_const, actual_raise_amount
                
                # Call 3-bet with AQ, 99, 88, sometimes 77, AJs, KQs if opponent is loose or we have position/deep stacks
                if hand_category in ["Offsuit Ace", "Medium Pair"] or (hand_category == "Suited Ace" and "AJs" in str(my_player.get('hand',''))) or (hand_category == "Suited King" and "KQs" in str(my_player.get('hand',''))):
                    if raiser_player_type in ["loose_aggressive", "maniac"] or (three_bet_stat is not None and three_bet_stat > 8):
                        if position != 'SB': # Avoid calling 3bets OOP from SB too often
                            can_call_3bet = True
            
            if can_call_3bet:
                logger.info(f"Medium hand ({hand_category}) calling 3-bet from {last_aggressor_name_from_history}. Action: CALL, Amount: {bet_to_call}")
                return action_call_const, bet_to_call

            logger.info(f"Medium hand ({hand_category}) facing 3bet+ from {last_aggressor_name_from_history}. Action: FOLD")
            return action_fold_const, 0


    # --- SPECULATIVE HANDS (Suited Connectors, Small Pairs 66-22, some Suited Gappers, Weak Suited Aces) ---
    # Refined category check for speculative hands
    is_speculative_hand = hand_category in ["Suited Connector", "Small Pair"] or \
                          (hand_category == "Suited Ace" and any(h in str(my_player.get('hand','')) for h in ["A2s", "A3s", "A4s", "A5s"])) or \
                          (hand_category == "Suited Gapper" and any(h in str(my_player.get('hand','')) for h in ["J9s", "T8s", "97s", "86s", "75s", "64s"])) 

    if is_speculative_hand:
        actual_raise_amount = raise_amount_calculated
        can_make_valid_raise = actual_raise_amount > bet_to_call or \
                               (actual_raise_amount == my_stack and my_stack > bet_to_call)

        if num_raises_this_street == 0: # Opening or limping
            # Open raise SCs, small pairs, good suited gappers, weak suited aces from LP or BTN vs SB/BB
            can_open_speculative = False
            if position in ['CO', 'BTN']:
                can_open_speculative = True
            elif position == 'SB' and num_limpers == 0: # Stealing from SB
                can_open_speculative = True
            
            if can_open_speculative and can_make_valid_raise:
                logger.info(f"Speculative ({hand_category}, {str(my_player.get('hand',''))}) from {position}, opening. Action: RAISE, Amount: {actual_raise_amount}")
                return action_raise_const, actual_raise_amount
            
            # Limp/call small raises if multi-way potential and good price from other positions
            # Check if we can complete SB or check BB
            if is_sb and bet_to_call == (big_blind - small_blind) and num_limpers > 0: # Completing SB into limped pot
                 logger.info(f"Speculative ({hand_category}, {str(my_player.get('hand',''))}) in SB, completing into limped pot. Action: CALL, Amount: {bet_to_call}")
                 return action_call_const, bet_to_call
            if is_bb and can_check and bet_to_call == 0 : # Checking BB
                 logger.info(f"Speculative ({hand_category}, {str(my_player.get('hand',''))}) in BB, can check. Action: CHECK")
                 return action_check_const, 0

            # Consider calling a single BB if many limpers (good pot odds)
            # Pot odds = (pot_size + bet_to_call) / bet_to_call
            # Required equity for call = 1 / (Pot odds + 1)
            # For speculative hands, we often need better implied odds than direct pot odds.
            if bet_to_call == big_blind and num_limpers >= (2 if position not in ['MP', 'UTG'] else 3) and active_opponents_count >=3 :
                 effective_stack_for_call = my_stack 
                 # Call if bet is very small part of stack (e.g. < 5% for good implied odds)
                 if bet_to_call < effective_stack_for_call * 0.05 : 
                    logger.info(f"Speculative ({hand_category}, {str(my_player.get('hand',''))}), cheap call in multiway limped pot ({num_limpers} limpers). Action: CALL, Amount: {bet_to_call}")
                    return action_call_const, bet_to_call
            
            logger.info(f"Speculative ({hand_category}, {str(my_player.get('hand',''))}), no good spot to open/limp/call from {position}. Action: FOLD")
            return action_fold_const, 0

        elif num_raises_this_street == 1: # Facing one raise
            effective_stack = min(my_stack, last_raiser_action_info.get('stack_before_action', my_stack) if last_raiser_action_info else my_stack)
            # Implied odds: call if bet_to_call is small % of effective stack (e.g., < 5-7% for set mining/strong draws)
            # And preferably multi-way or vs loose player.
            
            # The "10x rule" or "5/10 rule" for speculative hands (call if bet is <10% of effective stack, if you expect to win >10x bet when you hit)
            # Simplified: call if bet_to_call < 7% of effective_stack for good suited connectors/small pairs, maybe 5% for others.
            max_call_percentage_speculative = 0.0
            if hand_category == "Small Pair": max_call_percentage_speculative = 0.07 # Set mining
            elif hand_category == "Suited Connector": max_call_percentage_speculative = 0.06
            elif hand_category == "Suited Ace" and any(h in str(my_player.get('hand','')) for h in ["A2s", "A3s", "A4s", "A5s"]): # Wheel aces
                max_call_percentage_speculative = 0.05 
            
            is_multiway_potential = active_opponents_count > 1 or len(callers_on_street) > 0 # More than just us and the raiser, or callers already in.
            
            raiser_is_loose_or_fishy = False
            if last_aggressor_profile and last_aggressor_profile.classify_player_type() in ["loose_aggressive", "loose_passive", "maniac", "whale"]:
                raiser_is_loose_or_fishy = True

            can_call_for_implied_odds = False
            if bet_to_call > 0 and (bet_to_call / effective_stack if effective_stack > 0 else 1) < max_call_percentage_speculative:
                if is_multiway_potential or raiser_is_loose_or_fishy or position in ['BB', 'BTN']: # More inclined to call in position or from BB
                    can_call_for_implied_odds = True
            
            # BB defense with direct pot odds for some speculative hands if raise is small
            if is_bb and bet_to_call <= 3.5 * big_blind : 
                pot_odds_to_call = (pot_size + bet_to_call) / bet_to_call if bet_to_call > 0 else 0
                # Rough equity needed: 1 / (pot_odds_to_call + 1)
                # Suited connectors/gappers might have ~15-25% raw equity vs a range here.
                # If pot_odds are good, e.g. > 3:1 (need 25% equity), can consider calling.
                if pot_odds_to_call > 3.0 and hand_category in ["Suited Connector", "Suited Gapper", "Suited Ace"]:
                    can_call_for_implied_odds = True # Or direct odds defense
                    logger.info(f"Speculative ({hand_category}, {str(my_player.get('hand',''))}) in BB, defending vs small raise due to pot odds ({pot_odds_to_call:.1f}:1). Action: CALL, Amount: {bet_to_call}")
                    return action_call_const, bet_to_call

            if can_call_for_implied_odds:
                logger.info(f"Speculative ({hand_category}, {str(my_player.get('hand',''))}), calling raise from {last_aggressor_name_from_history} with good implied/pot odds. Action: CALL, Amount: {bet_to_call}")
                return action_call_const, bet_to_call
            else:
                logger.info(f"Speculative ({hand_category}, {str(my_player.get('hand',''))}), not enough implied odds to call raise from {last_aggressor_name_from_history}. Action: FOLD")
                return action_fold_const, 0
        else: # Facing 3-bet or more
            # Generally fold all speculative hands to 3-bets unless very specific conditions (deep stacks, vs maniac 3-bettor, in position)
            # This is rare and risky.
            logger.info(f"Speculative ({hand_category}, {str(my_player.get('hand',''))}) facing 3bet+ from {last_aggressor_name_from_history}. Action: FOLD")
            return action_fold_const, 0


    # --- OTHER SUITED ACES (A9s, A8s, A7s, A6s) ---
    is_other_suited_ace = hand_category == "Suited Ace" and \
                          any(h in str(my_player.get('hand','')) for h in ["A9s", "A8s", "A7s", "A6s"])

    if is_other_suited_ace:
        actual_raise_amount = raise_amount_calculated
        can_make_valid_raise = actual_raise_amount > bet_to_call or \
                               (actual_raise_amount == my_stack and my_stack > bet_to_call)

        if num_raises_this_street == 0: # Opening situation
            if position in ['CO', 'BTN', 'SB'] and num_limpers == 0:
                if can_make_valid_raise:
                    logger.info(f"Other Suited Ace ({str(my_player.get('hand',''))}) from {position}, opening. Action: RAISE, Amount: {actual_raise_amount}")
                    return action_raise_const, actual_raise_amount
            if is_bb and can_check: # BB, checked to
                 logger.info(f"Other Suited Ace ({str(my_player.get('hand',''))}), BB can check, but raising. Action: RAISE, Amount: {actual_raise_amount if actual_raise_amount > 0 else min_raise}")
                 return action_raise_const, actual_raise_amount if actual_raise_amount > 0 else min_raise
            # If not opening from LP/SB or checking BB to raise, consider limping or folding based on other factors (not implemented here, defaults to fold)
            logger.info(f"Other Suited Ace ({str(my_player.get('hand',''))}) from {position}, not opening. Action: FOLD (or check if possible)")
            if can_check and bet_to_call == 0: return action_check_const, 0
            return action_fold_const, 0

        elif num_raises_this_street == 1: # Facing an open raise
            effective_stack = min(my_stack, last_raiser_action_info.get('stack_before_action', my_stack) if last_raiser_action_info else my_stack)
            
            # Consider 3-betting as a semi-bluff
            raiser_pos = last_raiser_action_info.get('position') if last_raiser_action_info else "unknown"
            pfr_from_steal_pos = 0
            raiser_is_likely_stealing = False
            if last_aggressor_profile and raiser_pos in ['CO', 'BTN', 'SB']:
                 # Simplified check for steal attempt (e.g. PFR > 30% from these positions or general high PFR)
                if last_aggressor_profile.position_stats.get(raiser_pos, {}).get('hands_dealt', 0) > 10:
                    pfr_from_steal_pos = (last_aggressor_profile.position_stats[raiser_pos]['pfr_hands'] / last_aggressor_profile.position_stats[raiser_pos]['hands_dealt']) * 100
                if pfr_from_steal_pos > 30 or last_aggressor_profile.get_pfr() > 28:
                    raiser_is_likely_stealing = True

            if raiser_is_likely_stealing and position in ['SB', 'BB', 'BTN'] and can_make_valid_raise: # 3betting from blinds or BTN vs steal
                logger.info(f"Other Suited Ace ({str(my_player.get('hand',''))}), 3-betting vs likely steal from {raiser_pos}. Action: RAISE, Amount: {actual_raise_amount}")
                return action_raise_const, actual_raise_amount

            # Calling conditions
            call_cost_percentage_of_stack = (bet_to_call / effective_stack) if effective_stack > 0 else 1
            max_call_percentage = 0.10 # Max 10% of stack to call a raise
            if is_bb: max_call_percentage = 0.15 # Defend BB a bit wider

            if call_cost_percentage_of_stack < max_call_percentage and bet_to_call > 0 :
                logger.info(f"Other Suited Ace ({str(my_player.get('hand',''))}), calling raise from {last_aggressor_name_from_history}. Cost: {call_cost_percentage_of_stack*100:.0f}% of stack. Action: CALL, Amount: {bet_to_call}")
                return action_call_const, bet_to_call
            
            logger.info(f"Other Suited Ace ({str(my_player.get('hand',''))}), facing raise, folding. B2C: {bet_to_call}, MyStack: {my_stack}, Raiser: {last_aggressor_name_from_history}")
            if can_check and bet_to_call == 0: return action_check_const, 0 # Should not happen if num_raises_this_street == 1
            return action_fold_const, 0

        else: # Facing 3-bet or more
            logger.info(f"Other Suited Ace ({str(my_player.get('hand',''))}) facing 3bet+ from {last_aggressor_name_from_history}. Action: FOLD")
            return action_fold_const, 0


    # --- WEAK HANDS ---
    if hand_category == "Weak":
        logger.debug(f"Preflop: Entered Weak hand category. NumRaises: {num_raises_this_street}, B2C: {bet_to_call}, Pos: {position}, is_bb: {is_bb}")
        
        # Defend BB vs single small raise if opponent is a frequent stealer from BTN/CO/SB
        if is_bb and num_raises_this_street == 1 and bet_to_call <= 3.5 * big_blind:
            if last_aggressor_profile and last_raiser_action_info:
                raiser_pos = last_raiser_action_info.get('position')
                # aggressor_steal_attempt_freq = last_aggressor_profile.get_steal_frequency(raiser_pos) # Needs specific stat
                # Using PFR from steal positions as proxy
                pfr_from_steal_pos = 0
                if raiser_pos in ['CO','BTN','SB'] and last_aggressor_profile.position_stats[raiser_pos]['hands_dealt'] > 10: # Min sample
                    pfr_from_steal_pos = (last_aggressor_profile.position_stats[raiser_pos]['pfr_hands'] / last_aggressor_profile.position_stats[raiser_pos]['hands_dealt']) * 100
                
                if pfr_from_steal_pos > 30 or last_aggressor_profile.get_pfr() > 28 : # Raiser is active or stealing often
                    pot_odds = (pot_size + bet_to_call) / bet_to_call if bet_to_call > 0 else 0
                    # Required equity approx 1 / (pot_odds + 1)
                    # If getting better than 2:1 or 2.5:1, might be worth calling with many hands.
                    if pot_odds > 2.0 : 
                        logger.info(f"Weak hand in BB vs steal from active player ({last_aggressor_name_from_history} from {raiser_pos}), good pot odds ({pot_odds:.1f}:1). Action: CALL, Amount: {bet_to_call}")
                        return action_call_const, bet_to_call
        
        if can_check and bet_to_call == 0:
            logger.info(f"Weak hand, can check. Action: CHECK")
            return action_check_const, 0
        
        logger.info(f"Weak hand, default. Action: FOLD (B2C: {bet_to_call}, CanCheck: {can_check})")
        return action_fold_const, 0

    # Fallback: This should ideally not be reached if all categories are handled.
    logger.warning(f"Preflop decision fall-through for hand category '{hand_category}'. Pos: {position}, B2C: {bet_to_call}, CanChk: {can_check}. Defaulting to check/fold.")
    if can_check and bet_to_call == 0:
        return action_check_const, 0
    return action_fold_const, 0


if __name__ == '__main__':
    # This block is for testing the function directly if needed.
    # Setup mock objects for my_player, opponent_tracker, etc.
    # logger.setLevel(logging.DEBUG) # Ensure logs are visible
    # handler = logging.StreamHandler()
    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # handler.setFormatter(formatter)
    # logger.addHandler(handler)
    # logger.propagate = False


    print("Preflop decision logic module loaded.")
    # Add example calls here to test functionality
    # mock_my_player = {'name': "Hero", 'hand': ["As", "Kd"], 'stack': 1000} # Example
    # mock_action_history = [
    #     {'player_name': 'Villain1', 'action_type': 'CALL', 'amount': 10, 'street': 'preflop'},
    #     {'player_name': 'Villain2', 'action_type': 'RAISE', 'amount': 40, 'street': 'preflop', 'stack_before_action': 1000, 'position': 'CO'},
    # ]
    # # Mock opponent tracker setup
    # class MockOpponentProfile:
    #     def __init__(self, name): self.player_name = name; self.vpip=25; self.pfr=20; self.hands_seen_count=50; self.position_stats = defaultdict(lambda: defaultdict(int))
    #     def get_vpip(self): return self.vpip
    #     def get_pfr(self): return self.pfr
    #     def classify_player_type(self): return "unknown"
    # class MockOpponentTracker:
    #     def __init__(self): self.opponents = {}
    #     def get_opponent_profile(self, name): 
    #         if name not in self.opponents: self.opponents[name] = MockOpponentProfile(name)
    #         return self.opponents[name]
    #     def get_table_dynamics(self): return {'table_type': 'normal'}

    # mock_tracker = MockOpponentTracker()

    # decision, amount = make_preflop_decision(
    #     my_player=mock_my_player, hand_category="Strong Pair", position="BTN", bet_to_call=30, can_check=False,
    #     my_stack=990, pot_size=65, active_opponents_count=2,
    #     small_blind=5, big_blind=10, my_current_bet_this_street=10, max_bet_on_table=40, min_raise=70,
    #     is_sb=False, is_bb=False,
    #     action_fold_const='fold', action_check_const='check', action_call_const='call', action_raise_const='raise',
    #     action_history=mock_action_history,
    #     opponent_tracker=mock_tracker 
    # )
    # print(f"Test Decision: {decision}, Amount: {amount}")
    pass # Placeholder for more comprehensive tests
