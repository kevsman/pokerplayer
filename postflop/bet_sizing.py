\
# filepath: h:\\Programming\\pokerplayer\\postflop\\bet_sizing.py

def get_optimal_value_bet_size_percentage(pot_size, hand_strength, street, opponent_count):
    """
    Dynamic bet sizing based on multiple factors.
    Returns the percentage of pot to bet for value.
    """
    base_sizing = {
        'flop': 0.7,   # 70% pot
        'turn': 0.75,  # 75% pot  
        'river': 0.8   # 80% pot
    }
    
    size_multiplier = base_sizing.get(street, 0.7)
    
    # Adjust for hand strength
    if hand_strength == 'very_strong':
        size_multiplier *= 1.1  # Bet bigger with very strong hands
    elif hand_strength == 'medium':
        size_multiplier *= 0.8  # Bet smaller with medium hands
    
    # Adjust for opponent count (multiway = smaller bets)
    if opponent_count > 1:
        size_multiplier *= max(0.6, 1.0 - (opponent_count - 1) * 0.2)
    
    return size_multiplier

def get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff=False):
    """
    Enhanced bet sizing function that uses dynamic percentage-based sizing.
    Integrates the new get_optimal_value_bet_size_percentage function.
    """
    if pot_size <= 0:
        return min(big_blind_amount * 2.5, my_stack)
    
    if bluff:
        # For bluffs, use simpler sizing
        if street == "river":
            bet = pot_size * 0.75  # Larger river bluffs
        elif street == "turn":
            bet = pot_size * 0.65
        else:
            bet = pot_size * 0.5 
        bet = max(bet, big_blind_amount) 
        return min(round(bet, 2), my_stack)
    
    # Determine hand strength category for dynamic sizing
    hand_strength = 'medium'  # default
    if numerical_hand_rank >= 7:  # Full house+
        hand_strength = 'very_strong'
    elif numerical_hand_rank >= 4:  # Three of a kind+
        hand_strength = 'very_strong'
    elif numerical_hand_rank >= 2:  # Pair+
        hand_strength = 'medium'
    # else remains 'medium' for draws/high card
    
    # Get optimal percentage from dynamic function
    bet_percentage = get_optimal_value_bet_size_percentage(pot_size, hand_strength, street, active_opponents_count)
    
    # Calculate bet amount
    bet = pot_size * bet_percentage
    
    # Ensure minimum bet size
    min_bet = big_blind_amount if street != "preflop" else big_blind_amount * 2
    bet = max(bet, min_bet)
    
    return min(round(bet, 2), my_stack)
