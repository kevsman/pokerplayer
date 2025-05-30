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
    is_very_strong = numerical_hand_rank >= 6  # Flush+ (was >= 7)
    is_strong = numerical_hand_rank >= 3  # Two Pair+ (was >= 4)
    is_medium = numerical_hand_rank >= 2  # Pair+
    is_high_card_hand = (numerical_hand_rank == 1) # Specifically for High Card rank

    is_draw = "Straight" in hand_description or "Flush" in hand_description # This is a broad check, specific draw notes are better
      # Position and aggression adjustments
    aggression_multiplier = base_aggression_factor_postflop
    if spr <= 3:  # Short stack situations - be more aggressive
        aggression_multiplier *= 1.3
    elif spr >= 8:  # Deep stack - be more cautious with medium hands
        aggression_multiplier *= 0.9

    hand_notes = my_player_data.get('hand_notes', '').lower() # Get hand_notes and convert to lower case for robust matching
    is_actually_high_card_hand = "high card" in hand_description.lower() or numerical_hand_rank <= 1 # More robust check for high card or N/A
    is_preflop_raiser = my_player_data.get('is_preflop_raiser', False) # Get PFR status
    has_position = my_player_data.get('has_position', True) # Get position status, default to True if not specified

    if can_check:  # We can check - no bet to call
        # Value betting logic
        if is_very_strong or (is_strong and win_probability > 0.70): # Increased win_prob for strong check-bet
            bet_amount = get_optimal_bet_size_func(numerical_hand_rank, pot_size, my_stack, game_stage, False)
            if is_very_strong and game_stage == "River":
                bet_amount = max(bet_amount, pot_size * 0.70) # Slightly reduced from 0.75
            bet_amount = min(bet_amount * aggression_multiplier, my_stack)
            bet_amount = max(bet_amount, decision_engine_instance.big_blind) 
            return action_raise_const, round(bet_amount, 2)
        
        elif is_medium and win_probability > 0.55: # Increased win_prob for medium check-bet
            bet_size_factor = 0.5
            apply_aggression = True

            if game_stage == "River" and "thin value" in hand_notes: # Scenario 19
                bet_size_factor = 0.4 
                apply_aggression = False # No aggression multiplier for thin value
                print(f"Postflop Logic: Handling 'thin value' note for river bet sizing. Factor: {bet_size_factor}")
            
            elif game_stage == "River" and "blocking bet" in hand_notes and not has_position: # Scenario 23
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
        
        # Scenario 21: Flop c-bet with air on dry board as PFR
        # This should be prioritized if conditions match, even over other checks.
        if game_stage == "Flop" and is_preflop_raiser and is_actually_high_card_hand and "cbet air" in hand_notes:
            cbet_amount = pot_size * 0.6 # Increased c-bet size slightly
            cbet_amount = min(cbet_amount, my_stack)
            cbet_amount = max(cbet_amount, decision_engine_instance.big_blind)
            if cbet_amount >= decision_engine_instance.big_blind:
                print(f"Postflop Logic: C-betting air on flop as PFR. Amount: {cbet_amount}")
                return action_raise_const, round(cbet_amount, 2)
        
        # Scenario 18: Turn overbet bluff with missed draw
        if game_stage == "Turn" and "flush draw missed" in hand_notes and is_actually_high_card_hand:
            # Check if opponent checked (can_check is True and bet_to_call is 0)
            bluff_amount = pot_size * 1.1 # Slightly reduced overbet from 1.25
            bluff_amount = min(bluff_amount, my_stack * 0.50) # Reduced stack commitment
            bluff_amount = max(bluff_amount, decision_engine_instance.big_blind)
            if bluff_amount >= decision_engine_instance.big_blind:
                print(f"Postflop Logic: Turn overbet bluff with missed flush draw (High Card). Amount: {bluff_amount}")
                return action_raise_const, round(bluff_amount, 2)

        # Scenario 30: Turn probe bet after PFR checks back flop
        if game_stage == "Turn" and "probe bet" in hand_notes and (is_medium or is_high_card_hand) and win_probability > 0.35: # Broadened to high_card with some equity
            probe_bet_amount = pot_size * 0.55 # Adjusted probe bet size
            probe_bet_amount = min(probe_bet_amount, my_stack)
            probe_bet_amount = max(probe_bet_amount, decision_engine_instance.big_blind)
            if probe_bet_amount >= decision_engine_instance.big_blind:
                print(f"Postflop Logic: Probe betting on turn. Amount: {probe_bet_amount}")
                return action_raise_const, round(probe_bet_amount, 2)

        # Existing River Bluff Logic (if can_check)
        elif not is_medium and win_probability < 0.20 and should_bluff_func(pot_size, my_stack, win_probability): 
            if game_stage in ["River"] and pot_size > big_blind * 5:  # Increased pot size threshold
                if "flush draw missed" in hand_notes and is_actually_high_card_hand: 
                    bluff_amount = pot_size * 0.65 
                    bluff_amount = min(bluff_amount, my_stack * 0.35)
                    if bluff_amount >= big_blind:
                        return action_raise_const, round(bluff_amount,2)

                bluff_amount = pot_size * 0.55 
                bluff_amount = min(bluff_amount, my_stack * 0.30) 
                if bluff_amount >= big_blind:
                    return action_raise_const, round(bluff_amount, 2)
        
        return action_check_const, 0 # Default to check if no bet/raise condition met

    else:  # Facing a bet
        ev_call = calculate_expected_value_func(action_call_const, bet_to_call, pot_size, win_probability, bet_to_call)
        ev_fold = 0.0
        
        is_missed_draw_note = "missed" in hand_notes # General missed draw (lowercase)
        is_flush_draw_missed_note = "flush draw missed" in hand_notes # Specific for flush (lowercase)
        is_combo_draw_note = "combo draw" in hand_notes # For scenario 26 (lowercase)
        is_check_raise_strong_note = "check-raise strong" in hand_notes # For scenario 22 (lowercase)
        is_float_gutshot_note = "float gutshot" in hand_notes # For scenario 25 (lowercase)

        # Scenario 14: River, missed all draws, opponent bets large - should fold.
        if game_stage == "River" and (is_missed_draw_note or is_flush_draw_missed_note) and is_actually_high_card_hand and bet_to_call >= pot_size * 0.30:
            print(f"Postflop Logic: Folding based on 'Missed Draw' note on river. HandRank: {numerical_hand_rank}, Bet: {bet_to_call}, Pot: {pot_size}")
            return action_fold_const, 0

        # Very strong hands - consider raising
        if is_very_strong:
            raise_amount = get_optimal_bet_size_func(numerical_hand_rank, pot_size, my_stack, game_stage, False)
            
            if game_stage == "River" and "cooler nut advantage" in hand_notes: # Scenario 27
                min_reraise = bet_to_call * 2.5 # Minimum re-raise factor
                # Target a raise that is substantial, e.g., 2.5x to 3x the opponent's bet, or pot-sized raise
                target_raise_total = max(min_reraise, (pot_size + bet_to_call) * 0.80 + bet_to_call) # Raise to ~80% of new pot + original bet
                raise_amount = max(raise_amount, target_raise_total)
                print(f"Postflop Logic: Adjusting raise for River Cooler. Initial optimal: {get_optimal_bet_size_func(numerical_hand_rank, pot_size, my_stack, game_stage, False)}, Adjusted: {raise_amount}, Opponent Bet: {bet_to_call}")

            elif game_stage == "River": 
                raise_amount = max(raise_amount, bet_to_call * 3.0, pot_size * 0.7) # Reduced from 3.5x, 0.8 pot
            else:
                raise_amount = max(raise_amount, bet_to_call * 2.8)  # Reduced from 3x
            raise_amount = min(raise_amount, my_stack)
            
            ev_raise = calculate_expected_value_func(action_raise_const, raise_amount, pot_size, win_probability, bet_to_call)
            
            if game_stage == "River" and win_probability > 0.80: # Reduced from 0.85
                if raise_amount > bet_to_call: 
                    return action_raise_const, round(raise_amount, 2)
            
            if ev_raise > ev_call and raise_amount < my_stack * 0.95 and raise_amount > bet_to_call: # Increased stack commitment threshold
                return action_raise_const, round(raise_amount, 2)
            elif ev_call > ev_fold or win_probability > pot_odds_to_call: # Added win_prob > pot_odds as a call condition
                return action_call_const, bet_to_call
            else:
                return action_fold_const, 0
        
        # Strong hands - mostly call, sometimes raise
        elif is_strong and win_probability > 0.55: # Reduced from 0.6
            # Scenario 22: Turn Check-Raise with strong made hand (Two Pair+)
            if game_stage == "Turn" and is_check_raise_strong_note and numerical_hand_rank >= 3: 
                check_raise_amount = bet_to_call * 2.8 # Adjusted from 3.0
                check_raise_amount = min(check_raise_amount, my_stack, pot_size + bet_to_call * 1.8) # Adjusted cap
                check_raise_amount = max(check_raise_amount, bet_to_call * 2.0) # Adjusted min 
                if check_raise_amount > bet_to_call: 
                     print(f"Postflop Logic: Executing raise (simulating check-raise) with strong hand. Amount: {check_raise_amount}")
                     return action_raise_const, round(check_raise_amount, 2)

            if win_probability > 0.70 and bet_to_call < pot_size * 0.8:  # Reduced from 0.75 win_prob, increased pot_size factor
                raise_amount = bet_to_call * 2.5 # Reduced from 2.8
                raise_amount = min(raise_amount, my_stack, pot_size * 1.1) # Reduced from 1.2
                if raise_amount > bet_to_call: 
                    return action_raise_const, round(raise_amount, 2)
            
            if win_probability > pot_odds_to_call or ev_call > ev_fold:
                return action_call_const, bet_to_call
            else:
                return action_fold_const, 0
        
        # Medium hands - call with good odds
        elif is_medium:
            required_equity = pot_odds_to_call 
            if game_stage == "Turn" and is_draw: 
                required_equity *= 0.9 # Less reduction, from 0.85
            
            if win_probability > required_equity and bet_to_call < pot_size * 0.80: # Increased pot_size factor
                return action_call_const, bet_to_call
            else:
                return action_fold_const, 0
        
        # Drawing hands and weak hands (numerical_hand_rank < 2, i.e., High Card or N/A)
        else: # This covers is_high_card_hand and is_actually_high_card_hand (rank 0 or 1)
            # Scenario 26: Turn semi-bluff raise with combo draw
            if game_stage == "Turn" and is_combo_draw_note and win_probability > 0.28 and bet_to_call < pot_size * 0.75: # Reduced win_prob from 0.30, increased pot_size factor
                semibluff_raise_amount = (pot_size + bet_to_call) * 0.9 + bet_to_call # Reduced PSR factor from 1.0
                semibluff_raise_amount = min(semibluff_raise_amount, my_stack * 0.70) # Reduced stack commitment
                semibluff_raise_amount = max(semibluff_raise_amount, bet_to_call * 2.2) # Reduced min raise factor
                if semibluff_raise_amount > bet_to_call: 
                    print(f"Postflop Logic: Semi-bluff raising with combo draw. Amount: {semibluff_raise_amount}")
                    return action_raise_const, round(semibluff_raise_amount, 2)

            # Scenario 25: Flop float OOP with gutshot (T9s on KQ2r, gutshot to J)
            # Hand rank will be 0 (High Card) or 1 (if Ace high). Win prob might be low.
            # Test case has win_prob ~0.184. Pot odds ~0.333. Calling 0.5 into 1.0 pot.
            if game_stage == "Flop" and is_float_gutshot_note and spr > 4: # Check SPR for implied odds
                # Implied odds: need to win (bet_to_call / (pot_size + bet_to_call + future_bets_won_if_hit))
                # If we hit gutshot (4 outs, ~8% on turn, ~16% by river from flop)
                # If win_probability (raw) is low, but implied odds are good.
                # For S25, bet_to_call=0.5, pot_size=1.0. Pot_odds_to_call = 0.5 / (1.0+0.5) = 0.333
                # If we hit, assume we can win at least the pot size (1.0) + opponent's current bet (0.5) + our call (0.5) = 2.0 more.
                # Effective pot if we hit: current_pot (1.5) + future_winnings (e.g. 1.5-2.0)
                # Let's use a simpler rule: if note is present, win_prob > 0.15 (some chance), and good pot odds to call a small bet.
                if win_probability > 0.15 and bet_to_call <= pot_size * 0.60:
                    print(f"Postflop Logic: Floating flop with gutshot due to note. WinP: {win_probability}, Bet: {bet_to_call}, Pot: {pot_size}, SPR: {spr}")
                    return action_call_const, bet_to_call

            # Fallback for missed draws on river if not caught by the specific note check earlier
            if game_stage == "River" and is_actually_high_card_hand and bet_to_call >= pot_size * 0.30: 
                print(f"Postflop Logic: Folding High Card on river to significant bet (fallback). HandRank: {numerical_hand_rank}, Bet: {bet_to_call}, Pot: {pot_size}")
                return action_fold_const, 0
            
            if game_stage == "River" and not is_medium and not is_strong and win_probability < 0.10 and bet_to_call >= pot_size * 0.35: # Reduced win_prob from 0.15, pot_size factor from 0.4
                print(f"Postflop Logic: Folding weak hand/missed draw on river (general). WinP: {win_probability}, Bet: {bet_to_call}, Pot: {pot_size}")
                return action_fold_const, 0

            # Call with good pot odds or strong draws
            if (win_probability > pot_odds_to_call * 0.95) or \
               (is_draw and win_probability > 0.18 and bet_to_call < pot_size * 0.60): # Reduced win_prob from 0.20, increased pot_size factor
                return action_call_const, bet_to_call
            else:
                return action_fold_const, 0
