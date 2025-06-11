\
# filepath: h:\\Programming\\pokerplayer\\postflop\\analysis_processing.py
import logging

# It's generally better for these specific analysis functions to handle their
# own imports conditionally based on availability flags passed to them,
# or for the main module to pass the imported functions/classes themselves.
# For now, we'll assume the necessary flags (ENHANCED_MODULES_AVAILABLE, etc.) are passed
# and used to gate calls to potentially missing modules.
# Actual imports of specific modules like AdvancedOpponentAnalyzer will be attempted here.

logger = logging.getLogger(__name__)

def process_initial_enhanced_analysis(
    numerical_hand_rank, win_probability, street, opponent_tracker, active_opponents_count,
    spr, position, pot_commitment_ratio, ENHANCED_MODULES_AVAILABLE,
    # Functions/Classes to be passed if not imported directly here
    classify_hand_strength_basic_func, get_standardized_pot_commitment_threshold_func,
    get_fixed_opponent_analysis_func, get_opponent_exploitative_adjustments_func,
    get_spr_strategy_recommendation_func, should_commit_stack_spr_func,
    passed_logger
):
    """Processes initial enhanced analysis if modules are available."""
    log = passed_logger if passed_logger else logger # Use passed logger

    hand_strength, hand_details, commitment_threshold = None, {}, 0.5 # Default commitment
    opponent_analysis, exploitative_adjustments = {}, {}
    spr_strategy, should_commit, commit_reason = {}, False, ""

    if ENHANCED_MODULES_AVAILABLE:
        try:
            hand_strength, hand_details = classify_hand_strength_basic_func(
                numerical_hand_rank=numerical_hand_rank,
                win_probability=win_probability,
                street=street,
                board_texture='moderate'  # Placeholder, can be enhanced
            )
            commitment_threshold = get_standardized_pot_commitment_threshold_func(hand_strength, street)
            log.info(f"Enhanced hand classification: {hand_strength} (rank={numerical_hand_rank}, win_prob={win_probability:.1%}, threshold={commitment_threshold:.1%})")

            opponent_analysis = get_fixed_opponent_analysis_func(opponent_tracker, active_opponents_count)
            exploitative_adjustments = get_opponent_exploitative_adjustments_func(opponent_analysis)
            log.info(f"Fixed opponent analysis: tracked={opponent_analysis.get('tracked_count',0)}, table_type={opponent_analysis.get('table_type','unknown')}, avg_vpip={opponent_analysis.get('avg_vpip',0):.1f}%, fold_equity={opponent_analysis.get('fold_equity_estimate',0):.1%}")

            spr_strategy = get_spr_strategy_recommendation_func(
                spr=spr, hand_strength=hand_strength, street=street, position=position,
                opponent_count=active_opponents_count, board_texture='moderate' # Placeholder
            )
            should_commit, commit_reason = should_commit_stack_spr_func(
                spr=spr, hand_strength=hand_strength, pot_commitment_ratio=pot_commitment_ratio, street=street
            )
            log.debug(f"SPR strategy: {spr_strategy.get('base_strategy','unknown')} (SPR={spr:.1f}, {spr_strategy.get('spr_category','unknown')})")
        except Exception as e:
            log.error(f"Error during initial enhanced analysis: {e}", exc_info=True)
            # Fallback to simpler logic if enhanced processing fails
            ENHANCED_MODULES_AVAILABLE = False # Mark as failed

    if not ENHANCED_MODULES_AVAILABLE: # Fallback logic if modules not available or failed
        if win_probability >= 0.80: hand_strength = 'very_strong'; commitment_threshold = 0.20
        elif win_probability >= 0.70: hand_strength = 'strong'; commitment_threshold = 0.30
        elif win_probability >= 0.55: hand_strength = 'medium'; commitment_threshold = 0.50
        else: hand_strength = 'weak'; commitment_threshold = 0.75
        hand_details = {'final_classification': hand_strength, 'win_probability': win_probability, 'is_very_strong': hand_strength == 'very_strong', 'is_strong': hand_strength == 'strong', 'is_medium': hand_strength == 'medium', 'is_weak': hand_strength == 'weak'}
        opponent_analysis = {'tracked_count': 0, 'table_type': 'unknown', 'avg_vpip': 25.0, 'fold_equity_estimate': 0.5, 'reasoning': 'enhanced_modules_not_available_or_failed'}
        spr_strategy = {'betting_action': 'bet_value', 'sizing_adjustment': 1.0, 'spr_category': 'medium' if 4 <= spr <= 13 else ('low' if spr < 4 else 'high')}
        should_commit = pot_commitment_ratio > commitment_threshold
        commit_reason = "fallback pot commitment logic"

    is_pot_committed = pot_commitment_ratio > commitment_threshold

    return {
        "hand_strength": hand_strength, "hand_details": hand_details, "commitment_threshold": commitment_threshold,
        "opponent_analysis": opponent_analysis, "exploitative_adjustments": exploitative_adjustments,
        "spr_strategy": spr_strategy, "should_commit": should_commit, "commit_reason": commit_reason,
        "is_pot_committed": is_pot_committed
    }

def integrate_advanced_module_data(
    win_probability, community_cards, ADVANCED_MODULES_AVAILABLE, opponent_tracker, my_player_data,
    bet_to_call, pot_size, my_stack, big_blind_amount, active_opponents_count, pot_odds_to_call,
    street, numerical_hand_rank, position, initial_opponent_analysis, passed_logger
):
    """Integrates data from advanced modules if available."""
    log = passed_logger if passed_logger else logger
    advanced_context = {}
    hand_strength_advanced = 'very_weak' # Default
    board_texture_advanced = {'texture': 'unknown', 'paired': False, 'flush_possible': False, 'straight_possible': False}

    # Basic hand strength determination (can be overridden by more specific classifications later)
    if win_probability >= 0.80: hand_strength_advanced = 'very_strong'
    elif win_probability >= 0.65: hand_strength_advanced = 'strong'
    elif win_probability >= 0.45: hand_strength_advanced = 'medium'
    elif win_probability >= 0.30: hand_strength_advanced = 'weak_made'

    # Basic board texture analysis
    if community_cards and len(community_cards) >= 3:
        suits = [card[-1] for card in community_cards if isinstance(card, str) and len(card) > 0]
        if suits:
            suit_counts = {suit: suits.count(suit) for suit in set(suits)}
            board_texture_advanced['flush_possible'] = any(count >= 3 for count in suit_counts.values())
        ranks = [card[:-1] for card in community_cards if isinstance(card, str) and len(card) > 0]
        if ranks:
            board_texture_advanced['paired'] = len(set(ranks)) < len(ranks)
            # Basic straight detection (very simplified)
            # This is a placeholder; real straight detection is complex
            # For a more robust solution, a dedicated straight detection function is needed.


    if ADVANCED_MODULES_AVAILABLE:
        # 1. Cash Game Enhancements
        try:
            from cash_game_enhancements import apply_cash_game_enhancements
            cash_game_decision_context = {
                'hand_strength': hand_strength_advanced, 'numerical_hand_rank': numerical_hand_rank,
                'win_probability': win_probability, 'position': position, 'street': street,
                'pot_size': pot_size, 'stack_size': my_stack, 'big_blind': big_blind_amount,
                'active_opponents': active_opponents_count, 'opponent_analysis': initial_opponent_analysis, # from previous step
                'board_texture': board_texture_advanced, 'bet_to_call': bet_to_call, 'pot_odds': pot_odds_to_call
            }
            cash_game_context = apply_cash_game_enhancements(cash_game_decision_context)
            advanced_context['cash_game_enhancements'] = cash_game_context
            log.info(f"Cash game enhancements applied: confidence={cash_game_context.get('overall_confidence', 0.5):.2f}")
        except ImportError: log.debug("Cash game enhancement module not available.")
        except Exception as e: log.warning(f"Cash game enhancements failed: {e}", exc_info=True)

        # 2. Advanced Opponent Modeling
        if opponent_tracker: # Ensure opponent_tracker is not None
            try:
                from advanced_opponent_modeling import AdvancedOpponentAnalyzer
                analyzer = AdvancedOpponentAnalyzer()
                if hasattr(opponent_tracker, 'opponents') and opponent_tracker.opponents:
                    for opponent_name, profile in opponent_tracker.opponents.items():
                        if hasattr(profile, 'hands_seen') and profile.hands_seen > 0:
                             analyzer.update_opponent_profile(opponent_name, {'vpip': profile.get_vpip(), 'pfr': profile.get_pfr(), 'hands_seen': profile.hands_seen})
                current_situation = {'street': street, 'position': position, 'situation': 'facing_bet' if bet_to_call > 0 else 'checked_to'}
                opponent_list = list(opponent_tracker.opponents.keys())[:active_opponents_count] if hasattr(opponent_tracker, 'opponents') else []
                primary_opponent = opponent_list[0] if opponent_list else "Unknown"
                exploitative_strategy = analyzer.get_exploitative_strategy(player_name=primary_opponent, current_situation=current_situation)
                advanced_context['advanced_opponent_analysis'] = exploitative_strategy
                log.info(f"Advanced opponent analysis: {exploitative_strategy.get('recommended_action','N/A')} - {exploitative_strategy.get('reasoning','N/A')}")
            except ImportError: log.debug("Advanced opponent modeling module not available.")
            except Exception as e: log.warning(f"Advanced opponent modeling failed: {e}", exc_info=True)

        # 3. Enhanced Board Analysis
        try:
            from enhanced_board_analysis import EnhancedBoardAnalyzer
            if community_cards:
                board_analyzer = EnhancedBoardAnalyzer()
                board_analysis_result = board_analyzer.analyze_board(community_cards)
                advanced_context['enhanced_board_analysis'] = board_analysis_result
                # Update board_texture_advanced with more detailed info if available
                board_texture_advanced.update(board_analysis_result)
                log.info(f"Enhanced board analysis: {board_analysis_result.get('texture','N/A')} texture, draws: {board_analysis_result.get('draw_analysis',{}).get('total_draws',0)}, betting_rec: {board_analysis_result.get('betting_implications',{}).get('recommended_sizing','N/A')}")
        except ImportError: log.debug("Enhanced board analysis module not available.")
        except Exception as e: log.warning(f"Enhanced board analysis failed: {e}", exc_info=True)

        # 4. Performance Monitoring Setup
        try:
            from performance_monitoring import PerformanceMetrics
            perf_tracker = PerformanceMetrics()
            decision_context_perf = {
                'street': street, 'hand_rank': numerical_hand_rank, 'win_probability': win_probability,
                'pot_odds': pot_odds_to_call, 'bet_to_call': bet_to_call, 'pot_size': pot_size,
                'stack_size': my_stack, 'opponents': active_opponents_count
            }
            advanced_context['performance_tracker'] = perf_tracker # Store tracker instance
            advanced_context['decision_context_for_perf'] = decision_context_perf # Store data for tracker
            # perf_tracker.record_decision_context(decision_context_perf) # Example usage
            log.debug("Performance monitoring setup.")
        except ImportError: log.debug("Performance monitoring module not available.")
        except Exception as e: log.warning(f"Performance monitoring setup failed: {e}", exc_info=True)

    log.debug(f"Advanced enhancements integrated: {list(advanced_context.keys())}")
    return {
        "advanced_context": advanced_context,
        "hand_strength_from_advanced": hand_strength_advanced, # This is the basic one from this function
        "board_texture_from_advanced": board_texture_advanced
    }

def refine_hand_classification_and_commitment(
    numerical_hand_rank, win_probability, hand_description, street, spr,
    VERY_STRONG_HAND_THRESHOLD, STRONG_HAND_THRESHOLD, MEDIUM_HAND_THRESHOLD,
    passed_logger
):
    """Refines hand strength classification and pot commitment thresholds."""
    log = passed_logger if passed_logger else logger
    hand_strength_refined = 'weak' # Default
    is_very_strong, is_strong, is_medium, is_weak = False, False, False, True
    commitment_threshold_refined = 0.35 # Default for weak

    try:
        from enhanced_postflop_improvements import classify_hand_strength_enhanced as classify_hand_strength_improved, standardize_pot_commitment_thresholds
        
        hand_strength_refined = classify_hand_strength_improved(
            numerical_hand_rank=numerical_hand_rank,
            win_probability=win_probability,
            hand_description=hand_description
        )
        is_very_strong = hand_strength_refined == 'very_strong'
        is_strong = hand_strength_refined == 'strong'
        is_medium = hand_strength_refined == 'medium'
        is_weak = hand_strength_refined in ['weak_made', 'very_weak', 'drawing']
        commitment_threshold_refined = standardize_pot_commitment_thresholds(hand_strength_refined, street, spr)
        log.debug(f"Refined classification (enhanced_postflop_improvements): {hand_strength_refined}, commitment_threshold: {commitment_threshold_refined:.2%}")
    except ImportError:
        log.warning("Module 'enhanced_postflop_improvements' not available for refining classification. Using fallback.")
        # Fallback logic from the original file
        is_very_strong = numerical_hand_rank >= VERY_STRONG_HAND_THRESHOLD or win_probability > 0.85
        is_strong = not is_very_strong and (numerical_hand_rank >= STRONG_HAND_THRESHOLD or win_probability > 0.65)
        is_medium = not is_very_strong and not is_strong and (numerical_hand_rank >= MEDIUM_HAND_THRESHOLD or win_probability > 0.45)
        is_weak = not (is_very_strong or is_strong or is_medium)

        if is_very_strong or is_strong: commitment_threshold_refined = 0.60
        elif is_medium: commitment_threshold_refined = 0.45
        else: commitment_threshold_refined = 0.35

        if is_very_strong: hand_strength_refined = 'very_strong'
        elif is_strong: hand_strength_refined = 'strong'
        elif is_medium: hand_strength_refined = 'medium'
        else: hand_strength_refined = 'weak' # Generic weak if no better category
        log.debug(f"Refined classification (fallback): {hand_strength_refined}, commitment_threshold: {commitment_threshold_refined:.2%}")

    return {
        "hand_strength_refined": hand_strength_refined,
        "is_very_strong_refined": is_very_strong, "is_strong_refined": is_strong,
        "is_medium_refined": is_medium, "is_weak_refined": is_weak,
        "commitment_threshold_refined": commitment_threshold_refined
    }

def consolidate_opponent_analysis(
    opponent_tracker, active_opponents_count, ENHANCED_MODULES_AVAILABLE,
    get_fixed_opponent_analysis_func, # Pass the function from the main module
    passed_logger
):
    """Consolidates opponent analysis from various sources."""
    log = passed_logger if passed_logger else logger
    final_opponent_analysis = None
    opponent_analysis_source = "unknown"

    try:
        from enhanced_postflop_improvements import fix_opponent_tracker_integration
        final_opponent_analysis = fix_opponent_tracker_integration(opponent_tracker, active_opponents_count)
        opponent_analysis_source = "enhanced_postflop_improvements.fix_opponent_tracker_integration"
        log.info(f"Using opponent analysis from: {opponent_analysis_source}")
    except ImportError:
        log.warning("Module 'enhanced_postflop_improvements.fix_opponent_tracker_integration' not available.")
    except Exception as e:
        log.error(f"Error in fix_opponent_tracker_integration: {e}", exc_info=True)

    if final_opponent_analysis is None and ENHANCED_MODULES_AVAILABLE and get_fixed_opponent_analysis_func:
        log.warning("Falling back to get_fixed_opponent_analysis_func.")
        try:
            final_opponent_analysis = get_fixed_opponent_analysis_func(opponent_tracker, active_opponents_count)
            opponent_analysis_source = "get_fixed_opponent_analysis_func (fallback)"
            log.info(f"Using opponent analysis from: {opponent_analysis_source}")
        except Exception as e:
            log.error(f"Error in get_fixed_opponent_analysis_func (fallback): {e}", exc_info=True)
    
    if final_opponent_analysis is None:
        log.warning("All primary opponent analysis methods failed or unavailable. Using default unknown state.")
        final_opponent_analysis = {
            'tracked_count': 0, 'table_type': 'unknown', 'avg_vpip': 25.0,
            'fold_equity_estimate': 0.5, 'reasoning': 'all_sources_failed_using_default',
            'player_type_distribution': {'unknown': 1.0}
        }
        opponent_analysis_source = "default_unknown_state"
        log.info(f"Using opponent analysis from: {opponent_analysis_source}")

    # Ensure essential keys exist
    final_opponent_analysis.setdefault('table_type', 'unknown')
    final_opponent_analysis.setdefault('fold_equity_estimate', 0.5)
    final_opponent_analysis.setdefault('avg_vpip', 25.0)
    final_opponent_analysis.setdefault('reasoning', 'default_values_applied')
    
    log.info(f"Final opponent analysis ({opponent_analysis_source}): tracked={final_opponent_analysis.get('tracked_count', 'N/A')}, "
               f"table_type={final_opponent_analysis.get('table_type', 'N/A')}, "
               f"avg_vpip={final_opponent_analysis.get('avg_vpip', 0.0):.1f}, "
               f"fold_equity={final_opponent_analysis.get('fold_equity_estimate', 0.0):.1%}")

    return {
        "final_opponent_analysis": final_opponent_analysis,
        "opponent_analysis_source": opponent_analysis_source
    }

def determine_final_decision_hand_strength(
    is_very_strong_current, is_strong_current, is_medium_current, # From refined classification
    numerical_hand_rank, win_probability, street,
    is_drawing_hand_func, # Pass the utility function
    passed_logger
):
    """Determines the final hand strength category for decision-making, with adjustments."""
    log = passed_logger if passed_logger else logger
    
    # Start with refined flags
    is_very_strong = is_very_strong_current
    is_strong = is_strong_current
    is_medium = is_medium_current

    # Specific adjustment for one-pair hands (original logic block)
    if numerical_hand_rank == 2:  # One pair
        if win_probability >= 0.75:
            is_very_strong = False; is_strong = True; is_medium = False
        elif win_probability >= 0.60:
            is_very_strong = False; is_strong = True; is_medium = False # Classified as strong if win_prob is 60%+
        elif win_probability >= 0.45:
            is_very_strong = False; is_strong = False; is_medium = True
        else: # Weak one pair
            is_very_strong = False; is_strong = False; is_medium = False
    # else:
        # For non-one-pair hands, the flags from refine_hand_classification_and_commitment are used.
        # No explicit 'else' needed if we are just potentially overriding for numerical_hand_rank == 2

    # Final classification based on the (potentially adjusted) flags
    if is_very_strong: hand_strength_final_decision = 'very_strong'
    elif is_strong: hand_strength_final_decision = 'strong'
    elif is_medium: hand_strength_final_decision = 'medium'
    else: # is_weak implicitly
        if numerical_hand_rank >= 1: # Made hand, but not strong or medium
            hand_strength_final_decision = 'weak_made'
        elif is_drawing_hand_func(win_probability, numerical_hand_rank, street):
            hand_strength_final_decision = 'drawing'
        else:
            hand_strength_final_decision = 'very_weak' # High card, no draw

    is_weak_final = hand_strength_final_decision in ['weak_made', 'very_weak', 'drawing']

    log.debug(f"Final decision hand strength: {hand_strength_final_decision} (is_weak={is_weak_final}). Orig rank={numerical_hand_rank}, win_prob={win_probability:.2%}")
    log.info(f"Post-adjustment hand strength flags: very_strong={is_very_strong}, strong={is_strong}, medium={is_medium} (Final Category: {hand_strength_final_decision})")

    return {
        "hand_strength_final_decision": hand_strength_final_decision,
        "is_weak_final": is_weak_final,
        "is_very_strong_final": is_very_strong, # Return final flags as well
        "is_strong_final": is_strong,
        "is_medium_final": is_medium
    }
