# postflop_decision_logic.py

# Note: ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE are passed as arguments (e.g., action_fold_const)
# get_optimal_bet_size_func, calculate_expected_value_func, should_bluff_func may be passed.

def make_postflop_decision(
    decision_engine_instance, numerical_hand_rank, hand_description, bet_to_call, can_check, 
    pot_size, my_stack, win_probability, pot_odds_to_call, game_stage, spr,
    action_fold_const, action_check_const, action_call_const, action_raise_const,
    get_optimal_bet_size_func, # from bet_utils
    calculate_expected_value_func, # from ev_utils
    should_bluff_func, # from ev_utils
    my_player_data # Added to access hand_notes for specific scenarios
    ):
    """Enhanced post-flop decision making logic."""
    
    big_blind = decision_engine_instance.big_blind
    base_aggression_factor_postflop = decision_engine_instance.base_aggression_factor_postflop

    print(f"Postflop Logic: Hand Rank: {numerical_hand_rank}, WinP: {win_probability:.3f}, SPR: {spr:.2f}, BetToCall: {bet_to_call}, Pot: {pot_size}, MyStack: {my_stack}, Stage: {game_stage}, Notes: {my_player_data.get('hand_notes', '')}")

    # Define hand strength categories based on hand rank
    is_very_strong = numerical_hand_rank >= 7  # Full house+
    is_strong = numerical_hand_rank >= 4  # Three of a kind+
    is_medium = numerical_hand_rank >= 2  # Pair+
    is_draw = "Straight" in hand_description or "Flush" in hand_description
      # Position and aggression adjustments
    aggression_multiplier = base_aggression_factor_postflop
    if spr <= 3:  # Short stack situations - be more aggressive
        aggression_multiplier *= 1.3
    elif spr >= 8:  # Deep stack - be more cautious with medium hands
        aggression_multiplier *= 0.9

    hand_notes = my_player_data.get('hand_notes', '') # Get hand_notes for broader use
    is_actually_high_card_hand = "High Card" in hand_description or numerical_hand_rank == 0 # More robust check for high card
    is_preflop_raiser = my_player_data.get('is_preflop_raiser', False) # Get PFR status
    has_position = my_player_data.get('has_position', True) # Get position status

    if can_check:  # We can check - no bet to call
        # Value betting logic
        if is_very_strong or (is_strong and win_probability > 0.65):
            bet_amount = get_optimal_bet_size_func(numerical_hand_rank, pot_size, my_stack, game_stage, False)
            if is_very_strong and game_stage == "River":
                bet_amount = max(bet_amount, pot_size * 0.75) 
            bet_amount = min(bet_amount * aggression_multiplier, my_stack)
            bet_amount = max(bet_amount, decision_engine_instance.big_blind) 
            return action_raise_const, round(bet_amount, 2)
        
        elif is_medium and win_probability > 0.50:
            bet_size_factor = 0.5
            apply_aggression = True

            if game_stage == "River" and "Thin Value" in hand_notes: # Scenario 19
                bet_size_factor = 0.4 
                apply_aggression = False # No aggression multiplier for thin value
                print(f"Postflop Logic: Handling 'Thin Value' note for river bet sizing. Factor: {bet_size_factor}")
            
            elif game_stage == "River" and "Blocking Bet" in hand_notes and not has_position: # Scenario 23
                bet_size_factor = 0.30 
                apply_aggression = False 
                print(f"Postflop Logic: Applying blocking bet sizing for {hand_description}. Factor: {bet_size_factor}")

            bet_amount = pot_size * bet_size_factor
            if apply_aggression:
                bet_amount = min(bet_amount * aggression_multiplier, my_stack)
            else:
                bet_amount = min(bet_amount, my_stack)
            
            bet_amount = max(bet_amount, decision_engine_instance.big_blind)
            return action_raise_const, round(bet_amount, 2)
        
        elif is_medium and game_stage == "River" and win_probability > 0.30:
            bet_amount = pot_size * 0.4 
            bet_amount = min(bet_amount * aggression_multiplier, my_stack)
            bet_amount = max(bet_amount, decision_engine_instance.big_blind)
            return action_raise_const, round(bet_amount, 2)
        
        # Bluffing opportunities
        # Scenario 18: Turn overbet bluff with missed draw
        if game_stage == "Turn" and "Flush Draw Missed" in hand_notes and is_actually_high_card_hand and numerical_hand_rank < 1:
            # Check if opponent checked (can_check is True and bet_to_call is 0)
            bluff_amount = pot_size * 1.25 
            bluff_amount = min(bluff_amount, my_stack * 0.60) 
            bluff_amount = max(bluff_amount, decision_engine_instance.big_blind)
            if bluff_amount >= decision_engine_instance.big_blind:
                print(f"Postflop Logic: Turn overbet bluff with missed flush draw (High Card). Amount: {bluff_amount}")
                return action_raise_const, round(bluff_amount, 2)

        # Scenario 21: Flop c-bet with air on dry board as PFR
        if game_stage == "Flop" and is_preflop_raiser and numerical_hand_rank < 1 and "CBet Air" in hand_notes:
            cbet_amount = pot_size * 0.5 
            cbet_amount = min(cbet_amount, my_stack)
            cbet_amount = max(cbet_amount, decision_engine_instance.big_blind)
            if cbet_amount >= decision_engine_instance.big_blind:
                print(f"Postflop Logic: C-betting air on flop as PFR. Amount: {cbet_amount}")
                return action_raise_const, round(cbet_amount, 2)
        
        # Scenario 30: Turn probe bet after PFR checks back flop
        if game_stage == "Turn" and "Probe Bet" in hand_notes and is_medium and win_probability > 0.4:
            # This implies PFR checked flop and it's our turn to act (can_check is True)
            probe_bet_amount = pot_size * 0.6 
            probe_bet_amount = min(probe_bet_amount, my_stack)
            probe_bet_amount = max(probe_bet_amount, decision_engine_instance.big_blind)
            if probe_bet_amount >= decision_engine_instance.big_blind:
                print(f"Postflop Logic: Probe betting on turn. Amount: {probe_bet_amount}")
                return action_raise_const, round(probe_bet_amount, 2)

        # Existing River Bluff Logic
        elif not is_medium and win_probability < 0.25 and should_bluff_func(pot_size, my_stack, win_probability): 
            if game_stage in ["River"] and pot_size > big_blind * 4:  
                if "Flush Draw Missed" in hand_notes and is_actually_high_card_hand: # More specific for missed draw bluff
                    bluff_amount = pot_size * 0.7 
                    bluff_amount = min(bluff_amount, my_stack * 0.40)
                    if bluff_amount >= big_blind:
                        return action_raise_const, round(bluff_amount,2)

                bluff_amount = pot_size * 0.6 
                bluff_amount = min(bluff_amount, my_stack * 0.35) 
                if bluff_amount >= big_blind:
                    return action_raise_const, round(bluff_amount, 2)
        
        return action_check_const, 0

    else:  # Facing a bet
        ev_call = calculate_expected_value_func(action_call_const, bet_to_call, pot_size, win_probability, bet_to_call)
        ev_fold = 0.0
        
        is_missed_draw_note = "Missed" in hand_notes # General missed draw
        is_flush_draw_missed_note = "Flush Draw Missed" in hand_notes # Specific for flush
        is_combo_draw_note = "Combo Draw" in hand_notes # For scenario 26
        is_check_raise_strong_note = "Check-Raise Strong" in hand_notes # For scenario 22

        # Scenario 14: River, missed all draws, opponent bets large - should fold.
        # If hand_notes explicitly says a draw was missed, and it's the river facing a sizable bet.
        # numerical_hand_rank < 1 means High Card or worse. numerical_hand_rank == 0 is High Card.
        if game_stage == "River" and (is_missed_draw_note or is_flush_draw_missed_note) and numerical_hand_rank < 1 and bet_to_call >= pot_size * 0.35:
            print(f"Postflop Logic: Folding based on 'Missed Draw' note on river. HandRank: {numerical_hand_rank}, Bet: {bet_to_call}, Pot: {pot_size}")
            return action_fold_const, 0

        # Very strong hands - consider raising
        if is_very_strong:
            raise_amount = get_optimal_bet_size_func(numerical_hand_rank, pot_size, my_stack, game_stage, False)
            
            if game_stage == "River" and "Cooler Nut Advantage" in hand_notes: # Scenario 27
                min_reraise = bet_to_call * 2.5
                # Ensure raise_amount is at least min_reraise, and also consider pot-based sizing
                raise_amount = max(raise_amount, min_reraise, (pot_size + bet_to_call) * 0.75 + bet_to_call) # Raise to 3/4 of new pot + original bet
                print(f"Postflop Logic: Adjusting raise for River Cooler. Initial optimal: {get_optimal_bet_size_func(numerical_hand_rank, pot_size, my_stack, game_stage, False)}, Adjusted: {raise_amount}, Opponent Bet: {bet_to_call}")

            elif game_stage == "River": 
                raise_amount = max(raise_amount, bet_to_call * 3.5, pot_size * 0.8)
            else:
                raise_amount = max(raise_amount, bet_to_call * 3)  
            raise_amount = min(raise_amount, my_stack)
            
            ev_raise = calculate_expected_value_func(action_raise_const, raise_amount, pot_size, win_probability, bet_to_call)
            
            if game_stage == "River" and win_probability > 0.85: 
                if raise_amount > bet_to_call: # Ensure it's a valid raise
                    return action_raise_const, round(raise_amount, 2)
            
            if ev_raise > ev_call and raise_amount < my_stack * 0.9 and raise_amount > bet_to_call: 
                return action_raise_const, round(raise_amount, 2)
            elif ev_call > ev_fold: 
                return action_call_const, bet_to_call
            else:
                return action_fold_const, 0
        
        # Strong hands - mostly call, sometimes raise
        elif is_strong and win_probability > 0.6:
            # Scenario 22: Turn Check-Raise with strong made hand (Two Pair+)
            # This logic assumes the 'check' part happened, and now we are facing a bet.
            if game_stage == "Turn" and is_check_raise_strong_note and numerical_hand_rank >= 3: # Rank 3 is Two Pair
                check_raise_amount = bet_to_call * 3.0
                check_raise_amount = min(check_raise_amount, my_stack, pot_size + bet_to_call * 2) # Cap at pot + 2x bet
                check_raise_amount = max(check_raise_amount, bet_to_call * 2.2) 
                if check_raise_amount > bet_to_call: # Ensure it's a valid raise
                     print(f"Postflop Logic: Executing raise (simulating check-raise) with strong hand. Amount: {check_raise_amount}")
                     return action_raise_const, round(check_raise_amount, 2)

            if win_probability > 0.75 and bet_to_call < pot_size:  
                raise_amount = bet_to_call * 2.8
                raise_amount = min(raise_amount, my_stack, pot_size * 1.2)
                if raise_amount > bet_to_call: # Ensure it's a valid raise
                    return action_raise_const, round(raise_amount, 2)
            
            if win_probability > pot_odds_to_call or ev_call > ev_fold:
                return action_call_const, bet_to_call
            else:
                return action_fold_const, 0
        
        # Medium hands - call with good odds
        elif is_medium:
            required_equity = pot_odds_to_call 
            if game_stage == "Turn" and is_draw: 
                required_equity *= 0.85 
            
            if win_probability > required_equity and bet_to_call < pot_size * 0.75: 
                return action_call_const, bet_to_call
            else:
                return action_fold_const, 0
        
        # Drawing hands and weak hands (numerical_hand_rank < 2)
        else:
            # Scenario 26: Turn semi-bluff raise with combo draw
            if game_stage == "Turn" and is_combo_draw_note and win_probability > 0.30 and bet_to_call < pot_size * 0.7: 
                semibluff_raise_amount = (pot_size + bet_to_call) * 1.0 + bet_to_call # Pot-sized raise (pot + call + bet)
                semibluff_raise_amount = min(semibluff_raise_amount, my_stack * 0.75) 
                semibluff_raise_amount = max(semibluff_raise_amount, bet_to_call * 2.5) 
                if semibluff_raise_amount > bet_to_call: # Ensure it's a valid raise
                    print(f"Postflop Logic: Semi-bluff raising with combo draw. Amount: {semibluff_raise_amount}")
                    return action_raise_const, round(semibluff_raise_amount, 2)

            # Fallback for missed draws on river if not caught by the specific note check earlier
            if game_stage == "River" and numerical_hand_rank < 1 and bet_to_call >= pot_size * 0.35: 
                print(f"Postflop Logic: Folding High Card on river to significant bet (fallback). HandRank: {numerical_hand_rank}, Bet: {bet_to_call}, Pot: {pot_size}")
                return action_fold_const, 0
            
            if game_stage == "River" and not is_medium and not is_strong and win_probability < 0.15 and bet_to_call >= pot_size * 0.4: 
                print(f"Postflop Logic: Folding weak hand/missed draw on river (general). WinP: {win_probability}, Bet: {bet_to_call}, Pot: {pot_size}")
                return action_fold_const, 0

            # Call with good pot odds or strong draws
            if (win_probability > pot_odds_to_call * 1.05) or \
               (is_draw and win_probability > 0.20 and bet_to_call < pot_size * 0.55): 
                if game_stage == "Flop" and "Float Gutshot" in hand_notes and bet_to_call < pot_size * 0.6 and spr > 5: 
                    print(f"Postflop Logic: Floating flop with gutshot. WinP: {win_probability}, Bet: {bet_to_call}, Pot: {pot_size}, SPR: {spr}")
                    return action_call_const, bet_to_call
                
                return action_call_const, bet_to_call
            else:
                return action_fold_const, 0
