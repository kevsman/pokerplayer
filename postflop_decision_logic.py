# postflop_decision_logic.py

# Note: ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE are passed as arguments (e.g., action_fold_const)
# get_optimal_bet_size_func, calculate_expected_value_func, should_bluff_func may be passed.

def make_postflop_decision(
    decision_engine_instance, numerical_hand_rank, hand_description, bet_to_call, can_check, 
    pot_size, my_stack, win_probability, pot_odds_to_call, game_stage, spr,
    action_fold_const, action_check_const, action_call_const, action_raise_const,
    get_optimal_bet_size_func, # from bet_utils
    calculate_expected_value_func, # from ev_utils
    should_bluff_func # from ev_utils
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
        if is_very_strong or (is_strong and win_probability > 0.7):
            bet_amount = get_optimal_bet_size_func(numerical_hand_rank, pot_size, my_stack, game_stage, big_blind, False)
            bet_amount = min(bet_amount * aggression_multiplier, my_stack)
            bet_amount = max(bet_amount, big_blind)  # Minimum bet size
            return action_raise_const, round(bet_amount, 2)
          # Medium strength - bet for value if we have decent equity
        elif is_medium and win_probability > 0.45:  # Lowered from 0.55
            bet_amount = pot_size * 0.5  # Smaller value bet
            bet_amount = min(bet_amount * aggression_multiplier, my_stack)
            bet_amount = max(bet_amount, big_blind)
            return action_raise_const, round(bet_amount, 2)
          # River-specific logic for pairs - be more aggressive
        elif is_medium and game_stage == "River" and win_probability > 0.30:  # Very aggressive on river with pairs
            bet_amount = pot_size * 0.4  # Small value bet on river
            bet_amount = min(bet_amount * aggression_multiplier, my_stack)
            bet_amount = max(bet_amount, big_blind)
            return action_raise_const, round(bet_amount, 2)
        
        # Bluffing opportunities
        elif not is_medium and win_probability < 0.3 and should_bluff_func(pot_size, my_stack, win_probability):
            if game_stage in ["River"] and pot_size > big_blind * 3:  # River bluff
                bluff_amount = pot_size * 0.7
                bluff_amount = min(bluff_amount, my_stack * 0.4)
                if bluff_amount >= big_blind:
                    return action_raise_const, round(bluff_amount, 2)
        
        return action_check_const, 0

    else:  # Facing a bet        # Calculate EVs
        ev_call = calculate_expected_value_func(action_call_const, bet_to_call, pot_size, win_probability, bet_to_call)
        ev_fold = 0.0
          # Very strong hands - consider raising
        if is_very_strong:
            raise_amount = get_optimal_bet_size_func(numerical_hand_rank, pot_size, my_stack, game_stage, big_blind, False)
            raise_amount = max(raise_amount, bet_to_call * 2.5)  # Minimum 2.5x raise
            raise_amount = min(raise_amount, my_stack)
            
            ev_raise = calculate_expected_value_func(action_raise_const, raise_amount, pot_size, win_probability)
            
            if ev_raise > ev_call and raise_amount < my_stack * 0.8:
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
            required_equity = pot_odds_to_call * 0.9  # Give ourselves 10% discount
            if win_probability > required_equity and bet_to_call < pot_size * 0.8:
                return action_call_const, bet_to_call
            else:
                return action_fold_const, 0
        
        # Drawing hands and weak hands
        else:
            # Call with good pot odds or strong draws
            if (win_probability > pot_odds_to_call * 1.1) or \
               (is_draw and win_probability > 0.25 and bet_to_call < pot_size * 0.6):
                return action_call_const, bet_to_call
            else:
                return action_fold_const, 0
