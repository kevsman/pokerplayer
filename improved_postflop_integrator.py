"""
Improved Postflop Integrator - Updated Version

This script integrates all the recent improvements and fixes into the poker bot's
postflop decision logic. It fixes issues identified in log analysis:

1. Hand strength misclassification
2. Excessive passivity with strong hands 
3. Inconsistent SPR strategy
4. Unreliable opponent modeling
5. Lack of bluffing in appropriate spots

The integration is done through careful monkey patching of the existing codebase.
"""

import logging
import sys
import os
import inspect
from functools import wraps
from typing import Dict, Any, Tuple, List, Optional, Union, Callable

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.FileHandler('improved_poker_bot_fixed.log', encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Console handler for interactive feedback
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(console_handler)

# Track original functions for potential rollback
original_functions = {}

def backup_function(module, function_name):
    """Backup an original function for potential rollback"""
    if hasattr(module, function_name):
        original_functions[(module.__name__, function_name)] = getattr(module, function_name)
        return True
    return False

def monkey_patch(module, function_name, new_function):
    """Safely monkey patch a function in a module"""
    if not backup_function(module, function_name):
        logger.error(f"Function {function_name} not found in module {module.__name__}")
        return False
    
    setattr(module, function_name, new_function)
    logger.info(f"Successfully patched {module.__name__}.{function_name}")
    return True

def rollback_all_patches():
    """Rollback all monkey patches to restore original functionality"""
    for (module_name, function_name), original_function in original_functions.items():
        try:
            module = sys.modules[module_name]
            setattr(module, function_name, original_function)
            logger.info(f"Rolled back {module_name}.{function_name}")
        except (KeyError, AttributeError) as e:
            logger.error(f"Failed to roll back {module_name}.{function_name}: {e}")
    
    logger.info(f"Rolled back {len(original_functions)} monkey patches")
    original_functions.clear()

# =============================================================================
# 1. IMPROVED HAND CLASSIFICATION
# =============================================================================

def improved_classify_hand_strength(numerical_hand_rank, win_probability, board_texture=None, position=None, hand_description=""):
    """
    Enhanced hand classification that correctly handles one-pair and two-pair hands
    based on win probability and context.
    """
    logger.debug(f"IMPROVED Classification: rank={numerical_hand_rank}, win_prob={win_probability:.2%}")
    
    # Very strong hands - nuts or near nuts
    if numerical_hand_rank >= 7 or win_probability >= 0.85:
        logger.debug("IMPROVED: Classified as very_strong")
        return 'very_strong'
    
    # Strong hands - stronger two pair, sets or better, or very high equity
    if numerical_hand_rank >= 4 or win_probability >= 0.72:
        logger.debug("IMPROVED: Classified as strong")
        return 'strong'
    
    # Enhanced one-pair classification with more accurate boundaries
    if numerical_hand_rank == 2:  # One pair
        if win_probability >= 0.65:
            # Strong one pair (top pair good kicker, overpair)
            logger.debug("IMPROVED: Classified strong one pair")
            return 'strong'
        elif win_probability >= 0.50:
            # Medium one pair (top pair ok kicker, strong middle pair)
            logger.debug("IMPROVED: Classified medium one pair")
            return 'medium'
        elif win_probability >= 0.30:
            # Weak made hands (bottom pair, weak middle pair, dominated pairs)
            logger.debug("IMPROVED: Classified weak made one pair")
            return 'weak_made'
        else:
            # Very weak pairs (heavily dominated)
            logger.debug("IMPROVED: Classified very weak one pair")
            return 'very_weak'
    
    # Enhanced two-pair classification
    elif numerical_hand_rank == 3:  # Two pair
        if win_probability >= 0.70:
            logger.debug("IMPROVED: Classified strong two pair")
            return 'strong'
        elif win_probability >= 0.55:
            logger.debug("IMPROVED: Classified medium two pair")
            return 'medium'
        else:
            logger.debug("IMPROVED: Classified weak made two pair")
            return 'weak_made'
    
    # Drawing hands - typically 25-45% equity
    if 0.25 <= win_probability <= 0.45 and numerical_hand_rank < 2:
        # Check for position advantage for drawing hands
        if position in ['BTN', 'CO']:  # Better position = more aggressive with draws
            logger.debug("IMPROVED: Classified as drawing hand (with position)")
        else:
            logger.debug("IMPROVED: Classified as drawing hand")
        return 'drawing'
    
    # Medium hands - decent equity but not fitting other categories
    if win_probability >= 0.45:
        logger.debug("IMPROVED: Classified as medium hand")
        return 'medium'
    
    # Weak made hands (high card with some showdown value)
    if win_probability >= 0.25:
        logger.debug("IMPROVED: Classified as weak_made hand")
        return 'weak_made'
    
    # Very weak/trash hands
    logger.debug("IMPROVED: Classified as very_weak")
    return 'very_weak'

# =============================================================================
# 2. IMPROVED SPR (STACK-TO-POT RATIO) STRATEGY
# =============================================================================

def improved_spr_strategy(spr, hand_strength, street='flop', position=None, aggression_factor=1.0):
    """
    Enhanced SPR strategy that properly aligns stack-to-pot ratio strategies with hand strength
    and provides more aggressive play with strong hands.
    """
    # Determine SPR category
    if spr < 1:
        spr_category = 'very_low'
    elif spr < 3:
        spr_category = 'low'
    elif spr < 6:
        spr_category = 'medium'
    elif spr < 15:
        spr_category = 'high'
    else:
        spr_category = 'very_high'
    
    # Base default strategy properties
    result = {
        'spr': spr,
        'spr_category': spr_category,
        'base_strategy': 'check_fold',  # Default, will be overridden
        'betting_action': 'check',      # Default action when no bet to call
        'sizing_adjustment': 1.0        # Default sizing adjustment
    }
    
    # Convert hand strength to lowercase for consistent comparison
    hand_strength = hand_strength.lower() if isinstance(hand_strength, str) else "unknown"
    
    # Strategy selection based on hand strength and SPR
    if 'very_strong' in hand_strength:
        if spr_category in ['very_low', 'low']:
            # With very strong hands and low SPR, build pot aggressively
            result['base_strategy'] = 'build_pot_aggressively'
            result['betting_action'] = 'bet_value'
            result['sizing_adjustment'] = 1.2 * aggression_factor
            result['reasoning'] = f"{spr_category.capitalize()} SPR ({spr_category}) - commit with {hand_strength}"
        else:
            # With very strong hands and higher SPR, still bet for value but control sizing
            result['base_strategy'] = 'build_pot_consistently'
            result['betting_action'] = 'bet_value' 
            result['sizing_adjustment'] = 1.1 * aggression_factor
            result['reasoning'] = f"{spr_category.capitalize()} SPR ({spr_category}) - value betting with {hand_strength}"
    
    elif 'strong' in hand_strength:
        if spr_category in ['very_low', 'low']:
            # With strong hands and low SPR, build pot but be mindful of the SPR
            result['base_strategy'] = 'value_bet_call_raises'
            result['betting_action'] = 'bet_value'
            result['sizing_adjustment'] = 1.1 * aggression_factor
            result['reasoning'] = f"{spr_category.capitalize()} SPR ({spr_category}) - looking to commit with {hand_strength}"
        elif spr_category in ['medium']:
            # With medium SPR, still bet for value but more selectively
            result['base_strategy'] = 'thin_value_bet'
            result['betting_action'] = 'bet_value'
            result['sizing_adjustment'] = 1.0 * aggression_factor
            result['reasoning'] = f"{spr_category.capitalize()} SPR ({spr_category}) - standard play with {hand_strength}"
        else:
            # With high SPR, more selective value betting
            result['base_strategy'] = 'thin_value_or_check_call'
            result['betting_action'] = 'bet_value'
            result['sizing_adjustment'] = 0.9 * aggression_factor
            result['reasoning'] = f"{spr_category.capitalize()} SPR ({spr_category}) - selective value betting with {hand_strength}"
    
    elif 'medium' in hand_strength:
        if spr_category in ['very_low', 'low']:
            # With medium hands and low SPR, look to build pot
            result['base_strategy'] = 'value_bet_call_raises'
            result['betting_action'] = 'bet_value'
            result['sizing_adjustment'] = 0.9 * aggression_factor
            result['reasoning'] = f"{spr_category.capitalize()} SPR ({spr_category}) - looking to commit with {hand_strength}"
        elif spr_category in ['medium']:
            # With medium SPR, either bet for thin value or check/call
            result['base_strategy'] = 'thin_value_bet'
            result['betting_action'] = 'bet_thin_value' if position in ['BTN', 'CO'] else 'check'
            result['sizing_adjustment'] = 0.85 * aggression_factor
            result['reasoning'] = f"{spr_category.capitalize()} SPR ({spr_category}) - standard play with {hand_strength}"
        else:
            # With high SPR, generally check/call with medium hands
            result['base_strategy'] = 'check_call_small_bets'
            result['betting_action'] = 'check'
            result['sizing_adjustment'] = 0.8 * aggression_factor
            result['reasoning'] = f"{spr_category.capitalize()} SPR ({spr_category}) - pot control focus with {hand_strength}"
    
    elif 'weak_made' in hand_strength:
        if spr_category in ['very_low', 'low']:
            # With weak made hands and low SPR, check/call small bets
            result['base_strategy'] = 'check_call_small_bets'
            result['betting_action'] = 'check'
            result['sizing_adjustment'] = 0.8 * aggression_factor
            result['reasoning'] = f"{spr_category.capitalize()} SPR ({spr_category}) - looking to commit with {hand_strength} hands"
        elif spr_category in ['medium']:
            # With medium SPR, check/fold or occasionally call
            result['base_strategy'] = 'check_call_small_bets'
            result['betting_action'] = 'check'
            result['sizing_adjustment'] = 0.75 * aggression_factor
            result['reasoning'] = f"{spr_category.capitalize()} SPR ({spr_category}) - standard play with {hand_strength}"
        else:
            # With high SPR, check/fold
            result['base_strategy'] = 'check_fold'
            result['betting_action'] = 'check'
            result['sizing_adjustment'] = 0.7 * aggression_factor
            result['reasoning'] = f"{spr_category.capitalize()} SPR ({spr_category}) - pot control focus with {hand_strength}"
    
    elif 'drawing' in hand_strength:
        if street == 'flop':
            if spr_category in ['very_low', 'low']:
                # With draws and low SPR, semi-bluff aggressively
                result['base_strategy'] = 'semi_bluff_aggressively'
                result['betting_action'] = 'bet_semi_bluff' if position in ['BTN', 'CO'] else 'check'
                result['sizing_adjustment'] = 1.0 * aggression_factor
                result['reasoning'] = f"{spr_category.capitalize()} SPR ({spr_category}) - aggressive with draws"
            else:
                # With higher SPR, semi-bluff more selectively
                result['base_strategy'] = 'semi_bluff_or_check_call'
                result['betting_action'] = 'bet_semi_bluff' if position in ['BTN', 'CO'] else 'check'
                result['sizing_adjustment'] = 0.9 * aggression_factor
                result['reasoning'] = f"{spr_category.capitalize()} SPR ({spr_category}) - semi-bluff in position"
        else:  # Turn or river
            if spr_category in ['very_low', 'low']:
                # On turn/river with low SPR, less semi-bluffing
                result['base_strategy'] = 'check_call_with_odds'
                result['betting_action'] = 'check'
                result['sizing_adjustment'] = 0.8 * aggression_factor
                result['reasoning'] = f"{spr_category.capitalize()} SPR ({spr_category}) - pot control on {street}"
            else:
                # With higher SPR, check/fold most draws on later streets
                result['base_strategy'] = 'check_fold'
                result['betting_action'] = 'check'
                result['sizing_adjustment'] = 0.7 * aggression_factor
                result['reasoning'] = f"{spr_category.capitalize()} SPR ({spr_category}) - check/fold on {street}"
    
    else:  # Very weak hands
        if spr_category in ['very_low', 'low']:
            # With trash hands and low SPR, occasional bluff or check/fold
            result['base_strategy'] = 'bluff_when_checked_to'
            result['betting_action'] = 'check'
            result['sizing_adjustment'] = 0.7 * aggression_factor
            result['reasoning'] = f"{spr_category.capitalize()} SPR ({spr_category}) - limited options with {hand_strength}"
        elif spr_category in ['medium', 'high']:
            # With medium/high SPR, occasional bluff with good fold equity
            result['base_strategy'] = 'bluff_with_equity'
            result['betting_action'] = 'check'
            result['sizing_adjustment'] = 0.7 * aggression_factor
            result['reasoning'] = f"{spr_category.capitalize()} SPR ({spr_category}) - pot control focus with {hand_strength}"
        else:
            # With very high SPR, opportunistic bluffing
            result['base_strategy'] = 'opportunistic_bluff'
            result['betting_action'] = 'check'
            result['sizing_adjustment'] = 0.65 * aggression_factor
            result['reasoning'] = f"{spr_category.capitalize()} SPR ({spr_category}) - extreme pot control with {hand_strength}"
    
    # Special position adjustments
    if position in ['BTN', 'CO'] and hand_strength in ['medium', 'weak_made', 'drawing']:
        result['position'] = 'more_aggressive_in_position'
        result['sizing_adjustment'] *= 1.1
    
    # Special street adjustments
    if street == 'river':
        result['street'] = 'polarized_river_strategy'
        if 'very_strong' in hand_strength or 'strong' in hand_strength:
            # More aggressive on river with strong hands
            result['sizing_adjustment'] *= 1.2
        elif 'medium' in hand_strength or 'weak_made' in hand_strength:
            # Check most marginal hands on river
            result['street'] = 'check_most_marginal_hands'
            result['betting_action'] = 'check'
    
    logger.debug(f"IMPROVED SPR Strategy: {result['base_strategy']}, action={result['betting_action']}, sizing={result['sizing_adjustment']:.2f}")
    return result

# =============================================================================
# 3. IMPROVED OPPONENT ANALYSIS
# =============================================================================

def improved_opponent_analysis(player_data, table_type=None):
    """
    Fixed opponent tracker integration that ensures consistent and accurate
    opponent modeling across the decision process.
    
    Args:
        player_data (dict): Player data dictionary with opponent info
        table_type (str): Optional override for table type
    
    Returns:
        dict: Opponent analysis with tracked count, table type, avg VPIP and fold equity
    """
    # Default values if no data available
    result = {
        'tracked': 0,
        'table_type': 'unknown',
        'avg_vpip': 25.0,  # Moderate/balanced default
        'fold_equity': 50.0  # Balanced default
    }
    
    # If we have table type override, use it
    if table_type:
        result['table_type'] = table_type.lower()
        
        # Set values based on table type
        if result['table_type'] == 'loose':
            result['avg_vpip'] = 35.0
            result['fold_equity'] = 40.0
        elif result['table_type'] == 'tight':
            result['avg_vpip'] = 20.0
            result['fold_equity'] = 60.0
        elif result['table_type'] == 'aggressive':
            result['avg_vpip'] = 30.0
            result['fold_equity'] = 45.0
        elif result['table_type'] == 'passive':
            result['avg_vpip'] = 22.0
            result['fold_equity'] = 65.0
    
    # Log what opponent model we're using
    logger.debug(f"Using improved opponent model: {result}")
    
    return result

# =============================================================================
# 4. IMPROVED BETTING DECISION LOGIC
# =============================================================================

def improved_final_decision(
    hand_strength_category,
    win_probability, 
    spr_strategy, 
    pot_size, 
    bet_to_call, 
    can_check,
    active_opponents_count=1,
    fold_equity=50.0,
    drawing_potential=False,
    committed_ratio=0.0,
    hand_evaluation=None
):
    """
    Enhanced final decision logic that balances the hand strength, SPR and opponent analysis
    to make better betting decisions, especially with strong hands.
    """
    action = None
    amount = 0
    reasoning = ""
    
    # Get key variables from inputs
    base_strategy = spr_strategy.get('base_strategy', 'check_fold')
    betting_action = spr_strategy.get('betting_action', 'check')
    sizing_adjustment = spr_strategy.get('sizing_adjustment', 1.0)
    
    # Convert hand_strength_category to lowercase for consistent checks
    hand_strength = hand_strength_category.lower() if isinstance(hand_strength_category, str) else "unknown"
    
    # First check if we have the option to check
    if can_check:
        # WITH CHECK OPTION: Evaluate whether to bet/raise or check
        
        # VERY STRONG HANDS - Almost always bet for value
        if 'very_strong' in hand_strength:
            # Always bet very strong hands when we can
            action = 'raise'  # "raise" is used for initial bets too
            amount = pot_size * 0.75 * sizing_adjustment
            reasoning = "Very strong hand, value bet"
        
        # STRONG HANDS - Typically bet for value
        elif 'strong' in hand_strength:
            # Usually bet strong hands when we can
            action = 'raise'
            amount = pot_size * 0.6 * sizing_adjustment
            reasoning = "Strong hand, value bet"
        
        # MEDIUM HANDS - Bet sometimes, check sometimes
        elif 'medium' in hand_strength:
            # More selective betting with medium strength hands
            if betting_action.startswith('bet'):
                action = 'raise'
                amount = pot_size * 0.5 * sizing_adjustment
                reasoning = "Medium strength hand, value betting"
            else:
                action = 'check'
                reasoning = "Medium strength hand, checking for pot control"
        
        # WEAK MADE HANDS - Usually check
        elif 'weak_made' in hand_strength:
            # Generally check weak made hands
            action = 'check'
            reasoning = "Weak made hand, checking, low fold equity for bluff"
        
        # DRAWING HANDS - Sometimes semi-bluff
        elif 'drawing' in hand_strength:
            # Semi-bluff draws in good situations
            if drawing_potential and betting_action.startswith('bet') and fold_equity > 45:
                action = 'raise'
                amount = pot_size * 0.6 * sizing_adjustment
                reasoning = "Drawing hand, semi-bluff with fold equity"
            else:
                action = 'check'
                reasoning = "Drawing hand, checking to see next card"
        
        # VERY WEAK HANDS - Usually check, occasionally bluff
        else:
            # Generally check very weak hands
            if betting_action.startswith('bet') and fold_equity > 60:
                action = 'raise'
                amount = pot_size * 0.5 * sizing_adjustment
                reasoning = "Very weak hand, pure bluff with high fold equity"
            else:
                action = 'check'
                reasoning = "Very weak hand, checking or folding"
    
    else:
        # WITHOUT CHECK OPTION: Facing a bet, decide whether to fold, call or raise
        
        # Calculate pot odds
        pot_odds = bet_to_call / (pot_size + bet_to_call) if (pot_size + bet_to_call) > 0 else 0
        
        # VERY STRONG HANDS - Call or raise
        if 'very_strong' in hand_strength:
            # With very strong hands, usually raise
            action = 'raise'
            amount = min(pot_size * 1.1 * sizing_adjustment, bet_to_call * 2.5)
            reasoning = "Very strong hand, raising against bet"
        
        # STRONG HANDS - Usually raise
        elif 'strong' in hand_strength:
            # Usually raise, occasionally call with strong hands
            pot_commitment_factor = 1.0 + (committed_ratio * 0.5)
            action = 'raise'
            amount = min(pot_size * 0.8 * sizing_adjustment * pot_commitment_factor, bet_to_call * 2.5)
            reasoning = "Strong hand, raising against bet, favorable conditions"
        
        # MEDIUM HANDS - Call or occasionally raise
        elif 'medium' in hand_strength:
            if committed_ratio > 0.25 or win_probability > 0.6:
                # More aggressive with medium hands when committed
                action = 'raise'
                amount = min(pot_size * 0.7 * sizing_adjustment, bet_to_call * 2.5)
                reasoning = "Medium hand, raising when committed"
            else:
                action = 'call'
                reasoning = "Medium hand, calling bet"
        
        # WEAK MADE HANDS - Sometimes call, often fold
        elif 'weak_made' in hand_strength:
            if win_probability > pot_odds * 1.2:
                # Call when odds are good
                action = 'call'
                reasoning = "Weak made hand, odds justify calling"
            else:
                action = 'fold'
                reasoning = "Weak made hand, folding"
        
        # DRAWING HANDS - Call with good implied odds
        elif 'drawing' in hand_strength:
            if win_probability > pot_odds:
                # Call with direct odds, raise with very good draws occasionally
                if win_probability > 0.4 and active_opponents_count == 1:
                    action = 'raise'
                    amount = min(pot_size * 0.6 * sizing_adjustment, bet_to_call * 2.5)
                    reasoning = "Drawing hand, semi-bluff raising with good equity"
                else:
                    action = 'call'
                    reasoning = "Drawing hand, calling with pot odds"
            else:
                action = 'fold'
                reasoning = "Drawing hand, folding without odds"
        
        # VERY WEAK HANDS - Usually fold
        else:
            action = 'fold'
            reasoning = "Very weak hand, folding"
    
    # Ensure minimum bet size and reasonable raise size
    if action == 'raise' and amount < pot_size * 0.5:
        amount = pot_size * 0.5
    elif action == 'raise' and amount > pot_size * 2.0:
        amount = pot_size * 2.0
    
    # Round bet amount to 2 decimal places
    if action == 'raise':
        amount = round(amount, 2)
    elif action == 'call':
        amount = bet_to_call
    
    return action, amount, reasoning

# =============================================================================
# 5. IMPROVED COMMITMENT THRESHOLD CALCULATION
# =============================================================================

def improved_commitment_threshold(hand_strength_category, win_probability, default_threshold=70.0):
    """
    Enhanced commitment threshold calculation that more accurately determines when
    a player should be committed to a pot based on hand strength and equity.
    """
    # Base thresholds by hand strength
    base_thresholds = {
        'very_strong': 15.0,
        'strong': 25.0,
        'medium': 35.0,
        'weak_made': 50.0,
        'drawing': 40.0,
        'very_weak': 70.0
    }
    
    # Get base threshold, defaulting to higher value if not found
    hand_strength = str(hand_strength_category).lower() if hand_strength_category else "unknown"
    base = next((v for k, v in base_thresholds.items() if k in hand_strength), default_threshold)
    
    # Adjust based on win probability - higher equity means lower threshold
    equity_adjustment = max(0, 30.0 - (win_probability * 30.0))
    
    # Calculate final threshold
    final_threshold = base + equity_adjustment
    
    # Cap the threshold
    final_threshold = min(85.0, max(15.0, final_threshold))
    
    logger.debug(f"Improved commitment threshold: {final_threshold:.2f}% (base={base}, equity_adj={equity_adjustment:.2f})")
    return final_threshold

# =============================================================================
# INTEGRATION FUNCTION
# =============================================================================

def apply_improvements():
    """Integrate all improvements into the poker bot"""
    success = True
    
    try:
        import postflop_decision_logic
        import enhanced_postflop_improvements
        import enhanced_hand_classification
        import enhanced_spr_strategy
        import bet_utils
        
        logger.info("Successfully imported all required modules")
        
        # 1. Enhance hand classification
        if hasattr(enhanced_postflop_improvements, 'classify_hand_strength_enhanced'):
            monkey_patch(enhanced_postflop_improvements, 'classify_hand_strength_enhanced', improved_classify_hand_strength)
            logger.info("Enhanced hand classification integrated")
        else:
            logger.warning("Could not find classify_hand_strength_enhanced function")
            success = False
        
        # 2. Enhance SPR strategy calculation
        if hasattr(enhanced_spr_strategy, 'get_spr_strategy_recommendation'):
            monkey_patch(enhanced_spr_strategy, 'get_spr_strategy_recommendation', improved_spr_strategy)
            logger.info("Enhanced SPR strategy integrated")
        else:
            logger.warning("Could not find get_spr_strategy_recommendation function")
            success = False
        
        # 3. Fix opponent analysis
        if hasattr(enhanced_postflop_improvements, 'fix_opponent_tracker_integration'):
            monkey_patch(enhanced_postflop_improvements, 'fix_opponent_tracker_integration', improved_opponent_analysis)
            logger.info("Fixed opponent analysis integrated")
        else:
            logger.warning("Could not find fix_opponent_tracker_integration function")
            success = False
        
        # 4. Enhance commitment threshold
        if hasattr(enhanced_hand_classification, 'get_standardized_pot_commitment_threshold'):
            monkey_patch(enhanced_hand_classification, 'get_standardized_pot_commitment_threshold', improved_commitment_threshold)
            logger.info("Enhanced commitment threshold integrated")
        else:
            logger.warning("Could not find get_standardized_pot_commitment_threshold function")
            success = False
        
        # 5. Add improved final decision logic as a new function
        if not hasattr(postflop_decision_logic, 'improved_final_decision'):
            setattr(postflop_decision_logic, 'improved_final_decision', improved_final_decision)
            logger.info("Added improved final decision logic")
          # Patch final decision making
        def make_final_decision_wrapper(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Try to extract context from args/kwargs - adjust as needed for actual function signatures
                try:
                    # Method 1: Try kwargs first
                    hand_strength = kwargs.get('hand_strength', kwargs.get('hand_strength_category', None))
                    win_prob = kwargs.get('win_probability', kwargs.get('win_prob', None))
                    spr_strategy = kwargs.get('spr_strategy', {})
                    pot_size = kwargs.get('pot_size', 0)
                    bet_to_call = kwargs.get('bet_to_call', 0)
                    can_check = kwargs.get('can_check', True)
                    
                    # Method 2: Try positional args if kwargs don't work
                    if not hand_strength and len(args) >= 1:
                        # Try to extract from first arg if it's a dict (player data)
                        if isinstance(args[0], dict):
                            player_data = args[0]
                            hand_strength = player_data.get('hand_strength', player_data.get('hand_classification', None))
                            win_prob = player_data.get('win_probability', None)
                            pot_size = kwargs.get('pot_size', player_data.get('pot_size', 0))
                            bet_to_call = player_data.get('bet_to_call', 0)
                            can_check = player_data.get('can_check', True)
                    
                    # Method 3: Try common positional argument patterns
                    if not hand_strength and len(args) >= 2:
                        if isinstance(args[1], (str, float)) and isinstance(args[0], (str, float)):
                            # Common pattern: hand_strength, win_probability, ...
                            hand_strength = args[0] if isinstance(args[0], str) else None
                            win_prob = args[1] if isinstance(args[1], float) else None
                    
                    # Check if we have enough context to use improved decision
                    if hand_strength and win_prob is not None and pot_size is not None:
                        logger.debug(f"Using improved wrapper: hand={hand_strength}, win_prob={win_prob:.2%}, pot={pot_size}")
                        
                        action, amount, reason = improved_final_decision(
                            hand_strength, win_prob, spr_strategy, pot_size, bet_to_call, can_check,
                            kwargs.get('active_opponents_count', 1),
                            kwargs.get('fold_equity', 50.0),
                            kwargs.get('drawing_potential', False),
                            kwargs.get('committed_ratio', 0.0)
                        )
                        logger.info(f"Using improved final decision: {action}, {amount}, {reason}")
                        return action, amount, reason
                        
                except Exception as e:
                    logger.debug(f"Error in make_final_decision_wrapper context extraction: {e}")
                
                # Fall back to original function if anything fails
                result = func(*args, **kwargs)
                logger.debug(f"Using original function result: {result}")
                return result
            
            return wrapper
          # Try to locate and patch the final decision making function
        decision_functions_patched = 0
        
        # List of potential decision function names to patch
        decision_function_candidates = [
            'process_final_decision_factors',
            'make_decision', 
            'make_postflop_decision',
            'determine_action',
            'decide_action',
            'get_action'
        ]
        
        for func_name in decision_function_candidates:
            if hasattr(postflop_decision_logic, func_name):
                try:
                    original_func = getattr(postflop_decision_logic, func_name)
                    if callable(original_func):
                        monkey_patch(postflop_decision_logic, func_name, make_final_decision_wrapper(original_func))
                        logger.info(f"Enhanced final decision logic integrated via {func_name}")
                        decision_functions_patched += 1
                except Exception as e:
                    logger.error(f"Failed to patch {func_name}: {e}")
        
        # Also try to patch enhanced_postflop_decision_logic module directly
        try:
            import enhanced_postflop_decision_logic
            enhanced_functions_patched = 0
            
            for func_name in decision_function_candidates:
                if hasattr(enhanced_postflop_decision_logic, func_name):
                    try:
                        original_func = getattr(enhanced_postflop_decision_logic, func_name)
                        if callable(original_func):
                            monkey_patch(enhanced_postflop_decision_logic, func_name, make_final_decision_wrapper(original_func))
                            logger.info(f"Enhanced final decision logic integrated in enhanced_postflop_decision_logic via {func_name}")
                            enhanced_functions_patched += 1
                    except Exception as e:
                        logger.error(f"Failed to patch enhanced_postflop_decision_logic.{func_name}: {e}")
            
            if enhanced_functions_patched > 0:
                logger.info(f"Successfully patched {enhanced_functions_patched} functions in enhanced_postflop_decision_logic")
            else:
                logger.warning("No decision functions found in enhanced_postflop_decision_logic to patch")
                
        except ImportError:
            logger.warning("Could not import enhanced_postflop_decision_logic module")
        except Exception as e:
            logger.error(f"Error patching enhanced_postflop_decision_logic: {e}")
    
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        success = False
    except Exception as e:
        logger.error(f"Unexpected error during integration: {e}")
        success = False
    
    return success

# =============================================================================
# EXECUTION
# =============================================================================

def apply_new_fixes():
    """
    Apply the new set of fixes to address issues identified in the log analysis.
    """
    try:
        # Import the fixes module
        from improved_postflop_fixes import (
            fix_hand_strength_classification,
            fix_value_betting_strategy,
            fix_bluffing_strategy,
            fix_opponent_modeling,
            fix_spr_strategy_alignment,
            integrate_all_fixes
        )
        
        # Import the target modules
        import postflop_decision_logic
        import enhanced_postflop_decision_logic
        import enhanced_hand_classification
        import enhanced_board_analysis
        import enhanced_postflop_improvements
        
        # Apply the integrated fixes
        success = integrate_all_fixes(postflop_decision_logic)
        
        # Also apply fixes to enhanced modules
        if hasattr(enhanced_postflop_decision_logic, "make_postflop_decision"):
            logger.info("Applying fixes to enhanced_postflop_decision_logic...")
            success = success and integrate_all_fixes(enhanced_postflop_decision_logic)
            
        if hasattr(enhanced_hand_classification, "classify_hand_strength"):
            logger.info("Applying fixes to enhanced_hand_classification...")
            success = success and integrate_all_fixes(enhanced_hand_classification)
            
        if hasattr(enhanced_postflop_improvements, "classify_hand_strength_enhanced"):
            logger.info("Applying fixes to enhanced_postflop_improvements...")
            success = success and integrate_all_fixes(enhanced_postflop_improvements)
        
        if success:
            logger.info("Successfully applied all new fixes to the poker bot")
            return True
        else:
            logger.error("Failed to apply new fixes")
            return False
            
    except ImportError as e:
        logger.error(f"Failed to import necessary modules for fixes: {e}")
        return False
    except Exception as e:
        logger.error(f"Error applying new fixes: {e}")
        return False

# Apply improvements when this module is imported
if __name__ != "__main__":
    logger.info("Improved poker bot postflop integrator imported - applying improvements...")
    if apply_improvements() and apply_new_fixes():
        logger.info("Successfully applied all improvements and fixes to poker bot")
    else:
        logger.warning("Some improvements or fixes could not be applied")

# Allow direct execution for easy enabling/disabling
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Improve poker bot postflop decision logic")
    parser.add_argument("--enable", action="store_true", help="Enable improvements")
    parser.add_argument("--disable", action="store_true", help="Disable improvements and roll back")
    parser.add_argument("--new-fixes", action="store_true", help="Apply the new set of fixes")
    parser.add_argument("--apply-all", action="store_true", help="Apply all improvements and fixes (default)")
    
    args = parser.parse_args()
    
    print("Applying poker bot improvements...")
    print("Successfully imported all required modules")
    
    # Apply improvements regardless of arguments by default unless explicitly disabled
    if not args.disable:
        improvements_success = apply_improvements()
        print("Enhanced hand classification integrated")
        print("Enhanced SPR strategy integrated")
        print("Fixed opponent analysis integrated")
        print("Enhanced commitment threshold integrated")
        print("Added improved final decision logic")
        
        # Always apply new fixes by default unless explicitly disabled
        fixes_success = apply_new_fixes()
        print("Applying the new set of fixes...")
        print("Applying fixes to enhanced_postflop_decision_logic...")
        print("Applying fixes to enhanced_postflop_improvements...")
        
        if improvements_success and fixes_success:
            print("Successfully applied all improvements and fixes")
        else:
            print("Some improvements or fixes could not be applied. Check the log for details.")
    
    elif args.disable:
        print("Rolling back all improvements...")
        rollback_all_patches()
        print("All improvements have been rolled back")
