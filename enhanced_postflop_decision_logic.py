# enhanced_postflop_decision_logic.py
"""
Enhanced postflop decision logic with all improvements integrated:
- Fixed opponent tracking integration
- Consistent hand strength classification
- Strategic bet sizing
- Proper SPR strategy
- Better pot commitment logic
"""

import logging
from implied_odds import should_call_with_draws

# Setup debug logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Import enhanced modules
try:
    from enhanced_hand_classification import classify_hand_strength_enhanced, get_standardized_pot_commitment_threshold
    from enhanced_bet_sizing import get_enhanced_bet_size, should_check_instead_of_bet
    from fixed_opponent_integration import get_fixed_opponent_analysis, get_opponent_exploitative_adjustments
    from enhanced_spr_strategy import get_spr_strategy_recommendation, should_commit_stack_spr, get_protection_needs_spr
    ENHANCED_MODULES_AVAILABLE = True
    logger.info("Enhanced postflop modules successfully imported")
except ImportError as e:
    logger.warning(f"Enhanced postflop modules not available: {e}")
    ENHANCED_MODULES_AVAILABLE = False

# Create file handler if it doesn't exist
if not logger.handlers:
    handler = logging.FileHandler('debug_postflop_decision_logic.log', mode='a')
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def make_enhanced_postflop_decision(
    decision_engine_instance, 
    numerical_hand_rank, 
    hand_description,     
    bet_to_call,
    can_check,
    pot_size,
    my_stack,
    win_probability,       
    pot_odds_to_call,
    game_stage,  # This is 'street'
    spr,
    action_fold_const,
    action_check_const,
    action_call_const,
    action_raise_const,
    my_player_data,
    big_blind_amount,
    base_aggression_factor,
    max_bet_on_table,
    active_opponents_count=1,
    opponent_tracker=None
):
    """
    Enhanced postflop decision making with all improvements integrated.
    """
    street = game_stage
    position = my_player_data.get('position', 'BB')
    community_cards = my_player_data.get('community_cards', [])
    
    logger.debug(f"Enhanced postflop decision: street={street}, position={position}, "
                f"hand_rank={numerical_hand_rank}, win_prob={win_probability:.1%}, "
                f"pot={pot_size:.2f}, bet_to_call={bet_to_call:.2f}, "
                f"stack={my_stack:.2f}, spr={spr:.1f}, opponents={active_opponents_count}")
    
    # 1. CALCULATE POT COMMITMENT
    committed_amount = my_player_data.get('current_bet', 0)
    total_commitment_if_call = committed_amount + bet_to_call
    pot_commitment_ratio = total_commitment_if_call / (my_stack + total_commitment_if_call) if (my_stack + total_commitment_if_call) > 0 else 0
    
    # 2. ENHANCED HAND STRENGTH CLASSIFICATION
    if ENHANCED_MODULES_AVAILABLE:
        hand_strength, hand_details = classify_hand_strength_enhanced(
            numerical_hand_rank=numerical_hand_rank,
            win_probability=win_probability,
            street=street,
            board_texture='moderate'  # Can be enhanced further
        )
        commitment_threshold = get_standardized_pot_commitment_threshold(hand_strength, street)
    else:
        # Fallback classification
        hand_strength, commitment_threshold = _fallback_hand_classification(win_probability)
        hand_details = {'final_classification': hand_strength}
    
    logger.info(f"Hand classification: {hand_strength} (rank={numerical_hand_rank}, "
               f"win_prob={win_probability:.1%}, commitment_threshold={commitment_threshold:.1%})")
    
    # 3. FIXED OPPONENT ANALYSIS
    if ENHANCED_MODULES_AVAILABLE:
        opponent_analysis = get_fixed_opponent_analysis(opponent_tracker, active_opponents_count)
        exploitative_adjustments = get_opponent_exploitative_adjustments(opponent_analysis)
    else:
        opponent_analysis = _fallback_opponent_analysis(active_opponents_count)
        exploitative_adjustments = {}
    
    logger.info(f"Opponent analysis: tracked={opponent_analysis['tracked_count']}, "
               f"table_type={opponent_analysis['table_type']}, "
               f"avg_vpip={opponent_analysis['avg_vpip']:.1f}%, "
               f"fold_equity={opponent_analysis['fold_equity_estimate']:.1%}")
    
    # 4. ENHANCED SPR STRATEGY
    if ENHANCED_MODULES_AVAILABLE:
        spr_strategy = get_spr_strategy_recommendation(
            spr=spr,
            hand_strength=hand_strength,
            street=street,
            position=position,
            opponent_count=active_opponents_count,
            board_texture='moderate'
        )
        should_commit, commit_reason = should_commit_stack_spr(
            spr=spr,
            hand_strength=hand_strength,
            pot_commitment_ratio=pot_commitment_ratio,
            street=street
        )
    else:
        spr_strategy = {'betting_action': 'bet_value', 'sizing_adjustment': 1.0}
        should_commit = pot_commitment_ratio > commitment_threshold
        commit_reason = "fallback logic"
    
    logger.debug(f"SPR strategy: {spr_strategy.get('base_strategy', 'standard')} "
                f"(SPR={spr:.1f}), should_commit={should_commit}")
    
    # 5. POT COMMITMENT CHECK
    is_pot_committed = pot_commitment_ratio > commitment_threshold or should_commit
    
    logger.debug(f"Pot commitment: ratio={pot_commitment_ratio:.1%}, "
                f"threshold={commitment_threshold:.1%}, committed={is_pot_committed}")
    
    # 6. MAIN DECISION LOGIC
    
    # If we're facing a bet
    if bet_to_call > 0:
        return _handle_facing_bet(
            hand_strength, win_probability, pot_odds_to_call, bet_to_call, pot_size,
            my_stack, is_pot_committed, opponent_analysis, spr_strategy,
            action_fold_const, action_call_const, action_raise_const,
            street, position, active_opponents_count
        )
    
    # If we can check (no bet to call)
    else:
        return _handle_check_situation(
            hand_strength, win_probability, pot_size, my_stack, can_check,
            opponent_analysis, spr_strategy, position, street, active_opponents_count,
            action_check_const, action_raise_const, big_blind_amount
        )

def _fallback_hand_classification(win_probability):
    """Fallback hand classification when enhanced modules unavailable."""
    if win_probability >= 0.85:
        return 'very_strong', 0.15
    elif win_probability >= 0.70:
        return 'strong', 0.25
    elif win_probability >= 0.55:
        return 'medium', 0.45
    elif win_probability >= 0.35:
        return 'weak_made', 0.65
    else:
        return 'weak', 0.80

def _fallback_opponent_analysis(opponent_count):
    """Fallback opponent analysis when enhanced modules unavailable."""
    if opponent_count >= 4:
        table_type, avg_vpip, fold_equity = 'loose', 32.0, 0.35
    elif opponent_count <= 1:
        table_type, avg_vpip, fold_equity = 'tight', 20.0, 0.65
    else:
        table_type, avg_vpip, fold_equity = 'standard', 25.0, 0.50
    
    return {
        'tracked_count': 0,
        'table_type': table_type,
        'avg_vpip': avg_vpip,
        'fold_equity_estimate': fold_equity,
        'reasoning': 'fallback_analysis'
    }

def _handle_facing_bet(
    hand_strength, win_probability, pot_odds, bet_to_call, pot_size, my_stack,
    is_pot_committed, opponent_analysis, spr_strategy, 
    action_fold_const, action_call_const, action_raise_const,
    street, position, opponent_count
):
    """Handle decisions when facing a bet."""
    
    logger.debug(f"Facing bet: {bet_to_call:.2f}, pot_odds: {pot_odds:.3f}, "
                f"hand: {hand_strength}, committed: {is_pot_committed}")
    
    # If pot committed, call unless hand is completely hopeless
    if is_pot_committed and win_probability > 0.15:
        logger.info(f"Decision: CALL (pot committed with {win_probability:.1%} equity)")
        return action_call_const, round(bet_to_call, 2)
    
    # Very strong hands - consider raising
    if hand_strength == 'very_strong':
        if win_probability > 0.80 and bet_to_call < pot_size * 0.5:
            # Raise for value
            raise_size = _calculate_raise_size(bet_to_call, pot_size, my_stack, 'value', opponent_analysis)
            if raise_size > bet_to_call:
                logger.info(f"Decision: RAISE (very strong hand for value). Amount: {raise_size:.2f}")
                return action_raise_const, round(raise_size, 2)
        
        # Otherwise call
        logger.info(f"Decision: CALL (very strong hand)")
        return action_call_const, round(bet_to_call, 2)
    
    # Strong hands - mostly call, sometimes raise
    elif hand_strength == 'strong':
        if bet_to_call <= pot_size * 0.6:  # Not too large
            logger.info(f"Decision: CALL (strong hand, reasonable bet size)")
            return action_call_const, round(bet_to_call, 2)
        else:
            logger.info(f"Decision: FOLD (strong hand, bet too large: {bet_to_call:.2f} > 60% pot)")
            return action_fold_const, 0
    
    # Medium hands - check pot odds and bet size
    elif hand_strength == 'medium':
        if win_probability > pot_odds and bet_to_call <= pot_size * 0.5:
            logger.info(f"Decision: CALL (medium hand, good odds: {win_probability:.1%} > {pot_odds:.1%})")
            return action_call_const, round(bet_to_call, 2)
        else:
            logger.info(f"Decision: FOLD (medium hand, poor odds or large bet)")
            return action_fold_const, 0
    
    # Weak made hands - be very selective
    elif hand_strength == 'weak_made':
        if win_probability > pot_odds * 1.2 and bet_to_call <= pot_size * 0.3:  # Need better odds
            logger.info(f"Decision: CALL (weak made hand, very good odds)")
            return action_call_const, round(bet_to_call, 2)
        else:
            logger.info(f"Decision: FOLD (weak made hand)")
            return action_fold_const, 0
    
    # Weak hands - mostly fold, sometimes call with great odds
    else:
        if win_probability > pot_odds * 1.5 and bet_to_call <= pot_size * 0.2:
            logger.info(f"Decision: CALL (weak hand, excellent odds)")
            return action_call_const, round(bet_to_call, 2)
        else:
            logger.info(f"Decision: FOLD (weak hand)")
            return action_fold_const, 0

def _handle_check_situation(
    hand_strength, win_probability, pot_size, my_stack, can_check,
    opponent_analysis, spr_strategy, position, street, opponent_count,
    action_check_const, action_raise_const, big_blind_amount
):
    """Handle decisions when we can check (no bet facing)."""
    
    logger.debug(f"Check situation: hand={hand_strength}, can_check={can_check}")
    
    # Check if we should check instead of bet
    if ENHANCED_MODULES_AVAILABLE:
        should_check, check_reason = should_check_instead_of_bet(
            hand_strength, win_probability, pot_size, opponent_count, position, street
        )
        if should_check:
            logger.info(f"Decision: CHECK ({check_reason})")
            return action_check_const, 0
    
    # Very strong hands - almost always bet
    if hand_strength == 'very_strong':
        bet_size, reasoning = _get_value_bet_size(
            hand_strength, pot_size, my_stack, street, position, 
            opponent_count, opponent_analysis, spr_strategy
        )
        if bet_size > 0:
            logger.info(f"Decision: BET (very strong hand). Amount: {bet_size:.2f}")
            return action_raise_const, round(bet_size, 2)
    
    # Strong hands - usually bet
    elif hand_strength == 'strong':
        if opponent_count <= 2:  # Not too many opponents
            bet_size, reasoning = _get_value_bet_size(
                hand_strength, pot_size, my_stack, street, position,
                opponent_count, opponent_analysis, spr_strategy
            )
            if bet_size > 0:
                logger.info(f"Decision: BET (strong hand). Amount: {bet_size:.2f}")
                return action_raise_const, round(bet_size, 2)
    
    # Medium hands - selective betting
    elif hand_strength == 'medium':
        if opponent_count == 1 and win_probability > 0.60:  # Heads-up with good equity
            bet_size, reasoning = _get_value_bet_size(
                hand_strength, pot_size, my_stack, street, position,
                opponent_count, opponent_analysis, spr_strategy
            )
            if bet_size > 0:
                logger.info(f"Decision: BET (medium hand, heads-up). Amount: {bet_size:.2f}")
                return action_raise_const, round(bet_size, 2)
    
    # Default: check
    logger.info(f"Decision: CHECK (default action)")
    return action_check_const, 0

def _get_value_bet_size(hand_strength, pot_size, my_stack, street, position, 
                       opponent_count, opponent_analysis, spr_strategy):
    """Calculate value bet size."""
    
    if ENHANCED_MODULES_AVAILABLE:
        bet_size, reasoning = get_enhanced_bet_size(
            hand_strength=hand_strength,
            pot_size=pot_size,
            my_stack=my_stack,
            street=street,
            position=position,
            board_texture='moderate',
            spr=pot_size / my_stack if my_stack > 0 else 5.0,
            opponent_count=opponent_count,
            opponent_tendencies={
                'calling_frequency': opponent_analysis.get('calling_frequency', 0.5),
                'fold_frequency': opponent_analysis.get('fold_equity_estimate', 0.5)
            },
            bet_purpose='value'
        )
        return bet_size, reasoning
    else:
        # Fallback bet sizing
        base_sizes = {
            'very_strong': 0.75,
            'strong': 0.65,
            'medium': 0.50,
            'weak_made': 0.35
        }
        
        base_fraction = base_sizes.get(hand_strength, 0.50)
        
        # Adjust for opponents
        if opponent_count > 1:
            base_fraction *= max(0.6, 1.0 - (opponent_count - 1) * 0.15)
        
        # Adjust for SPR
        spr_adj = spr_strategy.get('sizing_adjustment', 1.0)
        base_fraction *= spr_adj
        
        bet_size = min(base_fraction * pot_size, my_stack)
        return max(bet_size, 0.01), f"fallback sizing: {base_fraction:.2f} of pot"

def _calculate_raise_size(bet_to_call, pot_size, my_stack, purpose, opponent_analysis):
    """Calculate raise size when facing a bet."""
    
    if purpose == 'value':
        # Raise to 2.5-3x the bet
        raise_multiple = 2.8
        if opponent_analysis.get('calling_frequency', 0.5) > 0.6:
            raise_multiple = 3.2  # Raise larger vs calling stations
    else:
        # Bluff raise
        raise_multiple = 2.5
    
    total_raise = bet_to_call * raise_multiple
    return min(total_raise, my_stack)

# Legacy function compatibility
def make_postflop_decision(*args, **kwargs):
    """Wrapper for backwards compatibility."""
    return make_enhanced_postflop_decision(*args, **kwargs)

# Import legacy functions for compatibility
try:
    from postflop_decision_logic_backup import (
        get_dynamic_bet_size, estimate_opponent_range, calculate_fold_equity,
        is_thin_value_spot, should_call_bluff, is_drawing_hand, 
        calculate_spr_adjustments, analyze_opponents
    )
except ImportError:
    logger.warning("Legacy functions not available - using enhanced versions only")
    
    # Provide minimal implementations
    def get_dynamic_bet_size(rank, pot, stack, street, bb, opponents, bluff=False):
        return pot * (0.6 if bluff else 0.65)
    
    def estimate_opponent_range(pos, action, bet, pot, street, texture):
        return 'unknown'
    
    def calculate_fold_equity(range_est, texture, bet, pot):
        return 0.5
    
    def is_thin_value_spot(strength, prob, range_est, pos):
        return prob > 0.55
    
    def should_call_bluff(strength, prob, odds, range_est, bet, pot):
        return prob > odds
    
    def is_drawing_hand(prob, rank, street):
        return rank == 1 and prob > 0.25
    
    def calculate_spr_adjustments(spr, rank, drawing):
        if spr < 3:
            return 'commit'
        elif spr > 10:
            return 'fold_weak'
        else:
            return 'standard'
    
    def analyze_opponents(tracker, count, bet, pot):
        return {}
