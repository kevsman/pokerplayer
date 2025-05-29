# bet_utils.py

def get_optimal_bet_size(hand_strength, pot_size, stack_size, game_stage, big_blind, bluff=False):
    """
    Calculate optimal bet size based on hand strength and situation
    Returns bet size
    """
    if pot_size <= 0:
        return min(big_blind * 2.5, stack_size)

    # Stack-to-pot ratio considerations
    spr = stack_size / pot_size if pot_size > 0 else float('inf')

    if bluff:
        if game_stage == "River":
            bet = pot_size * 0.75  # Larger river bluffs
        elif game_stage == "Turn":
            bet = pot_size * 0.65
        else:
            bet = pot_size * 0.5 
        bet = max(bet, big_blind) 
        return min(round(bet, 2), stack_size)
        
    # Value betting based on hand strength (now expects numerical hand rank)
    if isinstance(hand_strength, (int, float)) and hand_strength >= 7:  # Full house+
        if game_stage == "River":
            bet = pot_size * 0.85  # Large value bet on river
        else:
            bet = pot_size * 0.75
    elif isinstance(hand_strength, (int, float)) and hand_strength >= 4:  # Three of a kind+
        if game_stage == "River":
            bet = pot_size * 0.70
        else:
            bet = pot_size * 0.65
    elif isinstance(hand_strength, (int, float)) and hand_strength >= 2:  # Pair+
        if game_stage == "River":
            bet = pot_size * 0.55  # Medium value bet
        else:
            bet = pot_size * 0.50
    else:  # High card or weak hands
        bet = pot_size * 0.33
    
    # Adjust for stack depth
    if spr <= 2:  # Very short stack - be more aggressive
        bet *= 1.3
    elif spr <= 4:  # Short stack
        bet *= 1.1
    elif spr >= 15:  # Very deep - be more cautious with medium hands
        if isinstance(hand_strength, (int, float)) and hand_strength < 4:
            bet *= 0.8
    
    # Ensure minimum bet size
    min_bet = big_blind if game_stage != "Preflop" else big_blind * 2
    bet = max(bet, min_bet)
    
    return min(round(bet, 2), stack_size)
