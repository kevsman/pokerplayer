# preflop_decision_logic.py
import math # For round
from hand_utils import get_preflop_hand_category # Ensure this is imported

# Constants for actions (consider moving to a shared constants file)
ACTION_FOLD = "fold"
ACTION_CHECK = "check"
ACTION_CALL = "call"
ACTION_RAISE = "raise"

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
    if max_bet_on_table <= big_blind and not (is_sb and my_current_bet_this_street == small_blind and bet_to_call == big_blind - small_blind) and not (is_bb and my_current_bet_this_street == big_blind and bet_to_call == 0):
        # If we are not SB facing an unraised pot, or BB facing an unraised pot.
        # Expected pot if no limpers and action is on us (not SB/BB): SB+BB
        # Expected pot if we are SB (unopened): SB
        # Expected pot if we are BB (unopened, SB called): SB_call + BB
        
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
            num_limpers = int(round(money_from_others_not_blinds / big_blind))
        num_limpers = max(0, num_limpers)


    # --- Raise Amount Calculation (Revised) ---
    if max_bet_on_table <= big_blind: # No prior actual raise, only blinds or limps posted. This is an opening or isolation raise situation.
        # Opening raise or isolation raise over limpers: 3xBB base + 1BB for each limper.
        # (Consider position-based opening sizes later, e.g., 2.5x from BTN/CO)
        base_open_multiple = 3 
        # if position in ['CO', 'BTN'] and num_limpers == 0: # Example: 2.5x for CO/BTN opens
        #     base_open_multiple = 2.5
        raise_amount_calculated = (base_open_multiple * big_blind) + (num_limpers * big_blind)
    else: # Facing a real raise (max_bet_on_table > big_blind). This is a re-raise (3-bet, 4-bet, etc.) situation.
        # Standard 3-bet/re-raise sizing: 3x the opponent's total bet on this street.
        raise_amount_calculated = 3 * max_bet_on_table # Total bet amount for our re-raise

    # Ensure raise is at least min_raise and respects stack size
    raise_amount_calculated = max(raise_amount_calculated, min_raise if min_raise > bet_to_call else 0) # min_raise is total, ensure it's actually a raise
    if bet_to_call > 0 and raise_amount_calculated <= bet_to_call : # If calculated amount is not a raise over the call
        raise_amount_calculated = min_raise # Default to min_raise if previous calc was too small but > bet_to_call

    raise_amount_calculated = round(min(raise_amount_calculated, my_stack), 2)
    
    # This check was here, ensure it's still valid:
    # If we decide to raise, the amount must be at least min_raise.
    # min_raise is the *total* bet amount for a valid minimum raise.
    # If raise_amount_calculated < min_raise and raise_amount_calculated > bet_to_call: # If it's intended as a raise but too small
    #    raise_amount_calculated = min_raise
    # This should be covered by max(raise_amount_calculated, min_raise) if min_raise is correctly the total bet.
    # Let's refine: if we intend to raise, the amount must be >= min_raise.
    # The decision to raise comes later. This is just the 'default' calculated raise.


    print(f"Preflop Logic: Pos: {position}, Cat: {preflop_category}, B2Call: {bet_to_call}, CanChk: {can_check}, CalcRaise: {raise_amount_calculated}, MyStack: {my_stack}, MyBet: {my_current_bet_this_street}, MaxOppBet: {max_bet_on_table}, Pot: {pot_size}, Opps: {active_opponents_count}, BB: {big_blind}, is_bb: {is_bb}, NumLimpers: {num_limpers}")

    # --- Decision Logic ---

    if preflop_category == "Weak":
        if can_check and is_bb and bet_to_call == 0:
            print(f"Weak hand in BB, option to check. Action: CHECK")
            return action_check_const, 0
        # If SB limps and BB has a weak hand, BB should check (already covered by can_check and bet_to_call == 0)
        # If facing a raise, fold weak hands.
        if bet_to_call > 0:
            # Exception: If it's a very small completion bet in BB vs SB limp, and pot odds are amazing.
            # However, for "Weak" category, folding is generally safer.
            if is_bb and max_bet_on_table == small_blind and bet_to_call == (small_blind - my_current_bet_this_street):
                 # This is SB limping, BB has option to complete. With a truly weak hand, check if possible, else fold to raise.
                 # If bet_to_call is small_blind (meaning SB limped and we are BB with BB already in), this is effectively a check.
                 # The issue is if SB limps, BB's bet_to_call is 0 if SB just posted SB.
                 # If SB completes to BB, then BB's bet_to_call is 0.
                 # This specific logic for SB limp completion needs to be handled by `can_check` and `bet_to_call == 0` for BB.
                 pass # Covered by general check/fold logic

            print(f"Weak hand facing bet > SB completion. Action: FOLD")
            return action_fold_const, 0
        
        # If no bet to call, and cannot check (e.g., UTG must act), fold weak hands.
        if bet_to_call == 0 and not can_check:
             print(f"Weak hand, cannot check (e.g. UTG open), no bet to call. Action: FOLD")
             return action_fold_const, 0
        
        # If no bet to call, can check, and not BB (e.g. UTG limp is allowed by rules, or later position check through)
        if bet_to_call == 0 and can_check and not is_bb:
            print(f"Weak hand, not BB, can check (limp/check through). Action: CHECK")
            return action_check_const, 0
        
        # Default for weak hands: if can check, check. Otherwise, fold.
        # This covers the BB case where it's checked to them (bet_to_call == 0, can_check == True)
        print(f"Weak hand, default. Action: CHECK if can_check else FOLD. (can_check={can_check}, bet_to_call={bet_to_call})")
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
                if bet_to_call < my_stack * 0.5: # Arbitrary threshold for calling with premium if raise sizing failed
                    print(f"Premium Pair, facing bet, raise calc failed, calling. Action: CALL, Amount: {bet_to_call}")
                    return action_call_const, bet_to_call
                else: # If too expensive to call after failed raise attempt
                    print(f"Premium Pair, facing bet, raise calc failed, too expensive to call. Action: FOLD") # Should be rare
                    return action_fold_const, 0
            
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
            # Opening or raising over limpers if no one has made a 'real' raise yet
            if max_bet_on_table <= big_blind:
                # Use the global raise_amount_calculated for opening
                open_raise = raise_amount_calculated
                open_raise = max(open_raise, min_raise) # Ensure it's at least min_raise
                open_raise = round(min(open_raise, my_stack),2)

                if open_raise > bet_to_call or (open_raise == my_stack and my_stack > bet_to_call): # Must be a raise or covering all-in
                    # Filter out weaker hands in this category for UTG/MP opens if they are too weak
                    if position == 'UTG' and preflop_category in ["Medium Pair", "Suited Playable"]: # Too loose for UTG open
                         if can_check: return action_check_const, 0
                         return action_fold_const, 0
                    if position == 'MP' and preflop_category == "Medium Pair" and preflop_category not in ["Strong Pair"]: # e.g. 77-99 from MP might be too loose for 3x open
                         # TT+ is Strong Pair. So this is for 77-99.
                         # Let's allow MP to open Medium Pairs for now, test_preflop_utg1_open_raise_tt is TT (Strong Pair)
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
                if preflop_category == "Strong Pair": # TT, JJ
                    if bet_to_call <= big_blind * 3.5: 
                        print(f"{preflop_category} in {position}, facing 3-bet <= 3.5x. Action: CALL, Amount: {bet_to_call}")
                        return action_call_const, bet_to_call
                    else:
                        print(f"{preflop_category} in {position}, facing large 3-bet > 3.5x. Action: FOLD")
                        return action_fold_const, 0
                # For other strong hands like AK, AQ, KQs in UTG/MP facing a raise.
                # Call smaller raises.
                print(f"{preflop_category} in {position}, facing raise <= 4BB. Action: CALL, Amount: {bet_to_call}")
                return action_call_const, bet_to_call
            else: # Facing a large raise
                print(f"{preflop_category} in {position}, facing large raise > 4BB. Action: FOLD")
                return action_fold_const, 0
        elif position in ['CO', 'BTN']:
            # Opening or raising over limpers
            if max_bet_on_table <= big_blind:
                open_raise = raise_amount_calculated # Use global calc: (3*BB or 2.5*BB) + limpers
                open_raise = max(open_raise, min_raise)
                open_raise = round(min(open_raise, my_stack),2)
                if open_raise > bet_to_call or (open_raise == my_stack and my_stack > bet_to_call):
                    print(f"{preflop_category} in {position}, opening/raising limpers. Action: RAISE, Amount: {open_raise}")
                    return action_raise_const, open_raise
                else: # Raise calculation failed
                     if can_check: return action_check_const, 0
                     return action_fold_const, 0 # Should not happen often here
            # Facing a raise (max_bet_on_table > big_blind)
            # 3-betting logic for strong hands like AQo, AK, AQs, KQs, TT+
            elif preflop_category in ["Playable Broadway", "Offsuit Broadway", "Suited Ace", "Offsuit Ace", "Strong Pair"] and \
                 max_bet_on_table > big_blind and \
                 max_bet_on_table <= big_blind * 3.5: # Facing an open raise (e.g. up to 3.5x)
                
                three_bet_amount = raise_amount_calculated # Global calc is 3 * max_bet_on_table
                three_bet_amount = max(three_bet_amount, min_raise)
                three_bet_amount = round(min(three_bet_amount, my_stack), 2)

                if three_bet_amount > bet_to_call: # Ensure it's a valid raise
                    print(f"{preflop_category} in {position}, 3-betting vs open. Action: RAISE, Amount: {three_bet_amount}")
                    return action_raise_const, three_bet_amount
                else: # 3-bet calculation failed to be a raise, fallback to call
                    print(f"{preflop_category} in {position}, 3-bet calc failed, calling. Action: CALL, Amount: {bet_to_call}")
                    return action_call_const, bet_to_call
            # Call wider if not 3-betting or if it's a weaker hand in this category
            elif bet_to_call <= big_blind * 5: 
                print(f"{preflop_category} in {position}, facing raise <= 5BB. Action: CALL, Amount: {bet_to_call}")
                return action_call_const, bet_to_call
            else: # Facing a very large raise (4bet+)
                print(f"{preflop_category} in {position}, facing large raise > 5BB. Action: FOLD")
                return action_fold_const, 0
        elif position == 'SB':
            # Opening / Isolating from SB
            if max_bet_on_table <= big_blind : # No prior raise, SB can open/iso-limp
                open_raise = raise_amount_calculated # Global calc: (3*BB) + limpers
                open_raise = max(open_raise, min_raise)
                open_raise = round(min(open_raise, my_stack),2)
                if open_raise > bet_to_call or (open_raise == my_stack and my_stack > bet_to_call):
                     # Filter some weaker hands from SB open if desired, e.g. Medium Pair might be too loose for 3x
                    if preflop_category == "Medium Pair" and num_limpers == 0: # Don't open 77-99 from SB for 3x if unopened
                        if bet_to_call == big_blind - small_blind : # Limp completion scenario
                             print(f"{preflop_category} in SB, completing. Action: CALL, Amount: {bet_to_call}")
                             return action_call_const, bet_to_call
                        # else fold if must bet more than completion
                        print(f"{preflop_category} in SB, too weak to open raise, folding. Action: FOLD")
                        return action_fold_const, 0

                    print(f"{preflop_category} in SB, opening/isolating. Action: RAISE, Amount: {open_raise}")
                    return action_raise_const, open_raise
                else: # Raise calculation failed
                     if bet_to_call == big_blind - small_blind and can_check : # effectively can complete
                         print(f"{preflop_category} in SB, completing (raise calc failed). Action: CALL, Amount: {bet_to_call}")
                         return action_call_const, bet_to_call
                     print(f"{preflop_category} in SB, opening/isolating, raise calc issue, folding. Action: FOLD")
                     return action_fold_const, 0
            # Facing a raise when in SB
            elif preflop_category in ["Suited Ace", "Playable Broadway", "Strong Pair", "Suited Playable", "Offsuit Broadway"] and \
                 bet_to_call <= big_blind * 3.5 and \
                 max_bet_on_table <= big_blind * 4: # Call raises up to ~3.5-4BB from SB with decent hands
                print(f"{preflop_category} in SB, facing raise, calling. Action: CALL, Amount: {bet_to_call}")
                return action_call_const, bet_to_call
            # Add SB 3-bet logic here if needed for stronger hands vs BTN/CO opens
            # e.g. if preflop_category in ["Suited Ace", "Offsuit Ace", "Strong Pair"] and vs BTN/CO open: 3-bet
            else: # Default for SB facing a raise with these hands if conditions not met (e.g. too large raise, or weaker like Medium Pair)
                print(f"{preflop_category} in SB, facing raise, conditions not met for call/3bet. Action: FOLD")
                return action_fold_const, 0
        elif position == 'BB':
            if can_check and bet_to_call == 0:
                print(f"{preflop_category} in BB, option to check. Action: CHECK")
                return action_check_const, 0
            # BB defense logic
            elif preflop_category == "Suited Playable" and bet_to_call <= big_blind * 3.5 and max_bet_on_table <= big_blind * 3.5 :
                print(f"{preflop_category} in BB, defending Suited Playable vs steal (<=3.5x BB). Action: CALL, Amount: {bet_to_call}")
                return action_call_const, bet_to_call
            elif preflop_category == "Medium Pair" and bet_to_call <= big_blind * 3.5 and max_bet_on_table <= big_blind * 4: # e.g. 77 vs CO 3x open (max_bet_on_table is total bet)
                print(f"{preflop_category} in BB, defending Medium Pair vs open (call <=3.5x BB). Action: CALL, Amount: {bet_to_call}")
                return action_call_const, bet_to_call
            # General BB defense for other hands in this broad category
            elif bet_to_call <= big_blind * 4 : 
                # Avoid calling too wide with weaker parts of this category if it's a large bet
                if preflop_category in ["Offsuit King"] and bet_to_call > big_blind * 3: # KJo vs 4x, maybe fold
                    print(f"{preflop_category} in BB, facing >3BB raise, folding. Action: FOLD")
                    return action_fold_const, 0
                print(f"{preflop_category} in BB, facing raise <= 4BB. Action: CALL, Amount: {bet_to_call}")
                return action_call_const, bet_to_call
            else:
                print(f"{preflop_category} in BB, facing large raise > 4BB. Action: FOLD")
                return action_fold_const, 0

    if preflop_category == "Suited Connector": # e.g. JTs, 98s, 87s
        if position in ['MP', 'CO', 'BTN']:
            if max_bet_on_table <= big_blind: # Opening or action is on us with no prior raise (use new opening condition)
                open_raise_amount = raise_amount_calculated # Use global open sizing
                # Potentially adjust for suited connectors specifically if desired (e.g. always 2.5x or 3x)
                # For now, use global: (3*BB) + limpers
                open_raise_amount = max(open_raise_amount, min_raise) 
                open_raise_amount = round(min(open_raise_amount, my_stack), 2)

                if open_raise_amount > bet_to_call or (open_raise_amount == my_stack and my_stack > bet_to_call):
                    print(f"Suited Connector in {position}, opening/raising limpers. Action: RAISE, Amount: {open_raise_amount}")
                    return action_raise_const, open_raise_amount
                else: # Raise calc failed
                    if can_check: return action_check_const, 0
                    return action_fold_const, 0
            else: # Facing a bet (max_bet_on_table > big_blind)
                if bet_to_call <= big_blind * 3:
                    print(f"Suited Connector in {position}, facing bet, amount to call <= 3BB. Action: CALL, Amount: {bet_to_call}")
                    return action_call_const, bet_to_call
                else:
                    print(f"Suited Connector in {position}, facing bet, conditions not met for call. Action: FOLD")
                    return action_fold_const, 0
        elif position == 'SB' or position == 'BB':
            if can_check and bet_to_call == 0:
                print(f"Suited Connector in {position} (Blind), can check. Action: CHECK")
                return action_check_const, 0
            if bet_to_call <= big_blind * 2.5: # Call small raises from blinds (e.g. vs minraise or 2.5x)
                print(f"Suited Connector in {position} (Blind), calling small raise. Action: CALL, Amount: {bet_to_call}")
                return action_call_const, bet_to_call
            else:
                print(f"Suited Connector in {position} (Blind), facing larger raise. Action: FOLD")
                return action_fold_const, 0
        else: # UTG
            print(f"Suited Connector in UTG. Action: FOLD") # Generally too loose to open/call from UTG
            return action_fold_const, 0
            
    # Default action if no specific logic met
    print(f"Preflop default: Category {preflop_category}, Pos {position}. Check/Fold.")
    return action_check_const if can_check else action_fold_const, 0

# Note: The function make_preflop_decision is now fully defined with enhanced logic and debugging prints.
