# postflop_decision_logic.py

import logging
from implied_odds import should_call_with_draws

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

# Create file handler if it doesn't exist
if not logger.handlers:
    handler = logging.FileHandler('debug_postflop_decision_logic.log', mode='a')
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

# Enhanced drawing hand detection function
def is_drawing_hand(win_probability, hand_rank, street):
    """
    Detect if this is likely a drawing hand based on equity and hand strength.
    Drawing hands typically have:
    - Moderate equity (25-50%) but low made hand strength
    - Are not on the river (no draws possible)
    """
    if street == 'river':
        return False  # No draws on river
    
    # High card or weak pair with reasonable equity = likely draw
    # This includes flush draws, straight draws, overcards, etc.
    return (hand_rank <= 2 and 0.25 <= win_probability <= 0.50)

def get_optimal_value_bet_size_percentage(pot_size, hand_strength, street, opponent_count):
    """
    Dynamic bet sizing based on multiple factors.
    Returns the percentage of pot to bet for value.
    """
    base_sizing = {
        'flop': 0.7,   # 70% pot
        'turn': 0.75,  # 75% pot  
        'river': 0.8   # 80% pot
    }
    
    size_multiplier = base_sizing.get(street, 0.7)
    
    # Adjust for hand strength
    if hand_strength == 'very_strong':
        size_multiplier *= 1.1  # Bet bigger with very strong hands
    elif hand_strength == 'medium':
        size_multiplier *= 0.8  # Bet smaller with medium hands
    
    # Adjust for opponent count (multiway = smaller bets)
    if opponent_count > 1:
        size_multiplier *= max(0.6, 1.0 - (opponent_count - 1) * 0.2)
    
    return size_multiplier

def get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff=False):
    """
    Enhanced bet sizing function that uses dynamic percentage-based sizing.
    Integrates the new get_optimal_value_bet_size_percentage function.
    """
    if pot_size <= 0:
        return min(big_blind_amount * 2.5, my_stack)
    
    if bluff:
        # For bluffs, use simpler sizing
        if street == "river":
            bet = pot_size * 0.75  # Larger river bluffs
        elif street == "turn":
            bet = pot_size * 0.65
        else:
            bet = pot_size * 0.5 
        bet = max(bet, big_blind_amount) 
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
    
    # Get optimal percentage from dynamic function
    bet_percentage = get_optimal_value_bet_size_percentage(pot_size, hand_strength, street, active_opponents_count)
    
    # Calculate bet amount
    bet = pot_size * bet_percentage
    
    # Ensure minimum bet size
    min_bet = big_blind_amount if street != "preflop" else big_blind_amount * 2
    bet = max(bet, min_bet)
    
    return min(round(bet, 2), my_stack)

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
    opponent_tracker=None  # Add opponent tracking data
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
    
    # ENHANCED POSTFLOP ANALYSIS WITH NEW MODULES
    position = my_player_data.get('position', 'BB')
    community_cards = my_player_data.get('community_cards', [])
      # 1. ENHANCED HAND STRENGTH CLASSIFICATION
    if ENHANCED_MODULES_AVAILABLE:
        hand_strength, hand_details = classify_hand_strength_basic(
            numerical_hand_rank=numerical_hand_rank,
            win_probability=win_probability,
            street=street,
            board_texture='moderate'  # Will be enhanced with board analysis
        )
        commitment_threshold = get_standardized_pot_commitment_threshold(hand_strength, street)
        
        logger.info(f"Enhanced hand classification: {hand_strength} (rank={numerical_hand_rank}, "
                   f"win_prob={win_probability:.1%}, threshold={commitment_threshold:.1%})")
    else:
        # Fallback to original classification
        if win_probability >= 0.80:
            hand_strength = 'very_strong'
            commitment_threshold = 0.20
        elif win_probability >= 0.70:
            hand_strength = 'strong'
            commitment_threshold = 0.30
        elif win_probability >= 0.55:
            hand_strength = 'medium'
            commitment_threshold = 0.50
        else:
            hand_strength = 'weak'
            commitment_threshold = 0.75
        
        hand_details = {
            'final_classification': hand_strength,
            'win_probability': win_probability,
            'is_very_strong': hand_strength == 'very_strong',
            'is_strong': hand_strength == 'strong',
            'is_medium': hand_strength == 'medium',
            'is_weak': hand_strength == 'weak'
        }
    
    # 2. FIXED OPPONENT ANALYSIS
    if ENHANCED_MODULES_AVAILABLE:
        opponent_analysis = get_fixed_opponent_analysis(opponent_tracker, active_opponents_count)
        exploitative_adjustments = get_opponent_exploitative_adjustments(opponent_analysis)
        
        logger.info(f"Fixed opponent analysis: tracked={opponent_analysis['tracked_count']}, "
                   f"table_type={opponent_analysis['table_type']}, "
                   f"avg_vpip={opponent_analysis['avg_vpip']:.1f}%, "
                   f"fold_equity={opponent_analysis['fold_equity_estimate']:.1%}")
    else:
        # Fallback opponent analysis
        opponent_analysis = {
            'tracked_count': 0,
            'table_type': 'unknown',
            'avg_vpip': 25.0,
            'fold_equity_estimate': 0.5,
            'reasoning': 'enhanced_modules_not_available'
        }
        exploitative_adjustments = {}
    
    # 3. ENHANCED SPR STRATEGY
    if ENHANCED_MODULES_AVAILABLE:
        spr_strategy = get_spr_strategy_recommendation(
            spr=spr,
            hand_strength=hand_strength,
            street=street,
            position=position,
            opponent_count=active_opponents_count,
            board_texture='moderate'  # Will be enhanced
        )
        
        should_commit, commit_reason = should_commit_stack_spr(
            spr=spr,
            hand_strength=hand_strength,
            pot_commitment_ratio=pot_commitment_ratio,
            street=street
        )
        
        logger.debug(f"SPR strategy: {spr_strategy['base_strategy']} "
                    f"(SPR={spr:.1f}, {spr_strategy['spr_category']})")
    else:
        # Fallback SPR analysis
        spr_strategy = {'betting_action': 'bet_value', 'sizing_adjustment': 1.0}
        should_commit = pot_commitment_ratio > commitment_threshold
        commit_reason = "fallback pot commitment logic"
    
    # 4. POT COMMITMENT CHECK (ENHANCED)
    is_pot_committed = pot_commitment_ratio > commitment_threshold
    
    logger.debug(f"Pot commitment: committed={committed_amount:.2f}, call={bet_to_call:.2f}, "
                f"total={total_commitment_if_call:.2f}, stack={my_stack:.2f}, "
                f"ratio={pot_commitment_ratio:.1%}, threshold={commitment_threshold:.1%}, "
                f"is_committed={is_pot_committed}")
      # ADVANCED MODULES INTEGRATION (if available)
    advanced_context = {}
      # Determine hand strength
    if win_probability >= 0.80:
        hand_strength = 'very_strong'
    elif win_probability >= 0.65:
        hand_strength = 'strong'
    elif win_probability >= 0.45:
        hand_strength = 'medium'
    elif win_probability >= 0.30:
        hand_strength = 'weak_made'
    else:
        hand_strength = 'very_weak'
    
    # Build board texture info
    board_texture = {
        'texture': 'unknown',
        'paired': False,
        'flush_possible': False,
        'straight_possible': False
    }
    
    # Basic board texture analysis
    if community_cards and len(community_cards) >= 3:
        suits = [card[-1] for card in community_cards]
        suit_counts = {suit: suits.count(suit) for suit in suits}
        board_texture['flush_possible'] = any(count >= 3 for count in suit_counts.values())
        
        ranks = [card[:-1] for card in community_cards]
        board_texture['paired'] = len(set(ranks)) < len(ranks)
    
    # Try to apply cash game enhancements if available
    try:
        from cash_game_enhancements import apply_cash_game_enhancements
        
        cash_game_decision_context = {
            'hand_strength': hand_strength, # This is the string \'very_strong\', \'strong\' etc.
            'numerical_hand_rank': numerical_hand_rank, # Added for more granular analysis
            'win_probability': win_probability,
            'position': position,
            'street': street,
            'pot_size': pot_size,
            'stack_size': my_stack,
            'big_blind': big_blind_amount,
            'active_opponents': active_opponents_count,
            'opponent_analysis': opponent_analysis,
            'board_texture': board_texture,
            'bet_to_call': bet_to_call,
            'pot_odds': pot_odds_to_call
        }
        
        # Apply cash game enhancements
        cash_game_context = apply_cash_game_enhancements(cash_game_decision_context)
        advanced_context['cash_game_enhancements'] = cash_game_context
        
        logger.info(f"Cash game enhancements applied: position={position}, hand_strength={hand_strength}, confidence={cash_game_context.get('overall_confidence', 0.5):.2f}")
        
    except ImportError:
        logger.debug("Cash game enhancement modules not available")
    except Exception as e:
        logger.warning(f"Cash game enhancements failed: {e}")
    
    # 1. Advanced Opponent Modeling
    if ADVANCED_MODULES_AVAILABLE and opponent_tracker:
        try:
            analyzer = AdvancedOpponentAnalyzer()
            
            # Initialize with existing opponent data
            for opponent_name, profile in opponent_tracker.opponents.items():
                if profile.hands_seen > 0:
                    analyzer.update_opponent_profile(opponent_name, {
                        'vpip': profile.get_vpip(),
                        'pfr': profile.get_pfr(),
                        'hands_seen': profile.hands_seen
                    })
            
            # Get exploitative strategy
            current_situation = {
                'street': street,
                'position': my_player_data.get('position', 'BB'),
                'situation': 'facing_bet' if bet_to_call > 0 else 'checked_to'
            }
              # Get the primary opponent to analyze (first active opponent)
            opponent_list = list(opponent_tracker.opponents.keys())[:active_opponents_count]
            primary_opponent = opponent_list[0] if opponent_list else "Unknown"
            
            exploitative_strategy = analyzer.get_exploitative_strategy(
                player_name=primary_opponent,
                current_situation=current_situation
            )
            
            advanced_context['opponent_analysis'] = exploitative_strategy
            logger.info(f"Advanced opponent analysis: {exploitative_strategy['recommended_action']} - {exploitative_strategy['reasoning']}")
            
        except Exception as e:
            logger.warning(f"Advanced opponent modeling failed: {e}")
      # 2. Enhanced Board Analysis  
    if ADVANCED_MODULES_AVAILABLE:
        try:
            community_cards = my_player_data.get('community_cards', [])
            if community_cards:
                board_analyzer = EnhancedBoardAnalyzer()
                board_analysis = board_analyzer.analyze_board(community_cards)
                
                advanced_context['board_analysis'] = board_analysis
                logger.info(f"Board analysis: {board_analysis['texture']} texture, "
                          f"draws: {board_analysis['draw_analysis']['total_draws']}, "
                          f"betting_rec: {board_analysis['betting_implications']['recommended_sizing']}")
                
        except Exception as e:
            logger.warning(f"Enhanced board analysis failed: {e}")
      # 3. Performance Monitoring Setup
    if ADVANCED_MODULES_AVAILABLE:
        try:
            perf_tracker = PerformanceMetrics()
            
            # Record current decision context for analysis
            decision_context = {
                'street': street,
                'hand_rank': numerical_hand_rank,
                'win_probability': win_probability,
                'pot_odds': pot_odds_to_call,
                'bet_to_call': bet_to_call,
                'pot_size': pot_size,
                'stack_size': my_stack,
                'opponents': active_opponents_count
            }
            
            advanced_context['performance_tracker'] = perf_tracker
            advanced_context['decision_context'] = decision_context
            
        except Exception as e:
            logger.warning(f"Performance monitoring setup failed: {e}")
            
    logger.debug(f"Advanced enhancements integrated: {list(advanced_context.keys())}")
      # Enhanced hand strength classification (FIX #1: Inconsistent Hand Classification)
    try:
        from enhanced_postflop_improvements import classify_hand_strength_enhanced as classify_hand_strength_improved, standardize_pot_commitment_thresholds
        
        hand_strength = classify_hand_strength_improved(
            numerical_hand_rank=numerical_hand_rank,
            win_probability=win_probability,
            hand_description=hand_description
        )
        
        is_very_strong = hand_strength == 'very_strong'
        is_strong = hand_strength == 'strong'
        is_medium = hand_strength == 'medium'
        is_weak = hand_strength in ['weak_made', 'very_weak', 'drawing']
        
        # Standardized pot commitment thresholds (FIX #5: Pot Commitment Logic)
        commitment_threshold = standardize_pot_commitment_thresholds(hand_strength, street, spr)
        
        logger.debug(f"Enhanced classification: {hand_strength}, commitment_threshold: {commitment_threshold:.2%}")
        
    except ImportError:
        # Fallback to original logic if enhanced module not available
        logger.warning("Enhanced postflop improvements not available, using original logic")
        is_very_strong = numerical_hand_rank >= VERY_STRONG_HAND_THRESHOLD or win_probability > 0.85
        is_strong = not is_very_strong and (numerical_hand_rank >= STRONG_HAND_THRESHOLD or win_probability > 0.65)
        is_medium = not is_very_strong and not is_strong and (numerical_hand_rank >= MEDIUM_HAND_THRESHOLD or win_probability > 0.45)
        
        if is_very_strong or is_strong:
            commitment_threshold = 0.6  # 60% for strong hands
        elif is_medium:
            commitment_threshold = 0.45  # 45% for medium hands
        else:
            commitment_threshold = 0.35  # 35% for weak hands (with drawing equity)
    
    is_pot_committed = pot_commitment_ratio >= commitment_threshold
    
    logger.debug(
        f"Pot commitment check: committed_amount={committed_amount}, bet_to_call={bet_to_call}, "
        f"total_commitment_if_call={total_commitment_if_call}, my_stack={my_stack}, "
        f"pot_commitment_ratio={pot_commitment_ratio:.2%}, commitment_threshold={commitment_threshold:.2%}, "
        f"is_pot_committed={is_pot_committed}"
    )
      # Enhanced opponent analysis using tracking data (FIX #4: Opponent Tracker Integration)
    # Addressing Issue #2: Contradictory Opponent Analysis Logging
    # The goal is to have one primary source of opponent_analysis for decision making.
    # If enhanced_postflop_improvements.fix_opponent_tracker_integration is available and works,
    # it should be the preferred source. Otherwise, fall back to other methods.

    final_opponent_analysis = None
    opponent_analysis_source = "unknown"

    try:
        from enhanced_postflop_improvements import fix_opponent_tracker_integration
        final_opponent_analysis = fix_opponent_tracker_integration(opponent_tracker, active_opponents_count)
        opponent_analysis_source = "enhanced_postflop_improvements.fix_opponent_tracker_integration"
        logger.info(f"Using opponent analysis from: {opponent_analysis_source}")
        logger.info(f"Enhanced opponent analysis: tracked={final_opponent_analysis.get('tracked_count', 'N/A')}, "
                   f"table_type={final_opponent_analysis.get('table_type', 'N/A')}, "
                   f"avg_vpip={final_opponent_analysis.get('avg_vpip', 0.0):.1f}, "
                   f"reasoning={final_opponent_analysis.get('reasoning', 'N/A')}")

    except ImportError:
        logger.warning("Module 'enhanced_postflop_improvements.fix_opponent_tracker_integration' not available.")
    except Exception as e:
        logger.error(f"Error in fix_opponent_tracker_integration: {e}", exc_info=True)

    if final_opponent_analysis is None:
        logger.warning("Falling back on opponent analysis methods due to previous failure or unavailability.")
        # Fallback to fixed_opponent_integration if the primary one failed or wasn't available
        if ENHANCED_MODULES_AVAILABLE:
            try:
                # This was the one logged as "Fixed opponent analysis" in the logs
                fixed_analysis = get_fixed_opponent_analysis(opponent_tracker, active_opponents_count)
                # We need to ensure this data is compatible or transformed if used as final_opponent_analysis
                # For now, let's assume it provides a similar structure or we adapt its usage.
                # To avoid direct contradiction, we will prefer the `fix_opponent_tracker_integration` if it ran.
                # If that failed, this is our next best.
                final_opponent_analysis = fixed_analysis # Potentially adapt this structure
                opponent_analysis_source = "fixed_opponent_integration.get_fixed_opponent_analysis"
                logger.info(f"Using opponent analysis from: {opponent_analysis_source}")
                logger.info(f"Fixed opponent analysis (fallback): tracked={final_opponent_analysis.get('tracked_count', 'N/A')}, "
                           f"table_type={final_opponent_analysis.get('table_type', 'N/A')}, "
                           f"avg_vpip={final_opponent_analysis.get('avg_vpip', 0.0):.1f}%, " # Original log had % here
                           f"fold_equity={final_opponent_analysis.get('fold_equity_estimate', 0.0):.1%}")

            except Exception as e:
                logger.error(f"Error in get_fixed_opponent_analysis: {e}", exc_info=True)
        else:
            logger.warning("ENHANCED_MODULES_AVAILABLE is False, cannot use get_fixed_opponent_analysis.")

    # If still no analysis, use a default unknown state
    if final_opponent_analysis is None:
        logger.warning("All opponent analysis methods failed or were unavailable. Using default unknown state.")
        final_opponent_analysis = {
            'tracked_count': 0,
            'table_type': 'unknown',
            'avg_vpip': 25.0, # Default VPIP
            'fold_equity_estimate': 0.5, # Default fold equity
            'reasoning': 'all_sources_failed_using_default',
            'player_type_distribution': {'unknown': 1.0}
        }
        opponent_analysis_source = "default_unknown_state"
        logger.info(f"Using opponent analysis from: {opponent_analysis_source}")

    # Ensure essential keys exist in final_opponent_analysis to prevent KeyErrors later
    final_opponent_analysis.setdefault('table_type', 'unknown')
    final_opponent_analysis.setdefault('fold_equity_estimate', 0.5)
    final_opponent_analysis.setdefault('avg_vpip', 25.0)
    final_opponent_analysis.setdefault('reasoning', 'default_values_applied')

    # Now, `final_opponent_analysis` should be the single source of truth for opponent data.
    # Update variables that were previously set by different opponent analysis sections.
    opponent_context = {'current_analysis': final_opponent_analysis, 'source': opponent_analysis_source}
    estimated_opponent_range = final_opponent_analysis['table_type'] # Or a more specific range if available
    fold_equity_estimate = final_opponent_analysis['fold_equity_estimate']

    # The old opponent_context and related logic can be removed or refactored
    # to use `final_opponent_analysis`.
    # For example, the section "Legacy opponent analysis for compatibility" might no longer be needed
    # if `final_opponent_analysis` is always populated.

    # Remove legacy opponent analysis block as it's now consolidated
    # logger.debug(f\"Opponent analysis: {len(opponent_context)} opponents tracked, table type: {table_dynamics.get(\'table_type\', \'unknown\')}, estimated_range: {estimated_opponent_range}\")

    # Calculate SPR adjustments for strategy
    drawing_potential = is_drawing_hand(win_probability, numerical_hand_rank, street)
    spr_strategy = calculate_spr_adjustments(spr, numerical_hand_rank, drawing_potential)
    
    logger.debug(f"SPR analysis: spr={spr:.2f}, strategy={spr_strategy}, drawing_potential={drawing_potential}")
      # Enhanced hand strength classification with more conservative thresholds
    # The issue: KQ with pair of 9s (numerical_hand_rank=2) was being classified as "medium"
    # but it's actually a weak hand (just bottom pair with medium kicker)
    
    # For one pair hands, be much more conservative about classification
    if numerical_hand_rank == 2:  # One pair
        # Addressing Issue #3: Hand Strength Classification Thresholds (weak_made for 52.8% win_prob)
        # If win_prob is > 0.5, it should at least be medium or potentially strong depending on context.
        # Classifying 52.8% as \'weak_made\' seems too pessimistic.
        if win_probability >= 0.75: # Strong top pair, overpair etc.
            is_very_strong = False # Unlikely for just one pair unless it's quads on board etc.
            is_strong = True
            is_medium = False
        elif win_probability >= 0.60: # Decent top pair, good middle pair
            is_very_strong = False
            is_strong = True # Let's try classifying as strong if win_prob is 60%+
            is_medium = False
        elif win_probability >= 0.45: # Middle pair, weak top pair, strong bottom pair
            is_very_strong = False
            is_strong = False
            is_medium = True
        else: # Weak one pair (bottom pair, very weak kicker)
            is_very_strong = False
            is_strong = False
            is_medium = False # This will make it weak
    else:
        # For non-one-pair hands, use original logic (or the enhanced classification if available)
        # This part assumes `is_very_strong`, `is_strong`, `is_medium` might have been set by
        # the `enhanced_postflop_improvements` block earlier. We should respect that if it ran.
        # If that block didn't run, this is the fallback.
        if not ('classify_hand_strength_improved' in locals() or 'classify_hand_strength_improved' in globals()):
            is_very_strong = numerical_hand_rank >= VERY_STRONG_HAND_THRESHOLD or win_probability > 0.85
            is_strong = not is_very_strong and (numerical_hand_rank >= STRONG_HAND_THRESHOLD or win_probability > 0.65)
            is_medium = not is_very_strong and not is_strong and (numerical_hand_rank >= MEDIUM_HAND_THRESHOLD or win_probability > 0.45)
    
    # Final classification based on the flags
    if is_very_strong:
        hand_strength_final_decision = 'very_strong'
    elif is_strong:
        hand_strength_final_decision = 'strong'
    elif is_medium:
        hand_strength_final_decision = 'medium'
    else: # is_weak implicitly
        # Distinguish between weak_made and drawing/very_weak based on numerical rank and win_prob
        if numerical_hand_rank >= 1: # Has at least high card, pair, etc.
            hand_strength_final_decision = 'weak_made'
        elif is_drawing_hand(win_probability, numerical_hand_rank, street):
            hand_strength_final_decision = 'drawing'
        else:
            hand_strength_final_decision = 'very_weak'

    is_weak = hand_strength_final_decision in ['weak_made', 'very_weak', 'drawing']

    logger.debug(f"Final Hand strength for decision: {hand_strength_final_decision} (is_weak={is_weak}). Original numerical_rank={numerical_hand_rank}, win_prob={win_probability:.2%}")
    logger.info(f"Post-adjustment hand strength: very_strong={is_very_strong}, strong={is_strong}, medium={is_medium}, weak={is_weak} (Final Category: {hand_strength_final_decision})")


    if can_check:
        logger.debug("Option to check is available.")
        
        # Apply SPR strategy adjustments before betting decisions
        if spr_strategy == 'commit' and (is_very_strong or is_strong):
            # Low SPR - commit with strong hands
            logger.debug(f"Low SPR ({spr:.2f}) strategy: commit with strong hand")
            bet_amount = min(my_stack, pot_size * 1.5)  # Aggressive betting to build pot/commit
            if bet_amount > 0:
                logger.info(f"Decision: BET (SPR commit strategy). Amount: {bet_amount:.2f}")
                return action_raise_const, round(bet_amount, 2)
            else:
                logger.info("Decision: CHECK (SPR commit but optimal bet is 0).")
                return action_check_const, 0
                
        elif spr_strategy == 'value_build_pot' and is_very_strong:
            # High SPR - build pot with very strong hands
            logger.debug(f"High SPR ({spr:.2f}) strategy: value build pot")
            bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff=False)
            bet_amount *= 1.2  # 20% larger bets to build pot
            bet_amount = min(bet_amount, my_stack)
            if bet_amount > 0:
                logger.info(f"Decision: BET (SPR value build pot strategy). Amount: {bet_amount:.2f}")
                return action_raise_const, round(bet_amount, 2)
            else:
                logger.info("Decision: CHECK (SPR value build pot but optimal bet is 0).")
                return action_check_const, 0
                
        elif spr_strategy == 'fold_weak' and not is_very_strong:
            # High SPR - fold weak hands more readily
            logger.debug(f"High SPR ({spr:.2f}) strategy: fold weak hands")
            if not is_strong and bet_to_call > 0:
                logger.info(f"Decision: CHECK (SPR fold weak strategy when can check).")
                return action_check_const, 0
        
        # MULTIWAY BETTING FIX (#2): Check multiway situation before betting
        try:
            from enhanced_postflop_improvements import get_multiway_betting_adjustment
            hand_strength = 'very_strong' if is_very_strong else 'strong' if is_strong else 'medium' if is_medium else 'weak'
            multiway_check = get_multiway_betting_adjustment(hand_strength, active_opponents_count, win_probability)
            
            if not multiway_check['should_bet']:
                logger.info(f"Decision: CHECK (multiway adjustment - {multiway_check['reasoning']})")
                return action_check_const, 0
        except ImportError:
            logger.debug("Multiway betting adjustment not available")
        
        if is_very_strong or (is_strong and win_probability > 0.75): # Value bet strong hands
            
            # Use advanced context to adjust betting strategy
            bet_adjustment_factor = 1.0
            
            # Apply cash game enhancements
            if 'cash_game_enhancements' in advanced_context:
                cash_enhancements = advanced_context['cash_game_enhancements']
                
                # Position-based adjustments
                position_adj = cash_enhancements.get('position_adjustments', {})
                if position_adj:
                    position_multiplier = position_adj.get('aggression_multiplier', 1.0)
                    bet_adjustment_factor *= position_multiplier
                    logger.debug(f"Cash game position adjustment ({my_player_data.get('position', 'unknown')}): {position_multiplier:.2f}")
                
                # Optimized bet sizing
                bet_sizing = cash_enhancements.get('optimized_bet_sizing', {})
                if bet_sizing and 'pot_fraction' in bet_sizing:
                    # Use cash game optimized sizing instead of default
                    cash_game_fraction = bet_sizing['pot_fraction']
                    logger.debug(f"Cash game optimized bet sizing: {cash_game_fraction:.2f} of pot")
                
                # Thin value analysis
                thin_value = cash_enhancements.get('thin_value_analysis', {})
                if thin_value.get('is_thin_value_spot', False):
                    # Adjust for thin value situations
                    thin_value_confidence = thin_value.get('confidence', 0.5)
                    if thin_value_confidence > 0.7:
                        bet_adjustment_factor *= 1.1  # Slightly larger for confident thin value
                        logger.debug(f"Thin value spot detected (confidence: {thin_value_confidence:.2f}) - increasing bet")
                
                # Stack depth adjustments
                stack_strategy = cash_enhancements.get('stack_strategy', {})
                if stack_strategy:
                    stack_type = stack_strategy.get('strategy_type', 'standard')
                    if stack_type == 'deep_stack':
                        bet_adjustment_factor *= 1.05  # Slightly larger bets with deep stacks
                        logger.debug("Deep stack strategy - increasing bet size")
                    elif stack_type == 'short_stack':
                        bet_adjustment_factor *= 0.95  # Smaller bets with short stacks
                        logger.debug("Short stack strategy - decreasing bet size")
            
            # Apply advanced opponent analysis
            if 'opponent_analysis' in advanced_context:
                opp_analysis = advanced_context['opponent_analysis']
                if opp_analysis['recommended_action'] == 'bet_larger':
                    bet_adjustment_factor *= 1.2
                    logger.debug(f"Advanced opponent analysis suggests larger bet: {opp_analysis['reasoning']}")
                elif opp_analysis['recommended_action'] == 'bet_smaller':
                    bet_adjustment_factor *= 0.8
                    logger.debug(f"Advanced opponent analysis suggests smaller bet: {opp_analysis['reasoning']}")
            
            # Apply board texture analysis
            if 'board_analysis' in advanced_context:
                board_analysis = advanced_context['board_analysis']
                board_texture = board_analysis.get('texture', 'unknown')
                
                if board_texture == 'very_wet':
                    bet_adjustment_factor *= 1.1  # Bet bigger on wet boards for protection
                    logger.debug("Wet board detected - increasing bet size for protection")
                elif board_texture == 'very_dry':
                    bet_adjustment_factor *= 0.9  # Bet smaller on dry boards to induce calls
                    logger.debug("Dry board detected - decreasing bet size to induce calls")
                
                # Consider draw-heavy boards
                draw_count = board_analysis.get('draw_analysis', {}).get('total_draws', 0)
                if draw_count >= 6:  # Many draws available
                    bet_adjustment_factor *= 1.15  # Bet bigger for protection
                    logger.debug(f"Draw-heavy board ({draw_count} draws) - increasing bet for protection")
            
            try:
                from enhanced_postflop_improvements import get_consistent_bet_sizing
                
                # Get enhanced bet sizing
                bet_size_fraction = get_consistent_bet_sizing(
                    hand_strength='very_strong' if is_very_strong else 'strong',
                    pot_size=pot_size,
                    street=street,                    spr=spr
                )
                
                bet_amount = pot_size * bet_size_fraction * bet_adjustment_factor
                bet_amount = min(bet_amount, my_stack)
                logger.debug(f"Enhanced bet sizing: {bet_size_fraction:.2f} of pot * {bet_adjustment_factor:.2f} adjustment = {bet_amount:.2f}")
                
            except ImportError:
                logger.warning("Enhanced bet sizing not available, using fallback")
                # Fallback to original logic
                bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff=False)
                
                # Apply advanced context adjustment to fallback as well
                bet_amount *= bet_adjustment_factor
                  # Adjust bet size based on opponent types
                if opponent_context:
                    # Against loose players, can bet larger for value
                    valid_opponents = [opp for opp in opponent_context.values() if isinstance(opp, dict) and 'vpip' in opp]
                    if valid_opponents:
                        avg_vpip = sum(opp['vpip'] for opp in valid_opponents) / len(valid_opponents)
                        if avg_vpip > 30:  # Loose table
                            bet_amount *= 1.15  # 15% larger bets
                            logger.debug(f"Loose opponents detected (avg VPIP {avg_vpip:.1f}%), increasing bet size by 15%")
                        elif avg_vpip < 20:  # Tight table
                            bet_amount *= 0.9   # 10% smaller bets
                            logger.debug(f"Tight opponents detected (avg VPIP {avg_vpip:.1f}%), decreasing bet size by 10%")
                
                # Adjust bet size for multiway pots - be more conservative with more opponents
                if active_opponents_count > 1:
                    multiway_factor = max(0.5, 1.0 - (active_opponents_count - 1) * 0.3)  # More aggressive reduction
                    original_bet_amount = bet_amount
                    bet_amount *= multiway_factor
                    logger.info(f"Multiway adjustment: {active_opponents_count} opponents, factor: {multiway_factor:.2f}, original: {original_bet_amount:.2f}, adjusted: {bet_amount:.2f}")
                else:
                    logger.debug(f"Heads-up: {active_opponents_count} opponent, no adjustment")
                bet_amount = min(bet_amount, my_stack)
            if bet_amount > 0:
                logger.info(f"Decision: BET (very_strong/strong with win_prob > 0.75, can check). Amount: {bet_amount:.2f}")
                return action_raise_const, round(bet_amount, 2) # Changed action_bet_const to action_raise_const
            else:
                logger.info("Decision: CHECK (very_strong/strong, but optimal bet is 0).")
                return action_check_const, 0
                
        elif is_strong: # Check/bet with strong hands (less aggressive than very_strong)
            # This is for the "thin value" case where we want to bet if checked to.
            # Check if this is a good thin value spot using advanced analysis
            is_thin_value = is_thin_value_spot(numerical_hand_rank, win_probability, estimated_opponent_range, 'unknown')
            
            if is_thin_value or win_probability > 0.65:
                bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff=False)
                  # Adjust bet size based on opponent tendencies for thin value
                if opponent_context:
                    # Against tight players, bet smaller for thin value
                    valid_opponents = [opp for opp in opponent_context.values() if isinstance(opp, dict) and 'vpip' in opp]
                    if valid_opponents:
                        avg_vpip = sum(opp['vpip'] for opp in valid_opponents) / len(valid_opponents)
                        if avg_vpip < 20:  # Very tight
                            bet_amount *= 0.8  # 20% smaller for thin value against tight players
                            logger.debug(f"Thin value against tight opponents (VPIP {avg_vpip:.1f}%), reducing bet size by 20%")
                
                # Adjust bet size for multiway pots
                if active_opponents_count > 1:
                    multiway_factor = max(0.5, 1.0 - (active_opponents_count - 1) * 0.3)  # More aggressive reduction
                    original_bet_amount = bet_amount
                    bet_amount *= multiway_factor
                    logger.info(f"Multiway adjustment (strong): {active_opponents_count} opponents, factor: {multiway_factor:.2f}, original: {original_bet_amount:.2f}, adjusted: {bet_amount:.2f}")
                else:
                    logger.debug(f"Heads-up (strong): {active_opponents_count} opponent, no adjustment")
                
                bet_amount = min(bet_amount, my_stack)
                if bet_amount > 0:
                    logger.info(f"Decision: BET (strong hand, thin value when checked to). Amount: {bet_amount:.2f}")                
                    return action_raise_const, round(bet_amount, 2) # Changed action_bet_const to action_raise_const
            
            # If optimal bet is 0, or if we decided not to value bet, consider a bluff (though less likely for 'is_strong')
            if decision_engine_instance.should_bluff_func(pot_size, my_stack, street, win_probability):
                bluff_bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff=True)
                bluff_bet_amount = min(bluff_bet_amount, my_stack)
                if bluff_bet_amount > 0:
                    logger.info(f"Decision: BET (strong hand, bluffing when can check). Amount: {bluff_bet_amount:.2f}")
                    return action_raise_const, round(bluff_bet_amount, 2) # Changed action_bet_const to action_raise_const
            
            logger.info("Decision: CHECK (strong hand, no value bet/bluff).")
            return action_check_const, 0
        
        elif is_medium: # Check/bet or check/bluff with medium hands
            # For medium hands, consider a thin value bet if win_probability is decent.
            if win_probability > 0.5: # Threshold for thin value with medium hand
                try:
                    from enhanced_postflop_improvements import get_consistent_bet_sizing
                    
                    # Get enhanced bet sizing for medium hands
                    bet_size_fraction = get_consistent_bet_sizing(
                        hand_strength='medium',
                        pot_size=pot_size,
                        street=street,
                        spr=spr
                    )
                    
                    value_bet_amount = pot_size * bet_size_fraction
                    logger.debug(f"Enhanced medium hand bet sizing: {bet_size_fraction:.2f} of pot = {value_bet_amount:.2f}")
                    
                except ImportError:
                    logger.warning("Enhanced bet sizing not available for medium hands, using fallback")
                    # Fallback to original logic
                    value_bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff=False)
                    # Adjust bet size for multiway pots - medium hands should also be more conservative
                    if active_opponents_count > 1:
                        multiway_factor = max(0.4, 1.0 - (active_opponents_count - 1) * 0.4)  # Even more aggressive reduction
                        original_bet_amount = value_bet_amount
                        value_bet_amount *= multiway_factor
                        logger.info(f"Multiway adjustment (medium): {active_opponents_count} opponents, factor: {multiway_factor:.2f}, original: {original_bet_amount:.2f}, adjusted: {value_bet_amount:.2f}")
                    else:
                        logger.debug(f"Heads-up (medium): {active_opponents_count} opponent, no adjustment")
                
                value_bet_amount = min(value_bet_amount, my_stack)
                if value_bet_amount > 0:
                    logger.info(f"Decision: BET (medium hand, thin value when checked to). Amount: {value_bet_amount:.2f}")
                    return action_raise_const, round(value_bet_amount, 2) # Changed action_bet_const to action_raise_const
            
            # If not value betting (either win_prob too low or optimal bet was 0), consider bluffing.
            # Calculate fold equity for bluffing decision
            potential_bluff_size = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff=True)
            calculated_fold_equity = calculate_fold_equity(estimated_opponent_range, 'unknown', potential_bluff_size, pot_size)
            
            # Use fold equity in bluffing decision
            if decision_engine_instance.should_bluff_func(pot_size, my_stack, street, win_probability): 
                # Additional check: only bluff if we have sufficient fold equity
                if calculated_fold_equity > 0.4 or not opponent_context:  # Need 40%+ fold equity or no opponent data
                    bluff_bet_amount = potential_bluff_size
                    bluff_bet_amount = min(bluff_bet_amount, my_stack)
                    if bluff_bet_amount > 0:
                        logger.info(f"Decision: BET (medium hand, bluffing when can check, fold equity: {calculated_fold_equity:.2%}). Amount: {bluff_bet_amount:.2f}")
                        return action_raise_const, round(bluff_bet_amount, 2)
                else:
                    logger.info(f"Decision: CHECK (medium hand, insufficient fold equity for bluff: {calculated_fold_equity:.2%}).")
                    return action_check_const, 0
            
            logger.info("Decision: CHECK (medium hand, no value bet/bluff).")
            return action_check_const, 0
            
        else: # Weak hand - Check or bluff
            # Don't bluff with weak hands when checked to on river - be conservative
            if street == 'river' and win_probability < 0.18:
                logger.info("Decision: CHECK (weak hand, checking behind on river).")
                return action_check_const, 0
                
            if street == 'river' and decision_engine_instance.should_bluff_func(pot_size, my_stack, street, win_probability):
                bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff=True)
                if my_stack <= pot_size:
                    bet_amount = my_stack
                elif bet_amount < pot_size:
                    bet_amount = min(pot_size, my_stack)
                else:
                    bet_amount = min(bet_amount, my_stack)
                
                # Override for all-in river bluffs when pot is small relative to stack
                # This addresses scenarios like test_river_all_in_bluff_vs_small_stack.
                # If pot_size is less than 20% of my_stack (i.e., stack is > 5x pot),
                # and the current decision is to bluff bet (bet_amount > 0) but not already all-in (bet_amount < my_stack),
                # then escalate to an all-in bluff.
                if pot_size < my_stack * 0.20 and bet_amount > 0 and bet_amount < my_stack:
                    logger.info(f"River bluff: Pot ({pot_size}) is < 20% of stack ({my_stack}). Current bet decision: {bet_amount}. Overriding to all-in ({my_stack}).")
                    bet_amount = my_stack  # Go all-in
                
                if bet_amount > 0:
                    logger.info(f"Decision: BET (weak hand, river bluff when checked to). Amount: {bet_amount:.2f}, Pot: {pot_size}, Stack: {my_stack}")
                    return action_raise_const, round(bet_amount, 2) # Changed action_bet_const to action_raise_const
                else: # If bet_amount resolved to 0 (e.g. stack is 0), check.
                    logger.info(f"Decision: CHECK (weak hand, intended bluff but bet_amount is 0). Pot: {pot_size}, Stack: {my_stack}")
                    return action_check_const, 0            
            logger.info("Decision: CHECK (weak hand).")
            return action_check_const, 0
            
    else:  # Facing a bet
        logger.debug(f"Facing a bet. bet_to_call: {bet_to_call}, pot_size: {pot_size}, my_stack: {my_stack}, max_bet_on_table: {max_bet_on_table}")
        # Log pot odds and win probability for all facing bet scenarios for better debugging
        logger.info(f"Facing bet: win_probability={win_probability:.2%}, pot_odds_to_call={pot_odds_to_call:.2%}, bet_to_call={bet_to_call}, pot_size={pot_size}")

        if is_very_strong:
          logger.debug(f"Hand is_very_strong. win_probability: {win_probability}")
          
          # On river with very strong hands (but not the nuts), be more conservative against large bets
          # This addresses test_river_full_house_vs_quads_possible where bot should call, not raise
          if street == 'river' and bet_to_call >= my_stack * 0.5:
              # Facing a large bet (half our stack or more) on river - be conservative even with very strong hands
              if win_probability <= 0.85:  # Not absolute nuts
                  call_amount = bet_to_call
                  logger.info(f"Decision: CALL (very_strong but conservative vs large river bet). Amount to call: {call_amount:.2f}")
                  return action_call_const, round(call_amount, 2)
          
          # Determine the minimum valid total raise amount
          # A raise must be at least the size of the last bet/raise.
          # last_bet_or_raise_size = max_bet_on_table - (sum of previous bets in this round by other players before this max_bet_on_table)
          # This is complex. A simpler rule: if opponent bet B (making current max_bet_on_table = B, assuming our current_bet was 0),
          # our min raise makes our total bet 2B.
          # If our current_bet for this round is C_our, and max_bet_on_table is M, then bet_to_call is M - C_our.
          # The last aggressive action size was M - (bet just before M).
          # For simplicity: if max_bet_on_table is the current highest bet, a min-raise means we make our total bet 2 * max_bet_on_table (if we had 0 in before this bet).
          # More generally, the raise increment must be at least the last bet/raise increment.
          # If the previous bet was P, and current max_bet_on_table is M, the increment was M-P.
          # So our raise must be to at least M + (M-P).
          # If there was no P (M is the first bet), then increment is M. Our raise is to M + M = 2M.
          # This needs the bet that occurred *before* max_bet_on_table.
          # For now, let's assume a simpler rule: must raise to at least (max_bet_on_table + bet_to_call).
          # This means if opponent bet 10 (max_bet_on_table=10, bet_to_call=10 if we had 0 in), we raise to at least 20.
          # If we had 5 in, opponent makes it 15 (max_bet_on_table=15, bet_to_call=10), we raise to at least 15+10=25.
          min_total_raise_to_amount = max_bet_on_table + bet_to_call 
          if bet_to_call == 0: # This case should ideally not be hit if we are "facing a bet"
               min_total_raise_to_amount = max_bet_on_table + big_blind_amount # fallback if bet_to_call is 0
          # Try to raise to 3x the opponent's total bet (max_bet_on_table)
          calculated_raise_total_amount = max_bet_on_table * 3
          
          if calculated_raise_total_amount < min_total_raise_to_amount:
              calculated_raise_total_amount = min_total_raise_to_amount
          # Amount to raise is total, capped by stack (my_stack is remaining, current_bet is already out)
          # So, total possible bet is my_stack + my_player_data.get('current_bet', 0)
          final_raise_amount = min(calculated_raise_total_amount, my_stack + my_player_data.get('current_bet', 0))
          
          is_all_in_raise = (final_raise_amount == my_stack + my_player_data.get('current_bet', 0))
          # A valid raise must be:
          # 1. Greater than the current max_bet_on_table.
          # 2. The raise amount (final_raise_amount - max_bet_on_table) must be >= bet_to_call (the last bet increment)
          #    OR it's an all-in for less than a full min-raise but still more than a call.
          # Simplified: final_raise_amount must be >= min_total_raise_to_amount OR it's an all-in.
          if final_raise_amount > max_bet_on_table and (final_raise_amount >= min_total_raise_to_amount or is_all_in_raise):
              logger.info(f"Decision: RAISE (very_strong). Total Amount: {final_raise_amount:.2f} (bet_to_call: {bet_to_call}, max_bet: {max_bet_on_table}, min_raise_to: {min_total_raise_to_amount})")
              return action_raise_const, round(final_raise_amount, 2)
          else:
              # If calculated raise is not valid, just call.
              logger.warning(f"Calculated raise for very_strong hand was invalid or too small. final_raise_amount: {final_raise_amount}, max_bet_on_table: {max_bet_on_table}, min_total_raise_to_amount: {min_total_raise_to_amount}. Defaulting to CALL.")
              call_amount = bet_to_call # Amount to add to current bet
              logger.info(f"Decision: CALL (very_strong, but failed to make a valid raise). Amount to call: {call_amount:.2f}")
              return action_call_const, round(call_amount, 2)
          
        elif is_strong:
            logger.debug(f"Hand is_strong. win_probability: {win_probability}, pot_odds: {pot_odds_to_call}")
            
            # Special case: Strong hand with low win probability facing aggressive action
            # This can happen with weak straights/flushes facing multiple bets
            bet_to_stack_ratio = bet_to_call / my_stack if my_stack > 0 else 1.0
            if win_probability < 0.40 and bet_to_stack_ratio > 0.35:
                logger.info(f"Decision: FOLD (strong hand but low win_prob {win_probability:.2f} and large bet {bet_to_stack_ratio:.2f} of stack).")
                return action_fold_const, 0
            
            # Check if this might be a bluff we should call
            should_call_as_bluff_catcher = should_call_bluff(
                numerical_hand_rank, win_probability, pot_odds_to_call, 
                estimated_opponent_range, bet_to_call, pot_size
            )
            
            if win_probability > pot_odds_to_call or should_call_as_bluff_catcher or (street == 'river' and win_probability > 0.7): # Good odds or strong river hand
                # Consider raising if pot odds are very good or implied odds are high
                # For now, just call with strong hands if odds are met.
                call_amount = bet_to_call
                logger.info(f"Decision: CALL (strong hand, good odds/river{'/bluff-catcher' if should_call_as_bluff_catcher else ''}). Amount to call: {call_amount:.2f}")
                return action_call_const, round(call_amount, 2)
            else: # Not good enough odds for a strong-ish hand
                # Calculate bet_to_pot_ratio for this specific bluff scenario
                current_bet_to_pot_ratio = bet_to_call / pot_size if pot_size > 0 else 0.5
                if decision_engine_instance.should_bluff_func(pot_size, my_stack, street, win_probability, bet_to_pot_ratio_for_bluff=current_bet_to_pot_ratio):                    # Min raise logic from above
                    min_total_raise_to_amount = max_bet_on_table + bet_to_call
                    if bet_to_call == 0: min_total_raise_to_amount = max_bet_on_table + big_blind_amount
                    calculated_raise_total_amount = max_bet_on_table * 2.5 # Smaller semi-bluff raise
                    if calculated_raise_total_amount < min_total_raise_to_amount:
                        calculated_raise_total_amount = min_total_raise_to_amount
                    final_raise_amount = min(calculated_raise_total_amount, my_stack + my_player_data.get('current_bet', 0))
                    is_all_in_raise = (final_raise_amount == my_stack + my_player_data.get('current_bet', 0))

                    if final_raise_amount > max_bet_on_table and (final_raise_amount >= min_total_raise_to_amount or is_all_in_raise):
                        logger.info(f"Decision: RAISE (strong hand, semi-bluff). Total Amount: {final_raise_amount:.2f}")
                        return action_raise_const, round(final_raise_amount, 2)
                
                logger.info(f"Decision: FOLD (strong hand, but odds not good enough, no semi-bluff). Bet_to_call: {bet_to_call}, Pot: {pot_size}")
                return action_fold_const, 0
        
        elif is_medium:
            logger.debug(f"Hand is_medium. win_probability: {win_probability:.2%}, pot_odds: {pot_odds_to_call:.2%}") # Added percentage formatting

            # FIX for incorrect fold with strong equity (Issue #1 from POKER_BOT_ANALYSIS_IMPROVEMENTS.md)
            # If win probability is significantly greater than pot odds, it\'s usually a call with a medium strength hand.
            # The previous logic might have been too quick to fold.
            # Example: win_prob=0.694, pot_odds=0.09. Bot folded. This should be a call.

            # Check for pot commitment first, as this might override other decisions
            if is_pot_committed:
                call_amount = bet_to_call
                logger.info(f"Decision: CALL (medium hand, pot committed). Amount to call: {call_amount:.2f}, Win Prob: {win_probability:.2%}, Pot Odds: {pot_odds_to_call:.2%}")
                return action_call_const, round(call_amount, 2)

            if win_probability > pot_odds_to_call:
                # Consider implied odds for drawing hands or hands that can improve significantly
                is_draw = is_drawing_hand(win_probability, numerical_hand_rank, street)
                can_call_on_implied_odds = False
                if is_draw:
                    # Assuming a function should_call_with_draws exists and is imported
                    # It would need opponent stack, effective stack, etc.
                    # For now, let\'s assume a simplified check or that it\'s part of win_prob
                    if should_call_with_draws(win_probability, pot_odds_to_call, pot_size, bet_to_call, my_stack, decision_engine_instance.get_effective_stack_for_implied_odds()):
                         can_call_on_implied_odds = True
                         logger.info(f"Medium hand is a draw, considering implied odds. Win Prob: {win_probability:.2%}, Pot Odds: {pot_odds_to_call:.2%}")


                if win_probability > pot_odds_to_call + 0.10 or can_call_on_implied_odds: # Adding a buffer or checking implied odds
                    call_amount = bet_to_call
                    logger.info(f"Decision: CALL (medium hand, win_prob > pot_odds + 10% or implied odds). Amount to call: {call_amount:.2f}, Win Prob: {win_probability:.2%}, Pot Odds: {pot_odds_to_call:.2%}")
                    return action_call_const, round(call_amount, 2)
                elif win_probability > pot_odds_to_call: # Still call if direct odds are good, even if not by a large margin
                    call_amount = bet_to_call
                    logger.info(f"Decision: CALL (medium hand, win_prob > pot_odds). Amount to call: {call_amount:.2f}, Win Prob: {win_probability:.2%}, Pot Odds: {pot_odds_to_call:.2%}")
                    return action_call_const, round(call_amount, 2)


            # If not calling based on direct/implied odds, then consider folding.
            # The original log showed: "Decision: FOLD (medium hand, odds not good or bet too large)"
            # We need to ensure the "odds not good" part is correctly evaluated.
            # The "bet too large" part might relate to stack preservation if odds are borderline.

            # Consider bluff catching if opponent is aggressive and bet is not too large
            # This requires opponent modeling, which is handled by `should_call_bluff`
            should_call_as_bluff_catcher = should_call_bluff(
                numerical_hand_rank, win_probability, pot_odds_to_call,
                estimated_opponent_range, bet_to_call, pot_size
            )
            if should_call_as_bluff_catcher:
                call_amount = bet_to_call
                logger.info(f"Decision: CALL (medium hand, bluff catching). Amount to call: {call_amount:.2f}, Win Prob: {win_probability:.2%}, Pot Odds: {pot_odds_to_call:.2%}")
                return action_call_const, round(call_amount, 2)
            
            # If none of the above conditions to call are met, then fold.
            logger.info(f"Decision: FOLD (medium hand, odds not good or bet too large after re-evaluation). Bet_to_call: {bet_to_call:.2f}, Pot: {pot_size:.2f}, Win Prob: {win_probability:.2%}, Pot Odds: {pot_odds_to_call:.2%}")
            return action_fold_const, 0
        
        elif is_weak: # Check or bluff
            # Don't bluff with weak hands when checked to on river - be conservative
            if street == 'river' and win_probability < 0.18:
                logger.info("Decision: CHECK (weak hand, checking behind on river).")
                return action_check_const, 0
                
            if street == 'river' and decision_engine_instance.should_bluff_func(pot_size, my_stack, street, win_probability):
                bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff=True)
                if my_stack <= pot_size:
                    bet_amount = my_stack
                elif bet_amount < pot_size:
                    bet_amount = min(pot_size, my_stack)
                else:
                    bet_amount = min(bet_amount, my_stack)
                
                # Override for all-in river bluffs when pot is small relative to stack
                # This addresses scenarios like test_river_all_in_bluff_vs_small_stack.
                # If pot_size is less than 20% of my_stack (i.e., stack is > 5x pot),
                # and the current decision is to bluff bet (bet_amount > 0) but not already all-in (bet_amount < my_stack),
                # then escalate to an all-in bluff.
                if pot_size < my_stack * 0.20 and bet_amount > 0 and bet_amount < my_stack:
                    logger.info(f"River bluff: Pot ({pot_size}) is < 20% of stack ({my_stack}). Current bet decision: {bet_amount}. Overriding to all-in ({my_stack}).")
                    bet_amount = my_stack  # Go all-in
                
                if bet_amount > 0:
                    logger.info(f"Decision: BET (weak hand, river bluff when checked to). Amount: {bet_amount:.2f}, Pot: {pot_size}, Stack: {my_stack}")
                    return action_raise_const, round(bet_amount, 2) # Changed action_bet_const to action_raise_const
                else: # If bet_amount resolved to 0 (e.g. stack is 0), check.
                    logger.info(f"Decision: CHECK (weak hand, intended bluff but bet_amount is 0). Pot: {pot_size}, Stack: {my_stack}")
                    return action_check_const, 0            
            logger.info("Decision: CHECK (weak hand).")
            return action_check_const, 0
            
    # Fallback, should not be reached if logic is complete
    logger.error("Fell through all decision logic in postflop. Defaulting to FOLD.")
    return action_fold_const, 0

# NEW FUNCTIONS FOR ENHANCED POSTFLOP PLAY

def estimate_opponent_range(position, preflop_action, bet_size, pot_size, street, board_texture):
    """
    Estimate opponent's likely hand range based on their actions.
    Returns a simplified range description for decision making.
    """
    if preflop_action == 'raise':
        if position in ['UTG', 'MP']:
            base_range = 'tight'  # Premium pairs, AK, AQ, suited broadways
        elif position in ['CO', 'BTN']:
            base_range = 'wide'   # All pairs, broadway, suited connectors
        elif position in ['SB', 'BB']:
            base_range = 'defend' # Wide defending range
        else:
            base_range = 'medium' # Default
    elif preflop_action == 'call':
        base_range = 'speculative'  # Drawing hands, medium pairs, suited aces
    else:
        base_range = 'unknown'
    
    # Adjust based on postflop betting
    if street != 'preflop' and bet_size > 0:
        bet_ratio = bet_size / pot_size if pot_size > 0 else 1
        if bet_ratio > 0.8:  # Large bet
            if board_texture == 'dry':
                return f"{base_range}_strong"  # Likely strong hand on dry board
            else:
                return f"{base_range}_polarized"  # Could be strong or bluff on wet board
        elif bet_ratio < 0.5:  # Small bet
            return f"{base_range}_weak"  # Likely weak hand or small value bet
    
    return base_range

def calculate_fold_equity(opponent_range, board_texture, bet_size, pot_size):
    """
    Estimate fold equity against opponent's estimated range.
    Returns probability that opponent will fold to our bet.
    """
    if opponent_range.endswith('_strong'):
        base_fold_equity = 0.2  # Strong hands rarely fold
    elif opponent_range.endswith('_weak'):
        base_fold_equity = 0.7  # Weak hands fold often
    elif opponent_range.endswith('_polarized'):
        base_fold_equity = 0.5  # Mixed range
    elif 'tight' in opponent_range:
        base_fold_equity = 0.6  # Tight players fold more
    elif 'wide' in opponent_range:
        base_fold_equity = 0.4  # Wide ranges call more
    else:
        base_fold_equity = 0.5  # Default
    
    # Adjust for bet size
    bet_ratio = bet_size / pot_size if pot_size > 0 else 1
    if bet_ratio > 1.0:  # Overbet
        base_fold_equity += 0.2
    elif bet_ratio > 0.75:  # Large bet
        base_fold_equity += 0.1
    elif bet_ratio < 0.5:  # Small bet
        base_fold_equity -= 0.1
    
    # Adjust for board texture
    if board_texture == 'wet':
        base_fold_equity -= 0.1  # Less fold equity on wet boards
    elif board_texture == 'dry':
        base_fold_equity += 0.1  # More fold equity on dry boards
    
    return max(0.1, min(0.9, base_fold_equity))

def is_thin_value_spot(hand_strength, win_probability, opponent_range, position):
    """
    Determine if this is a good spot for thin value betting.
    """
    if hand_strength < 2:  # Need at least a pair for thin value
        return False
    
    if win_probability < 0.55:  # Need reasonable equity
        return False
    
    # More liberal thin value in position
    if position in ['CO', 'BTN']:
        threshold = 0.55
    else:
        threshold = 0.60
    
    # Against weak ranges, can value bet thinner
    if 'weak' in opponent_range or 'speculative' in opponent_range:
        threshold -= 0.05
    
    return win_probability > threshold

def should_call_bluff(hand_strength, win_probability, pot_odds, opponent_range, bet_size, pot_size):
    """
    Determine if we should call a suspected bluff.
    """
    if hand_strength < 1:  # Need some made hand or strong draw
        return False
    
    # Calculate minimum defense frequency (MDF)
    bet_ratio = bet_size / pot_size if pot_size > 0 else 1
    mdf = 1 / (1 + bet_ratio)  # Minimum frequency to not be exploitable
    
    # Adjust based on opponent range
    if 'polarized' in opponent_range:
        # Against polarized ranges, need stronger hands to call
        required_equity = mdf + 0.1
    elif 'bluff_heavy' in opponent_range:
        # Against bluff-heavy ranges, can call lighter
        required_equity = mdf - 0.1
    else:
        required_equity = mdf
    
    # Compare our equity to required equity
    return win_probability >= required_equity

def calculate_spr_adjustments(spr, hand_strength, drawing_potential):
    """
    Adjust strategy based on Stack-to-Pot Ratio (SPR).
    """
    if spr < 2:  # Low SPR - commitment threshold
        # With low SPR, commit with top pair or better
        if hand_strength >= 2:
            return 'commit'
        else:
            return 'fold_or_shove'
    elif spr > 10:  # High SPR - play for stacks
        # With high SPR, need stronger hands to commit
        if hand_strength >= 4:  # Two pair or better
            return 'value_build_pot'
        elif drawing_potential:
            return 'speculative_call'
        else:
            return 'fold_weak'
    else:  # Medium SPR - standard play
        return 'standard'

# Enhanced opponent analysis using tracking data
def analyze_opponents(opponent_tracker, active_opponents_count, bet_to_call, pot_size):
    """
    Analyze opponents using tracking data for enhanced decision making.
    This function is called within make_postflop_decision to provide opponent context.
    """
    opponent_context = {}
    if opponent_tracker and active_opponents_count > 0:
        # Get table dynamics
        table_dynamics = opponent_tracker.get_table_dynamics()
        
        # Analyze each opponent (simplified for first implementation)
        for opponent_name, profile in opponent_tracker.opponents.items():
            if profile.hands_seen > 5:  # Only consider opponents with sufficient data
                player_type = profile.classify_player_type()
                fold_equity = profile.get_fold_equity_estimate('unknown', bet_to_call / pot_size if pot_size > 0 else 0.5)
                
                opponent_context[opponent_name] = {
                    'type': player_type,
                    'fold_equity': fold_equity,
                    'vpip': profile.get_vpip(),
                    'pfr': profile.get_pfr(),
                    'can_value_bet_thin': profile.should_value_bet_thin('unknown')
                }
        
        logger.debug(f"Opponent analysis: {len(opponent_context)} opponents tracked, table type: {table_dynamics.get('table_type', 'unknown')}")
    
    return opponent_context
