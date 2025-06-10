# preflop_decision_logic.py
import math # For round
from hand_utils import get_preflop_hand_category # Ensure this is imported

# Constants for actions (consider moving to a shared constants file)
ACTION_FOLD = "fold"
ACTION_CHECK = "check"
ACTION_CALL = "call"
ACTION_RAISE = "raise"

def adjust_for_implied_odds(hand_category, position, my_stack, effective_stack, big_blind):
    """
    Adjust hand selection based on implied odds for suited connectors and suited aces
    in late position with deep stacks.
    
    Args:
        hand_category: The category of the hand (e.g., "Suited Connector", "Suited Ace")
        position: Player's position (e.g., "CO", "BTN")
        my_stack: Player's current stack size
        effective_stack: Effective stack between player and opponents
        big_blind: Big blind amount
        
    Returns:
        bool: True if hand should be played more liberally due to implied odds
    """
    # Only apply to late positions with deep stacks
    if position in ['CO', 'BTN'] and effective_stack > 50 * big_blind:
        # More liberal with suited connectors and suited aces in late position
        if hand_category in ['Suited Connector', 'Suited Ace']:
            return True
    return False

def should_play_wider_in_position(hand_category, position, num_limpers, bet_to_call, big_blind):
    """
    Determine if we should play wider ranges based on position.
    This implements the key recommendation to play more hands in late position.
    """
    if position in ['CO', 'BTN']:
        # Late position - play wider ranges
        if hand_category in ['Offsuit Playable', 'Suited Playable', 'Medium Pair', 'Small Pair']:
            # More liberal in late position
            if bet_to_call <= big_blind * 3:  # Up to 3bb
                return True
        
        # Button steal spots - even wider
        if position == 'BTN' and num_limpers == 0 and bet_to_call <= big_blind:
            if hand_category in ['Suited Connector', 'Offsuit Playable', 'Small Pair']:
                return True
                
    return False

def make_preflop_decision(
    my_player, hand_category, position, bet_to_call, can_check, 
    my_stack, pot_size, active_opponents_count, 
    small_blind, big_blind, my_current_bet_this_street, max_bet_on_table, min_raise,
    is_sb, is_bb, # Added is_sb, is_bb
    action_fold_const, action_check_const, action_call_const, action_raise_const # Added action constants
    ):
    """Enhanced pre-flop decision making"""
    
    preflop_category = hand_category # Use the passed hand_category
    win_probability = 0 # Placeholder, as it's not directly used in this version of preflop logic after category
                        # If win_probability was used, it should be calculated from hand + position or passed in.

    # --- Limper Calculation (remains the same) ---
    num_limpers = 0
    # Corrected: max_bet_on_table is the highest bet any single player has made *in this round*.
    # pot_size includes all bets from previous rounds and current round.
    # my_current_bet_this_street is what my_player has put in *this* round.
    
    # Limper calculation: A limper is someone who called the big blind preflop.
    # This is tricky to calculate perfectly without full action history.
    # Simplified: if no raise yet (max_bet_on_table <= big_blind) and pot is larger than blinds + our bet.
    # MODIFIED CONDITION HERE:
    if max_bet_on_table <= big_blind and not (is_sb and my_current_bet_this_street == small_blind and bet_to_call == big_blind - small_blind):
        # If we are not SB facing an unraised pot where SB just needs to complete.
        # The case for BB having option to check when folded to (no limpers) is handled by num_limpers being 0 later.
        
        # A simpler limper estimation:
        # Money in pot beyond SB, BB, and our current bet (if we are not SB/BB and already bet)
        money_from_others_not_blinds = pot_size - my_current_bet_this_street
        if not is_sb and not is_bb: # If we are not blinds
             money_from_others_not_blinds = pot_size - (small_blind + big_blind) - my_current_bet_this_street
        elif is_sb: # If we are SB
            money_from_others_not_blinds = pot_size - small_blind # BB is the other main component
            if max_bet_on_table > small_blind : # BB must have at least BB
                 money_from_others_not_blinds -= big_blind
            else: # BB might not have posted if game just started and action is on SB weirdly
                 money_from_others_not_blinds -= max(0, max_bet_on_table) # count what BB put
        elif is_bb: # If we are BB
            money_from_others_not_blinds = pot_size - big_blind - small_blind # money from others beyond blinds

        money_from_others_not_blinds = max(0, money_from_others_not_blinds)

        if big_blind > 0:
            if money_from_others_not_blinds > 0:
                num_limpers = int(math.ceil(money_from_others_not_blinds / big_blind))
            else:
                num_limpers = 0
        else:
            num_limpers = 0 # Avoid division by zero if big_blind is 0
        num_limpers = max(0, num_limpers)    # --- Raise Amount Calculation (Revised) ---
    if max_bet_on_table <= big_blind: # No prior actual raise, only blinds or limps posted. This is an opening or isolation raise situation.
        # Opening raise or isolation raise over limpers.
        if position == 'CO':
            base_open_multiple = 3
        elif position == 'BTN':
            if num_limpers > 0:
                base_open_multiple = 3  # Use 3x for isolation over limpers
            else:
                base_open_multiple = 2.5  # Use 2.5x for normal opens
        else:
            base_open_multiple = 3
        raise_amount_calculated = (base_open_multiple * big_blind) + (num_limpers * big_blind)
    else: # Facing a real raise (max_bet_on_table > big_blind). This is a re-raise (3-bet, 4-bet, etc.) situation.
        # 3-bet/4-bet/squeeze sizing        # Squeeze: if more than one opponent has put in max_bet_on_table, use 4.5x open
        if position in ['CO', 'BTN'] and pot_size > 2 * max_bet_on_table:
            raise_amount_calculated = 4.5 * max_bet_on_table
        # 4-bet: if max_bet_on_table > 7*big_blind (likely a 3-bet), use 2.33x (to get 0.42 from 0.18)
        elif max_bet_on_table > 7 * big_blind:
            raise_amount_calculated = 2.33 * max_bet_on_table        # 3-bet OOP (SB/BB): 3x open for SB value hands
        elif position in ['SB', 'BB']:
            if position == 'BB':
                raise_amount_calculated = 4.0 * max_bet_on_table
            else:
                raise_amount_calculated = 3.0 * max_bet_on_table  # 3x for value hands, bluffs use custom sizing
        # 3-bet IP: 3x open
        else:
            raise_amount_calculated = 3 * max_bet_on_table
    
    # Final adjustments and validations
    raise_amount_calculated = max(raise_amount_calculated, min_raise if min_raise > bet_to_call else 0)
    if bet_to_call > 0 and raise_amount_calculated <= bet_to_call:
        raise_amount_calculated = min_raise
    raise_amount_calculated = round(min(raise_amount_calculated, my_stack), 2)
    
    # This check was here, ensure it's still valid:
    # If we decide to raise, the amount must be at least min_raise.
    # min_raise is the *total* bet amount for a valid minimum raise.
    # If raise_amount_calculated < min_raise and raise_amount_calculated > bet_to_call: # If it's intended as a raise but too small
    #    raise_amount_calculated = min_raise
    # This should be covered by max(raise_amount_calculated, min_raise) if min_raise is correctly the total bet.
    # Let's refine: if we intend to raise, the amount must be >= min_raise.
    # The decision to raise comes later. This is just the 'default' calculated raise.    print(f"Preflop Logic: Pos: {position}, Cat: {preflop_category}, B2Call: {bet_to_call}, CanChk: {can_check}, CalcRaise: {raise_amount_calculated}, MyStack: {my_stack}, MyBet: {my_current_bet_this_street}, MaxOppBet: {max_bet_on_table}, Pot: {pot_size}, Opps: {active_opponents_count}, BB: {big_blind}, is_bb: {is_bb}, NumLimpers: {num_limpers}")

    # --- Decision Logic ---
    
    print(f"DEBUG PREFLOP: Starting decision logic with hand_category='{preflop_category}'")
    
    if preflop_category == "Weak":
        print(f"DEBUG PREFLOP: Entered Weak hand category")
        
        if can_check and is_bb and bet_to_call == 0:
            print(f"DEBUG PREFLOP: BB can check with no bet to call. Action: CHECK")
            return action_check_const, 0
        
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
                    return action_raise_const, steal_amount
        
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
                    return action_raise_const, steal_amount
                      # If facing a raise, fold weak hands (with some exceptions)
        if bet_to_call > 0:
            print(f"DEBUG PREFLOP: Weak hand facing bet (bet_to_call={bet_to_call}). Action: FOLD")
            return action_fold_const, 0
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
                        return action_raise_const, steal_amount
            
            # If not a steal situation and cannot check, fold
            if not can_check:
                print(f"DEBUG PREFLOP: Weak hand, cannot check (e.g. UTG open), no bet to call. Action: FOLD")
                print(f"DEBUG PREFLOP: Details - can_check={can_check}, position={position}, bet_to_call={bet_to_call}")
                return action_fold_const, 0# Debug logging for BB check issue investigation
        print(f"DEBUG PREFLOP: At check/fold decision point:")
        print(f"  - position: {position}")
        print(f"  - bet_to_call: {bet_to_call}")
        print(f"  - can_check: {can_check}")
        print(f"  - is_bb: {is_bb}")
        print(f"  - hand_category: {hand_category}")
        
        # If no bet to call and can check (e.g. UTG limp, later position check through, or BB with no raise)
        if bet_to_call == 0 and can_check:
            print(f"DEBUG PREFLOP: Weak hand, can check (limp/check through or BB facing no bet). Action: CHECK")
            return action_check_const, 0
        
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
                return action_raise_const, actual_raise_amount
            else: # Should not happen if min_raise is valid and stack sufficient. Fallback to call if weird state.
                if bet_to_call < my_stack and bet_to_call > 0:
                    print(f"Premium Pair, opening/isolating, raise calc issue, calling. Action: CALL, Amount: {bet_to_call}")
                    return action_call_const, bet_to_call
                elif can_check:
                    print(f"Premium Pair, opening/isolating, raise calc issue, checking. Action: CHECK")
                    return action_check_const, 0
                else:
                    print(f"Premium Pair, opening/isolating, raise calc issue, folding. Action: FOLD")
                    return action_fold_const, 0
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
                     return action_raise_const, my_stack
                  # Fallback if raise calculation is problematic
                # Premium pairs (AA, KK, QQ) should almost never fold preflop
                # Call with any premium pair if we can't raise properly
                if bet_to_call < my_stack: # Can afford to call (not an impossible all-in for more than stack)
                    print(f"Premium Pair, facing bet, raise calc failed, calling with premium hand. Action: CALL, Amount: {bet_to_call}")
                    return action_call_const, bet_to_call
                else: # Only fold if the bet is somehow more than our entire stack (should never happen)
                    print(f"Premium Pair, facing bet larger than stack (impossible situation). Action: CALL ALL-IN, Amount: {my_stack}")
                    return action_call_const, my_stack
            
            # If calculated raise is a significant portion of stack, consider it an all-in.
            if actual_raise_amount >= my_stack * 0.85 and actual_raise_amount > bet_to_call : 
                print(f"Premium Pair, facing bet, large re-raise. Action: RAISE (ALL-IN), Amount: {my_stack}")
                return action_raise_const, my_stack
            
            print(f"Premium Pair, facing bet. Action: RAISE, Amount: {actual_raise_amount}")
            return action_raise_const, actual_raise_amount

    # AKs, AKo, AQs, AQo, AJs, AJo, KQs, KQo (Playable Broadway / Suited Ace)
    # Strong Pair (JJ, TT)
    # Suited Playable (KJs, KTs, QJs, QTs, JTs)
    # Medium Pair (99, 88, 77) - Added
    if preflop_category in ["Suited Ace", "Offsuit Ace", "Suited King", "Offsuit King", "Playable Broadway", "Offsuit Broadway", "Strong Pair", "Suited Playable", "Medium Pair"]:
        if position in ['UTG', 'MP']:
            # Facing a real raise (max_bet_on_table > big_blind)
            # Fold AJo/ATo facing UTG raise + MP 3-bet
            if bet_to_call > big_blind * 4 or (preflop_category in ["Offsuit Ace", "Offsuit Broadway"] and max_bet_on_table > 7 * big_blind):
                print(f"{preflop_category} in {position}, facing large raise or 3-bet. Action: FOLD")
                return action_fold_const, 0

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
                         return action_fold_const, 0
                    if position == 'MP' and preflop_category == "Medium Pair" and preflop_category not in ["Strong Pair"]: # e.g. 77-99 from MP might be too loose for 3x open
                         # TT+ is Strong Pair. So this is for 77-99.
                         # Let's allow MP to open Medium Pairs for now
                         pass

                    print(f"{preflop_category} in {position}, opening/raising limpers. Action: RAISE, Amount: {open_raise}")
                    return action_raise_const, open_raise
                else: # Raise calculation failed, try to check/fold
                     if can_check:
                         print(f"{preflop_category} in {position}, opening, raise calc issue, checking. Action: CHECK")
                         return action_check_const, 0
                     else:
                         print(f"{preflop_category} in {position}, opening, raise calc issue, folding. Action: FOLD")
                         return action_fold_const, 0
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
                            return action_raise_const, three_bet_amount
                    
                    # If not 3-betting (e.g. TT, JJ vs larger raise, or AKo if 3-bet calc failed)
                    if bet_to_call <= big_blind * 3.5: 
                        print(f"{preflop_category} in {position}, facing raise <= 3.5x. Action: CALL, Amount: {bet_to_call}")
                        return action_call_const, bet_to_call
                    else:
                        print(f"{preflop_category} in {position}, facing large raise > 3.5x. Action: FOLD")
                        return action_fold_const, 0
                # For suited aces like A8s in CO vs UTG open - should call, not 3-bet
                # Only 3-bet stronger suited aces (AJs+) not weaker ones (A8s, A9s)
                elif preflop_category == "Suited Ace":
                    print(f"{preflop_category} in {position}, facing raise <= 4BB. Action: CALL, Amount: {bet_to_call}")
                    return action_call_const, bet_to_call
                # For other strong hands like AK, AQ, KQs in UTG/MP facing a raise.
                # Call smaller raises.
                print(f"{preflop_category} in {position}, facing raise <= 4BB. Action: CALL, Amount: {bet_to_call}")
                return action_call_const, bet_to_call
            else: # Facing a large raise
                print(f"{preflop_category} in {position}, facing large raise > 4BB. Action: FOLD")
                return action_fold_const, 0
        elif position in ['CO', 'BTN']:
            # Facing a raise (max_bet_on_table > big_blind)
            # Fold weak offsuit aces facing large raises, but check pot odds for strong hands like AQ offsuit
            if preflop_category == "Offsuit Ace" and max_bet_on_table > 7 * big_blind:
                # This might be too tight for BTN vs CO, but as a general rule for "Offsuit Ace"
                print(f"{preflop_category} in {position}, facing large raise or 3-bet. Action: FOLD")
                return action_fold_const, 0
            # For Offsuit Broadway (like AQ offsuit), check pot odds before folding to large raises
            elif preflop_category == "Offsuit Broadway" and max_bet_on_table > 7 * big_blind:
                # Calculate pot odds to decide if we should call with a strong hand
                pot_odds_needed = bet_to_call / (pot_size + bet_to_call) if (pot_size + bet_to_call) > 0 else 1
                if pot_odds_needed <= 0.40:  # AQ offsuit should call with good pot odds
                    print(f"{preflop_category} in {position}, facing large raise but good pot odds ({pot_odds_needed:.1%} equity needed). Action: CALL, Amount: {bet_to_call}")
                    return action_call_const, bet_to_call
                else:
                    print(f"{preflop_category} in {position}, facing large raise with poor pot odds ({pot_odds_needed:.1%} equity needed). Action: FOLD")
                    return action_fold_const, 0

            # Squeeze logic: if pot_size > 2*max_bet_on_table, treat as squeeze (already part of raise_amount_calculated)
            # The raise_amount_calculated for CO/BTN already considers squeeze (4.5x) or 3-bet (3x).
            
            # Opening or raising over limpers
            if max_bet_on_table <= big_blind:
                open_raise = raise_amount_calculated # Use global calc: (3*BB or 2.5*BB for BTN) + limpers
                open_raise = max(open_raise, min_raise)
                open_raise = round(min(open_raise, my_stack),2)
                if open_raise > bet_to_call or (open_raise == my_stack and my_stack > bet_to_call):
                    print(f"{preflop_category} in {position}, opening/isolating. Action: RAISE, Amount: {open_raise}")
                    return action_raise_const, open_raise
                else: # Raise calculation failed
                     if can_check: # Should not happen if opening unless BB
                         print(f"{preflop_category} in {position}, opening, raise calc issue, checking. Action: CHECK")
                         return action_check_const, 0
                     else:
                         print(f"{preflop_category} in {position}, opening, raise calc issue, folding. Action: FOLD")
                         return action_fold_const, 0
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
                    return action_raise_const, three_bet_amount
                elif bet_to_call < my_stack : # Fallback to call if 3-bet calc is too small but can call
                    print(f"{preflop_category} in {position}, 3-bet calc low, calling. Action: CALL, Amount: {bet_to_call}")
                    return action_call_const, bet_to_call
                else: # Cannot 3-bet effectively or call
                    print(f"{preflop_category} in {position}, cannot 3-bet/call effectively. Action: FOLD")
                    return action_fold_const, 0
            elif bet_to_call <= big_blind * 10: # Facing a larger bet (likely 3-bet or 4-bet)
                # Call with strong suited hands and strong pairs if odds are decent and not too much of stack.
                if preflop_category in ["Suited Ace", "Playable Broadway", "Strong Pair"] and bet_to_call < my_stack * 0.33:
                    print(f"{preflop_category} in {position}, facing large bet, calling. Action: CALL, Amount: {bet_to_call}")
                    return action_call_const, bet_to_call
                else:
                    print(f"{preflop_category} in {position}, facing large bet, folding. Action: FOLD")
                    return action_fold_const, 0
            else: # Facing a very large bet
                print(f"{preflop_category} in {position}, facing very large bet. Action: FOLD")
                return action_fold_const, 0
        elif position == 'SB':
            # SB strategy: 3-bet or fold mostly. Call very selectively.
            if max_bet_on_table <= big_blind: # Opening from SB (limped to SB or SB is first to act after blinds)
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
                         return action_fold_const, 0

                if open_raise > bet_to_call: # bet_to_call should be small_blind if completing, or 0 if opening
                    print(f"{preflop_category} in SB, opening/raising. Action: RAISE, Amount: {open_raise}")
                    return action_raise_const, open_raise
                elif can_check: # Should only happen if it was checked to SB and BB, and SB wants to check.
                                # But this block is for stronger hands, unlikely to check here.
                                # More likely, this means raise calc failed.
                    print(f"{preflop_category} in SB, open/raise calc issue, checking. Action: CHECK")
                    return action_check_const, 0
                else: # Cannot raise effectively
                    print(f"{preflop_category} in SB, open/raise calc issue, folding. Action: FOLD")
                    return action_fold_const, 0
            else: # Facing a raise in SB
                # Strong hands 3-bet: Suited Ace (AJs+), Playable Broadway (KQs), Strong Pair (TT+)
                # Simplified: 3-bet "Strong Pair", "Suited Ace", "Playable Broadway"
                is_strong_for_3bet = preflop_category in ["Strong Pair", "Suited Ace", "Playable Broadway"]
                
                if is_strong_for_3bet and max_bet_on_table < my_stack * 0.33 : # Avoid 3-betting into huge bets
                    three_bet_amount = raise_amount_calculated # Global calc for SB 3bet (e.g., 3.0 * max_bet_on_table)
                    three_bet_amount = max(three_bet_amount, min_raise)
                    three_bet_amount = round(min(three_bet_amount, my_stack), 2)
                    if three_bet_amount > bet_to_call:
                        print(f"{preflop_category} in SB, 3-betting. Action: RAISE, Amount: {three_bet_amount}")
                        return action_raise_const, three_bet_amount
                
                # Generally fold other hands from SB when facing a raise unless very specific read/situation
                print(f"{preflop_category} in SB, facing raise, folding. Action: FOLD")
                return action_fold_const, 0

        elif position == 'BB':
            # BB strategy: Defend wider. Call, 3-bet, or check.
            if max_bet_on_table <= big_blind: # Limped pot or folded to BB
                if can_check and bet_to_call == 0: # Option to check
                    print(f"{preflop_category} in BB, can check. Action: CHECK")
                    return action_check_const, 0
                else: # Must be limpers, BB can raise (or complete if SB limped and bet_to_call is small)
                    iso_raise = raise_amount_calculated # Global calc: (base_open_multiple * big_blind) + (num_limpers * big_blind)
                    iso_raise = max(iso_raise, min_raise)
                    iso_raise = round(min(iso_raise, my_stack), 2)
                    
                    # Raise with a decent range over limpers, especially stronger hands in this category
                    # Don't raise with weakest parts of "Medium Pair" or "Suited Playable" if many limpers (reverse implied odds)
                    # For simplicity, if it's in this strong category, consider raising over limps.
                    if iso_raise > bet_to_call:
                        print(f"{preflop_category} in BB, isolating limpers/raising. Action: RAISE, Amount: {iso_raise}")
                        return action_raise_const, iso_raise
                    elif can_check: # This implies bet_to_call was 0, caught above. Or raise calc failed.
                        print(f"{preflop_category} in BB, raise calc issue or already checked to, checking. Action: CHECK")
                        return action_check_const, 0
                    else: # Should not happen if BB can act and not check
                        print(f"{preflop_category} in BB, unexpected state, folding. Action: FOLD")
                        return action_fold_const, 0
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
                        return action_raise_const, three_bet_amount

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
                    return action_call_const, bet_to_call
                elif can_check and bet_to_call == 0: # Should have been caught by opening logic if folded to BB
                     print(f"{preflop_category} in BB, can check (unlikely here). Action: CHECK")
                     return action_check_const, 0
                
                print(f"{preflop_category} in BB, facing raise, folding. Action: FOLD")
                return action_fold_const, 0
        # Fallback if position not matched (should not occur if all positions handled)
        else:
            print(f"WARNING: {preflop_category} in unhandled position {position}. Defaulting to check/fold.")
            if can_check:
                return action_check_const, 0
            return action_fold_const, 0
