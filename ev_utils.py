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
        fold_equity = _estimate_fold_equity(amount, pot_size)
        ev_if_fold = fold_equity * pot_size
        opponent_call_amount = amount
        new_pot = pot_size + amount + opponent_call_amount
        ev_if_call = (1 - fold_equity) * ((win_probability * new_pot) - amount)
        return ev_if_fold + ev_if_call
        
    return 0.0

def should_bluff(fold_equity, pot_size, bet_size):
    """
    Determine if bluffing is profitable
    A bluff is profitable if: fold_equity > bet_size / (pot_size + bet_size)
    """
    if pot_size + bet_size <= 0:
        return False
    
    required_fold_equity = bet_size / (pot_size + bet_size)
    return fold_equity > required_fold_equity
