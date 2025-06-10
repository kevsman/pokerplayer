# enhanced_postflop_improvements.py
"""
Enhanced postflop decision logic improvements based on analysis of debug logs.
This module contains the improved functions to replace parts of the existing postflop logic.
"""

import logging

logger = logging.getLogger(__name__)

def classify_hand_strength_enhanced(numerical_hand_rank, win_probability, board_texture=None, position=None, hand_description=""):
    """
    Enhanced hand strength classification that addresses the issues identified in the analysis.
    
    Args:
        numerical_hand_rank: Integer ranking of hand strength
        win_probability: Decimal probability of winning (0.0-1.0)
        board_texture: Dictionary with board texture analysis (optional)
        position: Player position (optional)
        hand_description: Text description of hand (for debugging)
    
    Returns:
        String classification: 'very_strong', 'strong', 'medium', 'weak_made', 'very_weak', 'drawing'
    """
    
    logger.debug(f"Classifying hand: rank={numerical_hand_rank}, win_prob={win_probability:.2%}, desc='{hand_description}'")
    
    # Very strong hands - nuts or near nuts
    if numerical_hand_rank >= 7 or win_probability >= 0.85:
        logger.debug("Classified as very_strong")
        return 'very_strong'
    
    # Strong hands - two pair or better, or very high equity
    if numerical_hand_rank >= 4 or win_probability >= 0.75:
        logger.debug("Classified as strong") 
        return 'strong'
    
    # Enhanced one-pair classification with more granular boundaries
    if numerical_hand_rank == 2:  # One pair
        # Analyze the hand description for more context
        hand_desc_lower = hand_description.lower()
        
        # Very strong one pair (top pair good kicker, overpair vs tight range)
        if win_probability >= 0.70:
            logger.debug("Classified one pair as strong (high equity)")
            return 'strong'
          # Strong-medium one pair (top pair decent kicker) 
        elif win_probability >= 0.60:
            # Default to medium for 60%+ equity unless specifically indicated as weak
            if any(phrase in hand_desc_lower for phrase in ['bottom pair', 'weak', 'dominated', 'bad kicker']):
                logger.debug("Classified one pair as weak_made (weak indicators)")
                return 'weak_made'
            else:
                logger.debug("Classified one pair as medium (60%+ equity)")
                return 'medium'
        
        # Medium one pair (decent middle pair, weak top pair)
        elif win_probability >= 0.45:
            # Check for signs of decent pair vs weak kicker scenarios
            if any(phrase in hand_desc_lower for phrase in ['middle pair', 'second pair', 'top pair']):
                logger.debug("Classified one pair as medium (marginal)")
                return 'medium'
            else:
                logger.debug("Classified one pair as weak_made (low-medium equity)")
                return 'weak_made'
        
        # Weak made hands (bottom pair, weak middle pair, dominated pairs)
        elif win_probability >= 0.30:
            logger.debug("Classified one pair as weak_made (dominated or weak)")
            return 'weak_made'
        
        # Very weak pairs (dominated, facing aggression)
        else:
            logger.debug("Classified one pair as very_weak (heavily dominated)")
            return 'very_weak'
    
    # Enhanced three-of-a-kind and two-pair classification  
    elif numerical_hand_rank == 3:  # Two pair
        if win_probability >= 0.80:
            return 'strong'
        elif win_probability >= 0.65:
            return 'medium'
        else:
            return 'weak_made'
    
    # Drawing hands - typically 25-45% equity
    if 0.25 <= win_probability <= 0.45 and numerical_hand_rank < 2:
        # Enhanced drawing hand detection with board context
        if board_texture:
            if board_texture.get('draw_heavy', False):
                logger.debug("Classified as drawing hand (on draw-heavy board)")
                return 'drawing'
        
        # Position-based drawing hand adjustments
        if position in ['BTN', 'CO']:
            logger.debug("Classified as drawing hand (good position)")
            return 'drawing'
        
        logger.debug("Classified as drawing hand")
        return 'drawing'
    
    # Medium hands - decent but not great (high cards, weak pairs)
    if numerical_hand_rank >= 1 and win_probability >= 0.50:
        logger.debug("Classified as medium")
        return 'medium'
    
    # Weak made hands (any pair, ace high vs tight ranges)
    if win_probability >= 0.25:
        logger.debug("Classified as weak_made")
        return 'weak_made'
    
    # Very weak hands
    logger.debug("Classified as very_weak")
    return 'very_weak'


def get_multiway_betting_adjustment(hand_strength, active_opponents_count, win_probability):
    """
    Get betting adjustments for multiway pots (addresses issue #2 from analysis).
    
    Args:
        hand_strength: String classification from classify_hand_strength_enhanced
        active_opponents_count: Number of active opponents
        win_probability: Decimal probability of winning
    
    Returns:
        dict: Contains 'should_bet', 'size_multiplier', 'reasoning'
    """
    
    if active_opponents_count <= 1:
        return {
            'should_bet': True,
            'size_multiplier': 1.0,
            'reasoning': 'heads_up_no_adjustment'
        }
      # Conservative multiway adjustments
    if active_opponents_count >= 4:
        # 4+ opponents - be very conservative
        if hand_strength in ['very_weak', 'weak_made', 'drawing']:
            return {
                'should_bet': False,
                'size_multiplier': 0.0,
                'reasoning': f'fold_weak_vs_{active_opponents_count}_opponents'
            }
        elif hand_strength == 'medium':
            # Medium hands should not bet vs 4+ opponents regardless of equity
            return {
                'should_bet': False,
                'size_multiplier': 0.0,
                'reasoning': f'check_medium_vs_{active_opponents_count}_opponents'
            }
        elif hand_strength == 'strong':
            return {
                'should_bet': True,
                'size_multiplier': 0.7,
                'reasoning': f'value_bet_strong_vs_{active_opponents_count}_reduced_size'
            }
        else:  # very_strong
            return {
                'should_bet': True,
                'size_multiplier': 0.8,
                'reasoning': f'value_bet_very_strong_vs_{active_opponents_count}'
            }
    
    elif active_opponents_count == 3:
        # 3 opponents - moderately conservative
        if hand_strength in ['very_weak', 'weak_made']:
            return {
                'should_bet': False,
                'size_multiplier': 0.0,
                'reasoning': 'check_weak_vs_3_opponents'
            }
        elif hand_strength == 'medium':
            return {
                'should_bet': win_probability >= 0.60,
                'size_multiplier': 0.6,
                'reasoning': 'conditional_medium_vs_3_opponents'
            }
        else:  # strong or very_strong
            return {
                'should_bet': True,
                'size_multiplier': 0.8,
                'reasoning': 'value_bet_vs_3_opponents'
            }
    
    else:  # 2 opponents
        # 2 opponents - slightly conservative
        if hand_strength == 'very_weak':
            return {
                'should_bet': False,
                'size_multiplier': 0.0,
                'reasoning': 'check_very_weak_vs_2_opponents'
            }
        elif hand_strength in ['weak_made', 'drawing']:
            return {
                'should_bet': False,
                'size_multiplier': 0.0,
                'reasoning': 'check_weak_vs_2_opponents'
            }
        elif hand_strength == 'medium':
            return {
                'should_bet': win_probability >= 0.55,
                'size_multiplier': 0.8,
                'reasoning': 'conditional_medium_vs_2_opponents'
            }
        else:  # strong or very_strong
            return {
                'should_bet': True,
                'size_multiplier': 0.9,
                'reasoning': 'value_bet_vs_2_opponents'
            }


def get_consistent_bet_sizing(hand_strength, pot_size, street, spr, board_texture=None):
    """
    Get consistent bet sizing based on hand strength and situation (addresses issue #3).
    
    Args:
        hand_strength: String classification
        pot_size: Current pot size
        street: 'flop', 'turn', 'river'
        spr: Stack-to-pot ratio
        board_texture: Optional board texture analysis
    
    Returns:
        float: Bet size as fraction of pot
    """
    
    # Base bet sizes by hand strength
    base_sizes = {
        'very_strong': 0.75,  # 75% pot
        'strong': 0.65,       # 65% pot 
        'medium': 0.50,       # 50% pot
        'weak_made': 0.30,    # 30% pot (defensive)
        'very_weak': 0.0,     # Don't bet
        'drawing': 0.0        # Don't bet (unless bluffing)
    }
    
    base_size = base_sizes.get(hand_strength, 0.5)
    
    # Street adjustments
    street_multipliers = {
        'flop': 1.0,
        'turn': 1.1,   # Slightly larger on turn
        'river': 1.2   # Larger on river for value/polarization
    }
    
    street_mult = street_multipliers.get(street, 1.0)
    base_size *= street_mult
    
    # SPR adjustments
    if spr < 2:
        # Low SPR - bet larger to get it in
        base_size *= 1.3
    elif spr > 8:
        # High SPR - bet smaller, play more carefully
        base_size *= 0.8
    
    # Board texture adjustments (if available)
    if board_texture:
        if board_texture.get('draw_heavy', False):
            # Bet larger on draw-heavy boards for protection
            base_size *= 1.2
        elif board_texture.get('coordinated', False):
            # Bet smaller on coordinated boards
            base_size *= 0.9
    
    return min(base_size, 1.5)  # Cap at 1.5x pot


def standardize_pot_commitment_thresholds(hand_strength, street, spr):
    """
    Standardize pot commitment thresholds with enhanced logic (addresses issue #5).
    
    Args:
        hand_strength: String classification
        street: 'flop', 'turn', 'river'
        spr: Stack-to-pot ratio
    
    Returns:
        float: Commitment threshold (0.0-1.0)
    """
    
    # Enhanced base thresholds by hand strength with better granularity
    base_thresholds = {
        'very_strong': 0.20,  # Commit with 20% of stack (nuts/near-nuts)
        'strong': 0.30,       # Commit with 30% of stack (two pair+, strong pairs)
        'medium': 0.45,       # Commit with 45% of stack (decent pairs, good draws)
        'weak_made': 0.60,    # Commit with 60% of stack (weak pairs with equity)
        'very_weak': 0.75,    # Only commit at 75% (pot stuck scenarios)
        'drawing': 0.55       # Commit at 55% with draws (implied odds factor)
    }
    
    threshold = base_thresholds.get(hand_strength, 0.50)
    
    # Enhanced street adjustments - theory-based commitment progression
    street_multipliers = {
        'flop': 1.1,    # Slightly higher threshold on flop (more streets to play)
        'turn': 1.0,    # Standard threshold on turn
        'river': 0.85   # Lower threshold on river (no future streets)
    }
    
    threshold *= street_multipliers.get(street, 1.0)
    
    # Enhanced SPR adjustments with better scaling
    if spr < 1.5:
        # Very low SPR - commit very easily (pot committed territory)
        threshold *= 0.7
    elif spr < 3:
        # Low SPR - commit more easily
        threshold *= 0.85
    elif spr > 15:
        # Very high SPR - much more conservative
        threshold *= 1.4
    elif spr > 8:
        # High SPR - more conservative
        threshold *= 1.2
    
    # Additional context-based adjustments
    
    # Multiway pot adjustment (passed via hand_strength context if available)
    # This would need opponent count data, but for now use hand strength as proxy
    if hand_strength in ['weak_made', 'very_weak']:
        # Be more conservative with marginal hands in complex spots
        threshold *= 1.1
    
    # Ensure reasonable bounds with better limits
    return min(max(threshold, 0.12), 0.85)  # Keep between 12% and 85%


def fix_opponent_tracker_integration(opponent_tracker, active_opponents_count):
    """
    Fix the opponent tracker integration issue (addresses issue #4).
    
    Args:
        opponent_tracker: OpponentTracker instance
        active_opponents_count: Number of active opponents
    
    Returns:
        dict: Fixed opponent analysis data
    """
    
    if not opponent_tracker:
        return {
            'tracked_count': 0,
            'table_type': 'unknown',
            'avg_vpip': 25.0,  # Default assumptions
            'avg_pfr': 18.0,
            'avg_aggression': 1.5,
            'fold_equity_estimate': 0.5,
            'reasoning': 'no_tracker_available'
        }
    
    try:
        # Get tracked opponents with sufficient data
        tracked_opponents = []
        for name, profile in opponent_tracker.opponents.items():
            if profile.hands_seen >= 3:  # Lowered threshold for more data
                tracked_opponents.append(profile)
        
        tracked_count = len(tracked_opponents)
        
        if tracked_count == 0:
            # If no opponents tracked with sufficient hands, determine why
            total_profiles = len(opponent_tracker.opponents)
            reason = 'tracker_not_working_properly'
            if active_opponents_count > 0 and total_profiles == 0:
                reason = 'tracker_has_no_profiles_despite_active_opponents'
                logger.warning(f"Opponent tracker has no profiles, but {active_opponents_count} active opponents on table.")
            elif total_profiles > 0:
                reason = f'tracker_has_{total_profiles}_profiles_but_none_with_enough_hands_seen_threshold_3'
                logger.warning(f"Opponent tracker has {total_profiles} profiles, but none with hands_seen >= 3 (active_opponents_count: {active_opponents_count}).")
            else: # active_opponents_count is 0 or total_profiles is 0 (and active_opponents_count is 0)
                 reason = 'no_active_opponents_or_no_profiles_to_track'
                 logger.info(f"Opponent tracker: No active opponents ({active_opponents_count}) or no profiles ({total_profiles}) to assess for sufficient data.")


            return {
                'tracked_count': 0, # This means 0 opponents with sufficient data
                'table_type': 'unknown',
                'avg_vpip': 25.0,
                'avg_pfr': 18.0,
                'avg_aggression': 1.5,
                'fold_equity_estimate': 0.5,
                'reasoning': reason
            }
        
        # Calculate averages from tracked data
        total_vpip = sum(profile.get_vpip() for profile in tracked_opponents)
        total_pfr = sum(profile.get_pfr() for profile in tracked_opponents)
        
        avg_vpip = total_vpip / tracked_count if tracked_count > 0 else 25.0
        avg_pfr = total_pfr / tracked_count if tracked_count > 0 else 18.0
        avg_aggression = avg_pfr / avg_vpip if avg_vpip > 0 else 0.7
        
        # Estimate table type
        if avg_vpip < 18:
            table_type = 'tight'
        elif avg_vpip > 35:
            table_type = 'loose'
        else:
            table_type = 'standard'
        
        # Estimate fold equity based on table type
        fold_equity_estimates = {
            'tight': 0.65,
            'standard': 0.50,
            'loose': 0.35
        }
        fold_equity = fold_equity_estimates.get(table_type, 0.50)
        
        return {
            'tracked_count': tracked_count,
            'table_type': table_type,
            'avg_vpip': avg_vpip,
            'avg_pfr': avg_pfr,
            'avg_aggression': avg_aggression,
            'fold_equity_estimate': fold_equity,
            'reasoning': f'analyzed_{tracked_count}_opponents'
        }
        
    except Exception as e:
        logger.error(f"Error in opponent tracker integration: {e}")
        return {
            'tracked_count': 0,
            'table_type': 'unknown',
            'avg_vpip': 25.0,
            'avg_pfr': 18.0,
            'avg_aggression': 1.5,
            'fold_equity_estimate': 0.5,
            'reasoning': f'tracker_error_{str(e)[:50]}'
        }


def improved_drawing_hand_analysis(numerical_hand_rank, win_probability, pot_odds, bet_to_call, pot_size, my_stack, street):
    """
    Improved drawing hand analysis (addresses issue #6).
    
    Args:
        numerical_hand_rank: Hand ranking
        win_probability: Win probability
        pot_odds: Required pot odds to call
        bet_to_call: Amount needed to call
        pot_size: Current pot size
        my_stack: Remaining stack
        street: Current street
    
    Returns:
        dict: Analysis of drawing hand decision
    """
      # Identify if this is likely a drawing hand
    is_drawing = (numerical_hand_rank < 2 and 0.10 <= win_probability <= 0.50)
    
    if not is_drawing:
        return {
            'is_drawing': False,
            'should_call': False,
            'reasoning': 'not_a_drawing_hand'
        }
    
    # Basic pot odds check
    has_pot_odds = win_probability > pot_odds
    
    # Implied odds considerations
    implied_odds_multiplier = 1.0
    
    if street == 'flop':
        # Two streets to improve - better implied odds
        implied_odds_multiplier = 1.4
    elif street == 'turn':
        # One street to improve - some implied odds
        implied_odds_multiplier = 1.2
    else:  # river
        # No more cards - only direct pot odds matter
        implied_odds_multiplier = 1.0
    
    effective_equity = win_probability * implied_odds_multiplier
    
    # Reverse implied odds check
    reverse_implied_penalty = 0.0
    
    # If we're drawing to a weak hand, reduce equity
    if win_probability < 0.30:
        reverse_implied_penalty = 0.05  # 5% penalty
    
    adjusted_equity = effective_equity - reverse_implied_penalty
    
    # Stack preservation check
    bet_to_stack_ratio = bet_to_call / my_stack if my_stack > 0 else 1.0
    stack_preservation_ok = bet_to_stack_ratio <= 0.25  # Don't risk more than 25% of stack
    
    # Final decision
    should_call = (
        adjusted_equity > pot_odds and
        stack_preservation_ok and
        bet_to_call <= 0.6 * pot_size  # Don't call large bets with draws
    )
    
    return {
        'is_drawing': True,
        'should_call': should_call,
        'win_probability': win_probability,
        'pot_odds': pot_odds,
        'implied_odds_multiplier': implied_odds_multiplier,
        'effective_equity': effective_equity,
        'reverse_implied_penalty': reverse_implied_penalty,
        'adjusted_equity': adjusted_equity,
        'bet_to_stack_ratio': bet_to_stack_ratio,
        'stack_preservation_ok': stack_preservation_ok,
        'reasoning': f'draw_analysis_call_{should_call}'
    }


def enhanced_bluffing_strategy(pot_size, my_stack, street, win_probability, position=None, board_texture=None, opponent_analysis=None):
    """
    Enhanced bluffing strategy (addresses issue #7).
    
    Args:
        pot_size: Current pot size
        my_stack: Remaining stack
        street: Current street
        win_probability: Win probability
        position: Player position (optional)
        board_texture: Board analysis (optional)
        opponent_analysis: Opponent data (optional)
    
    Returns:
        dict: Bluffing decision and analysis
    """
    
    # Base bluffing frequency by position
    position_bluff_freq = {
        'EP': 0.15,   # Early position - less bluffing
        'MP': 0.20,   # Middle position - moderate
        'LP': 0.30,   # Late position - more bluffing
        'SB': 0.10,   # Small blind - very conservative
        'BB': 0.15,   # Big blind - conservative
        'BTN': 0.35   # Button - most bluffing
    }
    
    base_freq = position_bluff_freq.get(position, 0.20)
    
    # Street adjustments
    street_multipliers = {
        'flop': 0.8,   # Less bluffing on flop
        'turn': 1.0,   # Standard on turn
        'river': 1.3   # More bluffing on river (polarized)
    }
    
    street_mult = street_multipliers.get(street, 1.0)
    bluff_frequency = base_freq * street_mult
    
    # Board texture adjustments
    if board_texture:
        if board_texture.get('draw_heavy', False):
            bluff_frequency *= 1.2  # More bluffing on draw-heavy boards
        if board_texture.get('paired', False):
            bluff_frequency *= 0.8  # Less bluffing on paired boards
        if board_texture.get('coordinated', False):
            bluff_frequency *= 1.1  # Slightly more on coordinated boards
    
    # Opponent adjustments
    if opponent_analysis:
        fold_equity = opponent_analysis.get('fold_equity_estimate', 0.5)
        if fold_equity > 0.6:
            bluff_frequency *= 1.3  # Bluff more against tight opponents
        elif fold_equity < 0.4:
            bluff_frequency *= 0.7  # Bluff less against loose opponents
    
    # Stack size considerations
    stack_to_pot = my_stack / pot_size if pot_size > 0 else 10
    if stack_to_pot < 1:
        bluff_frequency *= 0.5  # Less bluffing when short-stacked
    elif stack_to_pot > 5:
        bluff_frequency *= 1.2  # More bluffing when deep-stacked
    
    # Win probability considerations - don't bluff with decent equity
    if win_probability > 0.25:
        bluff_frequency *= 0.6  # Semi-bluff less frequently
    
    # Final decision (simplified - would use random number in real implementation)
    should_bluff = bluff_frequency > 0.25  # Threshold for bluffing
    
    # Bluff sizing
    if should_bluff:
        if street == 'river':
            bluff_size = 0.8  # Larger river bluffs
        else:
            bluff_size = 0.6  # Moderate turn/flop bluffs
    else:
        bluff_size = 0.0
    
    return {
        'should_bluff': should_bluff,
        'bluff_frequency': bluff_frequency,
        'bluff_size_pot_fraction': bluff_size,
        'reasoning': f'pos_{position}_street_{street}_freq_{bluff_frequency:.2f}'
    }


# Test function to validate improvements
def test_enhanced_logic():
    """Test the enhanced logic functions with known problem scenarios."""
    
    print("Testing Enhanced Postflop Improvements...")
    
    # Test Case 1: KQ with pair of 9s (the main issue from logs)
    print("\n1. Testing KQ with pair of 9s classification:")
    classification = classify_hand_strength_enhanced(
        numerical_hand_rank=2,
        win_probability=0.35,
        hand_description="KQ with pair of 9s"
    )
    print(f"   Result: {classification} (should be 'weak_made' or 'very_weak')")
    
    # Test Case 2: Multiway betting with medium hand
    print("\n2. Testing multiway betting adjustment:")
    multiway_result = get_multiway_betting_adjustment(
        hand_strength='medium',
        active_opponents_count=5,
        win_probability=0.55
    )
    print(f"   Result: {multiway_result}")
    
    # Test Case 3: Consistent bet sizing
    print("\n3. Testing consistent bet sizing:")
    bet_size = get_consistent_bet_sizing(
        hand_strength='strong',
        pot_size=0.20,
        street='flop',
        spr=5.0
    )
    print(f"   Result: {bet_size:.2f} pot fraction")
    
    # Test Case 4: Pot commitment thresholds
    print("\n4. Testing pot commitment thresholds:")
    threshold = standardize_pot_commitment_thresholds(
        hand_strength='medium',
        street='turn',
        spr=3.0
    )
    print(f"   Result: {threshold:.2%} commitment threshold")
    
    print("\n✓ Enhanced logic tests completed")


if __name__ == "__main__":
    test_enhanced_logic()
