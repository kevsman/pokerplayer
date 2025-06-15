\
# filepath: h:\\Programming\\pokerplayer\\postflop\\bet_sizing.py

def get_optimal_value_bet_size_percentage(pot_size, hand_strength, street, opponent_count):
    """
    AGGRESSIVE dynamic bet sizing for table dominance.
    Returns the percentage of pot to bet for maximum pressure.
    """
    base_sizing = {
        'flop': 0.80,   # 80% pot - very aggressive
        'turn': 0.85,   # 85% pot - maintain pressure  
        'river': 0.90   # 90% pot - max value extraction
    }
    
    size_multiplier = base_sizing.get(street, 0.80)
    
    # Adjust for hand strength - be aggressive across all strengths
    if hand_strength == 'very_strong':
        size_multiplier *= 1.25  # Massive bets with nuts
    elif hand_strength == 'strong':
        size_multiplier *= 1.15  # Large bets with strong hands
    elif hand_strength == 'medium':
        size_multiplier *= 1.05  # Still bet bigger with medium hands
    # Even weak hands bet standard aggressive size for control
    
    # Adjust for opponent count (still aggressive but slightly smaller multiway)
    if opponent_count > 1:
        size_multiplier *= max(0.75, 1.0 - (opponent_count - 1) * 0.15)  # Less reduction than before
    
    return min(size_multiplier, 1.5)  # Cap at 150% pot for overbet pressure

def get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff=False, aggression_factor=2.5):
    """
    Enhanced AGGRESSIVE bet sizing function for maximum table control.
    Integrates enhanced aggression for assertive play.
    """
    if pot_size <= 0:
        return min(big_blind_amount * 3.5 * aggression_factor, my_stack)
    
    if bluff:
        # Much more aggressive bluff sizing for table control
        if street == "river":
            bet = pot_size * (0.85 + 0.2 * aggression_factor)  # Massive river bluffs
        elif street == "turn":
            bet = pot_size * (0.75 + 0.2 * aggression_factor)  # Large turn bluffs
        else:
            bet = pot_size * (0.65 + 0.2 * aggression_factor)  # Aggressive flop bluffs
        bet = max(bet, big_blind_amount * 2.0) 
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
    
    # Get optimal percentage from dynamic function and enhance with aggression
    base_percentage = get_optimal_value_bet_size_percentage(pot_size, hand_strength, street, active_opponents_count)
    
    # Apply aggressive enhancement
    aggressive_percentage = base_percentage * (1.0 + (aggression_factor - 1.0) * 0.3)  # Scale up by 30% per aggression point
    
    # Extra boost for control
    if hand_strength == 'very_strong':
        aggressive_percentage *= 1.2  # Even bigger with strong hands
    elif hand_strength == 'medium':
        aggressive_percentage *= 1.15  # More aggressive with medium hands too
    
    # Calculate bet amount
    bet = pot_size * aggressive_percentage
    
    # Higher minimum bet size for pressure
    min_bet = big_blind_amount * 1.5 if street != "preflop" else big_blind_amount * 3.0
    bet = max(bet, min_bet)
    
    return min(round(bet, 2), my_stack)
