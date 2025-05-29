# bet_utils.py

def get_optimal_bet_size(hand_strength, pot_size, stack_size, game_stage, big_blind, bluff=False):
    """
    Calculate optimal bet size based on hand strength and situation
    Returns bet size
    """
    if pot_size <= 0:
        return min(big_blind * 2.5, stack_size)

    if bluff:
        bet = pot_size * 0.5 
        bet = max(bet, big_blind) 
        return min(round(bet,2), stack_size)
        
    if hand_strength >= 0.8:
        bet = pot_size * 0.70
    elif hand_strength >= 0.65:
        bet = pot_size * 0.60
    elif hand_strength >= 0.5:
        bet = pot_size * 0.50
    else:
        bet = pot_size * 0.33
    
    bet = max(bet, big_blind if game_stage != "Preflop" else big_blind * 2)
    return min(round(bet,2), stack_size)
