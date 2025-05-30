# postflop_decision_logic.py

import logging

# Note: ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE are passed as arguments (e.g., action_fold_const)

def make_postflop_decision(
    decision_engine_instance, 
    numerical_hand_rank, 
    hand_description, 
    bet_to_call, 
    can_check, 
    pot_size, 
    my_stack, 
    win_probability, 
    pot_odds_to_call, 
    game_stage, 
    spr,
    action_fold_const,
    action_check_const, 
    action_call_const,  
    action_bet_const,
    action_raise_const, 
    my_player_data, # Added to access notes, current_bet etc.
    big_blind_amount, # Added, was big_blind
    base_aggression_factor # Added, was base_aggression_factor_postflop
):
    """Enhanced post-flop decision making logic."""
    
    # Access helper functions from decision_engine_instance if they are methods of it
    # or ensure they are available in the scope if they are global utility functions.
    # For now, assuming they are attributes/methods of decision_engine_instance or global
    get_optimal_bet_size_func = decision_engine_instance.get_optimal_bet_size_func # Example if it's a method
    should_bluff_func = decision_engine_instance.should_bluff_func # Example
    # calculate_expected_value_func = decision_engine_instance.calculate_expected_value_func # Example

    # Use passed big_blind_amount and base_aggression_factor directly
    big_blind = big_blind_amount
    # base_aggression_factor_postflop = base_aggression_factor # Already passed as base_aggression_factor

    is_very_strong = numerical_hand_rank >= 6
    is_strong = numerical_hand_rank >= 3
    is_medium = numerical_hand_rank >= 2
    # is_high_card_hand = (numerical_hand_rank == 1) # Defined later as is_actually_high_card_hand

    aggression_multiplier = base_aggression_factor # Use the passed base_aggression_factor
    if spr <= 3:
        aggression_multiplier *= 1.3
    elif spr >= 8:
        aggression_multiplier *= 0.9

    hand_notes = my_player_data.get('hand_notes', '').lower()
    is_actually_high_card_hand = "high card" in hand_description.lower() or numerical_hand_rank <= 1
    is_preflop_raiser = my_player_data.get('is_preflop_raiser', False)
    has_position = my_player_data.get('has_position', True)
    current_street = game_stage

    # Define note-based booleans
    is_check_raise_strong_note = "check-raise strong" in hand_notes
    is_combo_draw_note = "combo draw" in hand_notes
    is_float_gutshot_note = "float gutshot" in hand_notes

    # Simplified EV calculation for now to define ev_call and ev_fold
    if bet_to_call > 0:
        ev_call = (win_probability * (pot_size + bet_to_call)) - ((1 - win_probability) * bet_to_call)
    else:
        ev_call = win_probability * pot_size
    ev_fold = 0

    logging.debug(f"make_postflop_decision: street={current_street}, my_player_data={my_player_data}, pot_size={pot_size}, win_prob={win_probability}, pot_odds={pot_odds_to_call}")

    if not my_player_data.get('has_turn', False):
        return None, 0 

    if can_check:
        if is_very_strong or (is_strong and win_probability > 0.40) or (is_medium and win_probability > 0.60):
            # Assuming get_optimal_bet_size_func is available via decision_engine_instance or globally
            bet_amount = get_optimal_bet_size_func(numerical_hand_rank, pot_size, my_stack, game_stage, False)
            if is_very_strong and game_stage == "River":
                bet_amount = max(bet_amount, pot_size * 0.70) 
            bet_amount = min(bet_amount * aggression_multiplier, my_stack)
            bet_amount = max(bet_amount, big_blind) 
            return action_bet_const, round(bet_amount, 2)
        
        elif is_medium and win_probability > 0.50: 
            if game_stage == "River":
                if "thin value" in hand_notes: 
                    bet_amount = pot_size * 0.4 
                    bet_amount = min(bet_amount, my_stack)
                    bet_amount = max(bet_amount, big_blind) 
                    return action_bet_const, round(bet_amount, 2)
                
                elif "blocking bet" in hand_notes and not has_position: 
                    bet_amount = pot_size * 0.30
                    bet_amount = min(bet_amount, my_stack)
                    bet_amount = max(bet_amount, big_blind) 
                    return action_bet_const, round(bet_amount, 2)

            bet_size_factor = 0.5
            bet_amount = pot_size * bet_size_factor
            bet_amount = min(bet_amount * aggression_multiplier, my_stack) 
            bet_amount = max(bet_amount, big_blind) 
            return action_bet_const, round(bet_amount, 2)
        
        if game_stage == "Flop" and is_preflop_raiser and is_actually_high_card_hand and "cbet air" in hand_notes:
            cbet_amount = pot_size * 0.6
            cbet_amount = min(cbet_amount, my_stack)
            cbet_amount = max(cbet_amount, big_blind)
            if cbet_amount >= big_blind:
                return action_bet_const, round(cbet_amount, 2)
        
        if game_stage == "Turn" and "flush draw missed" in hand_notes and is_actually_high_card_hand:
            bluff_amount = pot_size * 1.1
            bluff_amount = min(bluff_amount, my_stack * 0.50)
            bluff_amount = max(bluff_amount, big_blind)
            if bluff_amount >= big_blind:
                return action_bet_const, round(bluff_amount, 2)

        if game_stage == "Turn" and "probe bet" in hand_notes and (is_medium or is_actually_high_card_hand) and win_probability > 0.10:
            probe_bet_amount = pot_size * 0.55
            probe_bet_amount = min(probe_bet_amount, my_stack)
            probe_bet_amount = max(probe_bet_amount, big_blind)
            if probe_bet_amount >= big_blind:
                return action_bet_const, round(probe_bet_amount, 2)

        # Assuming should_bluff_func is available
        elif not is_medium and win_probability < 0.20 and should_bluff_func(pot_size, my_stack, win_probability): 
            if game_stage in ["River"] and pot_size > big_blind * 5:
                if "flush draw missed" in hand_notes and is_actually_high_card_hand: 
                    bluff_amount = pot_size * 0.65 
                    bluff_amount = min(bluff_amount, my_stack * 0.35)
                    if bluff_amount >= big_blind:
                        return action_bet_const, round(bluff_amount,2)

                bluff_amount = pot_size * 0.55 
                bluff_amount = min(bluff_amount, my_stack * 0.30) 
                if bluff_amount >= big_blind:
                    return action_bet_const, round(bluff_amount, 2)
        
        return action_check_const, 0

    else:  # Facing a bet
        logging.debug(f"Facing a bet. bet_to_call: {bet_to_call}, pot_size: {pot_size}, my_stack: {my_stack}")
        if is_very_strong:
            logging.debug(f"Hand is_very_strong. win_probability: {win_probability}")
            if current_street == 'River' and win_probability > 0.90 and bet_to_call > 0:
                logging.debug("River, very strong hand, win_prob > 0.90, facing a bet. Considering a raise.")
                pot_sized_raise_total_bet = bet_to_call + (pot_size + bet_to_call) 
                three_x_raise_total_bet = bet_to_call * 3.0 
                raise_amount_total = max(three_x_raise_total_bet, pot_sized_raise_total_bet)
                min_total_raise_bet = bet_to_call + max(bet_to_call, big_blind)
                raise_amount_total = max(raise_amount_total, min_total_raise_bet)
                # Access current_bet from my_player_data
                raise_amount_total = min(raise_amount_total, my_stack + my_player_data.get('current_bet', 0))
                actual_bet_amount_for_engine = raise_amount_total

                logging.debug(f"Calculated raise. pot_sized_raise_total_bet: {pot_sized_raise_total_bet}, three_x_raise_total_bet: {three_x_raise_total_bet}")
                logging.debug(f"min_total_raise_bet: {min_total_raise_bet}, initial raise_amount_total: {raise_amount_total}")
                logging.debug(f"Opponent\'s bet (bet_to_call): {bet_to_call}, My current bet in round: {my_player_data.get('current_bet', 0)}")
                logging.debug(f"Final actual_bet_amount_for_engine for raise: {actual_bet_amount_for_engine}, my_stack: {my_stack}")

                if actual_bet_amount_for_engine > bet_to_call and actual_bet_amount_for_engine <= (my_stack + my_player_data.get('current_bet', 0)):
                    logging.info(f"Decision: RAISE (very strong river) to {actual_bet_amount_for_engine}")
                    return action_raise_const, actual_bet_amount_for_engine
                else:
                    logging.warning(f"Calculated raise {actual_bet_amount_for_engine} was not valid (bet_to_call: {bet_to_call}, stack: {my_stack}). Defaulting to CALL.")
                    logging.info(f"Decision: CALL (fallback from invalid raise attempt)")
                    return action_call_const, bet_to_call
            
            logging.debug(f"Hand is_very_strong, but not meeting specific river raise conditions (street: {current_street}, win_prob: {win_probability}, bet_to_call: {bet_to_call}). Defaulting to CALL.")
            logging.info(f"Decision: CALL (very strong, but not river re-raise scenario)")
            return action_call_const, bet_to_call
        
        elif is_strong:
            if game_stage == "Turn" and is_check_raise_strong_note and my_player_data.get('last_action') == action_check_const:
                # Assuming get_optimal_bet_size_func is available
                check_raise_amount = get_optimal_bet_size_func(numerical_hand_rank, pot_size + bet_to_call, my_stack, game_stage, True)
                check_raise_amount = max(check_raise_amount, bet_to_call * 2.5)
                check_raise_amount = min(check_raise_amount, my_stack)
                if check_raise_amount > bet_to_call:
                    return action_raise_const, round(check_raise_amount, 2)

            if ev_call > ev_fold or win_probability > pot_odds_to_call:
                 return action_call_const, bet_to_call
            else:
                return action_fold_const, 0

        elif is_medium and win_probability > 0.35:
            if game_stage == "Turn" and is_combo_draw_note and win_probability > pot_odds_to_call * 0.9:
                 return action_call_const, bet_to_call
            
            if ev_call > ev_fold or win_probability > pot_odds_to_call:
                return action_call_const, bet_to_call
            else:
                return action_fold_const, 0
        
        else: 
            if game_stage == "Flop" and is_float_gutshot_note and not has_position and bet_to_call <= pot_size * 0.40 and win_probability > pot_odds_to_call * 0.8:
                return action_call_const, bet_to_call

            if is_actually_high_card_hand and bet_to_call >= big_blind * 2 and win_probability < 0.55 :
                return action_fold_const, 0
            
            if win_probability < pot_odds_to_call * 0.8: # Be more willing to fold if odds are bad
                return action_fold_const, 0

            if ev_call > ev_fold: # Fallback call based on simplified EV
                return action_call_const, bet_to_call
            
            return action_fold_const, 0
