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
    community_cards, # ADDED community_cards parameter
    active_opponents_count=1, # Add opponent count for multiway considerations
    opponent_tracker=None,  # Add opponent tracking data
    all_players_raw_data=None, # New parameter for all players' data from parser
    action_history=None # Add action_history here
):
    street = game_stage # Use game_stage as street    
    
    if action_history is None:
        action_history = []

    # Extract position for clarity and consistent use
    position = my_player_data.get('position', 'Unknown')

    logger.debug(
        f"make_postflop_decision: street={street}, my_player_data={my_player_data}, "
        f"pot_size={pot_size}, win_prob={win_probability}, pot_odds={pot_odds_to_call}, "
        f"bet_to_call={bet_to_call}, max_bet_on_table={max_bet_on_table}, "
        f"active_opponents_count={active_opponents_count}, can_check={can_check}, "
        f"community_cards={community_cards}, position={position}, "
        f"action_history_len={len(action_history)}"
    )
    if action_history:
        logger.debug(f"Last action in history: {action_history[-1]}")

    # --- Start: action_history processing (seems mostly fine from previous attempt) ---
    last_aggressor_on_street = None
    last_bet_or_raise_action = None
    current_street_actions = [a for a in action_history if a.get('street', '').lower() == street.lower()]

    for action_item in reversed(current_street_actions):
        action_type = action_item.get('action_type', '').upper()
        if action_type in ['BET', 'RAISE']:
            last_aggressor_on_street = action_item.get('player_id')
            last_bet_or_raise_action = action_item
            break
    
    logger.debug(f"Last aggressor on {street}: {last_aggressor_on_street}, Action: {last_bet_or_raise_action}")

    was_pfr = my_player_data.get('was_preflop_aggressor', False)
    street_sequence = ['preflop', 'flop', 'turn', 'river']
    current_street_index = street_sequence.index(street.lower()) if street.lower() in street_sequence else -1
    was_aggressor_previous_street = False
    if current_street_index > 0:
        previous_street = street_sequence[current_street_index - 1]
        # last_aggressor_on_previous_street = None # Variable not used later, removed for now
        previous_street_actions = [a for a in action_history if a.get('street', '').lower() == previous_street.lower()]
        for action_item in reversed(previous_street_actions):
            action_type = action_item.get('action_type', '').upper()
            if action_type in ['BET', 'RAISE']:
                aggressor_id_previous_street = action_item.get('player_id')
                if aggressor_id_previous_street == my_player_data.get('name'):
                    was_aggressor_previous_street = True
                break 
        logger.debug(f"Was aggressor on previous street ({previous_street}): {was_aggressor_previous_street}")

    if not was_pfr and street.lower() == 'flop':
        preflop_actions = [a for a in action_history if a.get('street', '').lower() == 'preflop']
        last_preflop_aggressor = None
        for action_item in reversed(preflop_actions):
            if action_item.get('action_type', '').upper() == 'RAISE':
                last_preflop_aggressor = action_item.get('player_id')
                break 
        if last_preflop_aggressor == my_player_data.get('name'):
            was_pfr = True
            logger.debug("Inferred PFR status from action_history for flop c-bet logic.")

    if was_pfr:
        logger.debug("Player was pre-flop aggressor. Considering c-bet options.")
    
    is_facing_donk_bet = False
    if street.lower() == 'flop' and was_pfr and bet_to_call > 0 and last_aggressor_on_street and last_aggressor_on_street != my_player_data.get('name'):
        first_action_on_flop = current_street_actions[0] if current_street_actions else None
        # Check if the first actor on the flop (who bet) is not the bot (PFR) and bot is not BTN (likely OOP)
        if first_action_on_flop and \
           first_action_on_flop.get('action_type', '').upper() == 'BET' and \
           first_action_on_flop.get('player_id') != my_player_data.get('name') and \
           position != 'BTN': # Simplified: PFR is likely IP if BTN, so if not BTN and facing bet, could be donk
            is_facing_donk_bet = True
            logger.info(f"Facing a potential donk bet from {last_aggressor_on_street} on the {street}.")
    # --- End: action_history processing ---

    # --- Start: Initialize and call analysis functions to define missing variables ---
    hand_strength_final_decision = "unknown"
    final_opponent_analysis = {'table_type': 'unknown', 'is_weak_passive': False, 'fold_to_cbet': 0.5} # Added default fold_to_cbet
    board_texture_analysis = {}
    board_texture = "unknown"
    is_pot_committed = False
    spr_strategy = {'base_strategy': 'evaluate', 'can_bluff': False} # Default SPR strategy

    # Estimated opponent stack for implied odds
    estimated_opponent_stack_for_implied_odds = my_stack # Default/fallback
    if all_players_raw_data and active_opponents_count > 0: # Check active_opponents_count too
        opponent_stacks = []
        for p_id, p_data in all_players_raw_data.items():
            # Check if player is still in hand (not folded) and not the bot
            is_active_opponent = p_data.get('is_active_player', True) and not p_data.get('folded', False) and p_id != my_player_data.get('name')
            if is_active_opponent:
                 opponent_stacks.append(_parse_stack_value_for_postflop(p_data.get('stack', 0)))
        if opponent_stacks:
            estimated_opponent_stack_for_implied_odds = min(opponent_stacks) if active_opponents_count == 1 else sum(opponent_stacks) / len(opponent_stacks) # Simplification for multiway

    logger.debug(f"Estimated opponent stack for implied odds: {estimated_opponent_stack_for_implied_odds}")

    if ADVANCED_MODULES_AVAILABLE:
        try:
            if community_cards is not None: # Ensure community_cards is not None
                board_analyzer = EnhancedBoardAnalyzer(community_cards)
                board_texture_analysis = board_analyzer.analyze_board_texture()
                board_texture = board_texture_analysis.get('overall_texture', 'unknown')
                logger.debug(f"Advanced board analysis: {board_texture_analysis}")
            else:
                logger.warning("Community cards are None, cannot perform advanced board analysis.")
        except NameError: # EnhancedBoardAnalyzer might not be defined if import failed silently
             logger.warning("EnhancedBoardAnalyzer not available for advanced board analysis.")
        except Exception as e:
            logger.warning(f"Could not perform advanced board analysis: {e}")
    else: # Fallback basic board texture
        if community_cards and len(community_cards) >= 3:
            suits = [card[-1] for card in community_cards if isinstance(card, str) and len(card) > 1]
            if len(set(suits)) <= 2 and len(suits) >=3 : board_texture = "wet_flush_possible"
        logger.debug(f"Basic board texture (placeholder): {board_texture}")


    if ENHANCED_MODULES_AVAILABLE and _get_fixed_opponent_analysis_func and opponent_tracker:
        try:
            final_opponent_analysis = _get_fixed_opponent_analysis_func(
                opponent_tracker=opponent_tracker, 
                all_players_data=all_players_raw_data, 
                current_street=street,
                active_opponents_count=active_opponents_count,
                pot_size=pot_size,
                action_history=action_history 
            )
            if not isinstance(final_opponent_analysis, dict): # Ensure it's a dict
                logger.warning(f"Opponent analysis returned non-dict: {final_opponent_analysis}. Using default.")
                final_opponent_analysis = {'table_type': 'unknown', 'is_weak_passive': False, 'fold_to_cbet': 0.5}
            else: # Ensure essential keys exist
                final_opponent_analysis.setdefault('table_type', 'unknown')
                final_opponent_analysis.setdefault('is_weak_passive', False)
                final_opponent_analysis.setdefault('fold_to_cbet', 0.5) # Default fold to cbet
            logger.debug(f"Fixed opponent analysis: {final_opponent_analysis}")
        except Exception as e:
            logger.error(f"Error getting fixed opponent analysis: {e}")
            final_opponent_analysis = {'table_type': 'unknown', 'is_weak_passive': False, 'fold_to_cbet': 0.5}
    else:
        logger.warning("Enhanced opponent analysis not available or opponent_tracker missing.")

    try:
        hand_strength_final_decision = determine_final_decision_hand_strength(
            numerical_hand_rank=numerical_hand_rank, hand_description=hand_description,
            community_cards=community_cards, street=street, win_probability=win_probability, spr=spr,
            opponent_analysis_data=final_opponent_analysis, action_history=action_history,
            board_texture=board_texture # Pass board_texture
        )
        logger.debug(f"Determined final hand strength: {hand_strength_final_decision}")
    except Exception as e:
        logger.error(f"Error determining final hand strength: {e}")
        if numerical_hand_rank >= VERY_STRONG_HAND_THRESHOLD: hand_strength_final_decision = "very_strong"
        elif numerical_hand_rank >= STRONG_HAND_THRESHOLD: hand_strength_final_decision = "strong"
        elif numerical_hand_rank >= MEDIUM_HAND_THRESHOLD: hand_strength_final_decision = "medium"
        elif community_cards and my_player_data.get('hand') and is_drawing_hand(my_player_data.get('hand', []), community_cards):
            hand_strength_final_decision = "drawing"
        else: hand_strength_final_decision = "weak_made"

    is_very_strong = hand_strength_final_decision == "very_strong"
    is_strong = hand_strength_final_decision == "strong"
    is_medium = hand_strength_final_decision == "medium"
    # is_weak_final = hand_strength_final_decision in ["weak_made", "very_weak", "drawing"] # drawing is often handled as weak until made
    # Corrected is_weak_final to align with typical categories
    is_weak_made = hand_strength_final_decision == "weak_made"
    is_very_weak = hand_strength_final_decision == "very_weak" # Assuming this category exists
    is_drawing = hand_strength_final_decision == "drawing"
    is_weak_final = is_weak_made or is_very_weak # Drawing is handled separately in decision branches

    # Potentially committed based on SPR and hand strength
    if ENHANCED_MODULES_AVAILABLE and _get_spr_strategy_recommendation_func and _should_commit_stack_spr_func:
        try:
            spr_strategy_result = _get_spr_strategy_recommendation_func( # Renamed to avoid conflict
                spr=spr, hand_strength=hand_strength_final_decision, street=street,
                pot_size=pot_size, effective_stack=my_stack
            )
            if isinstance(spr_strategy_result, dict): spr_strategy = spr_strategy_result
            
            is_pot_committed_result = _should_commit_stack_spr_func( # Renamed
                spr=spr, hand_strength=hand_strength_final_decision,
                strategy_recommendation=spr_strategy 
            )
            if isinstance(is_pot_committed_result, bool): is_pot_committed = is_pot_committed_result
            logger.debug(f"SPR Strategy: {spr_strategy}, Pot Committed: {is_pot_committed}")
        except Exception as e:
            logger.error(f"Error getting SPR strategy/commitment: {e}")
    else:
        logger.warning("Enhanced SPR modules not available for strategy/commitment.")
        if spr < 1.5 and is_very_strong: is_pot_committed = True
        elif spr < 3 and is_strong and street != 'flop': is_pot_committed = True


    effectively_can_genuinely_check = can_check and bet_to_call == 0
    # --- End: Initialize and call analysis functions ---

    if effectively_can_genuinely_check:
        logger.debug("Option to genuinely check is available (can_check=True, bet_to_call=0). Evaluating check vs. bet/raise.")
        
        if is_very_strong:
            if ENHANCED_MODULES_AVAILABLE and should_check_instead_of_bet: # Check function itself
                should_check_flag, check_reason = should_check_instead_of_bet(hand_strength_final_decision, win_probability, pot_size, active_opponents_count, position, street)
                if should_check_flag:
                    logger.info(f"Decision: {action_check_const} (Very strong hand, checking because: {check_reason})")
                    return action_check_const, 0
            bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, purpose="value_bet_very_strong")
            logger.info(f"Decision: {action_raise_const} {bet_amount} (Very strong hand, value bet)")
            return action_raise_const, bet_amount
        
        elif is_strong:
            if ENHANCED_MODULES_AVAILABLE and should_check_instead_of_bet:
                should_check_flag, check_reason = should_check_instead_of_bet(hand_strength_final_decision, win_probability, pot_size, active_opponents_count, position, street)
                if should_check_flag:
                    logger.info(f"Decision: {action_check_const} (Strong hand, checking because: {check_reason})")
                    return action_check_const, 0
            bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, purpose="value_bet_strong")
            logger.info(f"Decision: {action_raise_const} {bet_amount} (Strong hand, value bet)")
            return action_raise_const, bet_amount

        elif is_medium:
            can_bet_medium = False # Renamed from can_cbet_medium for clarity
            bet_purpose_detail = "thin value bet" 
            bet_factor = 0.5 # Default bet factor

            if was_pfr:
                fold_to_cbet_stat = final_opponent_analysis.get(f'fold_to_{street.lower()}_cbet', 0.5)
                logger.info(f"Medium hand, PFR on {street}. Opponent fold to C-bet: {fold_to_cbet_stat:.2f}. Win prob: {win_probability:.2f}, Opps: {active_opponents_count}")

                # Condition for value C-bet (opponent doesn't fold much, we have decent equity)
                if win_probability > (0.55 / (active_opponents_count or 1)) and fold_to_cbet_stat < 0.45:
                    can_bet_medium = True
                    bet_purpose_detail = f"c-bet for value vs sticky opponent on {street}"
                    bet_factor = 0.65
                # Condition for bluff/semi-bluff C-bet (opponent folds often)
                elif fold_to_cbet_stat > 0.55 and active_opponents_count <= 2:
                    can_bet_medium = True
                    bet_purpose_detail = f"c-bet as bluff/semi-bluff vs folding opponent on {street}"
                    bet_factor = 0.55
                # Fallback based on original logic if specific conditions not met
                elif win_probability > 0.45 and active_opponents_count <= 2: 
                    can_bet_medium = True
                    bet_purpose_detail = f"c-bet with medium strength on {street} (fallback logic)"
                    bet_factor = 0.6
            
            # If not PFR, or PFR but c-bet conditions not met, consider thin value bet if spot is good
            if not can_bet_medium and is_thin_value_spot(hand_strength_final_decision, win_probability, final_opponent_analysis.get('table_type', 'unknown'), position):
                can_bet_medium = True # Re-purpose flag for general medium strength bet
                bet_purpose_detail = "thin value bet (non-PFR or PFR check-bet)"
                bet_factor = 0.5

            if can_bet_medium:
                bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff= (bet_purpose_detail.startswith("c-bet as bluff")), purpose=bet_purpose_detail) * bet_factor
                bet_amount = max(bet_amount, big_blind_amount if big_blind_amount else 0) 
                logger.info(f"Decision: {action_raise_const} {bet_amount:.2f} (Medium hand, {bet_purpose_detail})")
                return action_raise_const, bet_amount
            else:
                if ENHANCED_MODULES_AVAILABLE and should_check_instead_of_bet:
                    should_check_flag, check_reason = should_check_instead_of_bet(hand_strength_final_decision, win_probability, pot_size, active_opponents_count, position, street)
                    if should_check_flag:
                        logger.info(f"Decision: {action_check_const} (Medium hand, {('PFR but ' if was_pfr else '')}checking because: {check_reason})")
                        return action_check_const, 0
                
                logger.info(f"Decision: {action_check_const} (Medium hand, {('PFR ' if was_pfr else '')}choosing to check-evaluate or pot control)")
                return action_check_const, 0

        elif is_drawing: 
            if was_pfr:
                can_semi_bluff_cbet = False
                fold_to_cbet_stat_draw = final_opponent_analysis.get(f'fold_to_{street.lower()}_cbet', 0.5)
                logger.info(f"Drawing hand, PFR on {street}. Opponent fold to C-bet: {fold_to_cbet_stat_draw:.2f}. Win prob (draw equity): {win_probability:.2f}, Opps: {active_opponents_count}")

                if fold_to_cbet_stat_draw > 0.5 and win_probability > 0.20 and active_opponents_count <= 2 :
                    can_semi_bluff_cbet = True
                elif win_probability > 0.30 and active_opponents_count <= 1 and fold_to_cbet_stat_draw > 0.35 : # Strong draw, can bet even if opp folds a bit less
                    can_semi_bluff_cbet = True
                    logger.info("Strong draw, considering semi-bluff c-bet with moderate opponent fold equity.")

                if can_semi_bluff_cbet:
                    bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff=True, purpose=f"semi_bluff_cbet_on_{street}")
                    logger.info(f"Decision: {action_raise_const} {bet_amount:.2f} (Drawing hand, PFR semi-bluff c-bet on {street})")
                    return action_raise_const, bet_amount
                else:
                    logger.info(f"Decision: {action_check_const} (Drawing hand, PFR choosing to check on {street}, not ideal semi-bluff or taking free card)")
                    return action_check_const, 0
            else: 
                logger.info(f"Decision: {action_check_const} (Drawing hand, not PFR, checking to see next card on {street})")
                return action_check_const, 0
            
        elif is_weak_made: 
            can_bluff = False
            log_message_detail_prefix = ""
            if was_pfr:
                fold_to_cbet_stat_weak = final_opponent_analysis.get(f'fold_to_{street.lower()}_cbet', 0.5)
                log_message_detail_prefix = f"c-bet " 
                logger.info(f"Weak made hand, PFR on {street}. Opponent fold to C-bet: {fold_to_cbet_stat_weak:.2f}. Considering {log_message_detail_prefix}bluff.")
                if fold_to_cbet_stat_weak > 0.6 and active_opponents_count <= 2: 
                    can_bluff = True
            
            if can_bluff: # Primarily for PFR c-bet bluffs with weak made hands
                bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff=True, purpose=f"pure_cbet_bluff_on_{street}")
                logger.info(f"Decision: {action_raise_const} {bet_amount:.2f} (Weak made hand, PFR {log_message_detail_prefix}bluffing on {street} due to high opponent fold rate)")
                return action_raise_const, bet_amount
            else:
                if ENHANCED_MODULES_AVAILABLE and should_check_instead_of_bet:
                    should_check_flag, check_reason = should_check_instead_of_bet(hand_strength_final_decision, win_probability, pot_size, active_opponents_count, position, street)
                    if should_check_flag: # Check if conditions (like scaring opponent) met
                        logger.info(f"Decision: {action_check_const} (Weak made hand, {('PFR but ' if was_pfr else '')}checking because: {check_reason})")
                        return action_check_const, 0
                logger.info(f"Decision: {action_check_const} (Weak made hand, checking on {street}, low fold equity for {log_message_detail_prefix}bluff or other check condition not met)")
                return action_check_const, 0
        else: # is_very_weak or other unhandled weak states
            logger.info(f"Decision: {action_check_const} (Very weak hand or unhandled weak state, check-fold strategy likely)")
            return action_check_const, 0
            
    else: # This means (bet_to_call > 0) OR (not can_check originally)
        if bet_to_call > 0:
            logger.debug(f"Facing a bet of {bet_to_call} (can_check was {can_check}). Evaluating call, raise, or fold.")
            if last_bet_or_raise_action:
                bet_originator = last_bet_or_raise_action.get('player_id')
                bet_type_faced = last_bet_or_raise_action.get('action_type')
                bet_amount_faced = last_bet_or_raise_action.get('amount')
                logger.info(f"Facing a {bet_type_faced} of {bet_amount_faced} from {bet_originator} on {street}.")

            # --- Multi-street aggression detection ---
            is_multi_street_aggressor = False
            if street.lower() in ['turn', 'river'] and last_aggressor_on_street:
                num_prior_street_bets_by_aggressor = 0
                if street.lower() == 'river':
                    turn_actions = [a for a in action_history if a.get('street','').lower() == 'turn' and a.get('player_id') == last_aggressor_on_street and a.get('action_type','').upper() in ['BET', 'RAISE']]
                    if turn_actions: num_prior_street_bets_by_aggressor +=1
                
                # Check Flop aggression (relevant for both Turn and River if checking previous streets)
                flop_actions = [a for a in action_history if a.get('street','').lower() == 'flop' and a.get('player_id') == last_aggressor_on_street and a.get('action_type','').upper() in ['BET', 'RAISE']]
                if flop_actions: num_prior_street_bets_by_aggressor +=1
                
                if street.lower() == 'turn' and num_prior_street_bets_by_aggressor >= 1: # Bet flop, now betting turn (2nd barrel)
                    is_multi_street_aggressor = True
                    logger.info(f"Aggressor {last_aggressor_on_street} is showing multi-street aggression (2nd barrel on {street}).")
                elif street.lower() == 'river' and num_prior_street_bets_by_aggressor >= 2: # Bet flop & turn, now river (3rd barrel)
                    is_multi_street_aggressor = True
                    logger.info(f"Aggressor {last_aggressor_on_street} is showing multi-street aggression (3rd barrel on {street}).")
            # --- End multi-street aggression detection ---

            if is_facing_donk_bet:
                logger.info(f"Specifically handling a donk bet of {bet_to_call} from {last_aggressor_on_street} on {street}.")
                # Opponent stats for donk bettor (e.g., from final_opponent_analysis if it has per-player details)
                # aggressor_profile = final_opponent_analysis.get('opponent_profiles', {}).get(last_aggressor_on_street)
                # fold_to_raise_after_donk = aggressor_profile.get('fold_to_raise_after_donk_flop', 0.4) if aggressor_profile else 0.4

                if is_very_strong or is_strong:
                    donk_raise_amount_factor = 2.5 
                    # if fold_to_raise_after_donk < 0.3: donk_raise_amount_factor = 3.0 # They call raises
                    # elif fold_to_raise_after_donk > 0.6: donk_raise_amount_factor = 2.0 # They fold to raises
                    raise_amount = bet_to_call * donk_raise_amount_factor 
                    min_raise_val = (bet_to_call * 2) if bet_to_call > 0 else (big_blind_amount if big_blind_amount else 0) # Local min_raise
                    min_raise_val = max(min_raise_val, big_blind_amount if big_blind_amount else 0)
                    raise_amount = max(raise_amount, min_raise_val)
                    logger.info(f"Decision: {action_raise_const} {raise_amount:.2f} (Strong/Very Strong hand, raising donk bet for value on {street})")
                    return action_raise_const, min(raise_amount, my_stack)
                elif is_medium:
                    if win_probability > pot_odds_to_call * 0.85: # Slightly better odds needed vs donk if just calling
                         logger.info(f"Decision: {action_call_const} {bet_to_call} (Medium hand, calling donk bet on {street} with reasonable equity/odds)")
                         return action_call_const, bet_to_call
                    else:
                         logger.info(f"Decision: {action_fold_const} (Medium hand, folding to donk bet on {street}, odds not good enough)")
                         return action_fold_const, 0
                elif is_drawing:
                    if my_player_data.get('hand') and community_cards and should_call_with_draws(my_player_data.get('hand', []), community_cards, win_probability, pot_size, bet_to_call, estimated_opponent_stack_for_implied_odds, my_stack, street):
                        logger.info(f"Decision: {action_call_const} {bet_to_call} (Drawing hand, calling donk bet on {street} with implied odds)")
                        return action_call_const, bet_to_call
                    elif win_probability > pot_odds_to_call: 
                        logger.info(f"Decision: {action_call_const} {bet_to_call} (Drawing hand, calling donk bet on {street} with direct pot odds)")
                        return action_call_const, bet_to_call
                    else:
                        logger.info(f"Decision: {action_fold_const} (Drawing hand, folding to donk bet on {street})")
                        return action_fold_const, 0
                else: 
                    logger.info(f"Decision: {action_fold_const} (Weak hand, folding to donk bet on {street})")
                    return action_fold_const, 0
        else: 
            logger.debug(f"Cannot check (can_check=False, bet_to_call=0). Evaluating options. This path implies forced action (e.g. all-in already).")
            # If cannot check and bet_to_call is 0, it might mean player is all-in or some other edge case.
            # The logic below assumes we can still act (fold, call (0), raise).
            # If player is all-in and action is on them with no bet to call, it's effectively a check.
            # This state should ideally be handled before this point or clarified.
            # For now, proceed with existing logic, but this is a potential area for refinement.

        min_raise_amount = max_bet_on_table + bet_to_call # Simplified: min raise is current total bet + original bet. More accurately, it's 2x last bet/raise.
                                                        # Or if no bet yet, then BB.
                                                        # For facing a bet: min raise is typically bet_to_call + (last_raise_amount or last_bet_amount)
        # A common rule: a raise must be at least the size of the previous bet or raise in the same round.
        # If last_bet_or_raise_action exists and was a bet/raise, its amount is relevant.
        # If bet_to_call > 0, then min_raise should be at least bet_to_call * 2 (from player's perspective of total new money)
        # or pot_size related. For simplicity, let's use a clearer min_raise.
        # If someone bet 50, and I call 50, new total is X. If I raise, my raise must be at least 50 more. So total bet is 100.
        min_raise = (bet_to_call * 2) if bet_to_call > 0 else (big_blind_amount if big_blind_amount else 0)
        min_raise = max(min_raise, big_blind_amount if big_blind_amount else 0)


        if is_very_strong:
            if ENHANCED_MODULES_AVAILABLE and spr_strategy.get('base_strategy') == 'commit' or is_pot_committed:
                bet_amount = my_stack 
                logger.info(f"Decision: {action_raise_const} {bet_amount} (Very strong hand, committing stack on {street}, SPR={spr:.1f})")
            else:
                bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, purpose=f"value_raise_very_strong_vs_bet_on_{street}")
                bet_amount = max(bet_amount, min_raise) 
            logger.info(f"Decision: {action_raise_const} {bet_amount} (Very strong hand, value raise vs bet on {street})")
            return action_raise_const, min(bet_amount, my_stack)

        elif is_strong:
            is_tiny_bet = bet_to_call <= (pot_size * 0.25) 
            should_call_current_bet = win_probability >= pot_odds_to_call or (is_tiny_bet and win_probability > (pot_odds_to_call * 0.7)) # Looser call for tiny bets

            if is_multi_street_aggressor and not final_opponent_analysis.get('aggressor_bluffs_multi_street', False): # Assuming this key could exist
                logger.info(f"Facing multi-street aggression from likely non-bluffer with Strong hand on {street}. Playing more cautiously.")
                if should_call_current_bet: # If direct odds are good, call, but avoid re-raising unless very good reason
                    logger.info(f"Decision: {action_call_const} {bet_to_call} (Strong hand, calling multi-street bet on {street} due to odds)")
                    return action_call_const, bet_to_call
                else:
                    logger.info(f"Decision: {action_fold_const} (Strong hand, folding to multi-street bet on {street}, odds not sufficient vs strong range)")
                    return action_fold_const, 0

            if should_call_current_bet: 
                # Consider raising if opponent is passive or we want to build pot and not facing scary multi-street aggression
                consider_raise = False
                if final_opponent_analysis.get('is_weak_passive', False) or base_aggression_factor > 0.6: # Original conditions
                     consider_raise = True
                # Add condition: if opponent folds to raises after betting
                # fold_to_raise_after_bet = final_opponent_analysis.get('opponent_profiles', {}).get(last_aggressor_on_street, {}).get(f'fold_to_raise_after_betting_{street}', 0.3)
                # if fold_to_raise_after_bet > 0.5: consider_raise = True

                if consider_raise and (spr < 4 or final_opponent_analysis.get('is_weak_passive', False)): 
                    bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, purpose=f"value_raise_strong_vs_bet_on_{street}")
                    bet_amount = max(bet_amount, min_raise)
                    logger.info(f"Decision: {action_raise_const} {bet_amount} (Strong hand, raising against bet on {street}, favorable conditions)")
                    return action_raise_const, min(bet_amount, my_stack)
                else:
                    logger.info(f"Decision: {action_call_const} {bet_to_call} (Strong hand, calling bet on {street}, good odds or tiny bet, not ideal to raise)")
                    return action_call_const, bet_to_call
            else:
                logger.info(f"Decision: {action_fold_const} (Strong hand, folding to bet on {street}, bad pot odds: {pot_odds_to_call:.2f} vs win_prob: {win_probability:.2f} and not a tiny bet or equity too low)")
                return action_fold_const, 0

        elif is_medium:
            call_for_implied_odds = my_player_data.get('hand') and community_cards and should_call_with_draws(my_player_data.get('hand', []), community_cards, win_probability, pot_size, bet_to_call, estimated_opponent_stack_for_implied_odds, my_stack, street)
            
            if is_multi_street_aggressor and not final_opponent_analysis.get('aggressor_bluffs_multi_street', False):
                 logger.info(f"Facing multi-street aggression with Medium hand on {street}. Likely folding unless amazing implied odds for a monster draw.")
                 if call_for_implied_odds and win_probability > 0.3: # Need very good draw
                    logger.info(f"Decision: {action_call_const} {bet_to_call} (Medium hand/strong draw, calling multi-street bet on {street} due to excellent implied odds)")
                    return action_call_const, bet_to_call
                 else:
                    logger.info(f"Decision: {action_fold_const} (Medium hand, folding to multi-street bet on {street})")
                    return action_fold_const, 0

            if call_for_implied_odds:
                 logger.info(f"Decision: {action_call_const} {bet_to_call} (Medium hand/draw, calling bet on {street} with implied odds)")
                 return action_call_const, bet_to_call
            elif win_probability >= pot_odds_to_call: 
                logger.info(f"Decision: {action_call_const} {bet_to_call} (Medium hand, calling bet on {street} with direct pot odds)")
                return action_call_const, bet_to_call
            else:
                if should_call_bluff(hand_strength_final_decision, win_probability, pot_odds_to_call, final_opponent_analysis.get('table_type', 'unknown'), bet_to_call, pot_size): 
                    logger.info(f"Decision: {action_call_const} {bet_to_call} (Medium hand, calling bet on {street} as a bluff catcher)")
                    return action_call_const, bet_to_call
                
                logger.info(f"Decision: {action_fold_const} (Medium hand, folding to bet on {street}, insufficient odds/bluff catching criteria)")
                return action_fold_const, 0

        elif is_drawing: 
            call_for_implied_odds_draw = my_player_data.get('hand') and community_cards and should_call_with_draws(my_player_data.get('hand', []), community_cards, win_probability, pot_size, bet_to_call, estimated_opponent_stack_for_implied_odds, my_stack, street)
            
            if is_multi_street_aggressor and not final_opponent_analysis.get('aggressor_bluffs_multi_street', False):
                logger.info(f"Facing multi-street aggression with Drawing hand on {street}. Need excellent odds/implied odds.")
                if call_for_implied_odds_draw and win_probability > 0.25 : # Stronger draw needed
                    logger.info(f"Decision: {action_call_const} {bet_to_call} (Drawing hand, calling multi-street bet on {street} due to good implied odds)")
                    return action_call_const, bet_to_call
                elif win_probability > pot_odds_to_call and win_probability > 0.33 : # Very strong combo draw for direct odds
                    logger.info(f"Decision: {action_call_const} {bet_to_call} (Strong drawing hand, calling multi-street bet on {street} with direct pot odds)")
                    return action_call_const, bet_to_call
                else:
                    logger.info(f"Decision: {action_fold_const} (Drawing hand, folding to multi-street bet on {street})")
                    return action_fold_const, 0

            if call_for_implied_odds_draw:
                logger.info(f"Decision: {action_call_const} {bet_to_call} (Drawing hand, calling bet on {street} with implied odds)")
                return action_call_const, bet_to_call
            else: 
                if win_probability > pot_odds_to_call: 
                     logger.info(f"Decision: {action_call_const} {bet_to_call} (Drawing hand, calling bet on {street} with direct pot odds for strong draw)")
                     return action_call_const, bet_to_call
                logger.info(f"Decision: {action_fold_const} (Drawing hand, folding to bet on {street}, no implied or direct odds)")
                return action_fold_const, 0
        elif is_weak_made: 
            # Explicitly handle weak_made when facing bet
            # Use final_opponent_analysis.get('table_type', 'unknown')
            if should_call_bluff(hand_strength_final_decision, win_probability, pot_odds_to_call, final_opponent_analysis.get('table_type', 'unknown'), bet_to_call, pot_size):
                logger.info(f"Decision: {action_call_const} {bet_to_call} (Weak made hand, calling as bluff catcher)")
                return action_call_const, bet_to_call
            else:
                logger.info(f"Decision: {action_fold_const} (Weak made hand, folding, not a good bluff catcher spot)")
                return action_fold_const, 0
        else: # very_weak or other unhandled states
            logger.info(f"Decision: {action_fold_const} (Very weak hand or unhandled, folding to bet on {street})")
            return action_fold_const, 0

    logger.error("Fell through all decision logic in postflop. Defaulting to FOLD.")
    return action_fold_const, 0

# Functions previously here have been moved to the postflop directory
