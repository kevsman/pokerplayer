# postflop_decision_logic.py

import logging
from implied_odds import should_call_with_draws # Ensure this import is present
from opponent_persistence import save_opponent_analysis, load_opponent_analysis

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
            logger.error(f"Could not parse stack value: {stack_str}")
            return 0.0
    return 0.0

# Define make_postflop_decision function
def make_postflop_decision(
    decision_engine_instance, numerical_hand_rank, hand_description,
    bet_to_call, can_check, pot_size, my_stack, win_probability,
    pot_odds_to_call, game_stage, spr,
    action_fold_const, action_check_const, action_call_const, action_raise_const,
    my_player_data, all_players_raw_data, big_blind_amount, base_aggression_factor,
    max_bet_on_table, active_opponents_count, opponent_tracker,
    was_preflop_aggressor=False, action_history=None, aggression_history=None,
    preflop_category=None # <-- NEW ARGUMENT
):
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[DEBUG] make_postflop_decision: opponent_tracker type={type(opponent_tracker)}, id={id(opponent_tracker) if opponent_tracker is not None else 'None'}")
    # Removed the problematic load_all_profiles() call that was overwriting progress
    
    # --- Opponent analysis integration (latest range/FE) ---
    from postflop.opponent_analysis import estimate_opponent_range, calculate_fold_equity
    position = my_player_data.get('position', 'BB')
    preflop_action = 'raise' if (action_history and 'preflop' in action_history and 'raise' in action_history['preflop']) else 'call'
    board_texture = my_player_data.get('board_texture', 'unknown')
    street = game_stage
    opp_range = estimate_opponent_range(position, preflop_action, bet_to_call, pot_size, street, board_texture)
    fold_equity = calculate_fold_equity(opp_range, board_texture, bet_to_call, pot_size)
    # Use opp_range and fold_equity in decision logic below as needed
    # Example: If fold_equity is high, increase bluff frequency; if opp_range is strong, tighten value betting

    logger.debug(
        f"make_postflop_decision: street={street}, my_player_data={my_player_data}, "
        f"pot_size={pot_size}, win_prob={win_probability}, pot_odds={pot_odds_to_call}, "
        f"bet_to_call={bet_to_call}, max_bet_on_table={max_bet_on_table}, "
        f"active_opponents_count={active_opponents_count}, can_check={can_check}, "
        f"was_preflop_aggressor={was_preflop_aggressor}, action_history={action_history}"
    )
    
    # We'll set this flag even if it was passed in, for backward compatibility
    was_pfr = was_preflop_aggressor
    if action_history and 'preflop' in action_history and 'raise' in action_history['preflop']:
        was_pfr = True
    
    # Check if we were the aggressor on the previous street
    was_aggressor_previous_street = False
    previous_street = None
    
    if street == 'flop':
        previous_street = 'preflop'
    elif street == 'turn':
        previous_street = 'flop'
    elif street == 'river':
        previous_street = 'turn'
    
    if aggression_history and previous_street in aggression_history:
        was_aggressor_previous_street = aggression_history[previous_street]
    
    logger.info(f"Hand history context: was_pfr={was_pfr}, was_aggressor_previous_street={was_aggressor_previous_street}")
    
    # Adjust strategy based on hand history
    aggression_multiplier = 1.0
    if was_pfr:
        # More aggressive if we were the preflop raiser
        aggression_multiplier *= 1.2
    if was_aggressor_previous_street:
        # More aggressive if we were the aggressor on the previous street
        aggression_multiplier *= 1.1
    
    # Log the aggression multiplier
    logger.info(f"Using aggression_multiplier={aggression_multiplier} based on hand history")

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

    # --- Board Texture Awareness & Hand Strength Re-Evaluation (Improvements 1, 3, 4) ---
    board_danger_level = assess_board_danger(community_cards)
    logger.info(f"Board danger level: {board_danger_level}/10")
    # Use EnhancedBoardAnalyzer to check for dangerous board textures (e.g., 4+ of the same suit)
    try:
        from enhanced_board_analysis import EnhancedBoardAnalyzer
        board_analyzer = EnhancedBoardAnalyzer()
        board_analysis = board_analyzer.analyze_board(community_cards)
        suits = [card[-1] for card in community_cards if len(card) >= 2]
        suit_counts = {s: suits.count(s) for s in set(suits)}
        max_suit_count = max(suit_counts.values()) if suit_counts else 0
        has_four_flush = max_suit_count >= 4
        my_hand = my_player_data.get('hand', [])
        my_suit_cards = [card for card in my_hand if len(card) >= 2 and card[-1] == max(suit_counts, key=suit_counts.get, default=None)]
        has_nut_flush = False
        # Simple nut flush check: holding the highest card of the suit on a 4-flush board
        if has_four_flush and my_suit_cards:
            board_ranks = [card[:-1] for card in community_cards if card[-1] == my_suit_cards[0][-1]]
            my_ranks = [card[:-1] for card in my_suit_cards]
            all_ranks = board_ranks + my_ranks
            # If we have the Ace of the suit, we have the nut flush
            has_nut_flush = any(card.startswith('A') and card[-1] == my_suit_cards[0][-1] for card in my_hand)
        # If board is very wet (4+ of a suit) and we do NOT have a flush, or only have trips, downgrade hand strength
        if has_four_flush and not has_nut_flush:
            # If our best hand is trips or worse, or our flush is not the nut flush, be very conservative
            if hand_strength_final_decision in ['very_strong', 'strong', 'medium']:
                # If we do not have a flush, or our flush is not the nut flush, treat as weak
                if not my_suit_cards or not has_nut_flush:
                    logger.info("Board has 4+ of a suit and we do not have the nut flush. Downgrading hand strength for safety.")
                    hand_strength_final_decision = 'weak_made'
                    is_weak_final = True
                    is_very_strong = False
                    is_strong = False
                    is_medium = False
        # If facing a large bet/raise on a very wet board and we do not have the nut flush, prefer folding
        if has_four_flush and bet_to_call > 0 and not has_nut_flush:
            bet_ratio = bet_to_call / pot_size if pot_size > 0 else 0
            if bet_ratio > 0.5:
                logger.info(f"Facing a large bet ({bet_to_call:.2f}) on a 4-flush board without the nut flush. Folding for safety.")
                return action_fold_const, 0
        # Use board_analysis for bet sizing and protection logic
        wetness_score = board_analysis.get('wetness_score', 5)
        betting_implications = board_analysis.get('betting_implications', {})
        # Adjust bet sizing for strong/very strong hands on wet boards
        if (is_very_strong or is_strong) and wetness_score >= 6:
            # Bet larger for protection
            bet_size_factor = 1.2
        elif (is_very_strong or is_strong) and wetness_score <= 2:
            # Bet smaller for thin value
            bet_size_factor = 0.8
        else:
            bet_size_factor = 1.0
        # Attach bet_size_factor to my_player_data for use in bet sizing calls
        my_player_data['bet_size_factor'] = bet_size_factor
        # If board is dry and betting_implications suggest thin value, allow more thin value bets with medium hands
        allow_thin_value = False
        if is_medium and betting_implications.get('value_betting') == 'thin_value_possible':
            allow_thin_value = True
        my_player_data['allow_thin_value'] = allow_thin_value
    except Exception as e:
        logger.warning(f"Enhanced board texture awareness failed: {e}")

    # === Advanced Post-Flop Strategy Integration ===
    # 1. Blocker Effects: Use blockers to influence bluff/value bet frequency
    blocker_effect = has_blocker_effects(my_player_data.get('hand', []), community_cards, target_ranks=['A', 'K', 'Q'])
    # 2. Range Merging/Polarization: Adjust value/bluff mix
    range_strategy = should_merge_or_polarize_range(final_opponent_analysis.get('table_type', 'unknown'), board_texture)
    # 3. Overbetting/Underbetting: Suggest non-standard bet sizes
    overbet_suggestion = should_overbet_or_underbet(street, hand_strength_final_decision, board_texture, nut_advantage=True)
    # 4. Multi-Street Planning: Double-barrel bluff logic
    double_barrel = should_double_barrel_bluff(board_texture, (action_history.get('flop', '') if action_history else ''), final_opponent_analysis.get('table_type', 'unknown'))
    # 5. Delayed C-Betting: Delayed c-bet logic
    delay_cbet = should_delay_cbet(street, (action_history.get('flop', '') if action_history else ''), board_texture, final_opponent_analysis.get('table_type', 'unknown'))
    # 6. Inducing Bluffs: Check to induce bluff
    induce_bluff = should_induce_bluff(final_opponent_analysis.get('table_type', 'unknown'), hand_strength_final_decision, street, action_history)
    # 7. River Overbluffing: Overbluff river in specific scenarios
    river_bluff = should_river_overbluff(final_opponent_analysis.get('table_type', 'unknown'), (action_history.get('river', []) if action_history else []))
    # 8. Multiway Pot Adjustments: Pot control in multiway pots
    multiway_adjustment = adjust_for_multiway_pot(active_opponents_count, hand_strength_final_decision)

    # === Use advanced strategies to adjust decisions ===

    # Delayed C-Betting Logic
    if delay_cbet and street == 'flop' and was_pfr and effectively_can_genuinely_check:
        logger.info(f"Decision: {action_check_const} (Delayed c-bet suggested by advanced strategy)")
        return action_check_const, 0

    # Double-Barrel Bluff Logic
    if double_barrel and street == 'turn' and was_pfr and is_weak_final:
        # Bluffing with a double barrel. Bet size can be around 2/3 pot.
        bluff_amount = min(my_stack, pot_size * 0.67)
        logger.info(f"Decision: {action_raise_const} {bluff_amount} (Double-barrel bluff suggested by advanced strategy)")
        return action_raise_const, bluff_amount

    # Induce Bluff Logic
    if induce_bluff and effectively_can_genuinely_check and (is_medium or is_strong):
        logger.info(f"Decision: {action_check_const} (Checking to induce a bluff with a medium/strong hand)")
        return action_check_const, 0

    # River Overbluffing Logic
    if river_bluff and street == 'river' and is_weak_final:
        # Overbluffing the river. Bet size can be large, like pot size.
        bluff_amount = min(my_stack, pot_size)
        logger.info(f"Decision: {action_raise_const} {bluff_amount} (River overbluff suggested by advanced strategy)")
        return action_raise_const, bluff_amount

    # Example: Overbetting/Underbetting
    if overbet_suggestion == 'overbet' and not effectively_can_genuinely_check and is_very_strong:
        overbet_amount = min(my_stack, pot_size * 1.5)
        logger.info(f"Decision: {action_raise_const} {overbet_amount} (Overbet suggested by advanced strategy)")
        return action_raise_const, overbet_amount
    if overbet_suggestion == 'underbet' and effectively_can_genuinely_check and is_medium:
        underbet_amount = max(big_blind_amount, pot_size * 0.25)
        logger.info(f"Decision: {action_raise_const} {underbet_amount} (Underbet suggested by advanced strategy)")
        return action_raise_const, underbet_amount

    # Example: Range merging/polarization
    if range_strategy == 'merge' and is_medium and effectively_can_genuinely_check:
        merge_bet = max(big_blind_amount, pot_size * 0.33)
        logger.info(f"Decision: {action_raise_const} {merge_bet} (Range merge: betting more medium hands for value)")
        return action_raise_const, merge_bet
    if range_strategy == 'polarize' and is_weak_final and not effectively_can_genuinely_check:
        # Only bluff with blockers
        if blocker_effect:
            polarize_bluff = max(big_blind_amount, pot_size * 0.75)
            logger.info(f"Decision: {action_raise_const} {polarize_bluff} (Polarized bluff with blocker effect)")
            return action_raise_const, polarize_bluff

    # Example: Multiway pot adjustment
    if multiway_adjustment == 'pot_control' and is_medium and effectively_can_genuinely_check:
        logger.info(f"Decision: {action_check_const} (Pot control in multiway pot with medium hand)")
        return action_check_const, 0

    # Example: Double-barrel bluff
    if double_barrel and is_weak_final and not effectively_can_genuinely_check:
        double_barrel_amount = max(big_blind_amount, pot_size * 0.7)
        logger.info(f"Decision: {action_raise_const} {double_barrel_amount} (Double-barrel bluff suggested)")
        return action_raise_const, double_barrel_amount

    # Example: Delayed c-bet
    if delay_cbet and is_strong and effectively_can_genuinely_check:
        delayed_cbet_amount = max(big_blind_amount, pot_size * 0.5)
        logger.info(f"Decision: {action_raise_const} {delayed_cbet_amount} (Delayed c-bet suggested)")
        return action_raise_const, delayed_cbet_amount

    # Example: Induce bluff
    if induce_bluff and is_strong and effectively_can_genuinely_check:
        logger.info(f"Decision: {action_check_const} (Checking to induce bluff from aggressive opponent)")
        return action_check_const, 0

    # Example: River overbluff
    if river_bluff and is_weak_final and not effectively_can_genuinely_check and street == 'river':
        river_bluff_amount = max(big_blind_amount, pot_size * 0.9)
        logger.info(f"Decision: {action_raise_const} {river_bluff_amount} (River overbluff suggested)")
        return action_raise_const, river_bluff_amount

    if can_check and (bet_to_call == 0):
        logger.debug("Option to genuinely check is available (can_check=True, bet_to_call=0). Evaluating check vs. bet/raise.")
        # This is the block for when we can truly check (action is on us, no prior bet in this round)
        
        if is_very_strong:
            # NEW: Board danger check
            if board_danger_level >= 7:
                logger.warning(f"Very strong hand, but board is dangerous (level: {board_danger_level}). Checking cautiously.")
                logger.info(f"Decision: {action_check_const} (Very strong hand, but checking due to dangerous board)")
                return action_check_const, 0
            # Check if we should check instead of bet (e.g., for trapping or if board is scary)
            if ENHANCED_MODULES_AVAILABLE: # Check if enhanced modules are available
                should_check_flag, check_reason = should_check_instead_of_bet(hand_strength_final_decision, win_probability, pot_size, active_opponents_count, position, street)
                if should_check_flag:
                    logger.info(f"Decision: {action_check_const} (Very strong hand, checking because: {check_reason})")
                    return action_check_const, 0
            # Fallback or if not checking for trap
            bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count)
            bet_amount *= my_player_data.get('bet_size_factor', 1.0)  # Apply bet size factor
            logger.info(f"Decision: {action_raise_const} {bet_amount} (Very strong hand, value bet)")
            return action_raise_const, bet_amount        
        elif is_strong:
            # NEW: Board danger check
            if board_danger_level >= 5:
                logger.warning(f"Strong hand, but board is dangerous (level: {board_danger_level}). Checking cautiously.")
                logger.info(f"Decision: {action_check_const} (Strong hand, but checking due to dangerous board)")
                return action_check_const, 0
            if ENHANCED_MODULES_AVAILABLE: # Check if enhanced modules are available
                should_check_flag, check_reason = should_check_instead_of_bet(hand_strength_final_decision, win_probability, pot_size, active_opponents_count, position, street)
                if should_check_flag:
                    logger.info(f"Decision: {action_check_const} (Strong hand, checking because: {check_reason})")
                    return action_check_const, 0
            # Fallback or if not checking for specific reason
            bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count)
            bet_amount *= my_player_data.get('bet_size_factor', 1.0)  # Apply bet size factor
            logger.info(f"Decision: {action_raise_const} {bet_amount} (Strong hand, value bet)")
            return action_raise_const, bet_amount
            
        elif is_medium:
            # NEW: Board danger check
            if board_danger_level >= 4:
                logger.warning(f"Medium hand, but board is dangerous (level: {board_danger_level}). Checking to be safe.")
                logger.info(f"Decision: {action_check_const} (Medium hand, checking due to potentially dangerous board)")
                return action_check_const, 0
            can_cbet_medium = False
            bet_purpose_detail = "thin value bet" # Default purpose
            bet_factor = 0.65 # Increased from 0.5 - more aggressive thin value bets

            if was_pfr:
                # Much more liberal c-betting conditions for PFR with medium strength
                if win_probability > 0.40 and active_opponents_count <= 3: # Looser thresholds (was 0.45 and <= 2)
                    can_cbet_medium = True
                    bet_purpose_detail = "c-bet with medium strength"
                    bet_factor = 0.75 # Larger c-bet (was 0.6)
                    logger.info(f"Medium hand, PFR: Considering more aggressive c-bet. Win prob: {win_probability:.2f}, Opps: {active_opponents_count}")

            # Check original thin value spot condition OR new PFR c-bet condition
            if can_cbet_medium or is_thin_value_spot(hand_strength_final_decision, win_probability, final_opponent_analysis.get('table_type', 'unknown'), position):
                if can_cbet_medium and not is_thin_value_spot(hand_strength_final_decision, win_probability, final_opponent_analysis.get('table_type', 'unknown'), position):
                    # This ensures the log reflects the PFR c-bet if that's the primary driver
                    bet_purpose_detail = "c-bet with medium strength (PFR)"
                    bet_factor = 0.6 
                elif is_thin_value_spot(hand_strength_final_decision, win_probability, final_opponent_analysis.get('table_type', 'unknown'), position) and not can_cbet_medium:                     # Original thin value spot, not PFR driven or PFR conditions not met but thin value spot is.
                     bet_purpose_detail = "thin value bet"
                     bet_factor = 0.5
                
                bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff=False) * bet_factor
                bet_amount = max(bet_amount, big_blind_amount) # Ensure min bet
                logger.info(f"Decision: {action_raise_const} {bet_amount:.2f} (Medium hand, {bet_purpose_detail})")
                return action_raise_const, bet_amount
            else:
                # If not betting, consider if specific check conditions apply
                if ENHANCED_MODULES_AVAILABLE:
                    should_check_flag, check_reason = should_check_instead_of_bet(hand_strength_final_decision, win_probability, pot_size, active_opponents_count, position, street)
                    if should_check_flag:
                        logger.info(f"Decision: {action_check_const} (Medium hand, {('PFR but ' if was_pfr else '')}checking because: {check_reason})")
                        return action_check_const, 0
                logger.info(f"Decision: {action_check_const} (Medium hand, {('PFR ' if was_pfr else '')}choosing to check-evaluate or pot control)")
                return action_check_const, 0
                
        else: # is_weak_final is true
            if hand_strength_final_decision == 'drawing':
                # More aggressive approach with drawing hands
                
                # Factor in position more heavily for drawing hands
                position_is_favorable = position in ['BTN', 'CO', 'MP'] 
                
                # Check if we're the preflop aggressor OR in favorable position
                if was_pfr or position_is_favorable:
                    can_semi_bluff = False
                    
                    # Much looser conditions for semi-bluffing with draws:
                    # Lower equity needed (20% vs 25%), can bluff against more opponents (3 vs 2),
                    # and lower fold equity required (30% vs 35%)
                    if win_probability > 0.20 and active_opponents_count <= 3:
                        # Calculate fold equity based on a 0.65 pot bet (more aggressive)
                        fold_equity_for_draw_bluff = calculate_fold_equity(
                            final_opponent_analysis.get('table_type', 'unknown'), 
                            board_texture, 
                            pot_size * 0.65, 
                            pot_size
                        )
                        
                        if fold_equity_for_draw_bluff > 0.30:
                            can_semi_bluff = True
                            logger.info(f"Drawing hand: More aggressive semi-bluff. Win prob: {win_probability:.2f}, " +
                                       f"Fold equity: {fold_equity_for_draw_bluff:.2f}, Opps: {active_opponents_count}")

                    if can_semi_bluff:
                        # More aggressive bet sizing for semi-bluffs (0.65-0.80 pot instead of 0.5)
                        bet_size_factor = 1.2 if position_is_favorable else 1.0  # Bet bigger in position
                        bet_amount = get_dynamic_bet_size(
                            numerical_hand_rank, 
                            pot_size, 
                            my_stack, 
                            street, 
                            big_blind_amount, 
                            active_opponents_count, 
                            bluff=True
                        ) * bet_size_factor
                        
                        bet_description = "PFR semi-bluff c-bet" if was_pfr else "position-based semi-bluff"
                        logger.info(f"Decision: {action_raise_const} {bet_amount:.2f} (Drawing hand, {bet_description})")
                        return action_raise_const, bet_amount                    
                    else:
                        logger.info(f"Decision: {action_check_const} (Drawing hand, {('PFR' if was_pfr else 'in position')} choosing to check)")
                        return action_check_const, 0
                else:  # Not PFR and not in favorable position
                    # Still consider semi-bluffing in certain scenarios even when not PFR
                    if win_probability > 0.30 and active_opponents_count == 1:
                        fold_equity_for_draw_bluff = calculate_fold_equity(
                            final_opponent_analysis.get('table_type', 'unknown'), 
                            board_texture, 
                            pot_size * 0.50, 
                            pot_size
                        )
                        
                        if fold_equity_for_draw_bluff > 0.45:  # Higher fold equity needed when not PFR
                            bet_amount = get_dynamic_bet_size(
                                numerical_hand_rank, 
                                pot_size, 
                                my_stack, 
                                street, 
                                big_blind_amount, 
                                active_opponents_count, 
                                bluff=True
                            ) * 0.8  # Smaller sizing when not PFR
                            logger.info(f"Decision: {action_raise_const} {bet_amount:.2f} (Drawing hand, opportunistic semi-bluff)")
                            return action_raise_const, bet_amount
                    
                    logger.info(f"Decision: {action_check_const} (Drawing hand, checking to see next card)")
                    return action_check_const, 0
            elif hand_strength_final_decision == 'weak_made':
                # More aggressive with weak made hands - use 0.65 pot bet for higher fold equity
                fold_equity = calculate_fold_equity(final_opponent_analysis.get('table_type', 'unknown'), board_texture, pot_size * 0.65, pot_size) # Increased from 0.5 pot bet
                
                cbet_bluff_threshold = 0.6 # Default threshold
                log_message_detail_prefix = ""
                if was_pfr:
                    cbet_bluff_threshold = 0.45 # Lowered threshold for PFR c-bet bluff (tune this)
                    log_message_detail_prefix = "c-bet "
                    logger.info(f"Weak made hand, PFR: Considering {log_message_detail_prefix}bluff. Fold equity: {fold_equity:.2f}, Threshold: {cbet_bluff_threshold}")

                if fold_equity > cbet_bluff_threshold:
                    bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff=True)
                    logger.info(f"Decision: {action_raise_const} {bet_amount:.2f} (Weak made hand, {log_message_detail_prefix}bluffing with fold equity)")
                    return action_raise_const, bet_amount
                else:
                    if ENHANCED_MODULES_AVAILABLE:
                        should_check_flag, check_reason = should_check_instead_of_bet(hand_strength_final_decision, win_probability, pot_size, active_opponents_count, position, street)
                        if should_check_flag:
                            logger.info(f"Decision: {action_check_const} (Weak made hand, {('PFR but ' if was_pfr else '')}checking because: {check_reason})")
                            return action_check_const, 0
                    logger.info(f"Decision: {action_check_const} (Weak made hand, checking, low fold equity for {log_message_detail_prefix}bluff)")
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
            # NEW: Board danger check
            if board_danger_level >= 7 and bet_to_call > 0:
                logger.warning(f"Very strong hand, but board is dangerous (level: {board_danger_level}). Calling instead of raising.")
                logger.info(f"Decision: {action_call_const} {bet_to_call} (Very strong hand, but calling due to dangerous board)")
                return action_call_const, bet_to_call
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
            # NEW: Board danger check
            if board_danger_level >= 5 and bet_to_call > 0:
                logger.warning(f"Strong hand, but board is dangerous (level: {board_danger_level}). Calling instead of raising.")
                logger.info(f"Decision: {action_call_const} {bet_to_call} (Strong hand, calling due to dangerous board)")
                return action_call_const, bet_to_call
            # Much more aggressive with strong hands
            required_equity = (1 - win_probability) / win_probability if win_probability > 0 else float('inf')
            
            # Wider definition of tiny bet to call more
            is_small_bet = bet_to_call <= (pot_size * 0.40)  # Was 0.25 - now call bets up to 40% of pot more liberally
            is_tiny_bet = bet_to_call <= (pot_size * 0.25)
            
            # Much lower threshold for calling with strong hands (was 0.15)
            if pot_odds_to_call > required_equity * 0.8 or (is_small_bet and win_probability > 0.10):  # More liberal calling
                # More aggressive raising with strong hands
                
                # Raise more often - lowered threshold to 0.4 from 0.6
                if base_aggression_factor > 0.4 or final_opponent_analysis.get('table_type', '') != 'aggressive':
                    # Much more aggressive raising threshold - was spr < 4, now < 8
                    # Will raise with strong hands in virtually all SPR situations
                    if spr < 8 or final_opponent_analysis.get('is_weak_passive', False) or position in ['BTN', 'CO']:
                        bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count)
                        # Make slightly larger raises - multiply by 1.2
                        bet_amount = max(bet_amount * 1.2, min_raise)
                        logger.info(f"Decision: {action_raise_const} {bet_amount} (Strong hand, raising against bet, favorable conditions)")
                        return action_raise_const, min(bet_amount, my_stack)
                    else:
                        logger.info(f"Decision: {action_call_const} {bet_to_call} (Strong hand, calling bet, good odds or small bet)")
                        return action_call_const, bet_to_call
                else:
                    logger.info(f"Decision: {action_call_const} {bet_to_call} (Strong hand, calling bet, good odds or small bet)")
                    return action_call_const, bet_to_call
            else:
                # Almost never fold strong hands unless the bet is very large and equity is terrible
                if bet_to_call > pot_size * 0.75 and win_probability < 0.25:
                    logger.info(f"Decision: {action_fold_const} (Strong hand, folding to large bet with poor equity: {win_probability:.2f})")
                    return action_fold_const, 0
                else:                    
                    logger.info(f"Decision: {action_call_const} {bet_to_call} (Strong hand, calling despite marginal odds)")
                    return action_call_const, bet_to_call
                    
        elif is_medium:
            # NEW: Board danger check
            if board_danger_level >= 4 and bet_to_call > 0:
                logger.warning(f"Medium hand, but board is dangerous (level: {board_danger_level}). Folding to bet.")
                logger.info(f"Decision: {action_fold_const} (Medium hand, folding due to dangerous board)")
                return action_fold_const, 0
            # More aggressive with medium hands
            # Favor position - be more aggressive in position
            position_advantage = position in ['BTN', 'CO']

            # NEW: Avoid committing stack with medium hands unless win_probability is high
            large_bet = bet_to_call > pot_size * 0.5 or bet_to_call > my_stack * 0.5
            if large_bet and win_probability < 0.65:
                logger.info(f"Decision: {action_fold_const} (Medium hand, folding to large bet/all-in with low win probability: {win_probability:.2f})")
                return action_fold_const, 0

            # First check if we should raise instead of just calling
            if win_probability > 0.55 and position_advantage:
                # Consider raising with good medium hands when in position
                bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count)
                bet_amount = max(bet_amount * 0.8, min_raise)  # Slightly smaller sizing than with strong hands
                logger.info(f"Decision: {action_raise_const} {bet_amount} (Medium hand, position-based semi-bluff raise)")
                return action_raise_const, min(bet_amount, my_stack)
            
            # Much more liberal calling criteria with medium hands
            if should_call_with_draws(my_player_data.get('hand', []), community_cards, win_probability, pot_size, bet_to_call, 
                                      estimated_opponent_stack_for_implied_odds, my_stack, street) or (win_probability > 0.4 and bet_to_call <= pot_size * 0.4):
                 logger.info(f"Decision: {action_call_const} {bet_to_call} (Medium hand/draw, calling with implied odds or decent equity)")
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

    # --- Extra safeguard: Avoid overcommitting with Two Pair or similar hands on dangerous boards ---
    if hand_description and 'Two Pair' in hand_description:
        # If board is coordinated (3+ to straight/flush) or facing large bet, avoid all-in
        board_is_coordinated = False
        if community_cards:
            suits = [c[-1] for c in community_cards if len(c) > 1]
            ranks = [c[:-1] for c in community_cards if len(c) > 1]
            if len(set(suits)) <= 2 and len(suits) >= 4:
                board_is_coordinated = True  # Possible flush
            rank_values = sorted(["--A23456789TJQK".index(r) for r in ranks if r in "A23456789TJQK"])
            if len(rank_values) >= 4 and max(rank_values) - min(rank_values) <= 4:
                board_is_coordinated = True  # Possible straight
        large_bet = bet_to_call > pot_size * 0.4 or bet_to_call > my_stack * 0.4
        if board_is_coordinated or large_bet:
            logger.info(f"Two Pair on coordinated board or facing large bet. Avoiding stack commitment. Action: CALL or FOLD.")
            if win_probability > 0.5 and bet_to_call <= my_stack * 0.5:
                return action_call_const, bet_to_call
            else:
                return action_fold_const, 0

    # After all advanced strategy variables are set and before making a final decision:
    # --- Use improved drawing hand analysis for all drawing hands ---
    if hand_strength_final_decision == 'drawing':
        draw_analysis = improved_drawing_hand_analysis(
            numerical_hand_rank, win_probability, pot_odds_to_call, bet_to_call, pot_size, my_stack, street
        )
        logger.info(f"[IMPROVED DRAW ANALYSIS] {draw_analysis}")
        if draw_analysis['should_call']:
            logger.info(f"Decision: {action_call_const} {bet_to_call} (Drawing hand, improved analysis: call)")
            return action_call_const, bet_to_call
        else:
            logger.info(f"Decision: {action_fold_const} (Drawing hand, improved analysis: fold)")
            return action_fold_const, 0

    # --- Use improved value betting and bluffing strategies ---
    if is_very_strong or is_strong or is_medium:
        value_strategy = fix_value_betting_strategy(
            hand_strength_final_decision, win_probability, spr, can_check, pot_size, my_stack, position
        )
        logger.info(f"[IMPROVED VALUE BETTING] {value_strategy}")
        if value_strategy['bet_action'] == 'raise' and value_strategy['bet_size'] > 0:
            return action_raise_const, min(value_strategy['bet_size'], my_stack)
        elif value_strategy['bet_action'] == 'check':
            return action_check_const, 0

    # --- Use improved bluffing strategy if hand is weak or bluff spot ---
    if is_weak_final or hand_strength_final_decision in ['bluff', 'very_weak', 'weak_made']:
        bluff_strategy = fix_bluffing_strategy(
            hand_strength_final_decision, win_probability, fold_equity, spr, can_check, position, street, pot_size, my_stack
        )
        logger.info(f"[IMPROVED BLUFFING] {bluff_strategy}")
        if bluff_strategy['bet_action'] == 'raise' and bluff_strategy['bet_size'] > 0:
            return action_raise_const, min(bluff_strategy['bet_size'], my_stack)
        elif bluff_strategy['bet_action'] == 'check':
            return action_check_const, 0

    # --- Use improved multiway betting adjustment ---
    multiway_adj = get_multiway_betting_adjustment(hand_strength_final_decision, active_opponents_count, win_probability)
    logger.info(f"[IMPROVED MULTIWAY ADJUSTMENT] {multiway_adj}")
    if not multiway_adj['should_bet']:
        return action_check_const if can_check else action_fold_const, 0

    # --- Use improved final decision logic for all other cases ---
    action, amount, reasoning = improved_final_decision(
        hand_strength_final_decision, win_probability, spr_strategy, pot_size, bet_to_call, can_check,
        active_opponents_count=active_opponents_count, fold_equity=fold_equity, drawing_potential=drawing_potential,
        committed_ratio=pot_commitment_ratio, hand_evaluation=None
    )
    logger.info(f"[IMPROVED FINAL DECISION] {action}, {amount}, {reasoning}")

    # --- Use improved pot odds safeguard before folding ---
    if action == action_fold_const and bet_to_call > 0 and pot_size > 0:
        action, amount, reasoning = improved_pot_odds_safeguard(
            action, bet_to_call, pot_size, win_probability, hand_strength_final_decision, reasoning
        )
        logger.info(f"[IMPROVED POT ODDS SAFEGUARD] {action}, {amount}, {reasoning}")
        if action != action_fold_const:
            return action, amount

    return action, amount
# === END: Integrate improved/tuned logic ===
# ...existing code...
# === Advanced Post-Flop Strategy Utilities ===
def has_blocker_effects(my_hand, board, target_ranks, target_suits=None):
    """Returns True if hand contains blockers to key opponent holdings."""
    hand_cards = set(my_hand)
    board_cards = set(board)
    for rank in target_ranks:
        for suit in (target_suits or ['s', 'h', 'd', 'c']):
            card = f"{rank}{suit}"
            if card in hand_cards and card not in board_cards:
                return True
    return False

def should_merge_or_polarize_range(opponent_type, board_texture):
    """Suggests whether to merge or polarize betting range."""
    if opponent_type == 'calling_station':
        return 'merge'  # bet more medium hands for value
    if board_texture in ['dry', 'static']:
        return 'merge'
    return 'polarize'  # bet strong hands and bluffs

def should_overbet_or_underbet(street, hand_strength, board_texture, nut_advantage):
    """Suggests overbet or underbet opportunities."""
    if street == 'turn' and hand_strength == 'very_strong' and nut_advantage:
        return 'overbet'
    if street == 'river' and hand_strength in ['very_strong', 'bluff'] and nut_advantage:
        return 'overbet'
    if hand_strength == 'thin_value' and board_texture == 'dry':
        return 'underbet'
    return None

def adjust_for_multiway_pot(active_opponents_count, hand_strength):
    """Adjusts aggression for multiway pots."""
    if active_opponents_count > 2:
        if hand_strength in ['medium', 'thin_value', 'bluff']:
            return 'pot_control'
    return None

def should_double_barrel_bluff(board_runout, previous_action, opponent_type):
    """Returns True if double-barrel bluff is recommended."""
    if previous_action == 'cbet_flop' and board_runout in ['scare_card', 'overcard'] and opponent_type != 'calling_station':
        return True
    return False

def should_delay_cbet(street, previous_action, board_texture, opponent_type):
    """Returns True if delayed c-bet is optimal."""
    if street == 'turn' and previous_action == 'check_flop' and board_texture == 'dry' and opponent_type != 'aggressive':
        return True
    return False

def should_river_overbluff(opponent_type, river_action_history):
    """Returns True if river overbluff is recommended."""
    if opponent_type == 'fit_or_fold' and river_action_history.count('check') >= 2:
        return True
    return False

def should_induce_bluff(opponent_type, hand_strength, street, action_history):
    """Returns True if inducing a bluff is optimal."""
    if opponent_type == 'aggressive' and hand_strength in ['strong', 'medium'] and street == 'river' and action_history and action_history.get('river', []) == ['check']:
        return True
    return False

def assess_board_danger(community_cards):
    """
    Assess the danger level of the board texture.
    Returns a danger level from 0 (safest) to 10 (most dangerous).
    """
    danger = 0
    ranks = [c[0] for c in community_cards]
    suits = [c[1] for c in community_cards]

    # Three of a kind on board
    rank_counts = {r: ranks.count(r) for r in ranks}
    if 3 in rank_counts.values():
        danger += 8

    # Paired board
    elif 2 in rank_counts.values():
        danger += 4

    # Flush danger
    suit_counts = {s: suits.count(s) for s in suits}
    if 3 in suit_counts.values():
        danger += 3
    if 4 in suit_counts.values():
        danger += 6

    # Straight danger
    # This is a simplified check. A more robust check would analyze sequences.
    unique_ranks = sorted(list(set([('--TJQKA'.index(r) if r in '--TJQKA' else int(r)) for r in ranks])))
    if len(unique_ranks) >= 3:
        if unique_ranks[-1] - unique_ranks[0] <= 4: # Potential straight
            danger += 3
        if len(unique_ranks) >= 4 and unique_ranks[-1] - unique_ranks[0] <= 5: # Very likely straight
            danger += 5
            
    return min(danger, 10)

# Integrate advanced strategies into make_postflop_decision
# (Insert at appropriate points in the function, e.g., after hand strength and opponent analysis)
# Example integration (pseudo-code, adapt as needed):
#
# blocker = has_blocker_effects(my_player_data.get('hand', []), community_cards, target_ranks=['A', 'K'])
# range_strategy = should_merge_or_polarize_range(final_opponent_analysis.get('table_type', 'unknown'), board_texture)
# overbet_suggestion = should_overbet_or_underbet(street, hand_strength_final_decision, board_texture, nut_advantage=True)
# multiway_adjustment = adjust_for_multiway_pot(active_opponents_count, hand_strength_final_decision)
# double_barrel = should_double_barrel_bluff(board_texture, action_history.get('flop', ''), final_opponent_analysis.get('table_type', 'unknown'))
# delay_cbet = should_delay_cbet(street, action_history.get('flop', ''), board_texture, final_opponent_analysis.get('table_type', 'unknown'))
# river_bluff = should_river_overbluff(final_opponent_analysis.get('table_type', 'unknown'), (action_history.get('river', []) if action_history else []))
# induce_bluff = should_induce_bluff(final_opponent_analysis.get('table_type', 'unknown'), hand_strength_final_decision, street, action_history)
