# postflop_decision_logic.py

import logging
from implied_odds import should_call_with_draws # Ensure this import is present

# Setup debug logging first
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Import enhanced modules
try:
    from enhanced_hand_classification import classify_hand_strength_enhanced as classify_hand_strength_basic, get_standardized_pot_commitment_threshold
    from enhanced_bet_sizing import get_enhanced_bet_size, should_check_instead_of_bet
    from fixed_opponent_integration import get_fixed_opponent_analysis, get_opponent_exploitative_adjustments
    from enhanced_spr_strategy import get_spr_strategy_recommendation, should_commit_stack_spr, get_protection_needs_spr
    ENHANCED_MODULES_AVAILABLE = True
    logger.info("Enhanced postflop modules successfully imported")
except ImportError as e:
    logger.warning(f"Enhanced postflop modules not available: {e}")
    ENHANCED_MODULES_AVAILABLE = False

# Import advanced enhancement modules
try:
    from advanced_opponent_modeling import AdvancedOpponentAnalyzer
    from enhanced_board_analysis import EnhancedBoardAnalyzer
    from performance_monitoring import PerformanceMetrics
    ADVANCED_MODULES_AVAILABLE = True
    logger.info("Advanced enhancement modules successfully imported")
except ImportError as e:
    logger.warning(f"Advanced enhancement modules not available: {e}")
    ADVANCED_MODULES_AVAILABLE = False

# Import new postflop modules
from postflop.utils import is_drawing_hand
from postflop.bet_sizing import get_dynamic_bet_size
from postflop.opponent_analysis import estimate_opponent_range, calculate_fold_equity # analyze_opponents is in analysis_processing now
from postflop.strategy import is_thin_value_spot, should_call_bluff, calculate_spr_adjustments
from postflop.analysis_processing import (
    process_initial_enhanced_analysis,
    integrate_advanced_module_data,
    refine_hand_classification_and_commitment,
    consolidate_opponent_analysis,
    determine_final_decision_hand_strength
)


# Import functions that will be passed to analysis_processing
# These are conditionally imported here and passed to avoid circular dependencies
# or to manage their availability centrally.
_classify_hand_strength_basic_func = None
_get_standardized_pot_commitment_threshold_func = None
_get_fixed_opponent_analysis_func = None
_get_opponent_exploitative_adjustments_func = None
_get_spr_strategy_recommendation_func = None
_should_commit_stack_spr_func = None

if ENHANCED_MODULES_AVAILABLE:
    try:
        from enhanced_hand_classification import classify_hand_strength_enhanced as _classify_hand_strength_basic_func, \
                                               get_standardized_pot_commitment_threshold as _get_standardized_pot_commitment_threshold_func
        from fixed_opponent_integration import get_fixed_opponent_analysis as _get_fixed_opponent_analysis_func, \
                                             get_opponent_exploitative_adjustments as _get_opponent_exploitative_adjustments_func
        from enhanced_spr_strategy import get_spr_strategy_recommendation as _get_spr_strategy_recommendation_func, \
                                        should_commit_stack_spr as _should_commit_stack_spr_func
    except ImportError as e:
        logger.error(f"Failed to import one or more ENHANCED modules for passing: {e}")
        ENHANCED_MODULES_AVAILABLE = False # Downgrade if essential pass-throughs are missing


# Create file handler if it doesn't exist
if not logger.handlers:
    handler = logging.FileHandler('debug_postflop_decision_logic.log', mode='a', encoding='utf-8') # Added encoding='utf-8'
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Constants for hand strength (example values, adjust as needed)
# These might be defined elsewhere or passed as parameters
VERY_STRONG_HAND_THRESHOLD = 7  # e.g., Two Pair or better
STRONG_HAND_THRESHOLD = 4       # e.g., Top Pair or better
MEDIUM_HAND_THRESHOLD = 2       # e.g., Middle Pair or better

# Define action constants if not imported (assuming they are globally available or passed)
# ACTION_FOLD = "fold"
# ACTION_CHECK = "check"
# ACTION_CALL = "call"
# ACTION_BET = "bet"
# ACTION_RAISE = "raise"

# Functions previously here have been moved to the postflop directory


# Helper function for parsing stack values
def _parse_stack_value_for_postflop(stack_str: str) -> float:
    if isinstance(stack_str, (int, float)):
        return float(stack_str)
    if isinstance(stack_str, str):
        cleaned_str = stack_str.replace('€', '').replace('$', '').replace(',', '').strip()
        if not cleaned_str:
            return 0.0
        try:
            return float(cleaned_str)
        except ValueError:
            logger.warning(f"Could not parse stack value string: {stack_str}")
            return 0.0
    return 0.0


def make_postflop_decision(
    decision_engine_instance, 
    numerical_hand_rank, 
    hand_description,     
    bet_to_call,
    can_check,
    pot_size,
    my_stack,
    win_probability,       
    pot_odds_to_call,
    game_stage, # This is 'street'
    spr,
    action_fold_const,
    action_check_const,
    action_call_const,
    action_raise_const,
    my_player_data,
    big_blind_amount,
    base_aggression_factor,
    max_bet_on_table, # Added this parameter
    active_opponents_count=1, # Add opponent count for multiway considerations
    opponent_tracker=None,  # Add opponent tracking data
    all_players_raw_data=None # New parameter for all players' data from parser
):
    street = game_stage # Use game_stage as street    
    logger.debug(
        f"make_postflop_decision: street={street}, my_player_data={my_player_data}, "
        f"pot_size={pot_size}, win_prob={win_probability}, pot_odds={pot_odds_to_call}, "
        f"bet_to_call={bet_to_call}, max_bet_on_table={max_bet_on_table}, "
        f"active_opponents_count={active_opponents_count}, can_check={can_check}"
    )
    
    # Calculate pot commitment variables first
    committed_amount = my_player_data.get('current_bet', 0)
    total_commitment_if_call = committed_amount + bet_to_call
    pot_commitment_ratio = total_commitment_if_call / (my_stack + total_commitment_if_call) if (my_stack + total_commitment_if_call) > 0 else 0
    
    position = my_player_data.get('position', 'BB')
    community_cards = my_player_data.get('community_cards', [])

    # Determine opponent stack for implied odds
    opponent_stacks_for_implied_odds = []
    if all_players_raw_data:
        my_player_name_from_data = my_player_data.get('name')
        for p_data in all_players_raw_data:
            is_opponent = True
            # Check if it's my player by name or by a specific flag if parser sets it
            if my_player_name_from_data and p_data.get('name') == my_player_name_from_data:
                is_opponent = False
            elif p_data.get('is_my_player'): # Assuming parser might set 'is_my_player'
                is_opponent = False
            
            if is_opponent and not p_data.get('is_empty', False) and p_data.get('stack') and p_data.get('stack') != 'N/A':
                stack_val = _parse_stack_value_for_postflop(p_data.get('stack'))
                if stack_val > 0: # Consider only opponents with a positive stack
                    opponent_stacks_for_implied_odds.append(stack_val)

    estimated_opponent_stack_for_implied_odds = my_stack # Default to my_stack
    if opponent_stacks_for_implied_odds:
        if active_opponents_count == 1 and len(opponent_stacks_for_implied_odds) == 1:
            estimated_opponent_stack_for_implied_odds = opponent_stacks_for_implied_odds[0]
        else: # Multiple opponents or if counts mismatch, use the smallest stack.
            estimated_opponent_stack_for_implied_odds = min(opponent_stacks_for_implied_odds)
    else:
        logger.info("No opponent stacks found/parsed for implied odds; using my_stack as fallback.")
    logger.debug(f"Estimated opponent stack for implied odds: {estimated_opponent_stack_for_implied_odds}")

    # 1. INITIAL ENHANCED ANALYSIS (Hand Strength, Basic Opponent, SPR)
    initial_analysis_result = process_initial_enhanced_analysis(
        numerical_hand_rank, win_probability, street, opponent_tracker, active_opponents_count,
        spr, position, pot_commitment_ratio, ENHANCED_MODULES_AVAILABLE,
        _classify_hand_strength_basic_func, _get_standardized_pot_commitment_threshold_func,
        _get_fixed_opponent_analysis_func, _get_opponent_exploitative_adjustments_func,
        _get_spr_strategy_recommendation_func, _should_commit_stack_spr_func,
        logger # Pass logger instance
    )
    hand_strength = initial_analysis_result["hand_strength"]
    # hand_details = initial_analysis_result["hand_details"] # If needed
    commitment_threshold = initial_analysis_result["commitment_threshold"]
    opponent_analysis_from_initial = initial_analysis_result["opponent_analysis"] # Used as input for advanced
    # exploitative_adjustments = initial_analysis_result["exploitative_adjustments"] # If needed
    spr_strategy = initial_analysis_result["spr_strategy"]
    # should_commit = initial_analysis_result["should_commit"] # If needed directly
    # commit_reason = initial_analysis_result["commit_reason"] # If needed
    is_pot_committed_initial = initial_analysis_result["is_pot_committed"]

    logger.debug(f"Initial Pot commitment: committed={committed_amount:.2f}, call={bet_to_call:.2f}, "
                f"total={total_commitment_if_call:.2f}, stack={my_stack:.2f}, "
                f"ratio={pot_commitment_ratio:.1%}, threshold={commitment_threshold:.1%}, "
                f"is_committed={is_pot_committed_initial}")

    # 2. ADVANCED MODULES INTEGRATION
    advanced_integration_result = integrate_advanced_module_data(
        win_probability, community_cards, ADVANCED_MODULES_AVAILABLE, opponent_tracker, my_player_data,
        bet_to_call, pot_size, my_stack, big_blind_amount, active_opponents_count, pot_odds_to_call,
        street, numerical_hand_rank, position, opponent_analysis_from_initial, # Pass initial opponent analysis
        logger # Pass logger instance
    )
    advanced_context = advanced_integration_result["advanced_context"]
    # hand_strength_from_advanced = advanced_integration_result["hand_strength_from_advanced"] # If needed
    board_texture = advanced_integration_result["board_texture_from_advanced"] # Updated board texture

    # 3. REFINE HAND CLASSIFICATION AND COMMITMENT (using enhanced_postflop_improvements)
    refined_classification_result = refine_hand_classification_and_commitment(
        numerical_hand_rank, win_probability, hand_description, street, spr,
        VERY_STRONG_HAND_THRESHOLD, STRONG_HAND_THRESHOLD, MEDIUM_HAND_THRESHOLD,
        logger # Pass logger instance
    )
    # hand_strength_refined = refined_classification_result["hand_strength_refined"] # If needed directly
    is_very_strong_refined = refined_classification_result["is_very_strong_refined"]
    is_strong_refined = refined_classification_result["is_strong_refined"]
    is_medium_refined = refined_classification_result["is_medium_refined"]
    # is_weak_refined = refined_classification_result["is_weak_refined"] # If needed
    commitment_threshold_refined = refined_classification_result["commitment_threshold_refined"]

    is_pot_committed = pot_commitment_ratio >= commitment_threshold_refined # Use refined threshold
    logger.debug(
        f"Refined Pot commitment check: ratio={pot_commitment_ratio:.2%}, refined_threshold={commitment_threshold_refined:.2%}, "
        f"is_pot_committed={is_pot_committed}"
    )

    # 4. CONSOLIDATE OPPONENT ANALYSIS
    consolidated_opponent_result = consolidate_opponent_analysis(
        opponent_tracker, active_opponents_count, ENHANCED_MODULES_AVAILABLE,
        _get_fixed_opponent_analysis_func, # Pass the specific function for fallback
        logger # Pass logger instance
    )
    final_opponent_analysis = consolidated_opponent_result["final_opponent_analysis"]
    opponent_analysis_source = consolidated_opponent_result["opponent_analysis_source"]
    
    opponent_context = {'current_analysis': final_opponent_analysis, 'source': opponent_analysis_source}
    # estimated_opponent_range = final_opponent_analysis.get('table_type', 'unknown') # Example usage
    # fold_equity_estimate = final_opponent_analysis.get('fold_equity_estimate', 0.5) # Example usage

    # 5. DETERMINE FINAL DECISION HAND STRENGTH (with one-pair adjustments etc.)
    final_strength_result = determine_final_decision_hand_strength(
        is_very_strong_refined, is_strong_refined, is_medium_refined, # From refined classification
        numerical_hand_rank, win_probability, street,
        is_drawing_hand, # Pass the utility function
        logger # Pass logger instance
    )
    hand_strength_final_decision = final_strength_result["hand_strength_final_decision"]
    is_weak_final = final_strength_result["is_weak_final"]
    is_very_strong = final_strength_result["is_very_strong_final"]
    is_strong = final_strength_result["is_strong_final"]
    is_medium = final_strength_result["is_medium_final"]

    # Update local hand strength related booleans based on final determination for subsequent logic
    # is_very_strong, is_strong, is_medium, is_weak are now set based on final_strength_result

    # Calculate SPR adjustments for strategy using the final hand strength category
    # Note: calculate_spr_adjustments expects numerical_hand_rank, but our hand_strength_final_decision is a string.
    # We might need to adapt calculate_spr_adjustments or pass numerical_hand_rank if it's more appropriate.
    # For now, assuming calculate_spr_adjustments can work with numerical_hand_rank or we adapt its call.
    # The original call used numerical_hand_rank for the second param of calculate_spr_adjustments.
    # Let's keep that, but also consider hand_strength_final_decision for its logic if needed.
    drawing_potential = is_drawing_hand(win_probability, numerical_hand_rank, street)
    # The spr_strategy from initial_analysis_result might be sufficient, or we might re-calculate
    # if hand_strength_final_decision significantly changes the context for SPR.
    # For now, we use the initially calculated spr_strategy but log the final hand strength.
    logger.debug(f"SPR analysis context: spr={spr:.2f}, initial_spr_strategy={spr_strategy}, drawing_potential={drawing_potential}, final_hand_strength_for_decision={hand_strength_final_decision}")

    # Decision logic starts here, using the processed and consolidated data
    # (is_pot_committed, hand_strength_final_decision, is_weak_final, final_opponent_analysis, advanced_context etc.)

    # If can_check is True but there's a bet_to_call, it means the "check" button
    # likely acts as a "call" button. In this scenario, we are effectively facing a bet.
    # Genuine check is only possible if can_check is True AND bet_to_call is 0.
    effectively_can_genuinely_check = can_check and (bet_to_call == 0)

    if effectively_can_genuinely_check:
        logger.debug("Option to genuinely check is available (can_check=True, bet_to_call=0). Evaluating check vs. bet/raise.")
        # This is the block for when we can truly check (action is on us, no prior bet in this round)
        
        if is_very_strong:
            # Check if we should check instead of bet (e.g., for trapping or if board is scary)
            if ENHANCED_MODULES_AVAILABLE and should_check_instead_of_bet(hand_strength_final_decision, win_probability, pot_size, active_opponents_count, position, street): # Corrected arguments
                logger.info(f"Decision: {action_check_const} (Very strong hand, checking to trap or due to board)")
                return action_check_const, 0
            else:
                bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count)
                logger.info(f"Decision: {action_raise_const} {bet_amount} (Very strong hand, value bet)")
                return action_raise_const, bet_amount
        
        elif is_strong:
            if ENHANCED_MODULES_AVAILABLE and should_check_instead_of_bet(hand_strength_final_decision, win_probability, pot_size, active_opponents_count, position, street): # Corrected arguments
                logger.info(f"Decision: {action_check_const} (Strong hand, checking for pot control or board texture)")
                return action_check_const, 0
            else:
                bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count)
                logger.info(f"Decision: {action_raise_const} {bet_amount} (Strong hand, value bet)")
                return action_raise_const, bet_amount

        elif is_medium:
            if is_thin_value_spot(hand_strength_final_decision, win_probability, final_opponent_analysis.get('table_type', 'unknown'), position):
                bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff=False) / 2 # Smaller for thin value
                bet_amount = max(bet_amount, big_blind_amount) # Ensure min bet
                logger.info(f"Decision: {action_raise_const} {bet_amount} (Medium hand, thin value bet)")
                return action_raise_const, bet_amount
            else:
                logger.info(f"Decision: {action_check_const} (Medium hand, pot control or check-evaluate)")
                return action_check_const, 0

        else: # is_weak_final is true
            if hand_strength_final_decision == 'drawing':
                logger.info(f"Decision: {action_check_const} (Drawing hand, checking to see next card)")
                return action_check_const, 0
            elif hand_strength_final_decision == 'weak_made':
                fold_equity = calculate_fold_equity(final_opponent_analysis.get('table_type', 'unknown'), board_texture, pot_size * 0.5, pot_size)
                if fold_equity > 0.6: 
                    bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff=True)
                    logger.info(f"Decision: {action_raise_const} {bet_amount} (Weak made hand, bluffing with high fold equity)")
                    return action_raise_const, bet_amount
                else:
                    logger.info(f"Decision: {action_check_const} (Weak made hand, checking, low fold equity for bluff)")
                    return action_check_const, 0
            else: # very_weak
                logger.info(f"Decision: {action_check_const} (Very weak hand, check-fold strategy likely)")
                return action_check_const, 0
            
    else: # This means (bet_to_call > 0) OR (not can_check originally)
        if bet_to_call > 0:
            logger.debug(f"Facing a bet of {bet_to_call} (can_check was {can_check}). Evaluating call, raise, or fold.")
        else: # implies can_check was False and bet_to_call is 0
            logger.debug(f"Cannot check (can_check=False, bet_to_call=0). Evaluating options.")
        
        min_raise = max_bet_on_table * 2 # Simplified min raise logic
        
        if is_very_strong:
            # Value raise, consider stack commitment based on SPR
            if ENHANCED_MODULES_AVAILABLE and spr_strategy.get('base_strategy') == 'commit' or is_pot_committed:
                bet_amount = my_stack # All-in
                logger.info(f"Decision: {action_raise_const} {bet_amount} (Very strong hand, committing stack, SPR={spr:.1f})")
            else:
                bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count)
                bet_amount = max(bet_amount, min_raise) 
                logger.info(f"Decision: {action_raise_const} {bet_amount} (Very strong hand, value raise)")
            return action_raise_const, min(bet_amount, my_stack)

        elif is_strong:
            # Value raise or call depending on aggression and opponent.
            if pot_odds_to_call > (1 - win_probability) / win_probability if win_probability > 0 else float('inf'): 
                # Consider raising if opponent is passive or we want to build pot
                if base_aggression_factor > 0.6 or final_opponent_analysis.get('table_type', '').startswith('passive'):
                    bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count)
                    bet_amount = max(bet_amount, min_raise)
                    logger.info(f"Decision: {action_raise_const} {bet_amount} (Strong hand, raising against bet)")
                    return action_raise_const, min(bet_amount, my_stack)
                else:
                    logger.info(f"Decision: {action_call_const} {bet_to_call} (Strong hand, calling bet, good odds)")
                    return action_call_const, bet_to_call
            else:
                logger.info(f"Decision: {action_fold_const} (Strong hand, folding, bad pot odds: {pot_odds_to_call:.2f} vs req: {(1-win_probability)/win_probability if win_probability > 0 else float('inf'):.2f})")
                return action_fold_const, 0

        elif is_medium:
            # Call if odds are good, consider folding if bet is large or SPR is awkward.
            # Using the determined estimated_opponent_stack_for_implied_odds
            if should_call_with_draws(my_player_data.get('hand', []), community_cards, win_probability, pot_size, bet_to_call, estimated_opponent_stack_for_implied_odds, my_stack, street):
                 logger.info(f"Decision: {action_call_const} {bet_to_call} (Medium hand/draw, calling with implied odds)")
                 return action_call_const, bet_to_call
            elif pot_odds_to_call > (1 - win_probability) / win_probability if win_probability > 0 else float('inf'):
                logger.info(f"Decision: {action_call_const} {bet_to_call} (Medium hand, calling with direct pot odds)")
                return action_call_const, bet_to_call
            else:
                # Consider bluff raising if opponent folds a lot and bet is small
                if should_call_bluff(hand_strength_final_decision, win_probability, pot_odds_to_call, final_opponent_analysis.get('table_type', 'unknown'), bet_to_call, pot_size):
                     # This function name is misleading here, it's more about should_semi_bluff_raise
                     # For now, let's assume it means we have a good spot to turn hand into bluff raise
                    bluff_raise_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff=True)
                    bluff_raise_amount = max(bluff_raise_amount, min_raise)
                    logger.info(f"Decision: {action_raise_const} {bluff_raise_amount} (Medium hand, bluff-raising based on opponent)")
                    return action_raise_const, min(bluff_raise_amount, my_stack)
                
                logger.info(f"Decision: {action_fold_const} (Medium hand, folding, insufficient odds)")
                return action_fold_const, 0

        else: # is_weak_final is true
            if hand_strength_final_decision == 'drawing':
                # Using the determined estimated_opponent_stack_for_implied_odds
                if should_call_with_draws(my_player_data.get('hand', []), community_cards, win_probability, pot_size, bet_to_call, estimated_opponent_stack_for_implied_odds, my_stack, street):
                    logger.info(f"Decision: {action_call_const} {bet_to_call} (Drawing hand, calling with implied odds)")
                    return action_call_const, bet_to_call
                else:
                    logger.info(f"Decision: {action_fold_const} (Drawing hand, folding, no odds)")
                    return action_fold_const, 0
            elif hand_strength_final_decision == 'weak_made':
                if should_call_bluff(hand_strength_final_decision, win_probability, pot_odds_to_call, final_opponent_analysis.get('table_type', 'unknown'), bet_to_call, pot_size):
                    logger.info(f"Decision: {action_call_const} {bet_to_call} (Weak made hand, calling as bluff catcher)")
                    return action_call_const, bet_to_call
                else:
                    logger.info(f"Decision: {action_fold_const} (Weak made hand, folding)")
                    return action_fold_const, 0
            else: # very_weak
                logger.info(f"Decision: {action_fold_const} (Very weak hand, folding to bet)")
                return action_fold_const, 0

    # Fallback, should not be reached if logic is complete
    logger.error("Fell through all decision logic in postflop. Defaulting to FOLD.")
    return action_fold_const, 0

# Functions previously here have been moved to the postflop directory
