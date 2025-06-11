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
    # --- End: Initialize and call analysis_functions ---

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
            can_bet_medium = False 
            bet_purpose_detail = "thin value bet" 
            bet_factor = 0.5 

            if was_pfr:
                fold_to_cbet_stat = final_opponent_analysis.get(f'fold_to_{street.lower()}_cbet', 0.5)
                logger.info(f"Medium hand, PFR on {street}. Opponent fold to C-bet: {fold_to_cbet_stat:.2f}. Win prob: {win_probability:.2f}, Opps: {active_opponents_count}")

                if win_probability > (0.55 / (active_opponents_count or 1)) and fold_to_cbet_stat < 0.45:
                    can_bet_medium = True
                    bet_purpose_detail = f"c-bet for value vs sticky opponent on {street}"
                    bet_factor = 0.65
                elif fold_to_cbet_stat > 0.55 and active_opponents_count <= 2:
                    can_bet_medium = True
                    bet_purpose_detail = f"c-bet as bluff/semi-bluff vs folding opponent on {street}"
                    bet_factor = 0.55
                elif win_probability > 0.45 and active_opponents_count <= 2: 
                    can_bet_medium = True
                    bet_purpose_detail = f"c-bet with medium strength on {street} (fallback logic)"
                    bet_factor = 0.6
            
            if not can_bet_medium and is_thin_value_spot(hand_strength_final_decision, win_probability, final_opponent_analysis.get('table_type', 'unknown'), position):
                can_bet_medium = True 
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
                elif win_probability > 0.30 and active_opponents_count <= 1 and fold_to_cbet_stat_draw > 0.35 : 
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
            
            if can_bluff: 
                bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff=True, purpose=f"pure_cbet_bluff_on_{street}")
                logger.info(f"Decision: {action_raise_const} {bet_amount:.2f} (Weak made hand, PFR {log_message_detail_prefix}bluffing on {street} due to high opponent fold rate)")
                return action_raise_const, bet_amount
            else:
                if ENHANCED_MODULES_AVAILABLE and should_check_instead_of_bet:
                    should_check_flag, check_reason = should_check_instead_of_bet(hand_strength_final_decision, win_probability, pot_size, active_opponents_count, position, street)
                    if should_check_flag: 
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
            barrels = 0 
            if last_aggressor_on_street:
                flop_actions_by_aggressor = [
                    a for a in action_history if
                    a.get('street','').lower() == 'flop' and
                    a.get('player_id') == last_aggressor_on_street and
                    a.get('action_type','').upper() in ['BET', 'RAISE']
                ]
                if street.lower() == 'turn':
                    if flop_actions_by_aggressor:
                        barrels = 2 
                        is_multi_street_aggressor = True
                        logger.info(f"Aggressor {last_aggressor_on_street} is firing a 2nd barrel on the {street}.")
                elif street.lower() == 'river':
                    turn_actions_by_aggressor = [
                        a for a in action_history if
                        a.get('street','').lower() == 'turn' and
                        a.get('player_id') == last_aggressor_on_street and
                        a.get('action_type','').upper() in ['BET', 'RAISE']
                    ]
                    if flop_actions_by_aggressor and turn_actions_by_aggressor:
                        barrels = 3 
                        is_multi_street_aggressor = True
                        logger.info(f"Aggressor {last_aggressor_on_street} is firing a 3rd barrel on the {street}.")
                    elif turn_actions_by_aggressor: 
                        barrels = 2 
                        is_multi_street_aggressor = True 
                        logger.info(f"Aggressor {last_aggressor_on_street} bet the turn and is now betting the {street} (2nd consecutive barrel from them).")
            # --- End multi-street aggression detection ---

            if is_facing_donk_bet:
                logger.info(f"Specifically handling a donk bet of {bet_to_call} from {last_aggressor_on_street} on {street}.")
                aggressor_profile = final_opponent_analysis.get('opponent_profiles', {}).get(last_aggressor_on_street, {})
                donk_bet_freq = aggressor_profile.get(f'donk_bet_{street.lower()}', 0.1) 
                fold_to_raise_after_donk = aggressor_profile.get(f'fold_to_raise_after_donk_{street.lower()}', 0.5)

                logger.debug(f"Donk bettor ({last_aggressor_on_street}) profile: Donk freq on {street}: {donk_bet_freq:.2f}, Fold to raise after donk: {fold_to_raise_after_donk:.2f}")

                if is_very_strong:
                    raise_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, purpose="raise_vs_donk_value_very_strong", bet_to_call=bet_to_call, opponent_profile=aggressor_profile)
                    logger.info(f"Decision: {action_raise_const} {raise_amount} (Very strong hand vs donk bet)")
                    return action_raise_const, raise_amount
                elif is_strong:
                    if fold_to_raise_after_donk < 0.3 and spr > 4: 
                        logger.info(f"Decision: {action_call_const} (Strong hand vs sticky donk bettor, high SPR. Calling to control pot / see turn)")
                        return action_call_const, bet_to_call
                    else:
                        raise_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, purpose="raise_vs_donk_value_strong", bet_to_call=bet_to_call, opponent_profile=aggressor_profile)
                        logger.info(f"Decision: {action_raise_const} {raise_amount} (Strong hand vs donk bet, raising for value/protection)")
                        return action_raise_const, raise_amount
                elif is_medium:
                    if fold_to_raise_after_donk > 0.6 and win_probability > 0.3: 
                        raise_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, purpose="raise_vs_donk_medium_bluff_value", bet_to_call=bet_to_call, opponent_profile=aggressor_profile)
                        logger.info(f"Decision: {action_raise_const} {raise_amount} (Medium hand, raising donk due to high fold_to_raise_after_donk)")
                        return action_raise_const, raise_amount
                    elif pot_odds_to_call > 0.20: # Requires pot_odds_to_call to be defined
                        logger.info(f"Decision: {action_call_const} (Medium hand vs donk bet, calling due to pot odds)")
                        return action_call_const, bet_to_call
                    else:
                        logger.info(f"Decision: {action_fold_const} (Medium hand vs donk bet, insufficient odds/fold equity to continue)")
                        return action_fold_const, 0
                elif is_drawing:
                    required_equity_direct = bet_to_call / (pot_size + bet_to_call + bet_to_call) if (pot_size + bet_to_call + bet_to_call) > 0 else 1.0
                    if fold_to_raise_after_donk > 0.55 and win_probability > 0.25: 
                        raise_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff=True, purpose="raise_vs_donk_drawing_semibluff", bet_to_call=bet_to_call, opponent_profile=aggressor_profile)
                        logger.info(f"Decision: {action_raise_const} {raise_amount} (Drawing hand, semi-bluff raise vs donk)")
                        return action_raise_const, raise_amount
                    elif win_probability > required_equity_direct : 
                        logger.info(f"Decision: {action_call_const} (Drawing hand vs donk bet, calling for odds)")
                        return action_call_const, bet_to_call
                    else:
                        logger.info(f"Decision: {action_fold_const} (Drawing hand vs donk bet, insufficient odds to call)")
                        return action_fold_const, 0
                else: # is_weak_made or is_very_weak
                    if donk_bet_freq > 0.3 and fold_to_raise_after_donk > 0.65:
                        raise_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff=True, purpose="bluff_raise_vs_wide_donk", bet_to_call=bet_to_call, opponent_profile=aggressor_profile)
                        logger.info(f"Decision: {action_raise_const} {raise_amount} (Weak hand, bluff-raising wide/weak donk bettor)")
                        return action_raise_const, raise_amount
                    else:
                        logger.info(f"Decision: {action_fold_const} (Weak hand vs donk bet, folding)")
                        return action_fold_const, 0
                logger.warning(f"Fell through donk bet logic for hand strength {hand_strength_final_decision}. Defaulting to fold.")
                return action_fold_const, 0
            
            # General response to a bet/raise (if not a donk bet)
            aggressor_profile = final_opponent_analysis.get('opponent_profiles', {}).get(last_aggressor_on_street, {})
            opponent_aggression_street = aggressor_profile.get(f'aggression_frequency_{street.lower()}', 0.3) 
            opponent_fold_to_raise_street = aggressor_profile.get(f'fold_to_raise_{street.lower()}', 0.4)
            opponent_wtsd = aggressor_profile.get('wtsd', 0.25) 

            logger.debug(f"Facing bet from {last_aggressor_on_street}. Profile: AggFreq={opponent_aggression_street:.2f}, FoldToRaise={opponent_fold_to_raise_street:.2f}, WTSD={opponent_wtsd:.2f}, MultiStreetBarrels={barrels}")

            if is_very_strong:
                if spr < 1.0 or is_pot_committed: 
                     raise_amount = my_stack 
                else:
                    raise_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, purpose="value_raise_general_very_strong", bet_to_call=bet_to_call, opponent_profile=aggressor_profile)
                logger.info(f"Decision: {action_raise_const} {raise_amount} (Very strong hand, raising for value vs bet)")
                return action_raise_const, raise_amount
            elif is_strong:
                if is_pot_committed:
                    if win_probability > pot_odds_to_call: 
                        logger.info(f"Decision: {action_call_const} (Strong hand, pot committed, calling bet)")
                        return action_call_const, bet_to_call 
                    else: 
                        logger.info(f"Decision: {action_fold_const} (Strong hand, pot committed but equity too low vs bet, folding)")
                        return action_fold_const, 0
                if opponent_fold_to_raise_street > 0.5 and win_probability > 0.6: 
                    raise_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, purpose="value_raise_general_strong", bet_to_call=bet_to_call, opponent_profile=aggressor_profile)
                    logger.info(f"Decision: {action_raise_const} {raise_amount} (Strong hand, raising vs bet due to opponent fold equity)")
                    return action_raise_const, raise_amount
                elif win_probability > pot_odds_to_call: 
                    logger.info(f"Decision: {action_call_const} (Strong hand, calling bet due to good odds/equity)")
                    return action_call_const, bet_to_call
                else:
                    logger.info(f"Decision: {action_fold_const} (Strong hand, folding to bet, insufficient odds/raise equity)")
                    return action_fold_const, 0
            elif is_medium:
                is_opponent_passive_value_bettor = opponent_aggression_street < 0.2 and barrels == 0 
                if opponent_fold_to_raise_street > 0.65 and win_probability < 0.4: 
                    raise_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff=True, purpose="bluff_raise_medium_hand", bet_to_call=bet_to_call, opponent_profile=aggressor_profile)
                    logger.info(f"Decision: {action_raise_const} {raise_amount} (Medium hand, bluff-raising bet due to high opponent fold equity)")
                    return action_raise_const, raise_amount
                if is_opponent_passive_value_bettor and bet_to_call > pot_size * 0.5: 
                    logger.info(f"Decision: {action_fold_const} (Medium hand, folding to large bet from passive player)")
                    return action_fold_const, 0
                if barrels >=2 and win_probability < (pot_odds_to_call * 1.2 if pot_odds_to_call > 0 else 0.1): 
                     logger.info(f"Decision: {action_fold_const} (Medium hand, folding to multi-barrel, not enough equity to bluff catch)")
                     return action_fold_const, 0
                if win_probability > pot_odds_to_call:
                    logger.info(f"Decision: {action_call_const} (Medium hand, calling bet as bluff catcher / for showdown value)")
                    return action_call_const, bet_to_call
                else:
                    logger.info(f"Decision: {action_fold_const} (Medium hand, folding to bet, insufficient odds)")
                    return action_fold_const, 0
            elif is_drawing:
                required_equity_direct = bet_to_call / (pot_size + bet_to_call + bet_to_call) if (pot_size + bet_to_call + bet_to_call) > 0 else 1.0
                can_call_for_draw = win_probability > required_equity_direct 
                can_semibluff_raise = (
                    win_probability > 0.25 and opponent_fold_to_raise_street > 0.5 and
                    active_opponents_count <= 2 and spr > 2 and spr < 10 )
                if can_semibluff_raise:
                    raise_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff=True, purpose="semi_bluff_raise_drawing_hand", bet_to_call=bet_to_call, opponent_profile=aggressor_profile)
                    logger.info(f"Decision: {action_raise_const} {raise_amount} (Drawing hand, semi-bluff raising bet)")
                    return action_raise_const, raise_amount
                if can_call_for_draw:
                    logger.info(f"Decision: {action_call_const} (Drawing hand, calling bet for odds)")
                    return action_call_const, bet_to_call
                else:
                    logger.info(f"Decision: {action_fold_const} (Drawing hand, folding to bet, insufficient odds)")
                    return action_fold_const, 0
            else: # is_weak_made, is_very_weak
                can_pure_bluff_raise = (
                    opponent_aggression_street > 0.45 and opponent_fold_to_raise_street > 0.7 and
                    barrels < 2 and active_opponents_count == 1 )
                if is_pot_committed and win_probability > pot_odds_to_call: 
                     logger.info(f"Decision: {action_call_const} (Weak hand, but pot committed with some equity, calling bet)")
                     return action_call_const, bet_to_call
                if can_pure_bluff_raise:
                    raise_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, bluff=True, purpose="pure_bluff_raise_weak_hand", bet_to_call=bet_to_call, opponent_profile=aggressor_profile)
                    logger.info(f"Decision: {action_raise_const} {raise_amount} (Weak hand, pure bluff-raising bet against suitable opponent)")
                    return action_raise_const, raise_amount
                else:
                    logger.info(f"Decision: {action_fold_const} (Weak hand, folding to bet)")
                    return action_fold_const, 0
            logger.warning(f"Fell through bet response logic (general) for hand strength {hand_strength_final_decision}. Defaulting to fold.")
            return action_fold_const, 0
        else: # This implies (not can_check originally) AND (bet_to_call == 0)
            logger.warning(f"Unusual state: bet_to_call is 0, but can_check is False. Evaluating bet/fold. Hand strength: {hand_strength_final_decision}")
            if is_very_strong or is_strong:
                bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, purpose="forced_bet_strong_hand")
                logger.info(f"Decision: {action_raise_const} {bet_amount} (Strong/Very Strong hand, forced to act, betting)")
                return action_raise_const, bet_amount
            elif is_medium and win_probability > 0.4: # Medium hand, some equity
                 bet_amount = get_dynamic_bet_size(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, active_opponents_count, purpose="forced_bet_medium_hand")
                 logger.info(f"Decision: {action_raise_const} {bet_amount} (Medium hand, forced to act, betting)")
                 return action_raise_const, bet_amount
            else: # Weak, drawing, or medium with low equity
                logger.info(f"Decision: {action_fold_const} (Weak/Drawing/Low-equity Medium hand, forced to act, cannot check, folding)")
                return action_fold_const, 0
        # The line below was part of the original scaffold, removing it as logic above should return.
        # min_raise_amount = max_bet_on_table + bet_to_call
