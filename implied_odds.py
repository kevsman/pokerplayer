# Implied Odds Calculator for Poker Bot

import logging

logger = logging.getLogger(__name__)

def calculate_implied_odds(outs, pot_size, bet_to_call, opponent_stack, my_stack, street):
    """
    Calculate implied odds for drawing hands.
    
    Args:
        outs (int): Number of outs to improve
        pot_size (float): Current pot size
        bet_to_call (float): Amount needed to call
        opponent_stack (float): Opponent's remaining stack
        my_stack (float): Our remaining stack
        street (str): Current street ('flop', 'turn', 'river')
    
    Returns:
        dict: Contains implied odds analysis
    """
    if street == 'river':
        return {
            'implied_odds_ratio': 0,
            'should_call': False,
            'reason': 'No implied odds on river'
        }
    
    # Calculate direct pot odds
    total_investment = pot_size + bet_to_call
    direct_odds = bet_to_call / total_investment if total_investment > 0 else 0
    
    # Calculate card odds (probability of hitting)
    cards_remaining = 47 if street == 'flop' else 46  # Flop: 52-2-3=47, Turn: 52-2-4=46
    cards_to_come = 2 if street == 'flop' else 1
    
    if cards_to_come == 2:  # Flop to river
        hit_probability = 1 - ((cards_remaining - outs) / cards_remaining) * ((cards_remaining - outs - 1) / (cards_remaining - 1))
    else:  # Turn to river
        hit_probability = outs / cards_remaining
    
    # Estimate potential future winnings (implied odds)
    # Conservative estimate: we can win 50-70% of opponent's remaining stack when we hit
    potential_winnings_multiplier = 0.6  # Conservative estimate
    max_additional_winnings = min(opponent_stack, my_stack) * potential_winnings_multiplier
    
    # Calculate implied pot odds
    implied_pot_size = pot_size + max_additional_winnings
    implied_total_investment = implied_pot_size + bet_to_call
    implied_odds = bet_to_call / implied_total_investment if implied_total_investment > 0 else 0
    
    # Decision based on implied odds vs card odds
    required_odds = 1 - hit_probability  # What we need to be profitable
    should_call_direct = direct_odds <= required_odds
    should_call_implied = implied_odds <= required_odds
    
    return {
        'outs': outs,
        'hit_probability': hit_probability,
        'direct_odds': direct_odds,
        'implied_odds': implied_odds,
        'required_odds': required_odds,
        'should_call_direct': should_call_direct,
        'should_call_implied': should_call_implied,
        'potential_winnings': max_additional_winnings,
        'recommendation': 'CALL' if should_call_implied else 'FOLD'
    }

def estimate_drawing_outs(hand, community_cards, win_probability):
    """
    Estimate the number of outs based on hand strength and win probability.
    This is a simplified estimation - a more sophisticated version would 
    analyze actual card combinations.
    
    Args:
        hand (list): Player's hole cards
        community_cards (list): Community cards
        win_probability (float): Current win probability
    
    Returns:
        int: Estimated number of outs
    """
    # Simple heuristic based on win probability ranges
    if win_probability > 0.7:
        return 0  # Already strong, no draws needed
    elif win_probability > 0.5:
        return 2  # Weak draws or overcards
    elif win_probability > 0.35:
        return 4  # Gutshot straight draw or weak flush draw
    elif win_probability > 0.25:
        return 8  # Open-ended straight or flush draw
    elif win_probability > 0.15:
        return 12  # Strong combo draws
    else:
        return 0  # Too weak to continue
    
def should_call_with_draws(hand, community_cards, win_probability, pot_size, 
                          bet_to_call, opponent_stack, my_stack, street):
    """
    Determine if we should call with a drawing hand based on implied odds.
    
    Returns:
        dict: Decision analysis including recommendation
    """
    if street == 'river':
        return {
            'should_call': False,
            'reason': 'No draws on river'
        }
    
    # Estimate outs
    outs = estimate_drawing_outs(hand, community_cards, win_probability)
    
    if outs == 0:
        return {
            'should_call': False,
            'reason': 'No significant draws available'
        }
    
    # Calculate implied odds
    analysis = calculate_implied_odds(outs, pot_size, bet_to_call, 
                                    opponent_stack, my_stack, street)
    
    logger.debug(f"Draw analysis: {outs} outs, win_prob: {win_probability:.2%}, "
                f"recommendation: {analysis['recommendation']}")
    
    return {
        'should_call': analysis['recommendation'] == 'CALL',
        'outs': outs,
        'implied_odds_analysis': analysis,
        'reason': f"Implied odds analysis with {outs} outs"
    }
