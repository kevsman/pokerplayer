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
    """Push/fold logic for short stacks (<20BB)."""
    # Example: Push with any pair, any ace, broadways, suited connectors in late position
    if not is_short_stack(my_stack, big_blind):
        return None
    push_hands = [
        'Premium Pair', 'Strong Pair', 'Medium Pair', 'Small Pair',
        'Suited Ace', 'Offsuit Ace', 'Playable Broadway', 'Suited Connector', 'Suited Playable'
    ]
    if hand_category in push_hands:
        # Push if unopened or facing a raise <= 4BB
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

    # --- Opponent analysis integration ---
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[DEBUG] make_preflop_decision: opponent_tracker type={type(opponent_tracker)}, id={id(opponent_tracker) if opponent_tracker is not None else 'None'}")
    if opponent_tracker is not None:
        if hasattr(opponent_tracker, 'load_all_profiles'):
            logger.info("Calling opponent_tracker.load_all_profiles() in make_preflop_decision")
            opponent_tracker.load_all_profiles()
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
    push_fold_result = should_push_fold_short_stack(preflop_category, position, my_stack, bet_to_call, big_blind)
    if push_fold_result is not None:
        action, amount = push_fold_result
        preflop_logger.info(f"Short stack push/fold logic triggered. Action: {action.upper()}, Amount: {amount}")
        persist_opponents(); return action, amount

    # 2. 3-bet/4-bet bluff logic
    bluff_result = should_3bet_4bet_bluff(preflop_category, position, bet_to_call, max_bet_on_table, big_blind, opponent_stats)
    if bluff_result is not None:
        action, amount = bluff_result
        preflop_logger.info(f"3-bet/4-bet bluff logic triggered. Action: {action.upper()}, Amount: {amount}")
        persist_opponents(); return action, amount

    # 3. BB defense logic
    bb_defend_result = should_defend_bb_wider(preflop_category, position, bet_to_call, big_blind, opener_position)
    if bb_defend_result is not None:
        action, amount = bb_defend_result
        preflop_logger.info(f"BB defense logic triggered. Action: {action.upper()}, Amount: {amount}")
        persist_opponents(); return action, amount

    # 4. Overlimp/iso-raise logic
    overlimp_result = should_overlimp_or_isoraise(preflop_category, position, num_limpers, bet_to_call, big_blind)
    if overlimp_result is not None:
        action, amount = overlimp_result
        preflop_logger.info(f"Overlimp/iso-raise logic triggered. Action: {action.upper()}, Amount: {amount}")
        persist_opponents(); return action, amount

    # 5. Opponent tendencies adjustment (stub)
    opponent_adjustment = adjust_for_opponent_tendencies(preflop_category, position, opponent_stats)
    if opponent_adjustment is not None:
        action, amount = opponent_adjustment
        preflop_logger.info(f"Opponent tendencies adjustment logic triggered. Action: {action.upper()}, Amount: {amount}")
        persist_opponents(); return action, amount

    # --- Decision Logic ---
    
    print(f"DEBUG PREFLOP: Starting decision logic with hand_category='{preflop_category}'")
    preflop_logger.info(f"Starting decision logic with hand_category='{preflop_category}', position={position}, bet_to_call={bet_to_call}, stack={my_stack}, pot_size={pot_size}, opps={active_opponents_count}")
    
    # --- Integration of implied odds and position-based widening ---
    # Use implied odds logic for suited connectors/aces in late position with deep stacks
    if adjust_for_implied_odds(preflop_category, position, my_stack, my_stack, big_blind):
        print(f"{preflop_category} in {position}, deep stack implied odds adjustment. Action: CALL, Amount: {bet_to_call}")
        preflop_logger.info(f"{preflop_category} in {position}, deep stack implied odds adjustment. Action: CALL, Amount: {bet_to_call}")
        if bet_to_call <= my_stack * 0.1:  # Only call if not a large portion of stack
            persist_opponents(); return action_call_const, bet_to_call

    # Use position-based widening logic for late position
    if should_play_wider_in_position(preflop_category, position, num_limpers, bet_to_call, big_blind):
        print(f"{preflop_category} in {position}, playing wider in position. Action: RAISE, Amount: {raise_amount_calculated}")
        preflop_logger.info(f"{preflop_category} in {position}, playing wider in position. Action: RAISE, Amount: {raise_amount_calculated}")
        if raise_amount_calculated > bet_to_call:
            persist_opponents(); return action_raise_const, raise_amount_calculated
        elif can_check and bet_to_call == 0:
            persist_opponents(); return action_check_const, 0
        else:
            persist_opponents(); return action_call_const, bet_to_call
    
    if preflop_category == "Weak":
        print(f"DEBUG PREFLOP: Entered Weak hand category")
        preflop_logger.info(f"Entered Weak hand category for {preflop_category} in {position}")
        
        if can_check and is_bb and bet_to_call == 0:
            print(f"DEBUG PREFLOP: BB can check with no bet to call. Action: CHECK")
            preflop_logger.info(f"BB can check with no bet to call. Action: CHECK")
            persist_opponents(); return action_check_const, 0
        
        # Enhanced BTN stealing with wider range
        if position == 'BTN' and num_limpers == 0 and max_bet_on_table <= big_blind:
            # BTN should attempt steals with wider range including suited weak hands and some offsuit hands
            hand = my_player['hand']
            card1_suit = hand[0][-1]
            card2_suit = hand[1][-1]
            is_suited = card1_suit == card2_suit
            
            # Get card ranks
            card1_rank = hand[0][:-1] if hand[0][:-1] != '10' else 'T'
            card2_rank = hand[1][:-1] if hand[1][:-1] != '10' else 'T'
            
            # Expand steal range: suited kings, suited queens, any suited connector
            has_high_card = card1_rank in ['K', 'Q', 'J'] or card2_rank in ['K', 'Q', 'J']
            
            # Check for suited connectors or gappers
            from hand_utils import RANK_TO_VALUE
            rank1_val = RANK_TO_VALUE.get(card1_rank, 0)
            rank2_val = RANK_TO_VALUE.get(card2_rank, 0)
            if rank1_val < rank2_val:
                rank1_val, rank2_val = rank2_val, rank1_val
            
            is_connector = is_suited and (rank1_val - rank2_val) <= 2 and rank1_val >= 6
            
            # Steal with: suited high cards, suited connectors, some offsuit broadways
            should_steal = False
            if is_suited and (has_high_card or is_connector):
                should_steal = True
            elif not is_suited and has_high_card and (rank1_val >= 11 and rank2_val >= 9):  # J9o+
                should_steal = True
                
            if should_steal:
                steal_amount = raise_amount_calculated
                steal_amount = max(steal_amount, min_raise)
                steal_amount = round(min(steal_amount, my_stack), 2)
                if steal_amount > bet_to_call:
                    print(f"BTN steal with weak hand ({card1_rank}{card1_suit}, {card2_rank}{card2_suit}). Action: RAISE, Amount: {steal_amount}")
                    preflop_logger.info(f"BTN steal with weak hand ({card1_rank}{card1_suit}, {card2_rank}{card2_suit}). Action: RAISE, Amount: {steal_amount}")
                    persist_opponents(); return action_raise_const, steal_amount
        
        # CO late position play - more liberal than early position
        if position == 'CO' and num_limpers == 0 and max_bet_on_table <= big_blind:
            hand = my_player['hand']
            card1_rank = hand[0][:-1] if hand[0][:-1] != '10' else 'T'
            card2_rank = hand[1][:-1] if hand[1][:-1] != '10' else 'T'
            
            # More conservative than BTN but still wider than early position
            has_king_queen = card1_rank in ['K', 'Q'] or card2_rank in ['K', 'Q']
            if has_king_queen and (hand[0][-1] == hand[1][-1]):  # Suited K or Q
                steal_amount = raise_amount_calculated
                steal_amount = max(steal_amount, min_raise)
                steal_amount = round(min(steal_amount, my_stack), 2)
                if steal_amount > bet_to_call:
                    print(f"CO open with suited high card. Action: RAISE, Amount: {steal_amount}")
                    preflop_logger.info(f"CO open with suited high card. Action: RAISE, Amount: {steal_amount}")
                    persist_opponents(); return action_raise_const, steal_amount
                      # If facing a raise, fold weak hands (with some exceptions)
        if bet_to_call > 0:
            print(f"DEBUG PREFLOP: Weak hand facing bet (bet_to_call={bet_to_call}). Action: FOLD")
            preflop_logger.info(f"Weak hand facing bet (bet_to_call={bet_to_call}). Action: FOLD")
            persist_opponents(); return action_fold_const, 0
            # If no bet to call, and cannot check (e.g., UTG must act), fold weak hands.
        # Exception: BTN steal attempts with suited weak hands like K4s
        if bet_to_call == 0:
            print(f"DEBUG PREFLOP: bet_to_call == 0, checking for BTN steal scenarios")
            # Check if this is a BTN steal spot (no limpers, first to act)
            if position == 'BTN' and num_limpers == 0:                # BTN should attempt steals with wider range including suited kings
                # Check if it's a suited hand that could be a steal candidate
                hand = my_player['hand']
                card1_suit = hand[0][-1]
                card2_suit = hand[1][-1]
                is_suited = card1_suit == card2_suit
                 
                # Get card ranks
                card1_rank = hand[0][:-1] if hand[0][:-1] != '10' else 'T'
                card2_rank = hand[1][:-1] if hand[1][:-1] != '10' else 'T'
                 
                # Check if it contains a King and is suited (like K4s)
                has_king = card1_rank == 'K' or card2_rank == 'K'
                 
                if is_suited and has_king:
                    steal_amount = raise_amount_calculated
                    steal_amount = max(steal_amount, min_raise)
                    steal_amount = round(min(steal_amount, my_stack), 2)
                    if steal_amount > bet_to_call:
                        print(f"Weak suited King in BTN, steal attempt. Action: RAISE, Amount: {steal_amount}")
                        preflop_logger.info(f"Weak suited King in BTN, steal attempt. Action: RAISE, Amount: {steal_amount}")
                        persist_opponents(); return action_raise_const, steal_amount
            
            # If not a steal situation and cannot check, fold
            if not can_check:
                print(f"DEBUG PREFLOP: Weak hand, cannot check (e.g., UTG open), no bet to call. Action: FOLD")
                preflop_logger.info(f"Weak hand, cannot check (e.g., UTG open), no bet to call. Action: FOLD")
                persist_opponents(); return action_fold_const, 0# Debug logging for BB check issue investigation
        print(f"DEBUG PREFLOP: At check/fold decision point:")
        print(f"  - position: {position}")
        print(f"  - bet_to_call: {bet_to_call}")
        print(f"  - can_check: {can_check}")
        print(f"  - is_bb: {is_bb}")
        print(f"  - hand_category: {hand_category}")
        
        # If no bet to call and can check (e.g. UTG limp, later position check through, or BB with no raise)
        if bet_to_call == 0 and can_check:
            print(f"DEBUG PREFLOP: Weak hand, can check (limp/check through or BB facing no bet). Action: CHECK")
            preflop_logger.info(f"Weak hand, can check (limp/check through or BB facing no bet). Action: CHECK")
            persist_opponents(); return action_check_const, 0
        
        # Default for weak hands: if can check, check. Otherwise, fold.
        # This covers the BB case where it's checked to them (bet_to_call == 0, can_check == True)
        print(f"DEBUG PREFLOP: Weak hand, default. Action: CHECK if can_check else FOLD. (can_check={can_check}, bet_to_call={bet_to_call})")
        return action_check_const if can_check else action_fold_const, 0


    if preflop_category == "Premium Pair": # AA, KK, QQ
        # For Premium Pairs, the decision is almost always to raise if possible.
        # The raise_amount_calculated should be appropriate from the global calculation.
        # If max_bet_on_table <= big_blind (opening/iso): calc was (3*BB) + (limpers*BB)
        # If max_bet_on_table > big_blind (facing raise): calc was 3 * max_bet_on_table
        
        # If bet_to_call == 0 (or more generally, if max_bet_on_table <= big_blind, meaning we are first to make a 'real' bet)
        if max_bet_on_table <= big_blind: # We are opening or isolating limpers
            # Use the globally calculated raise_amount_calculated for opening/isolating
            actual_raise_amount = raise_amount_calculated
            actual_raise_amount = max(actual_raise_amount, min_raise) # Ensure it's at least min_raise
            actual_raise_amount = round(min(actual_raise_amount, my_stack), 2)
            if actual_raise_amount <= bet_to_call and actual_raise_amount < my_stack : # Not a valid raise, or not all-in
                 actual_raise_amount = min_raise # Fallback if calc is too low
                 actual_raise_amount = round(min(actual_raise_amount, my_stack), 2)

            if actual_raise_amount > bet_to_call or (actual_raise_amount == my_stack and my_stack > bet_to_call): # Must be a raise or a covering all-in
                print(f"Premium Pair, opening/isolating. Action: RAISE, Amount: {actual_raise_amount}")
                preflop_logger.info(f"Premium Pair, opening/isolating. Action: RAISE, Amount: {actual_raise_amount}")
                persist_opponents(); return action_raise_const, actual_raise_amount
            else: # Should not happen if min_raise is valid and stack sufficient. Fallback to call if weird state.
                if bet_to_call < my_stack and bet_to_call > 0:
                    print(f"Premium Pair, opening/isolating, raise calc issue, calling. Action: CALL, Amount: {bet_to_call}")
                    preflop_logger.info(f"Premium Pair, opening/isolating, raise calc issue, calling. Action: CALL, Amount: {bet_to_call}")
                    persist_opponents(); return action_call_const, bet_to_call
                elif can_check:
                    print(f"Premium Pair, opening/isolating, raise calc issue, checking. Action: CHECK")
                    preflop_logger.info(f"Premium Pair, opening/isolating, raise calc issue, checking. Action: CHECK")
                    persist_opponents(); return action_check_const, 0
                else:
                    print(f"Premium Pair, opening/isolating, raise calc issue, folding. Action: FOLD")
                    preflop_logger.info(f"Premium Pair, opening/isolating, raise calc issue, folding. Action: FOLD")
                    persist_opponents(); return action_fold_const, 0
        else: # Facing a bet or raise (max_bet_on_table > big_blind)
            # Re-raise. Use the globally calculated raise_amount_calculated (3x max_bet_on_table)
            actual_raise_amount = raise_amount_calculated
            actual_raise_amount = max(actual_raise_amount, min_raise) # Ensure it's a valid raise amount
            actual_raise_amount = round(min(actual_raise_amount, my_stack), 2)

            if actual_raise_amount <= bet_to_call: # Calculated raise is not even a call or is invalid.
                # This can happen if 3*max_bet_on_table is less than min_raise and min_raise itself is just a call.
                # Or if stack is too small. If stack is small, actual_raise_amount might be my_stack.
                if actual_raise_amount == my_stack and my_stack > bet_to_call: # All-in raise
                     print(f"Premium Pair, facing bet, re-raising ALL-IN. Action: RAISE, Amount: {my_stack}")
                     preflop_logger.info(f"Premium Pair, facing bet, re-raising ALL-IN. Action: RAISE, Amount: {my_stack}")
                     persist_opponents(); return action_raise_const, my_stack
                  # Fallback if raise calculation is problematic
                # Premium pairs (AA, KK, QQ) should almost never fold preflop
                # Call with any premium pair if we can't raise properly
                if bet_to_call < my_stack: # Can afford to call (not an impossible all-in for more than stack)
                    print(f"Premium Pair, facing bet, raise calc failed, calling with premium hand. Action: CALL, Amount: {bet_to_call}")
                    preflop_logger.info(f"Premium Pair, facing bet, raise calc failed, calling with premium hand. Action: CALL, Amount: {bet_to_call}")
                    persist_opponents(); return action_call_const, bet_to_call
                else: # Only fold if the bet is somehow more than our entire stack (should never happen)
                    print(f"Premium Pair, facing bet larger than stack (impossible situation). Action: CALL ALL-IN, Amount: {my_stack}")
                    preflop_logger.info(f"Premium Pair, facing bet larger than stack (impossible situation). Action: CALL ALL-IN, Amount: {my_stack}")
                    persist_opponents(); return action_call_const, my_stack
            
            # If calculated raise is a significant portion of stack, consider it an all-in.
            if actual_raise_amount >= my_stack * 0.85 and actual_raise_amount > bet_to_call : 
                print(f"Premium Pair, facing bet, large re-raise. Action: RAISE (ALL-IN), Amount: {my_stack}")
                preflop_logger.info(f"Premium Pair, facing bet, large re-raise. Action: RAISE (ALL-IN), Amount: {my_stack}")
                persist_opponents(); return action_raise_const, my_stack
            
            print(f"Premium Pair, facing bet. Action: RAISE, Amount: {actual_raise_amount}")
            preflop_logger.info(f"Premium Pair, facing bet. Action: RAISE, Amount: {actual_raise_amount}")
            persist_opponents(); return action_raise_const, actual_raise_amount

    # AKs, AKo, AQs, AQo, AJs, AJo, KQs, KQo (Playable Broadway / Suited Ace)
    # Strong Pair (JJ, TT)
    # Suited Playable (KJs, KTs, QJs, QTs, JTs)
    # Medium Pair (99, 88, 77) - Added
    if preflop_category in ["Suited Ace", "Offsuit Ace", "Suited King", "Offsuit King", "Playable Broadway", "Offsuit Broadway", "Strong Pair", "Suited Playable", "Medium Pair", "Offsuit Playable", "Small Pair", "Weak", "Premium Pair", "Suited Connector"]: # Added "Small Pair", "Weak", "Premium Pair", "Suited Connector"
        if position in ['UTG', 'MP']:
            # Facing a real raise (max_bet_on_table > big_blind)
            # Fold AJo/ATo facing UTG raise + MP 3-bet
            if bet_to_call > big_blind * 4 or (preflop_category in ["Offsuit Ace", "Offsuit Broadway"] and max_bet_on_table > 7 * big_blind):
                print(f"{preflop_category} in {position}, facing large raise or 3-bet. Action: FOLD")
                preflop_logger.info(f"{preflop_category} in {position}, facing large raise or 3-bet. Action: FOLD")
                persist_opponents(); return action_fold_const, 0

            # Opening or raising over limpers if no one has made a 'real' raise yet
            if max_bet_on_table <= big_blind:
                # Use the global raise_amount_calculated for opening
                open_raise = raise_amount_calculated
                open_raise = max(open_raise, min_raise) # Ensure it's at least min_raise
                open_raise = round(min(open_raise, my_stack),2)

                if open_raise > bet_to_call or (open_raise == my_stack and my_stack > bet_to_call): # Must be a raise or covering all-in
                    # Filter out weaker hands in this category for UTG/MP opens if they are too weak
                    if position == 'UTG' and preflop_category in ["Medium Pair", "Suited Playable"]: # Too loose for UTG open
                         print(f"{preflop_category} in UTG, too weak to open. Action: FOLD")
                         preflop_logger.info(f"{preflop_category} in UTG, too weak to open. Action: FOLD")
                         persist_opponents(); return action_fold_const, 0
                    if position == 'MP' and preflop_category == "Medium Pair" and preflop_category not in ["Strong Pair"]: # e.g. 77-99 from MP might be too loose for 3x open
                         # TT+ is Strong Pair. So this is for 77-99.
                         # Let's allow MP to open Medium Pairs for now
                         pass

                    print(f"{preflop_category} in {position}, opening/raising limpers. Action: RAISE, Amount: {open_raise}")
                    preflop_logger.info(f"{preflop_category} in {position}, opening/raising limpers. Action: RAISE, Amount: {open_raise}")
                    persist_opponents(); return action_raise_const, open_raise
                else: # Raise calculation failed, try to check/fold
                     if can_check:
                         print(f"{preflop_category} in {position}, opening, raise calc issue, checking. Action: CHECK")
                         preflop_logger.info(f"{preflop_category} in {position}, opening, raise calc issue, checking. Action: CHECK")
                         persist_opponents(); return action_check_const, 0
                     else:
                         print(f"{preflop_category} in {position}, opening, raise calc issue, folding. Action: FOLD")
                         preflop_logger.info(f"{preflop_category} in {position}, opening, raise calc issue, folding. Action: FOLD")
                         persist_opponents(); return action_fold_const, 0
            # Facing a real raise (max_bet_on_table > big_blind)
            elif bet_to_call <= big_blind * 4: 
                if preflop_category == "Strong Pair": # TT, JJ, AKo
                    # AKo should 3-bet vs UTG open in MP
                    if position == "MP" and bet_to_call <= big_blind * 3: # Assuming AKo is part of Strong Pair for this
                        three_bet_amount = raise_amount_calculated # Global calc for MP 3bet is 3x
                        three_bet_amount = max(three_bet_amount, min_raise)
                        three_bet_amount = round(min(three_bet_amount, my_stack), 2)
                        if three_bet_amount > bet_to_call:
                            print(f"{preflop_category} (likely AKo or strong pair) in MP, 3-betting. Action: RAISE, Amount: {three_bet_amount}")
                            preflop_logger.info(f"{preflop_category} (likely AKo or strong pair) in MP, 3-betting. Action: RAISE, Amount: {three_bet_amount}")
                            persist_opponents(); return action_raise_const, three_bet_amount
                    
                    # If not 3-betting (e.g. TT, JJ vs larger raise, or AKo if 3-bet calc failed)
                    if bet_to_call <= big_blind * 3.5: 
                        print(f"{preflop_category} in {position}, facing raise <= 3.5x. Action: CALL, Amount: {bet_to_call}")
                        preflop_logger.info(f"{preflop_category} in {position}, facing raise <= 3.5x. Action: CALL, Amount: {bet_to_call}")
                        persist_opponents(); return action_call_const, bet_to_call
                    else:
                        print(f"{preflop_category} in {position}, facing large raise > 3.5x. Action: FOLD")
                        preflop_logger.info(f"{preflop_category} in {position}, facing large raise > 3.5x. Action: FOLD")
                        persist_opponents(); return action_fold_const, 0
                # For suited aces like A8s in CO vs UTG open - should call, not 3-bet
                # Only 3-bet stronger suited aces (AJs+) not weaker ones (A8s, A9s)
                elif preflop_category == "Suited Ace":
                    print(f"{preflop_category} in {position}, facing raise <= 4BB. Action: CALL, Amount: {bet_to_call}")
                    preflop_logger.info(f"{preflop_category} in {position}, facing raise <= 4BB. Action: CALL, Amount: {bet_to_call}")
                    persist_opponents(); return action_call_const, bet_to_call
                # For other strong hands like AK, AQ, KQs in UTG/MP facing a raise.
                # Call smaller raises.
                print(f"{preflop_category} in {position}, facing raise <= 4BB. Action: CALL, Amount: {bet_to_call}")
                preflop_logger.info(f"{preflop_category} in {position}, facing raise <= 4BB. Action: CALL, Amount: {bet_to_call}")
                persist_opponents(); return action_call_const, bet_to_call
            else: # Facing a large raise
                print(f"{preflop_category} in {position}, facing large raise > 4BB. Action: FOLD")
                preflop_logger.info(f"{preflop_category} in {position}, facing large raise > 4BB. Action: FOLD")
                persist_opponents(); return action_fold_const, 0
        elif position in ['CO', 'BTN']:
            # Facing a raise (max_bet_on_table > big_blind)
            # Fold weak offsuit aces facing large raises, but check pot odds for strong hands like AQ offsuit
            if preflop_category == "Offsuit Ace" and max_bet_on_table > 7 * big_blind:
                # This might be too tight for BTN vs CO, but as a general rule for "Offsuit Ace"
                print(f"{preflop_category} in {position}, facing large raise or 3-bet. Action: FOLD")
                preflop_logger.info(f"{preflop_category} in {position}, facing large raise or 3-bet. Action: FOLD")
                persist_opponents(); return action_fold_const, 0
            # For Offsuit Broadway (like AQ offsuit), check pot odds before folding to large raises
            elif preflop_category == "Offsuit Broadway" and max_bet_on_table > 7 * big_blind:
                # Calculate pot odds to decide if we should call with a strong hand
                pot_odds_needed = bet_to_call / (pot_size + bet_to_call) if (pot_size + bet_to_call) > 0 else 1
                if pot_odds_needed <= 0.40:  # AQ offsuit should call with good pot odds
                    print(f"{preflop_category} in {position}, facing large raise but good pot odds ({pot_odds_needed:.1%} equity needed). Action: CALL, Amount: {bet_to_call}")
                    preflop_logger.info(f"{preflop_category} in {position}, facing large raise but good pot odds ({pot_odds_needed:.1%} equity needed). Action: CALL, Amount: {bet_to_call}")
                    persist_opponents(); return action_call_const, bet_to_call
                else:
                    print(f"{preflop_category} in {position}, facing large raise with poor pot odds ({pot_odds_needed:.1%} equity needed). Action: FOLD")
                    preflop_logger.info(f"{preflop_category} in {position}, facing large raise with poor pot odds ({pot_odds_needed:.1%} equity needed). Action: FOLD")
                    persist_opponents(); return action_fold_const, 0

            # Squeeze logic: if pot_size > 2*max_bet_on_table, treat as squeeze (already part of raise_amount_calculated)
            # The raise_amount_calculated for CO/BTN already considers squeeze (4.5x) or 3-bet (3x).
            
            # Opening or raising over limpers
            if max_bet_on_table <= big_blind:
                open_raise = raise_amount_calculated # Use global calc: (3*BB or 2.5*BB for BTN) + limpers
                open_raise = max(open_raise, min_raise)
                open_raise = round(min(open_raise, my_stack),2)
                if open_raise > bet_to_call or (open_raise == my_stack and my_stack > bet_to_call):
                    print(f"{preflop_category} in {position}, opening/isolating. Action: RAISE, Amount: {open_raise}")
                    preflop_logger.info(f"{preflop_category} in {position}, opening/isolating. Action: RAISE, Amount: {open_raise}")
                    persist_opponents(); return action_raise_const, open_raise
                else: # Raise calculation failed
                     if can_check: # Should not happen if opening unless BB
                         print(f"{preflop_category} in {position}, opening, raise calc issue, checking. Action: CHECK")
                         preflop_logger.info(f"{preflop_category} in {position}, opening, raise calc issue, checking. Action: CHECK")
                         persist_opponents(); return action_check_const, 0
                     else:
                         print(f"{preflop_category} in {position}, opening, raise calc issue, folding. Action: FOLD")
                         preflop_logger.info(f"{preflop_category} in {position}, opening, raise calc issue, folding. Action: FOLD")
                         persist_opponents(); return action_fold_const, 0
            # Facing a real raise (max_bet_on_table > big_blind)
            # Hands strong enough to 3-bet: "Playable Broadway", "Offsuit Broadway" (AQo, AJo), "Suited Ace", "Offsuit Ace" (AKo), "Strong Pair"
            elif preflop_category in ["Playable Broadway", "Offsuit Broadway", "Suited Ace", "Offsuit Ace", "Strong Pair"] and \
                 max_bet_on_table > big_blind and \
                 max_bet_on_table <= big_blind * 4.5: # Facing a standard open or small 3-bet
                three_bet_amount = raise_amount_calculated # Global calc for CO/BTN 3-bet (3x or 4.5x if squeeze)
                three_bet_amount = max(three_bet_amount, min_raise)
                three_bet_amount = round(min(three_bet_amount, my_stack), 2)
                if three_bet_amount > bet_to_call:
                    print(f"{preflop_category} in {position}, 3-betting. Action: RAISE, Amount: {three_bet_amount}")
                    preflop_logger.info(f"{preflop_category} in {position}, 3-betting. Action: RAISE, Amount: {three_bet_amount}")
                    persist_opponents(); return action_raise_const, three_bet_amount
                elif bet_to_call < my_stack : # Fallback to call if 3-bet calc is too small but can call
                    print(f"{preflop_category} in {position}, 3-bet calc low, calling. Action: CALL, Amount: {bet_to_call}")
                    preflop_logger.info(f"{preflop_category} in {position}, 3-bet calc low, calling. Action: CALL, Amount: {bet_to_call}")
                    persist_opponents(); return action_call_const, bet_to_call
                else: # Cannot 3-bet effectively or call
                    print(f"{preflop_category} in {position}, cannot 3-bet/call effectively. Action: FOLD")
                    preflop_logger.info(f"{preflop_category} in {position}, cannot 3-bet/call effectively. Action: FOLD")
                    persist_opponents(); return action_fold_const, 0
            elif bet_to_call <= big_blind * 10: # Facing a larger bet (likely 3-bet or 4-bet)
                # Call with strong suited hands and strong pairs if odds are decent and not too much of stack.
                if preflop_category in ["Suited Ace", "Playable Broadway", "Strong Pair"] and bet_to_call < my_stack * 0.33:
                    print(f"{preflop_category} in {position}, facing large bet, calling. Action: CALL, Amount: {bet_to_call}")
                    preflop_logger.info(f"{preflop_category} in {position}, facing large bet, calling. Action: CALL, Amount: {bet_to_call}")
                    persist_opponents(); return action_call_const, bet_to_call
                else:
                    print(f"{preflop_category} in {position}, facing large bet, folding. Action: FOLD")
                    preflop_logger.info(f"{preflop_category} in {position}, facing large bet, folding. Action: FOLD")
                    persist_opponents(); return action_fold_const, 0
            else: # Facing a very large bet
                print(f"{preflop_category} in {position}, facing very large bet. Action: FOLD")
                preflop_logger.info(f"{preflop_category} in {position}, facing very large bet. Action: FOLD")
                persist_opponents(); return action_fold_const, 0
        elif position == 'SB':
            # SB strategy: 3-bet or fold mostly. Call very selectively.
            if max_bet_on_table <= big_blind: # Opening from SB
                open_raise = raise_amount_calculated # Should be 3x BB + limpers (if any)
                open_raise = max(open_raise, min_raise)
                open_raise = round(min(open_raise, my_stack), 2)
                
                # Tighten SB open range for some categories if no limpers
                if num_limpers == 0 and preflop_category in ["Offsuit Ace", "Offsuit Broadway", "Medium Pair", "Suited Playable"]:
                     # KJs, KTs, QJs, QTs, JTs (Suited Playable) can be opened. ATo, KJo, QJo, JTo (Offsuit Broadway) are borderline.
                     # Medium pairs (77-99) are also borderline. Weaker Offsuit Aces (A9o-A2o) are folds.
                     if preflop_category in ["Offsuit Ace", "Medium Pair"] or \
                        (preflop_category == "Offsuit Broadway" and not any(r in hand_category for r in ["AK", "AQ", "KQ"])): # Fold weaker offsuit broadways
                         print(f"{preflop_category} in SB, too weak to open vs no limpers. Action: FOLD")
                         preflop_logger.info(f"{preflop_category} in SB, too weak to open vs no limpers. Action: FOLD")
                         persist_opponents(); return action_fold_const, 0

                if open_raise > bet_to_call: # bet_to_call should be small_blind if completing, or 0 if opening
                    print(f"{preflop_category} in SB, opening/raising. Action: RAISE, Amount: {open_raise}")
                    preflop_logger.info(f"{preflop_category} in SB, opening/raising. Action: RAISE, Amount: {open_raise}")
                    persist_opponents(); return action_raise_const, open_raise
                elif can_check: # Should only happen if it was checked to SB and BB, and SB wants to check.
                                # But this block is for stronger hands, unlikely to check here.
                                # More likely, this means raise calc failed.
                    print(f"{preflop_category} in SB, open/raise calc issue, checking. Action: CHECK")
                    preflop_logger.info(f"{preflop_category} in SB, open/raise calc issue, checking. Action: CHECK")
                    persist_opponents(); return action_check_const, 0
                else: # Cannot raise effectively
                    print(f"{preflop_category} in SB, open/raise calc issue, folding. Action: FOLD")
                    preflop_logger.info(f"{preflop_category} in SB, open/raise calc issue, folding. Action: FOLD")
                    persist_opponents(); return action_fold_const, 0
            else: # Facing a raise in SB
                my_bet_on_street_before_this_action = max_bet_on_table - bet_to_call
                # Use the 'small_blind' parameter passed to the function
                we_already_raised_this_street = my_bet_on_street_before_this_action > small_blind

                is_suited_ace_category = (preflop_category == "Suited Ace")
                
                if is_suited_ace_category and we_already_raised_this_street:
                    logger.info(f"{preflop_category} in SB, facing re-raise (4-bet+), folding. Action: FOLD")
                    persist_opponents(); return ACTION_FOLD, 0

                can_consider_initial_3bet = preflop_category in ["Strong Pair", "Suited Ace", "Playable Broadway"]
                can_consider_5bet_plus = preflop_category in ["Strong Pair", "Playable Broadway"] 

                eligible_for_aggressive_action = False
                if not we_already_raised_this_street and can_consider_initial_3bet:
                    eligible_for_aggressive_action = True
                elif we_already_raised_this_street and can_consider_5bet_plus:
                    if preflop_category == "Suited Ace": 
                        logger.info(f"{preflop_category} in SB, facing re-raise (4-bet+) (safeguard), folding. Action: FOLD")
                        persist_opponents(); return ACTION_FOLD, 0
                    eligible_for_aggressive_action = True
                
                commitment_factor = 0.45 if we_already_raised_this_street else 0.33 

                if eligible_for_aggressive_action and max_bet_on_table < my_stack * commitment_factor:
                    # raise_amount_calculated is already defined earlier in the function
                    reraise_amount = raise_amount_calculated 
                    reraise_amount = max(reraise_amount, min_raise) # Ensure it's a valid min raise total
                    reraise_amount = round(min(reraise_amount, my_stack), 2)

                    if reraise_amount > bet_to_call: # Ensure it's an actual raise
                        action_type = "re-raising (4-bet+)" if we_already_raised_this_street else "3-betting"
                        logger.info(f"{preflop_category} in SB, {action_type}. Action: RAISE, Amount: {reraise_amount}")
                        persist_opponents(); return ACTION_RAISE, reraise_amount
                
                logger.info(f"{preflop_category} in SB, facing raise, folding (default path). Action: FOLD")
                persist_opponents(); return ACTION_FOLD, 0
        elif position == 'BB':
            # BB strategy: Defend wider. Call, 3-bet, or check.
            if max_bet_on_table <= big_blind: # Limped pot or folded to BB
                if can_check and bet_to_call == 0: # Option to check
                    print(f"{preflop_category} in BB, can check. Action: CHECK")
                    preflop_logger.info(f"{preflop_category} in BB, can check. Action: CHECK")
                    persist_opponents(); return action_check_const, 0
                else: # Must be limpers, BB can raise (or complete if SB limped and bet_to_call is small)
                    # TODO: Implement BB logic for limpers or small bet_to_call
                    pass
            else: # Facing a raise in BB
                pot_odds = bet_to_call / (pot_size + bet_to_call) if (pot_size + bet_to_call) > 0 else 1
                
                should_3bet = False
                # 3-bet stronger hands: AQs+, KQs, TT+, AKo.
                if preflop_category == "Strong Pair": # TT, JJ
                    should_3bet = True
                elif preflop_category == "Suited Ace": # AQs, AKs (more broadly, strong suited aces)
                    should_3bet = True 
                elif preflop_category == "Playable Broadway": # KQs (more broadly, strong suited broadways)
                    should_3bet = True
                # AKo would be "Offsuit Ace" or "Offsuit Broadway". Need more specific check for AKo.
                # For now, this is a simplified 3-bet range from BB.

                if should_3bet and max_bet_on_table < my_stack * 0.4: # Avoid 3-betting too much stack
                    three_bet_amount = raise_amount_calculated # Global calc for BB 3bet (e.g., 4.0 * max_bet_on_table)
                    three_bet_amount = max(three_bet_amount, min_raise)
                    three_bet_amount = round(min(three_bet_amount, my_stack), 2)
                    if three_bet_amount > bet_to_call:
                        print(f"{preflop_category} in BB, 3-betting. Action: RAISE, Amount: {three_bet_amount}")
                        preflop_logger.info(f"{preflop_category} in BB, 3-betting. Action: RAISE, Amount: {three_bet_amount}")
                        persist_opponents(); return action_raise_const, three_bet_amount

                # Calling range: Suited Aces, Suited Kings, Playable Broadways, Offsuit Broadways, Strong/Medium Pairs, some Suited Playables
                can_afford_call = bet_to_call < my_stack
                # Call if bet_to_call is not too large (e.g., vs 2-3x open, call wider. Vs 3bet, be tighter)
                # Example: call if raise is up to 4-5x BB, or if pot odds are good.
                reasonable_bet_to_call_threshold = big_blind * 5 
                # If facing a 3-bet (e.g. max_bet_on_table is already > 3*BB), this threshold might be too high for calling wide.
                if max_bet_on_table > big_blind * 3.5: # Facing a likely 3-bet
                    reasonable_bet_to_call_threshold = big_blind * 10 # Adjust for calling 3-bets, but still be mindful of stack.
                                                                    # This means bet_to_call is the additional amount for the 3bet.

                is_decent_hand_to_call = preflop_category in ["Suited Ace", "Suited King", "Playable Broadway", "Offsuit Broadway", "Strong Pair", "Medium Pair", "Suited Playable"]

                if can_afford_call and bet_to_call <= reasonable_bet_to_call_threshold and is_decent_hand_to_call:
                    print(f"{preflop_category} in BB, facing raise, calling. Pot odds: {pot_odds:.2f}. Action: CALL, Amount: {bet_to_call}")
                    preflop_logger.info(f"{preflop_category} in BB, facing raise, calling. Pot odds: {pot_odds:.2f}. Action: CALL, Amount: {bet_to_call}")
                    persist_opponents(); return action_call_const, bet_to_call
                elif can_check and bet_to_call == 0: # Should have been caught by opening logic if folded to BB
                     print(f"{preflop_category} in BB, can check (unlikely here). Action: CHECK")
                     preflop_logger.info(f"{preflop_category} in BB, can check (unlikely here). Action: CHECK")
                     persist_opponents(); return action_check_const, 0
                
                print(f"{preflop_category} in BB, facing raise, folding. Action: FOLD")
                preflop_logger.info(f"{preflop_category} in BB, facing raise, folding. Action: FOLD")
                persist_opponents(); return action_fold_const, 0
        # Fallback if position not matched (should not occur if all positions handled)
        else:
            print(f"WARNING: {preflop_category} in unhandled position {position}. Defaulting to check/fold.")
            preflop_logger.warning(f"{preflop_category} in unhandled position {position}. Defaulting to check/fold.")
            if can_check:
                return action_check_const, 0
            return action_fold_const, 0

    # --- Win probability integration ---
    # Estimate win probability preflop using EquityCalculator
    try:
        eq_calc = EquityCalculator()
        # Assume my_player['hand'] is a list of two card strings, e.g., ['K♥', '4♥']
        # No community cards preflop
        hero_hand = my_player['hand']
        community_cards = []
        num_opps = active_opponents_count if active_opponents_count > 0 else 1
        win_probability = eq_calc.calculate_win_probability(hero_hand, community_cards, num_opps)
        preflop_logger.info(f"Estimated preflop win probability: {win_probability:.2%} for hand {hero_hand} vs {num_opps} opponents")
    except Exception as e:
        win_probability = 0.0
        preflop_logger.warning(f"Win probability calculation failed: {e}")

    # --- Decision Logic Continued ---
    # (Incorporate win_probability into decision logic where relevant)
    if win_probability < 0.15:
        print(f"DEBUG PREFLOP: Very low win probability ({win_probability:.2%}), likely fold.")
        preflop_logger.info(f"Very low win probability ({win_probability:.2%}) for hand {my_player['hand']}, position {position}. Consider folding.")
        return action_fold_const, 0
    elif win_probability > 0.75:
        print(f"DEBUG PREFLOP: High win probability ({win_probability:.2%}), consider raising.")
        preflop_logger.info(f"High win probability ({win_probability:.2%}) for hand {my_player['hand']}, position {position}. Consider raising.")
        if raise_amount_calculated > bet_to_call:
            return action_raise_const, raise_amount_calculated
        else:
            return action_call_const, bet_to_call

    # --- Win probability based fallback decision ---
    WIN_PROB_CALL_THRESHOLD = 0.6  # You can tune this threshold
    if bet_to_call > 0:
        # Use improved pot odds safeguard before folding
        action, amount, reasoning = improved_pot_odds_safeguard(
            action_fold_const if win_probability < WIN_PROB_CALL_THRESHOLD else action_call_const,
            bet_to_call, pot_size, win_probability, preflop_category, f"Preflop fallback: win_prob={win_probability:.2%}"
        )
        preflop_logger.info(f"[IMPROVED POT ODDS SAFEGUARD] {action}, {amount}, {reasoning}")
        if action != action_fold_const:
            persist_opponents(); return action, amount
        # Use improved folding logic for preflop
        if should_fold_preflop(my_player['hand'], position, bet_to_call / big_blind):
            preflop_logger.info(f"[IMPROVED FOLD] {my_player['hand']} in {position}, bet_size_bb={bet_to_call / big_blind:.2f}")
            persist_opponents(); return action_fold_const, 0
        # Use improved bluffing logic if appropriate
        if should_bluff('neutral', pot_size, 0.5, position):
            preflop_logger.info(f"[IMPROVED BLUFF] {my_player['hand']} in {position}, bluffing preflop")
            persist_opponents(); return action_raise_const, raise_amount_calculated
        # Default to call if in the middle range of win probabilities and no other conditions met
        preflop_logger.info(f"[IMPROVED DEFAULT CALL] {my_player['hand']} in {position}, default call")
        persist_opponents(); return action_call_const, bet_to_call

    # Fallback for unhandled preflop categories or logic fall-through
    print(f"WARNING: Unhandled preflop_category '{preflop_category}' or major logic fall-through in make_preflop_decision. Defaulting to FOLD.")
    preflop_logger.warning(f"Unhandled preflop_category '{preflop_category}' or major logic fall-through in make_preflop_decision. Defaulting to FOLD.")
    if opponent_tracker is not None and hasattr(opponent_tracker, 'save_all_profiles'):
        logger.info("Calling opponent_tracker.save_all_profiles() in make_preflop_decision")
        opponent_tracker.save_all_profiles()
    return action_fold_const, 0
