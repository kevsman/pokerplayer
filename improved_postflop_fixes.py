"""
Improved Postflop Fixes for Poker Bot

This module contains targeted fixes for the key issues identified in the poker bot's
postflop decision making:

1. Hand strength classification issues - especially with medium/strong hands
2. Excessive passivity with strong hands
3. Inconsistent SPR strategy application
4. Unreliable opponent modeling
5. Lack of strategic bluffing

Each fix is implemented as a separate function that can be integrated with the
improved_postflop_integrator.py module.
"""

import logging

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.FileHandler('improved_poker_bot_fixed.log', encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def fix_hand_strength_classification(numerical_hand_rank, win_probability, 
                                   original_classification, street='flop'):
    """
    Fixes the hand strength classification issues by using more accurate
    win probability thresholds and better interpretation of numerical ranks.
    
    Args:
        numerical_hand_rank: Integer hand rank
        win_probability: Decimal win probability (0.0-1.0)
        original_classification: String classification from existing system
        street: Current street ('flop', 'turn', 'river')
    
    Returns:
        tuple: (fixed_classification, commitment_threshold)
    """
    # Adjust thresholds based on street - we can be more certain on later streets
    street_multiplier = {
        'flop': 1.0,
        'turn': 0.9,  # We require 10% less certainty on the turn
        'river': 0.8  # We require 20% less certainty on the river
    }.get(street, 1.0)
    
    # Very strong hands: premium holdings with dominating equity
    if numerical_hand_rank >= 7 or win_probability >= 0.85:
        fixed_classification = 'very_strong'
        commitment_threshold = 15.0 * street_multiplier  # Lower threshold = more committed
    
    # Strong hands: strong made hands with good equity
    elif numerical_hand_rank >= 3 or win_probability >= 0.70:
        fixed_classification = 'strong'
        commitment_threshold = 25.0 * street_multiplier
    
    # Medium hands: decent showdown value
    elif (numerical_hand_rank == 2 and win_probability >= 0.55) or win_probability >= 0.65:
        fixed_classification = 'medium'
        commitment_threshold = 35.0 * street_multiplier
    
    # Weak made hands: marginal showdown value
    elif (numerical_hand_rank >= 1 and win_probability >= 0.30) or win_probability >= 0.40:
        fixed_classification = 'weak_made'
        commitment_threshold = 60.0 * street_multiplier
    
    # Drawing hands: significant potential to improve
    elif 0.25 <= win_probability <= 0.45 and numerical_hand_rank < 2:
        fixed_classification = 'drawing'
        commitment_threshold = 45.0 * street_multiplier
    
    # Very weak: low equity, minimal showdown value
    else:
        fixed_classification = 'very_weak'
        commitment_threshold = 85.0 * street_multiplier
    
    if fixed_classification != original_classification:
        logger.info(f"Fixed classification: {original_classification} → {fixed_classification} "
                    f"(rank={numerical_hand_rank}, win_prob={win_probability:.2%})")
    
    return fixed_classification, commitment_threshold

def fix_value_betting_strategy(hand_classification, win_probability, spr, can_check, pot_size, my_stack, position):
    """
    Fixes the excessive passivity by enhancing the bot's value betting strategy.
    Ensures the bot bets for value with strong hands even when it could check.
    
    Args:
        hand_classification: String classification of hand strength
        win_probability: Decimal win probability (0.0-1.0)
        spr: Stack-to-pot ratio
        can_check: Boolean indicating if checking is available
        pot_size: Current pot size
        my_stack: Player's remaining stack
        position: Player's position at the table
    
    Returns:
        dict: Strategy recommendation with bet_action, bet_size, and reasoning
    """
    # Default to conservative play
    strategy = {
        'bet_action': 'check',
        'bet_size': 0.0,
        'reasoning': 'Default conservative strategy'
    }
    
    # No need to decide about betting if we can't check
    if not can_check:
        return strategy
    
    # Position-based aggression factor (more aggressive in later positions)
    position_aggression = {
        'SB': 0.9,  # Less aggressive in small blind
        'BB': 0.95, # Slightly less aggressive in big blind
        'UTG': 0.85,
        'UTG+1': 0.9,
        'MP': 1.0,
        'MP+1': 1.05,
        'CO': 1.1,  # More aggressive in cutoff
        'BTN': 1.2  # Most aggressive on button
    }.get(position, 1.0)
    
    # Small SPR = more commitment with strong hands
    if spr <= 3:
        if hand_classification in ('very_strong', 'strong'):
            # With strong hands and small SPR, we want to get money in
            bet_size = min(pot_size * 0.8 * position_aggression, my_stack)
            strategy = {
                'bet_action': 'raise',
                'bet_size': bet_size,
                'reasoning': f'Strong hand ({win_probability:.1%} equity), small SPR ({spr:.1f}), betting for value'
            }
            logger.info(f"Value betting with {hand_classification} hand, small SPR {spr:.1f}, equity {win_probability:.1%}")
        
        elif hand_classification == 'medium' and win_probability >= 0.60:
            # Medium-strong hands should also bet with small SPR
            bet_size = min(pot_size * 0.6 * position_aggression, my_stack)
            strategy = {
                'bet_action': 'raise',
                'bet_size': bet_size,
                'reasoning': f'Medium hand with good equity ({win_probability:.1%}), small SPR ({spr:.1f}), betting for value'
            }
    
    # Medium SPR = balanced approach
    elif 3 < spr <= 7:
        if hand_classification in ('very_strong', 'strong'):
            # Value bet with strong hands
            bet_size = min(pot_size * 0.7 * position_aggression, my_stack)
            strategy = {
                'bet_action': 'raise',
                'bet_size': bet_size,
                'reasoning': f'Strong hand ({win_probability:.1%} equity), medium SPR ({spr:.1f}), betting for value'
            }
            logger.info(f"Value betting with {hand_classification} hand, medium SPR {spr:.1f}, equity {win_probability:.1%}")
        
        elif hand_classification == 'medium' and win_probability >= 0.65:
            # Only bet with stronger medium hands at medium SPR
            bet_size = min(pot_size * 0.5 * position_aggression, my_stack)
            strategy = {
                'bet_action': 'raise',
                'bet_size': bet_size,
                'reasoning': f'Medium+ hand ({win_probability:.1%}), medium SPR ({spr:.1f}), betting for thin value'
            }
    
    # Large SPR = selective value betting
    else:  # spr > 7
        if hand_classification == 'very_strong':
            # Value bet with very strong hands
            bet_size = min(pot_size * 0.6 * position_aggression, my_stack)
            strategy = {
                'bet_action': 'raise',
                'bet_size': bet_size,
                'reasoning': f'Very strong hand ({win_probability:.1%} equity), large SPR ({spr:.1f}), betting for value'
            }
            logger.info(f"Value betting with {hand_classification} hand, large SPR {spr:.1f}, equity {win_probability:.1%}")
        
        elif hand_classification == 'strong' and win_probability >= 0.75:
            # Only bet with stronger hands at large SPR
            bet_size = min(pot_size * 0.5 * position_aggression, my_stack)
            strategy = {
                'bet_action': 'raise',
                'bet_size': bet_size,
                'reasoning': f'Strong hand ({win_probability:.1%}), large SPR ({spr:.1f}), betting for value'
            }
    
    return strategy

def fix_bluffing_strategy(hand_classification, win_probability, fold_equity, 
                        spr, can_check, position, street, pot_size, my_stack):
    """
    Improves the bot's bluffing strategy to identify good bluffing spots.
    
    Args:
        hand_classification: String classification of hand strength
        win_probability: Decimal win probability (0.0-1.0)
        fold_equity: Estimated probability opponents will fold
        spr: Stack-to-pot ratio
        can_check: Boolean indicating if checking is available
        position: Player's position at the table
        street: Current street ('flop', 'turn', 'river')
        pot_size: Current pot size
        my_stack: Player's remaining stack
    
    Returns:
        dict: Bluffing strategy recommendation
    """
    # Default to no bluffing
    strategy = {
        'should_bluff': False,
        'bet_size': 0.0,
        'reasoning': 'Not a good bluffing spot'
    }
    
    # Can't bluff if we can't bet
    if not can_check:
        return strategy
    
    # Position-based bluffing factor (more bluffing in later positions)
    position_bluff_factor = {
        'SB': 0.7,   # Bad position for bluffing
        'BB': 0.8,
        'UTG': 0.6,  # Worst position for bluffing  
        'UTG+1': 0.7,
        'MP': 0.9,
        'MP+1': 1.0,
        'CO': 1.1,   # Good position for bluffing
        'BTN': 1.2   # Best position for bluffing
    }.get(position, 1.0)
    
    # Street-based bluffing factor
    street_bluff_factor = {
        'flop': 1.0,  # Base bluffing on flop
        'turn': 0.8,  # Less bluffing on turn
        'river': 0.6  # Even less bluffing on river
    }.get(street, 1.0)
    
    # Calculate bluffing score based on multiple factors
    bluffing_score = ((fold_equity / 100) * position_bluff_factor * street_bluff_factor)
    
    # Additional criteria for each street
    if street == 'flop':
        # On the flop, bluff more with drawing hands in good positions
        if hand_classification == 'drawing' and position in ['BTN', 'CO'] and fold_equity >= 40:
            bluffing_score *= 1.3
            logger.info(f"Considering flop bluff with drawing hand in position {position}, fold equity {fold_equity}%")
    
    elif street == 'turn':
        # On the turn, bluff more selectively
        if hand_classification == 'drawing' and win_probability >= 0.30 and fold_equity >= 50:
            bluffing_score *= 1.2
            logger.info(f"Considering turn bluff with {win_probability:.1%} equity, fold equity {fold_equity}%")
    
    elif street == 'river':
        # On the river, only bluff with very specific criteria
        if hand_classification in ['very_weak', 'weak_made'] and fold_equity >= 60:
            bluffing_score *= 1.1
            logger.info(f"Considering river bluff with weak hand, fold equity {fold_equity}%")
    
    # Make bluffing decision based on score
    if bluffing_score >= 0.5:  # Threshold for bluffing
        bet_size = min(pot_size * 0.6, my_stack * 0.3)  # Sensible bluff size
        strategy = {
            'should_bluff': True,
            'bet_size': bet_size,
            'reasoning': f'Good bluffing spot: {hand_classification} hand, {fold_equity}% fold equity, {position} position'
        }
        logger.info(f"Bluffing with {hand_classification} hand, score {bluffing_score:.2f}, bet ${bet_size:.2f}")
    
    return strategy

def fix_opponent_modeling(opponent_data=None, table_type='unknown', active_players=1):
    """
    Provides a more consistent and reliable opponent model when data is limited.
    
    Args:
        opponent_data: Dictionary with opponent tracker data, if available
        table_type: String describing table type ('tight', 'loose', etc.)
        active_players: Number of active players in the hand
    
    Returns:
        dict: Enhanced opponent model
    """
    # Default values based on table type
    default_models = {
        'tight': {'avg_vpip': 20.0, 'fold_equity': 65.0, 'aggression_factor': 1.2},
        'loose': {'avg_vpip': 35.0, 'fold_equity': 40.0, 'aggression_factor': 0.8},
        'passive': {'avg_vpip': 25.0, 'fold_equity': 55.0, 'aggression_factor': 0.7},
        'aggressive': {'avg_vpip': 30.0, 'fold_equity': 35.0, 'aggression_factor': 1.4},
        'unknown': {'avg_vpip': 25.0, 'fold_equity': 50.0, 'aggression_factor': 1.0}
    }
    
    # Start with default model based on table type
    model = default_models.get(table_type.lower(), default_models['unknown'])
    
    # Adjust fold equity based on number of active players
    if active_players > 1:
        # Fold equity decreases with more players
        model['fold_equity'] = max(model['fold_equity'] - (5 * (active_players - 1)), 20.0)
    
    # Incorporate opponent data if available
    if opponent_data and isinstance(opponent_data, dict):
        # Look for relevant stats in opponent data
        if 'avg_vpip' in opponent_data and opponent_data['avg_vpip'] is not None:
            model['avg_vpip'] = opponent_data['avg_vpip']
        
        if 'fold_equity' in opponent_data and opponent_data['fold_equity'] is not None:
            model['fold_equity'] = opponent_data['fold_equity']
        
        if 'aggression_factor' in opponent_data and opponent_data['aggression_factor'] is not None:
            model['aggression_factor'] = opponent_data['aggression_factor']
        
        # Calculate tracked player count
        model['tracked_players'] = opponent_data.get('tracked_players', 0)
    else:
        model['tracked_players'] = 0
    
    logger.info(f"Fixed opponent model: table_type={table_type}, "
               f"avg_vpip={model['avg_vpip']:.1f}%, fold_equity={model['fold_equity']:.1f}%")
    
    return model

def fix_spr_strategy_alignment(spr, hand_classification, win_probability, pot_size):
    """
    Provides consistent SPR-based strategy recommendations aligned with hand strength.
    
    Args:
        spr: Stack-to-pot ratio
        hand_classification: String classification of hand strength
        win_probability: Decimal win probability (0.0-1.0)
        pot_size: Current pot size
    
    Returns:
        dict: SPR strategy recommendation
    """
    # Determine SPR category
    if spr < 1:
        spr_category = 'very_low'
    elif 1 <= spr < 3:
        spr_category = 'low'
    elif 3 <= spr < 6:
        spr_category = 'medium'
    elif 6 <= spr < 10:
        spr_category = 'high'
    else:
        spr_category = 'very_high'
    
    # Base strategies by SPR category and hand strength
    strategies = {
        'very_low': {
            'very_strong': {'base_strategy': 'get_it_all_in', 'sizing_adjustment': 1.0, 
                           'betting_action': 'raise', 'reasoning': 'Very low SPR - commit with very strong'},
            'strong': {'base_strategy': 'get_it_all_in', 'sizing_adjustment': 1.0, 
                      'betting_action': 'raise', 'reasoning': 'Very low SPR - commit with strong'},
            'medium': {'base_strategy': 'value_bet_call_raises', 'sizing_adjustment': 0.9, 
                      'betting_action': 'raise', 'reasoning': 'Very low SPR - value bet with medium'},
            'weak_made': {'base_strategy': 'call_small_bets', 'sizing_adjustment': 0.8, 
                         'betting_action': 'check', 'reasoning': 'Very low SPR - must commit or fold with weak_made'},
            'drawing': {'base_strategy': 'implied_odds_only', 'sizing_adjustment': 0.7, 
                       'betting_action': 'check', 'reasoning': 'Very low SPR - draws need direct odds'},
            'very_weak': {'base_strategy': 'check_fold', 'sizing_adjustment': 0.6, 
                         'betting_action': 'check', 'reasoning': 'Very low SPR - avoid committing with very weak'}
        },
        'low': {
            'very_strong': {'base_strategy': 'get_it_all_in', 'sizing_adjustment': 1.0, 
                           'betting_action': 'raise', 'reasoning': 'Low SPR - commit with very strong'},
            'strong': {'base_strategy': 'value_bet_call_raises', 'sizing_adjustment': 1.0, 
                      'betting_action': 'raise', 'reasoning': 'Low SPR - value bet with strong'},
            'medium': {'base_strategy': 'value_bet_call_raises', 'sizing_adjustment': 0.9, 
                      'betting_action': 'raise', 'reasoning': 'Low SPR - value bet with medium'},
            'weak_made': {'base_strategy': 'check_call_small_bets', 'sizing_adjustment': 0.8, 
                         'betting_action': 'check', 'reasoning': 'Low SPR - pot control with weak_made'},
            'drawing': {'base_strategy': 'semi_bluff_or_call', 'sizing_adjustment': 0.8, 
                       'betting_action': 'check', 'reasoning': 'Low SPR - semi-bluff with good draws'},
            'very_weak': {'base_strategy': 'check_fold', 'sizing_adjustment': 0.7, 
                         'betting_action': 'check', 'reasoning': 'Low SPR - avoid committing with very weak'}
        },
        'medium': {
            'very_strong': {'base_strategy': 'bet_for_value', 'sizing_adjustment': 1.0, 
                           'betting_action': 'raise', 'reasoning': 'Medium SPR - bet for value with very strong'},
            'strong': {'base_strategy': 'bet_for_value', 'sizing_adjustment': 0.9, 
                      'betting_action': 'raise', 'reasoning': 'Medium SPR - bet for value with strong'},
            'medium': {'base_strategy': 'thin_value_bet', 'sizing_adjustment': 0.8, 
                      'betting_action': 'raise', 'reasoning': 'Medium SPR - thin value bet with medium'},
            'weak_made': {'base_strategy': 'check_call_or_small_bet', 'sizing_adjustment': 0.7, 
                         'betting_action': 'check', 'reasoning': 'Medium SPR - standard play with weak_made'},
            'drawing': {'base_strategy': 'semi_bluff_medium', 'sizing_adjustment': 0.7, 
                       'betting_action': 'check', 'reasoning': 'Medium SPR - semi-bluff with good draws'},
            'very_weak': {'base_strategy': 'semi_bluff_aggressively', 'sizing_adjustment': 0.6, 
                         'betting_action': 'check', 'reasoning': 'Medium SPR - standard play with weak'}
        },
        'high': {
            'very_strong': {'base_strategy': 'bet_for_value', 'sizing_adjustment': 0.9, 
                           'betting_action': 'raise', 'reasoning': 'High SPR - bet for value with very strong'},
            'strong': {'base_strategy': 'bet_for_value', 'sizing_adjustment': 0.8, 
                      'betting_action': 'raise', 'reasoning': 'High SPR - bet for value with strong'},
            'medium': {'base_strategy': 'pot_control', 'sizing_adjustment': 0.7, 
                      'betting_action': 'check', 'reasoning': 'High SPR - pot control with medium'},
            'weak_made': {'base_strategy': 'pot_control', 'sizing_adjustment': 0.6, 
                         'betting_action': 'check', 'reasoning': 'High SPR - pot control focus with weak_made'},
            'drawing': {'base_strategy': 'semi_bluff_with_equity', 'sizing_adjustment': 0.7, 
                       'betting_action': 'raise', 'reasoning': 'High SPR - good for draws and semi-bluffs'},
            'very_weak': {'base_strategy': 'bluff_with_equity', 'sizing_adjustment': 0.6, 
                         'betting_action': 'check', 'reasoning': 'High SPR - pot control focus with weak'}
        },
        'very_high': {
            'very_strong': {'base_strategy': 'build_pot_gradually', 'sizing_adjustment': 0.85, 
                           'betting_action': 'raise', 'reasoning': 'Very high SPR - build pot with very strong'},
            'strong': {'base_strategy': 'build_pot_gradually', 'sizing_adjustment': 0.8, 
                      'betting_action': 'raise', 'reasoning': 'Very high SPR - build pot with strong'},
            'medium': {'base_strategy': 'pot_control', 'sizing_adjustment': 0.75, 
                      'betting_action': 'check', 'reasoning': 'Very high SPR - pot control with medium'},
            'weak_made': {'base_strategy': 'pot_control', 'sizing_adjustment': 0.7, 
                         'betting_action': 'check', 'reasoning': 'Very high SPR - extreme pot control with weak_made'},
            'drawing': {'base_strategy': 'semi_bluff_selectively', 'sizing_adjustment': 0.75, 
                       'betting_action': 'check', 'reasoning': 'Very high SPR - selective semi-bluff with draws'},
            'very_weak': {'base_strategy': 'bluff_selectively', 'sizing_adjustment': 0.7, 
                         'betting_action': 'check', 'reasoning': 'Very high SPR - selective bluffing'}
        }
    }
    
    # Get the base strategy for this SPR category and hand strength
    strategy = strategies.get(spr_category, {}).get(hand_classification, 
              {'base_strategy': 'check_fold', 'sizing_adjustment': 0.5, 
               'betting_action': 'check', 'reasoning': 'Default conservative strategy'})
    
    # Add SPR context to the strategy
    strategy['spr'] = spr
    strategy['spr_category'] = spr_category
    
    # Override betting action based on win probability in certain cases
    if hand_classification in ['strong', 'very_strong'] and win_probability >= 0.7:
        strategy['betting_action'] = 'raise'
    
    logger.debug(f"SPR strategy: {strategy['base_strategy']} (SPR={spr:.1f}, {spr_category})")
    
    return strategy

def integrate_all_fixes(postflop_decision_logic_module):
    """
    Main function to integrate all fixes into the postflop decision logic.
    Uses monkey patching to enhance the existing functionality.
    
    Args:
        postflop_decision_logic_module: The module to enhance
    """
    import inspect
    from functools import wraps
    
    # Store original functions
    original_functions = {}
    
    # Backup original classify_hand_strength
    if hasattr(postflop_decision_logic_module, 'classify_hand_strength'):
        original_functions['classify_hand_strength'] = postflop_decision_logic_module.classify_hand_strength
    
    # Monkey patch the hand classification function
    def enhanced_classify_hand_strength(*args, **kwargs):
        """Enhanced hand classification with fixes"""
        original_result = original_functions['classify_hand_strength'](*args, **kwargs)
        
        # Extract parameters from the original call
        params = inspect.getcallargs(original_functions['classify_hand_strength'], *args, **kwargs)
        numerical_hand_rank = params.get('numerical_hand_rank', 1)
        win_probability = params.get('win_probability', 0.0)
        
        # Apply our fix
        fixed_classification, _ = fix_hand_strength_classification(
            numerical_hand_rank, win_probability, original_result)
        
        return fixed_classification
    
    # Apply the monkey patch
    if hasattr(postflop_decision_logic_module, 'classify_hand_strength'):
        postflop_decision_logic_module.classify_hand_strength = enhanced_classify_hand_strength
        logger.info("Enhanced hand classification function integrated")
    
    # Add the new functions to the module
    postflop_decision_logic_module.fix_value_betting_strategy = fix_value_betting_strategy
    postflop_decision_logic_module.fix_bluffing_strategy = fix_bluffing_strategy
    postflop_decision_logic_module.fix_opponent_modeling = fix_opponent_modeling
    postflop_decision_logic_module.fix_spr_strategy_alignment = fix_spr_strategy_alignment
    
    logger.info("All fixes integrated into postflop_decision_logic module")
    
    return True
