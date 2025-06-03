# ev_utils.py

def _estimate_fold_equity(bet_size, pot_size):
    """
    Estimate the probability that opponents will fold to our bet
    Based on bet size relative to pot
    """
    if pot_size <= 0:
        return 0.1  # Conservative estimate
        
    bet_to_pot_ratio = bet_size / pot_size
    
    # Rough estimates based on common poker theory
    if bet_to_pot_ratio <= 0.3:
        return 0.1  # Small bets rarely make opponents fold
    elif bet_to_pot_ratio <= 0.5:
        return 0.2
    elif bet_to_pot_ratio <= 0.75:
        return 0.3
    elif bet_to_pot_ratio <= 1.0:
        return 0.4
    elif bet_to_pot_ratio <= 1.5:
        return 0.5
    else:
        return 0.6  # Large overbets have higher fold equity

def calculate_expected_value(action, amount, pot_size, win_probability, 
                             action_fold_const, action_check_const, action_call_const, action_raise_const,
                             bet_to_call=0):
    """
    Calculate Expected Value (EV) for a given action
    Returns the EV in chips/currency units
    """
    if action == action_fold_const:
        return 0.0
        
    elif action == action_check_const:
        return win_probability * pot_size
        
    elif action == action_call_const:
        return (win_probability * (pot_size + bet_to_call)) - bet_to_call
        
    elif action == action_raise_const:
        # amount is the total size of our bet for this round
        # pot_size is the current pot, including opponent's bet (bet_to_call)
        # bet_to_call is the opponent's bet we need to call to stay in / raise over

        fold_equity = _estimate_fold_equity(amount, pot_size)
        
        # 1. If opponent folds: we win the current pot_size
        ev_if_opponent_folds = fold_equity * pot_size
        
        # 2. If opponent calls our raise:
        # Opponent needs to add (amount - bet_to_call) to the pot.
        # Our investment for this specific action is 'amount'.
        # The pot, if opponent calls, will be: pot_size (current pot) + (amount - bet_to_call) (opponent's addition)
        # Ensure amount is greater than bet_to_call for a valid raise scenario leading to this calculation.
        # If amount <= bet_to_call, this branch implies a misunderstanding of 'raise' or game state.
        # However, standard EV calc for raise assumes amount > bet_to_call.
        opponent_chips_to_add = amount - bet_to_call
        if opponent_chips_to_add < 0: # Should not happen if 'amount' is a valid total raise amount
            opponent_chips_to_add = 0 # Or handle as an error/invalid state

        pot_if_opponent_calls = pot_size + opponent_chips_to_add
        
        # EV when opponent calls = (win_prob * total_pot_if_they_call) - our_investment
        ev_when_opponent_calls = (win_probability * pot_if_opponent_calls) - amount
        
        ev_if_opponent_does_not_fold = (1 - fold_equity) * ev_when_opponent_calls
        
        return ev_if_opponent_folds + ev_if_opponent_does_not_fold
        
    return 0.0

def should_bluff(pot_size, stack_size, game_stage, win_probability, bet_to_pot_ratio_for_bluff=0.5):
    """
    Enhanced bluffing logic considering multiple factors
    Returns True if conditions are favorable for bluffing

    Args:
        pot_size (float): Current size of the pot.
        stack_size (float): Our current stack size.
        game_stage (str): Current stage of the game ("Flop", "Turn", "River").
        win_probability (float): Our estimated probability of winning the hand if it goes to showdown.
        bet_to_pot_ratio_for_bluff (float, optional): The bet size relative to the pot we are considering for the bluff.
                                                    This helps estimate if the bluff is likely to succeed.
                                                    Defaults to 0.5 (half-pot bet).
    """
    # Ensure win_probability is a float for comparisons
    try:
        win_prob_float = float(win_probability)
    except (ValueError, TypeError):
        # If conversion fails, assume it's not a valid probability for bluffing (conservative)
        return False

    # Don't bluff if we have a decent hand
    if win_prob_float > 0.35:
        return False
    
    # Don't bluff if pot is too small (not worth the risk)
    # Or if stack is too small relative to pot (preserve chips, less fold equity)
    if pot_size < stack_size * 0.05 or stack_size < pot_size * 2:
        return False
          # River bluffs should be more selective and require low win probability
    if game_stage == "River":
        # Don't bluff on river when we can check behind with weak hands
        # This addresses test_river_missed_draw_check_behind scenario
        if win_prob_float < 0.20:  # Only consider bluffing with very weak hands
            # Bluff more if the bet is substantial enough to cause folds
            return bet_to_pot_ratio_for_bluff >= 0.8 and win_prob_float < 0.12
        return False
    
    # Turn bluffs - can be semi-bluffs with some draw equity, or pure bluffs
    elif game_stage == "Turn":
        # Semi-bluff with some draw equity
        if 0.15 < win_prob_float < 0.30 and bet_to_pot_ratio_for_bluff >= 0.5:
            return True
        # Pure bluff on Turn if conditions are right (e.g. scare cards, tight opponent - not modeled here)
        # For now, limit pure Turn bluffs to lower win_prob
        if win_prob_float < 0.15 and bet_to_pot_ratio_for_bluff >= 0.6:
            return True
        return False
    
    # Flop bluffs - more liberal, especially with draws or on certain board textures
    # (board texture not modeled here yet)
    else: # Flop
        if win_prob_float < 0.25 and bet_to_pot_ratio_for_bluff >= 0.4:
            return True
        return False

def should_bluff_old(fold_equity, pot_size, bet_size):
    """
    Original bluffing function - determine if bluffing is profitable
    A bluff is profitable if: fold_equity > bet_size / (pot_size + bet_size)
    """
    if pot_size + bet_size <= 0:
        return False
    
    required_fold_equity = bet_size / (pot_size + bet_size)
    return fold_equity > required_fold_equity
