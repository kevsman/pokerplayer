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

    print(f"Postflop Logic: Hand Rank: {numerical_hand_rank}, WinP: {win_probability:.3f}, SPR: {spr:.2f}, BetToCall: {bet_to_call}")

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

    if can_check:  # We can check - no bet to call
        # Value betting logic
        if is_very_strong or (is_strong and win_probability > 0.65):
            bet_amount = get_optimal_bet_size_func(numerical_hand_rank, pot_size, my_stack, game_stage, False)
            # Ensure bet amount is substantial for very strong hands
            if is_very_strong and game_stage == "River":
                bet_amount = max(bet_amount, pot_size * 0.75) # Bet larger on river with nuts
            bet_amount = min(bet_amount * aggression_multiplier, my_stack)
            bet_amount = max(bet_amount, decision_engine_instance.big_blind) 
            return action_raise_const, round(bet_amount, 2)
        # Medium strength - bet for value if we have decent equity
        elif is_medium and win_probability > 0.50:  # Adjusted from 0.45
            bet_amount = pot_size * 0.5  # Smaller value bet
            bet_amount = min(bet_amount * aggression_multiplier, my_stack)
            bet_amount = max(bet_amount, decision_engine_instance.big_blind)
            return action_raise_const, round(bet_amount, 2)
        # River-specific logic for pairs - be more aggressive
        elif is_medium and game_stage == "River" and win_probability > 0.30:  # Very aggressive on river with pairs
            bet_amount = pot_size * 0.4  # Small value bet on river
            bet_amount = min(bet_amount * aggression_multiplier, my_stack)
            bet_amount = max(bet_amount, decision_engine_instance.big_blind)
            return action_raise_const, round(bet_amount, 2)
        
        # Bluffing opportunities
        # Accessing hand_notes from my_player_data for specific bluff scenario
        elif not is_medium and win_probability < 0.25 and should_bluff_func(pot_size, my_stack, win_probability): 
            if game_stage in ["River"] and pot_size > big_blind * 4:  
                hand_notes = my_player_data.get('hand_notes', '') # Get hand_notes
                if "Flush Draw Missed" in hand_notes and hand_description == "High Card":
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
        # Calculate EVs
        ev_call = calculate_expected_value_func(action_call_const, bet_to_call, pot_size, win_probability, bet_to_call)
        ev_fold = 0.0
        # Very strong hands - consider raising
        if is_very_strong:
            raise_amount = get_optimal_bet_size_func(numerical_hand_rank, pot_size, my_stack, game_stage, False)
            if game_stage == "River": # On the river, be more aggressive with raises
                raise_amount = max(raise_amount, bet_to_call * 3.5, pot_size * 0.8)
            else:
                raise_amount = max(raise_amount, bet_to_call * 3)  
            raise_amount = min(raise_amount, my_stack)
            
            ev_raise = calculate_expected_value_func(action_raise_const, raise_amount, pot_size, win_probability, bet_to_call)
            
            # For very strong hands, especially on the river, be more inclined to raise than call.
            if game_stage == "River" and win_probability > 0.85: # If very high confidence on river
                if raise_amount > bet_to_call: # Ensure it's a valid raise
                    return action_raise_const, round(raise_amount, 2)
            
            if ev_raise > ev_call and raise_amount < my_stack * 0.9: 
                return action_raise_const, round(raise_amount, 2)
            elif ev_call > ev_fold: 
                return action_call_const, bet_to_call
            else:
                return action_fold_const, 0
        
        # Strong hands - mostly call, sometimes raise
        elif is_strong and win_probability > 0.6:
            if win_probability > 0.75 and bet_to_call < pot_size:  # Very strong equity, reasonable bet size
                raise_amount = bet_to_call * 2.8
                raise_amount = min(raise_amount, my_stack, pot_size * 1.2)
                return action_raise_const, round(raise_amount, 2)
            elif win_probability > pot_odds_to_call or ev_call > ev_fold:
                return action_call_const, bet_to_call
            else:
                return action_fold_const, 0
        
        # Medium hands - call with good odds
        elif is_medium:
            # More liberal calling with pairs
            required_equity = pot_odds_to_call 
            if game_stage == "Turn" and is_draw: # If we have a pair + draw on turn, be more willing to call
                required_equity *= 0.85 # Discount required equity for draws
            
            if win_probability > required_equity and bet_to_call < pot_size * 0.75: # Call if equity > pot_odds and bet is not too large
                return action_call_const, bet_to_call
            else:
                return action_fold_const, 0
        
        # Drawing hands and weak hands
        else:
            # Scenario 14: River, missed all draws, opponent bets large - should fold.
            # If it's river, hand is weak (not medium or strong), and win_probability is low, and facing a significant bet.
            if game_stage == "River" and not is_medium and not is_strong and win_probability < 0.15 and bet_to_call >= pot_size * 0.5:
                print(f"Postflop Logic: Folding missed draw on river. WinP: {win_probability}, Bet: {bet_to_call}, Pot: {pot_size}")
                return action_fold_const, 0

            # Call with good pot odds or strong draws
            if (win_probability > pot_odds_to_call * 1.05) or \
               (is_draw and win_probability > 0.20 and bet_to_call < pot_size * 0.55): # Adjusted thresholds for draws
                return action_call_const, bet_to_call
            else:
                return action_fold_const, 0
