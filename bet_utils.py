# bet_utils.py

def get_optimal_bet_size(hand_strength, pot_size, stack_size, game_stage, big_blind, bluff=False, aggression_factor=1.0):
    """
    Calculate optimal bet size based on hand strength and situation
    Returns bet size with MAXIMUM AGGRESSION for complete table control
    """
    if pot_size <= 0:
        return min(big_blind * 4.0 * aggression_factor, stack_size)

    # Stack-to-pot ratio considerations
    spr = stack_size / pot_size if pot_size > 0 else float('inf')

    if bluff:
        # MAXIMUM aggressive bluff sizing for complete table domination
        if game_stage == "River":
            bet = pot_size * (1.2 + 0.3 * aggression_factor)  # Massive river bluffs
        elif game_stage == "Turn":
            bet = pot_size * (1.0 + 0.25 * aggression_factor)  # Huge turn bluffs
        else:
            bet = pot_size * (0.9 + 0.2 * aggression_factor)  # Large flop bluffs
        bet = max(bet, big_blind * 2.0) 
        return min(round(bet, 2), stack_size)
        
    # Value betting with EXTREME sizing for maximum pressure and control
    if isinstance(hand_strength, (int, float)) and hand_strength >= 7:  # Full house+
        if game_stage == "River":
            bet = pot_size * (1.3 + 0.2 * aggression_factor)  # Massive value bets
        else:
            bet = pot_size * (1.15 + 0.15 * aggression_factor)
    elif isinstance(hand_strength, (int, float)) and hand_strength >= 4:  # Three of a kind+
        if game_stage == "River":
            bet = pot_size * (1.1 + 0.15 * aggression_factor)
        else:
            bet = pot_size * (1.0 + 0.15 * aggression_factor)
    elif isinstance(hand_strength, (int, float)) and hand_strength >= 2:  # Pair+
        if game_stage == "River":
            bet = pot_size * (0.9 + 0.15 * aggression_factor)  # Large medium value bets
        else:
            bet = pot_size * (0.85 + 0.15 * aggression_factor)
    else:  # High card or weak hands - bet them very aggressively for control
        bet = pot_size * (0.75 + 0.15 * aggression_factor)  # Extremely aggressive with weak hands
    
    # Adjust for stack depth - be maximally aggressive across all stack depths
    if spr <= 2:  # Very short stack - all-in aggression
        bet *= (2.0 + 0.3 * aggression_factor)
    elif spr <= 4:  # Short stack
        bet *= (1.6 + 0.2 * aggression_factor)
    elif spr >= 15:  # Very deep - still be maximally aggressive
        if isinstance(hand_strength, (int, float)) and hand_strength < 4:
            bet *= (1.2 + 0.15 * aggression_factor)
    
    # Much higher minimum bet size for extreme pressure
    min_bet = big_blind * 2.5 if game_stage != "Preflop" else big_blind * 3.5
    bet = max(bet, min_bet)
    
    return min(round(bet, 2), stack_size)
