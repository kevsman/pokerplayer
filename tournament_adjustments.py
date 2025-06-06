# tournament_adjustments.py
# Tournament-specific strategy adjustments for poker bot

import logging

logger = logging.getLogger(__name__)

def get_tournament_adjustment_factor(stack_size, big_blind, current_level):
    """
    Calculate adjustment factor based on tournament stage and stack depth.
    
    Args:
        stack_size: Current stack in chips
        big_blind: Current big blind size
        current_level: Tournament level (1 = early, 2 = middle, 3 = late)
    
    Returns:
        Dict with adjustment factors for various play aspects
    """
    stack_bb = stack_size / big_blind if big_blind > 0 else 50
    
    adjustments = {
        'preflop_tightness': 1.0,     # 1.0 = normal, >1.0 = tighter
        'postflop_aggression': 1.0,   # 1.0 = normal, >1.0 = more aggressive
        'bluff_frequency': 1.0,       # 1.0 = normal, >1.0 = more bluffs
        'value_bet_sizing': 1.0,      # 1.0 = normal, >1.0 = larger bets
        'call_tightness': 1.0         # 1.0 = normal, >1.0 = tighter calls
    }
    
    # Early tournament (level 1): Play tighter, build stack slowly
    if current_level == 1:
        adjustments['preflop_tightness'] = 1.2
        adjustments['bluff_frequency'] = 0.8
        adjustments['call_tightness'] = 1.1
        
    # Middle tournament (level 2): Balanced play, some pressure
    elif current_level == 2:
        if stack_bb < 20:  # Short stack
            adjustments['preflop_tightness'] = 0.8  # Looser to accumulate chips
            adjustments['postflop_aggression'] = 1.3
            adjustments['bluff_frequency'] = 1.2
        elif stack_bb > 50:  # Big stack
            adjustments['postflop_aggression'] = 1.2
            adjustments['bluff_frequency'] = 1.1
            
    # Late tournament (level 3): ICM pressure, bubble considerations
    elif current_level == 3:
        if stack_bb < 15:  # Very short stack - push/fold mode
            adjustments['preflop_tightness'] = 0.6
            adjustments['postflop_aggression'] = 1.5
            adjustments['call_tightness'] = 1.4  # Be very selective
        elif stack_bb > 40:  # Big stack - apply pressure
            adjustments['bluff_frequency'] = 1.3
            adjustments['value_bet_sizing'] = 1.1
        else:  # Medium stack - survival mode
            adjustments['preflop_tightness'] = 1.3
            adjustments['call_tightness'] = 1.3
            adjustments['bluff_frequency'] = 0.7
    
    logger.debug(f"Tournament adjustments for level {current_level}, stack {stack_bb:.1f}BB: {adjustments}")
    return adjustments

def adjust_preflop_range_for_tournament(base_action, hand_category, adjustments):
    """
    Adjust preflop decisions based on tournament factors.
    
    Args:
        base_action: Original action decision
        hand_category: Hand strength category
        adjustments: Tournament adjustment factors
    
    Returns:
        Adjusted action or original if no change needed
    """
    tightness_factor = adjustments['preflop_tightness']
    
    # If we're supposed to be tighter and have a marginal hand
    if tightness_factor > 1.1 and hand_category in ["Medium Pair", "Suited Playable", "Offsuit Broadway"]:
        if base_action == "call":
            logger.debug(f"Tournament adjustment: Folding {hand_category} due to tightness factor {tightness_factor}")
            return "fold"
        elif base_action == "raise":
            # Consider changing raise to call for marginal hands
            logger.debug(f"Tournament adjustment: Changing raise to call for {hand_category}")
            return "call"
    
    # If we're supposed to be looser and have a decent hand
    elif tightness_factor < 0.9 and hand_category in ["Suited Ace", "Suited King", "Medium Pair"]:
        if base_action == "fold":
            logger.debug(f"Tournament adjustment: Calling {hand_category} due to loose factor {tightness_factor}")
            return "call"
    
    return base_action

def adjust_bet_size_for_tournament(base_size, pot_size, adjustments):
    """
    Adjust bet sizing based on tournament factors.
    
    Args:
        base_size: Original bet size
        pot_size: Current pot size
        adjustments: Tournament adjustment factors
    
    Returns:
        Adjusted bet size
    """
    value_factor = adjustments['value_bet_sizing']
    aggression_factor = adjustments['postflop_aggression']
    
    # Combine factors for overall adjustment
    combined_factor = (value_factor + aggression_factor) / 2
    adjusted_size = base_size * combined_factor
    
    logger.debug(f"Tournament bet size adjustment: {base_size:.3f} -> {adjusted_size:.3f} (factor: {combined_factor:.2f})")
    return adjusted_size
