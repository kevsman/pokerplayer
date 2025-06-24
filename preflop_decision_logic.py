# preflop_decision_logic.py
import math # For round
from hand_utils import get_preflop_hand_category # Ensure this is imported
import logging
import math # Ensure math is imported
from postflop.opponent_analysis import analyze_opponents
from opponent_persistence import save_opponent_analysis, load_opponent_analysis
import os
from equity_calculator import EquityCalculator
from improved_poker_bot_fixes import improved_pot_odds_safeguard, should_fold_preflop, should_bluff

logger = logging.getLogger(__name__) # Use module's name for the logger

# Set up preflop decision logger with absolute path and flush
preflop_log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), 'debug_preflop_decision_logic.log'))
preflop_file_handler = logging.FileHandler(preflop_log_file, mode='a', encoding='utf-8', delay=False)
preflop_file_handler.setLevel(logging.INFO)
preflop_file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
preflop_logger = logging.getLogger('preflop_decision_logger')
if not preflop_logger.hasHandlers():
    preflop_logger.addHandler(preflop_file_handler)
preflop_logger.setLevel(logging.INFO)

# Test log to confirm logger setup
preflop_logger.info('Preflop logger initialized. Log file: %s', preflop_log_file)
preflop_file_handler.flush()

# Constants for actions (consider moving to a shared constants file)
ACTION_FOLD = 'fold'
ACTION_CHECK = 'check'
ACTION_CALL = 'call'
ACTION_RAISE = 'raise'

def adjust_for_implied_odds(hand_category, position, my_stack, effective_stack, big_blind):
    # Adjust hand selection based on implied odds for suited connectors and suited aces
    if position in ['CO', 'BTN'] and effective_stack > 50 * big_blind:
        if hand_category in ['Suited Connector', 'Suited Ace']:
            return True
    return False

def should_squeeze_play(hand_category, position, active_opponents_count, max_bet_on_table, big_blind, my_stack, min_raise, bet_to_call):
    """Identifies and executes a squeeze play opportunity."""
    # A squeeze is a re-raise after an initial raise and one or more callers.
    # We can identify this situation if there was a raise and there are at least 2 opponents.
    is_squeeze_opportunity = max_bet_on_table > big_blind and active_opponents_count >= 2

    if not is_squeeze_opportunity:
        return None

    # Good hands to squeeze with: premium hands for value, and hands with good blockers/playability as bluffs.
    squeeze_hands = ['Premium', 'Strong', 'Suited Ace', 'Playable Broadway', 'Suited Connector']
    
    if position in ['CO', 'BTN', 'SB', 'BB'] and hand_category in squeeze_hands:
        # Sizing a squeeze: 4x the original raise is a good starting point.
        squeeze_amount = 4 * max_bet_on_table
        
        final_amount = max(squeeze_amount, min_raise)
        final_amount = round(min(final_amount, my_stack), 2)

        if final_amount > bet_to_call:
            return 'raise', final_amount

    return None

# Enhanced logic for optimal preflop decision-making
def should_play_wider_in_position(hand_category, position, num_limpers, bet_to_call, big_blind):
    if position in ['CO', 'BTN', 'SB']:
        if hand_category in ['Offsuit Playable', 'Suited Playable', 'Medium Pair', 'Small Pair', 'Suited Connector']:
            if bet_to_call <= big_blind * 4:
                return True
        if position in ['BTN', 'CO'] and num_limpers <= 1 and bet_to_call <= big_blind * 2:
            if hand_category in ['Weak Ace', 'Suited Gappers', 'Small Pair']:
                return True
        if position == 'BTN' and num_limpers == 0 and bet_to_call <= big_blind:
            if hand_category in ['Suited Connector', 'Offsuit Playable', 'Small Pair']:
                return True
    return False

# --- Additional Preflop Strategies for Cash Games ---

def is_short_stack(my_stack, big_blind):
    """Return True if stack is less than or equal to 20BB (short stack)."""
    return my_stack <= 20 * big_blind

def should_push_fold_short_stack(hand_category, position, my_stack, bet_to_call, big_blind):
    """Push/fold logic for short stacks (<=10BB)."""
    # Ensure big_blind is a float and not zero or None
    try:
        big_blind = float(big_blind)
    except (TypeError, ValueError):
        big_blind = 0.04  # Fallback to default if not provided
    if big_blind <= 0:
        big_blind = 0.04
    if my_stack > 10 * big_blind:
        return None
    # Only push with strong hands for all-in: pairs, strong aces, broadways
    push_hands = [
        'Premium Pair', 'Strong Pair', 'Medium Pair', 'Small Pair',
        'Suited Ace', 'Offsuit Ace', 'Playable Broadway'
    ]
    # Optionally allow suited connectors only from late position and only if very short (<=7BB)
    if hand_category == 'Suited Connector' and position in ['CO', 'BTN'] and my_stack <= 7 * big_blind:
        if bet_to_call <= 4 * big_blind:
            return ACTION_RAISE, my_stack
    if hand_category in push_hands:
        if bet_to_call <= 4 * big_blind:
            return ACTION_RAISE, my_stack  # All-in
    # Otherwise fold
    return ACTION_FOLD, 0

def should_3bet_4bet_bluff(hand_category, position, bet_to_call, max_bet_on_table, big_blind, opponent_stats=None):
    """Occasional 3-bet/4-bet bluffing with blockers/suited connectors."""
    bluff_hands = ['Suited Ace', 'Offsuit Ace', 'Suited Connector', 'Suited Gappers']
    late_positions = ['CO', 'BTN']
    if position in late_positions and hand_category in bluff_hands:
        # Only bluff if facing a single raise and not a huge bet
        if big_blind < max_bet_on_table <= 3.5 * big_blind and bet_to_call <= 3.5 * big_blind:
            # Optionally use opponent_stats to avoid bluffing vs nits
            return ACTION_RAISE, max(3 * max_bet_on_table, 8 * big_blind)
    return None

def should_defend_bb_wider(hand_category, position, bet_to_call, big_blind, opener_position):
    """Defend BB wider vs late position opens."""
    if position == 'BB' and opener_position in ['CO', 'BTN']:
        defend_hands = [
            'Suited Connector', 'Suited Playable', 'Offsuit Playable', 'Small Pair', 'Suited Gappers',
            'Suited Ace', 'Playable Broadway'
        ]
        if hand_category in defend_hands and bet_to_call <= 2.5 * big_blind:
            return ACTION_CALL, bet_to_call
    return None

def should_overlimp_or_isoraise(hand_category, position, num_limpers, bet_to_call, big_blind):
    """Logic for overlimping or iso-raising in multiway pots."""
    # Overlimp with suited connectors, small pairs, suited aces in late position
    overlimp_hands = ['Suited Connector', 'Small Pair', 'Suited Ace']
    if num_limpers >= 2 and bet_to_call == big_blind and position in ['CO', 'BTN']:
        if hand_category in overlimp_hands:
            return ACTION_CALL, bet_to_call
    # Iso-raise with strong hands
    iso_hands = ['Premium Pair', 'Strong Pair', 'Playable Broadway', 'Suited Ace']
    if num_limpers >= 1 and bet_to_call == big_blind and hand_category in iso_hands:
        return ACTION_RAISE, 4 * big_blind + num_limpers * big_blind
    return None

def adjust_for_opponent_tendencies(hand_category, position, opponent_stats=None):
    """Adjust preflop range based on opponent tendencies (loose/tight/aggro)."""
    # Example: If opener is loose, widen 3-bet/call range; if tight, tighten up
    # This is a placeholder; real implementation would use opponent_stats
    # For now, just a stub for future integration
    return None

# Adjustments for raise amount calculation
def make_preflop_decision(
    my_player, hand_category, position, bet_to_call, can_check,
    my_stack, pot_size, active_opponents_count,
    small_blind, big_blind, my_current_bet_this_street, max_bet_on_table, min_raise,
    is_sb, is_bb,
    action_fold_const, action_check_const, action_call_const, action_raise_const,
    opponent_stats=None, opener_position=None, num_limpers=0,
    opponent_tracker=None, action_history=None
):
    # Log and print at the very start to guarantee logger is triggered
    preflop_logger.info(f"make_preflop_decision called. Logging to: {preflop_log_file}")
    preflop_file_handler.flush()
    print(f"[DEBUG] make_preflop_decision called. Logging to: {preflop_log_file}")
    
    def persist_opponents():
        if opponent_tracker is not None and hasattr(opponent_tracker, 'save_all_profiles'):
            logger.info("Calling opponent_tracker.save_all_profiles() in make_preflop_decision (persist_opponents)")
            opponent_tracker.save_all_profiles()

    # --- Opponent analysis integration ---    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[DEBUG] make_preflop_decision: opponent_tracker type={type(opponent_tracker)}, id={id(opponent_tracker) if opponent_tracker is not None else 'None'}")
    # Removed the problematic load_all_profiles() call that was overwriting progress
    opponent_analysis = None
    if opponent_tracker is not None:
        try:
            opponent_analysis = analyze_opponents(opponent_tracker, active_opponents_count, bet_to_call, pot_size)
        except Exception as e:
            logger.warning(f"Opponent analysis failed: {e}")
    table_type = opponent_analysis['table_type'] if opponent_analysis and 'table_type' in opponent_analysis else 'unknown'
    avg_vpip = opponent_analysis['avg_vpip'] if opponent_analysis and 'avg_vpip' in opponent_analysis else 25.0
    fold_equity_estimate = opponent_analysis['fold_equity_estimate'] if opponent_analysis and 'fold_equity_estimate' in opponent_analysis else 0.5

    # --- Hand history integration ---
    recent_aggression = 0
    if action_history and 'preflop' in action_history:
        preflop_actions = action_history['preflop']
        if isinstance(preflop_actions, list):
            recent_aggression = sum(1 for act in preflop_actions if act in ['raise', '3bet', '4bet'])
        elif isinstance(preflop_actions, str):
            recent_aggression = preflop_actions.count('raise') + preflop_actions.count('3bet') + preflop_actions.count('4bet')

    # Example: Widen range if table is loose, tighten if tight
    widen_range = table_type == 'loose' or avg_vpip > 35
    tighten_range = table_type == 'nit' or avg_vpip < 15
    increase_bluff = fold_equity_estimate > 0.6 or (recent_aggression == 0 and fold_equity_estimate > 0.5)
    decrease_bluff = fold_equity_estimate < 0.3 or recent_aggression > 2

    # Use these flags to adjust logic below (examples):
    # - If widen_range, allow more hands to play/raise
    # - If tighten_range, fold more marginal hands
    # - If increase_bluff, allow more 3-bet/4-bet bluffs
    # - If decrease_bluff, avoid marginal bluffs

    preflop_category = hand_category
    win_probability = 0
    num_limpers = 0
    # --- Raise Sizing Logic Update (Standardized) ---
    if max_bet_on_table <= big_blind:
        # Standard open raise: 2.5x (BTN) or 3x (others) + 1BB per limper, capped at 5x BB
        if position == 'CO':
            base_open_multiple = 3
        elif position == 'BTN':
            base_open_multiple = 3 if num_limpers > 0 else 2.5
        else:
            base_open_multiple = 3
        raise_amount_calculated = (base_open_multiple * big_blind) + (num_limpers * big_blind)
        raise_amount_calculated = min(raise_amount_calculated, 5 * big_blind)
    else:
        # Facing a raise: use 3x for 3-bet, 2.2x for 4-bet, cap at 10x BB
        if max_bet_on_table <= 3 * big_blind:
            # 3-bet sizing
            raise_amount_calculated = 3 * max_bet_on_table
        elif max_bet_on_table <= 6 * big_blind:
            # 4-bet sizing
            raise_amount_calculated = 2.2 * max_bet_on_table
        else:
            # For very large bets, just add a small increment or go all-in if short
            raise_amount_calculated = max_bet_on_table + (2 * big_blind)
        raise_amount_calculated = min(raise_amount_calculated, 10 * big_blind, my_stack)
    raise_amount_calculated = max(raise_amount_calculated, min_raise if min_raise > bet_to_call else 0)
    if bet_to_call > 0 and raise_amount_calculated <= bet_to_call:
        raise_amount_calculated = min_raise
    raise_amount_calculated = round(min(raise_amount_calculated, my_stack), 2)
    # Ensure raise amount is valid
    # This check was here, ensure it's still valid:
    # If we decide to raise, the amount must be at least min_raise.
    # min_raise is the *total* bet amount for a valid minimum raise.
    # If raise_amount_calculated < min_raise and raise_amount_calculated > bet_to_call: # If it's intended as a raise but too small
    #    raise_amount_calculated = min_raise
    # This should be covered by max(raise_amount_calculated, min_raise) if min_raise is correctly the total bet.
    # Let's refine: if we intend to raise, the amount must be >= min_raise.
    # The decision to raise comes later. This is just the 'default' calculated raise.    print(f"Preflop Logic: Pos: {position}, Cat: {preflop_category}, B2Call: {bet_to_call}, CanChk: {can_check}, CalcRaise: {raise_amount_calculated}, MyStack: {my_stack}, MyBet: {my_current_bet_this_street}, MaxOppBet: {max_bet_on_table}, Pot: {pot_size}, Opps: {active_opponents_count}, BB: {big_blind}, is_bb: {is_bb}, NumLimpers: {num_limpers}")

    # --- Integrate modular preflop strategies ---
    # 1. Short stack push/fold logic
    # Only use push/fold logic for stacks <= 10BB
    if my_stack <= 10 * big_blind:
        push_fold_result = should_push_fold_short_stack(preflop_category, position, my_stack, bet_to_call, big_blind)
        if push_fold_result is not None:
            action, amount = push_fold_result
            preflop_logger.info(f"Short stack push/fold logic triggered. Action: {action.upper()}, Amount: {amount}")
            if action == ACTION_RAISE:
                persist_opponents()
                return action_raise_const, my_stack # Push for very short stacks (<=10BB)
            elif action == ACTION_FOLD:
                if can_check:
                    persist_opponents()
                    return action_check_const, 0
                else:
                    persist_opponents()
                    return action_fold_const, 0

    # 2. 3-bet/4-bet bluff logic
    bluff_result = should_3bet_4bet_bluff(preflop_category, position, bet_to_call, max_bet_on_table, big_blind, opponent_stats)
    if bluff_result is not None:
        action, amount = bluff_result
        preflop_logger.info(f"3-bet/4-bet bluff logic triggered. Action: {action.upper()}, Amount: {amount}")
        persist_opponents(); return action, amount

    # 3. Squeeze play logic
    squeeze_result = should_squeeze_play(preflop_category, position, active_opponents_count, max_bet_on_table, big_blind, my_stack, min_raise, bet_to_call)
    if squeeze_result is not None:
        action, amount = squeeze_result
        preflop_logger.info(f"Squeeze play logic triggered. Action: {action.upper()}, Amount: {amount}")
        persist_opponents(); return action, amount

    # 4. BB defense logic
    bb_defend_result = should_defend_bb_wider(preflop_category, position, bet_to_call, big_blind, opener_position)
    if bb_defend_result is not None:
        action, amount = bb_defend_result
        preflop_logger.info(f"BB defense logic triggered. Action: {action.upper()}, Amount: {amount}")
        persist_opponents(); return action, amount

    # 5. Overlimp/iso-raise logic
    overlimp_result = should_overlimp_or_isoraise(preflop_category, position, num_limpers, bet_to_call, big_blind)
    if overlimp_result is not None:
        action, amount = overlimp_result
        preflop_logger.info(f"Overlimp/iso-raise logic triggered. Action: {action.upper()}, Amount: {amount}")
        persist_opponents(); return action, amount

    # 6. Opponent tendencies adjustment (stub)
    opponent_adjustment = adjust_for_opponent_tendencies(preflop_category, position, opponent_stats)
    if opponent_adjustment is not None:
        action, amount = opponent_adjustment
        preflop_logger.info(f"Opponent tendencies adjustment logic triggered. Action: {action.upper()}, Amount: {amount}")
        persist_opponents(); return action, amount

    # --- Decision Logic ---
    # Use new hand categories and clear position-based logic
    print(f"DEBUG PREFLOP: Starting decision logic with hand_category='{preflop_category}'")
    preflop_logger.info(f"Starting decision logic with hand_category='{preflop_category}', position={position}, bet_to_call={bet_to_call}, stack={my_stack}, pot_size={pot_size}, opps={active_opponents_count}")

    # --- Strict early position hand selection (UTG/UTG+1) ---
    if position in ["UTG", "UTG+1"]:
        if preflop_category not in ["Premium", "Strong", "Medium Pair"]:
            preflop_logger.info(f"[STRICT UTG FOLD] {my_player['hand']} in {position} not in allowed range. Action: FOLD.")
            persist_opponents(); return action_fold_const, 0

    # --- Trash hands: always fold except BB check ---
    if preflop_category == "Trash":
        preflop_logger.info(f"Trash hand in {position}, folding. Action: FOLD.")
        if is_bb and bet_to_call == 0 and can_check:
            persist_opponents(); return action_check_const, 0
        persist_opponents(); return action_fold_const, 0

    # --- Premium hands: always raise or re-raise ---
    if preflop_category == "Premium":
        if max_bet_on_table <= big_blind:
            actual_raise_amount = max(raise_amount_calculated, min_raise)
            actual_raise_amount = round(min(actual_raise_amount, my_stack), 2)
            persist_opponents(); return action_raise_const, actual_raise_amount
        else:
            actual_raise_amount = max(raise_amount_calculated, min_raise)
            actual_raise_amount = round(min(actual_raise_amount, my_stack), 2)
            if actual_raise_amount > bet_to_call:
                persist_opponents(); return action_raise_const, actual_raise_amount
            else:
                persist_opponents(); return action_call_const, bet_to_call

    # --- Strong hands: raise or call depending on position and bet size ---
    if preflop_category == "Strong":
        if position in ["UTG", "MP"]:
            if max_bet_on_table <= big_blind:
                open_raise = max(raise_amount_calculated, min_raise)
                open_raise = round(min(open_raise, my_stack), 2)
                persist_opponents(); return action_raise_const, open_raise
            elif bet_to_call <= big_blind * 4:
                persist_opponents(); return action_call_const, bet_to_call
            else:
                persist_opponents(); return action_fold_const, 0
        else: # CO, BTN, SB, BB
            if max_bet_on_table <= big_blind:
                open_raise = max(raise_amount_calculated, min_raise)
                open_raise = round(min(open_raise, my_stack), 2)
                persist_opponents(); return action_raise_const, open_raise
            elif bet_to_call <= big_blind * 6:
                persist_opponents(); return action_call_const, bet_to_call
            else:
                persist_opponents(); return action_fold_const, 0

    # --- Medium Pair: open in MP+, call in blinds, fold to big raises ---
    if preflop_category == "Medium Pair":
        if position in ["UTG"]:
            persist_opponents(); return action_fold_const, 0
        elif max_bet_on_table <= big_blind:
            open_raise = max(raise_amount_calculated, min_raise)
            open_raise = round(min(open_raise, my_stack), 2)
            persist_opponents(); return action_raise_const, open_raise
        elif bet_to_call <= big_blind * 4:
            persist_opponents(); return action_call_const, bet_to_call
        else:
            persist_opponents(); return action_fold_const, 0

    # --- Small Pair: set mine in multiway pots, otherwise fold ---
    if preflop_category == "Small Pair":
        if bet_to_call <= big_blind * 2 and active_opponents_count >= 2:
            persist_opponents(); return action_call_const, bet_to_call
        elif max_bet_on_table <= big_blind and position in ["CO", "BTN", "SB"]:
            open_raise = max(raise_amount_calculated, min_raise)
            open_raise = round(min(open_raise, my_stack), 2)
            persist_opponents(); return action_raise_const, open_raise
        else:
            persist_opponents(); return action_fold_const, 0

    # --- Suited Ace: open/raise in late, call in blinds, fold to big raises ---
    if preflop_category == "Suited Ace":
        if position in ["CO", "BTN", "SB"] and max_bet_on_table <= big_blind:
            open_raise = max(raise_amount_calculated, min_raise)
            open_raise = round(min(open_raise, my_stack), 2)
            persist_opponents(); return action_raise_const, open_raise
        elif bet_to_call <= big_blind * 4:
            persist_opponents(); return action_call_const, bet_to_call
        else:
            persist_opponents(); return action_fold_const, 0

    # --- Suited Broadway, Offsuit Broadway, Suited Connector, Suited Gapper, Offsuit Ace, Offsuit King ---
    if preflop_category in ["Suited Broadway", "Offsuit Broadway", "Suited Connector", "Suited Gapper", "Offsuit Ace", "Offsuit King"]:
        # Open in late, call in blinds, fold to big raises
        if position in ["CO", "BTN"] and max_bet_on_table <= big_blind:
            open_raise = max(raise_amount_calculated, min_raise)
            open_raise = round(min(open_raise, my_stack), 2)
            persist_opponents(); return action_raise_const, open_raise
        elif position in ["SB", "BB"] and bet_to_call <= big_blind * 2:
            persist_opponents(); return action_call_const, bet_to_call
        elif bet_to_call == 0 and can_check:
            persist_opponents(); return action_check_const, 0
        else:
            persist_opponents(); return action_fold_const, 0

    # --- Default: fold ---
    preflop_logger.info(f"Default fallback: folding hand {my_player['hand']} in {position} (category: {preflop_category})")
    persist_opponents(); return action_fold_const, 0
