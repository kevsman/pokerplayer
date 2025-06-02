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

    # --- Raise Amount Calculation ---
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


    if bet_to_call == 0: # No bet to call, we are opening or checking
        # Opening raise: 3xBB + 1BB for each limper
        raise_amount_calculated = (3 * big_blind) + (num_limpers * big_blind)
        raise_amount_calculated = max(raise_amount_calculated, min_raise) # Ensure it's at least min_raise
    else: # Facing a bet, considering a re-raise (3-bet, 4-bet etc.)
        # Standard 3-bet sizing: 3x the original raise size (max_bet_on_table)
        # The raise amount is the *additional* amount on top of the call.
        # So, total bet = call_amount + 3 * (size_of_bet_faced)
        # size_of_bet_faced = max_bet_on_table (if we haven't bet yet)
        # or max_bet_on_table - my_current_bet_this_street (if we have bet, this is the raise over our bet)
        
        # The amount to raise *over* the call.
        # If opponent bets 10 (max_bet_on_table=10), we call 10. Standard 3bet is 3x their bet, so raise by 30. Total 40.
        # If opponent opens to 3BB, we 3-bet to 9-12BB total.
        # raise_increment = 3 * max_bet_on_table
        # raise_amount_calculated = bet_to_call + raise_increment 
        # This is simpler: target total bet of 3x the opponent's last bet/raise size.
        # If P1 bets 10, P2 raises to 30. P1's bet_to_call is 20. max_bet_on_table is 30.
        # P1 wants to 4-bet. Should be ~2.5-3x the size of P2's raise. P2 raised by 20 (30-10).
        # So P1 re-raises by 2.5*20 = 50. Total bet = 30 (call) + 50 (reraise) = 80.
        
        # Simplified: Make total bet 3x the current max_bet_on_table + money already in pot (excluding current street bets)
        # pot_before_this_betting_round = pot_size - (sum of all current_street_bets) -> hard to get easily
        # Let's use a common 3-bet sizing: 3 * amount_of_last_raise + amount_to_call
        # amount_of_last_raise is effectively max_bet_on_table if it was an open, or (max_bet_on_table - previous_bet_level)
        # For simplicity: raise to 3 * max_bet_on_table. This is the *total* bet.
        raise_amount_calculated = 3 * max_bet_on_table
        # Add money already in the pot from previous streets/players (approx pot_size - current street bets by active players)
        # This gets complicated. A simpler model:
        # If OOP: 3x raise + call amount. If IP: 2.5x raise + call amount.
        # raise_size_faced = max_bet_on_table - my_current_bet_this_street (if I am facing a raise over my bet)
        # or max_bet_on_table (if I am facing an initial bet/raise and I haven't bet yet)
        
        # Let's use the definition: raise amount is the TOTAL amount of the bet.
        # If someone bet 0.06 (max_bet_on_table = 0.06), and we want to 3-bet to 0.18 (3x).
        # raise_amount_calculated = 3 * max_bet_on_table
        # Ensure this is at least min_raise. min_raise is the *total* bet for a minimum raise.
        # e.g. blinds 1/2. UTG raises to 6. SB to act. bet_to_call=5. max_bet_on_table=6. min_raise for SB is 10.
        # Our 3x calc = 3*6 = 18. This is > 10.
        raise_amount_calculated = 3 * max_bet_on_table # Total bet amount
        raise_amount_calculated = max(raise_amount_calculated, min_raise)


    raise_amount_calculated = round(min(raise_amount_calculated, my_stack), 2)
    # Ensure raise amount is a valid raise if action is raise
    # If we decide to raise, the amount must be at least bet_to_call + (max_bet_on_table - opponent_who_made_that_bet_previous_bet)
    # Or more simply, total bet must be >= max_bet_on_table + (max_bet_on_table - largest_bet_before_max_bet)
    # The min_raise variable should represent the minimum *total* bet amount for a valid raise.
    if raise_amount_calculated < min_raise and raise_amount_calculated > bet_to_call: # If it's intended as a raise but too small
        raise_amount_calculated = min_raise


    print(f"Preflop Logic: Pos: {position}, Cat: {preflop_category}, B2Call: {bet_to_call}, CanChk: {can_check}, CalcRaise: {raise_amount_calculated}, MyStack: {my_stack}, MyBet: {my_current_bet_this_street}, MaxOppBet: {max_bet_on_table}, Pot: {pot_size}, Opps: {active_opponents_count}, BB: {big_blind}, is_bb: {is_bb}")

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
        if bet_to_call == 0: # We are opening
            # Standard open: 3xBB + 1BB per limper. Our raise_amount_calculated should be this.
            actual_raise_amount = (3 * big_blind) + (num_limpers * big_blind)
            actual_raise_amount = max(actual_raise_amount, min_raise) # Ensure it's at least min_raise
            actual_raise_amount = round(min(actual_raise_amount, my_stack), 2)
            print(f"Premium Pair, opening. Action: RAISE, Amount: {actual_raise_amount}")
            return action_raise_const, actual_raise_amount
        else: # Facing a bet or raise
            # Re-raise: 3x the previous total bet/raise size.
            # raise_amount_calculated was set to 3 * max_bet_on_table
            actual_raise_amount = raise_amount_calculated
            actual_raise_amount = max(actual_raise_amount, min_raise) # Ensure it's a valid raise amount
            actual_raise_amount = round(min(actual_raise_amount, my_stack), 2)

            if actual_raise_amount <= bet_to_call : # Calculated raise is not even a call or is invalid.
                                                  # This can happen if 3*max_bet_on_table is less than min_raise and min_raise itself is just a call.
                                                  # Default to a pot-sized raise over the call or min_raise.
                pot_sized_raise_increment = pot_size + bet_to_call # Bet pot on top of call
                actual_raise_amount = bet_to_call + pot_sized_raise_increment
                actual_raise_amount = max(actual_raise_amount, min_raise)


            actual_raise_amount = round(min(actual_raise_amount, my_stack), 2)
            if actual_raise_amount <= bet_to_call: # If still not a valid raise, just call if affordable, otherwise fold.
                if bet_to_call < my_stack * 0.3: # Arbitrary threshold for calling with premium if raise sizing failed
                    print(f"Premium Pair, facing bet, raise calc failed, calling. Action: CALL, Amount: {bet_to_call}")
                    return action_call_const, bet_to_call
                else:
                    print(f"Premium Pair, facing bet, raise calc failed, too expensive to call. Action: FOLD") # Should be rare
                    return action_fold_const, 0


            if actual_raise_amount >= my_stack * 0.85 : 
                print(f"Premium Pair, facing bet, large re-raise. Action: RAISE (ALL-IN), Amount: {my_stack}")
                return action_raise_const, my_stack
            
            print(f"Premium Pair, facing bet. Action: RAISE, Amount: {actual_raise_amount}")
            return action_raise_const, actual_raise_amount

    # AKs, AKo, AQs, AQo, AJs, AJo, KQs, KQo (Playable Broadway / Suited Ace)
    # Strong Pair (JJ, TT)
    # Suited Playable (KJs, KTs, QJs, QTs, JTs) - Added KTs here for BB defense
    if preflop_category in ["Suited Ace", "Offsuit Ace", "Suited King", "Offsuit King", "Playable Broadway", "Offsuit Broadway", "Strong Pair", "Suited Playable"]:
        if position in ['UTG', 'MP']:
            if bet_to_call == 0: # Opening
                open_raise = (3 * big_blind) + (num_limpers * big_blind)
                open_raise = max(open_raise, min_raise)
                open_raise = round(min(open_raise, my_stack),2)
                print(f"{preflop_category} in {position}, opening. Action: RAISE, Amount: {open_raise}")
                return action_raise_const, open_raise
            elif bet_to_call <= big_blind * 4: 
                # For Strong Pair (JJ, TT), consider calling 3-bets more often than folding.
                if preflop_category == "Strong Pair" and bet_to_call > big_blind * 3: # If it's a 3bet, and we have TT/JJ
                    # Facing a 3-bet, TT/JJ can be tricky. Let's call smaller 3-bets, fold to larger ones.
                    if bet_to_call <= big_blind * 3.5: # Call up to a 3.5x 3bet (e.g. 7BB if original raise was 2BB)
                        print(f"{preflop_category} in {position}, facing 3-bet <= 3.5x. Action: CALL, Amount: {bet_to_call}")
                        return action_call_const, bet_to_call
                    else:
                        print(f"{preflop_category} in {position}, facing large 3-bet > 3.5x. Action: FOLD")
                        return action_fold_const, 0
                print(f"{preflop_category} in {position}, facing raise <= 4BB. Action: CALL, Amount: {bet_to_call}")
                return action_call_const, bet_to_call
            else: # Facing a large raise
                print(f"{preflop_category} in {position}, facing large raise > 4BB. Action: FOLD")
                return action_fold_const, 0
        elif position in ['CO', 'BTN']: # Opening from CO or BTN
            if bet_to_call == 0: # Opening or raising over limpers
                open_raise = (3 * big_blind) + (num_limpers * big_blind)
                open_raise = max(open_raise, min_raise)
                open_raise = round(min(open_raise, my_stack),2)
                print(f"{preflop_category} in {position}, opening/raising limpers. Action: RAISE, Amount: {open_raise}")
                return action_raise_const, open_raise
            elif bet_to_call <= big_blind * 5: 
                print(f"{preflop_category} in {position}, facing raise <= 5BB. Action: CALL, Amount: {bet_to_call}")
                return action_call_const, bet_to_call
            else: # Facing a very large raise (4bet+)
                print(f"{preflop_category} in {position}, facing large raise > 5BB. Action: FOLD")
                return action_fold_const, 0
        elif position == 'SB':
            if max_bet_on_table <= big_blind and (bet_to_call == big_blind - small_blind or bet_to_call == 0) : # Folded to SB or limped to SB
                # This condition means it's either folded to SB (max_bet_on_table is BB, bet_to_call is BB-SB)
                # Or someone limped and SB has option to complete/raise (max_bet_on_table is BB, bet_to_call is BB-SB)
                # Or it's folded around and SB is effectively opening (bet_to_call is 0 if we consider SB already in)
                # Simplified: If action is on SB and no one has raised yet beyond the BB.
                open_raise = (3 * big_blind) # Standard SB open sizing vs BB
                if num_limpers > 0: # If BTN limped, SB might make it 4BB.
                    open_raise = (3 + num_limpers) * big_blind
                open_raise = max(open_raise, min_raise)
                open_raise = round(min(open_raise, my_stack),2)
                print(f"{preflop_category} in SB, opening/isolating. Action: RAISE, Amount: {open_raise}")
                return action_raise_const, open_raise
        elif position == 'BB': # Corrected: Direct comparison for single item
            if can_check and bet_to_call == 0:
                print(f"{preflop_category} in BB, option to check. Action: CHECK")
                return action_check_const, 0
            # BB defense logic: Call with Suited Playable (like KTs) if facing a steal up to 3.5x BB
            elif preflop_category == "Suited Playable" and bet_to_call <= big_blind * 3.5 and max_bet_on_table <= big_blind * 3.5 : # e.g. KTs vs SB 3.5x steal
                print(f"{preflop_category} in BB, defending vs steal (<=3.5x BB). Action: CALL, Amount: {bet_to_call}")
                return action_call_const, bet_to_call
            elif bet_to_call <= big_blind * 4 : 
                print(f"{preflop_category} in BB, facing raise <= 4BB. Action: CALL, Amount: {bet_to_call}")
                return action_call_const, bet_to_call
            else:
                print(f"{preflop_category} in BB, facing large raise > 4BB. Action: FOLD")
                return action_fold_const, 0

    if preflop_category == "Suited Connector": # e.g. JTs, 98s, 87s
        if position in ['MP', 'CO', 'BTN']:
            if bet_to_call == 0: # Opening or action is on us with no prior raise
                open_raise_amount = (2.5 * big_blind) # Default open for suited connectors
                if num_limpers > 0:
                    open_raise_amount = (3 * big_blind) + (num_limpers * big_blind)
                
                open_raise_amount = max(open_raise_amount, min_raise) # Ensure it's at least min_raise
                open_raise_amount = round(min(open_raise_amount, my_stack), 2)
                print(f"Suited Connector in {position}, opening/raising limpers. Action: RAISE, Amount: {open_raise_amount}")
                return action_raise_const, open_raise_amount
            else: # Facing a bet (bet_to_call > 0)
                # Call if the amount to call is up to 3 big blinds
                if bet_to_call <= big_blind * 3:
                    print(f"Suited Connector in {position}, facing bet, amount to call <= 3BB. Action: CALL, Amount: {bet_to_call}")
                    return action_call_const, bet_to_call
                else:
                    print(f"Suited Connector in {position}, facing bet, conditions not met for call. Action: FOLD")
                    return action_fold_const, 0
        elif position == 'SB' or position == 'BB': # Corrected: Direct comparison for single item
            if can_check and bet_to_call == 0:
                print(f"Suited Connector in {position} (Blind), can check. Action: CHECK")
                return action_check_const, 0
            if bet_to_call <= big_blind * 2: # Call small raises from blinds
                print(f"Suited Connector in {position} (Blind), calling small raise. Action: CALL, Amount: {bet_to_call}")
                return action_call_const, bet_to_call
            else:
                print(f"Suited Connector in {position} (Blind), facing larger raise. Action: FOLD")
                return action_fold_const, 0
        else: # UTG
            print(f"Suited Connector in UTG. Action: FOLD")
            return action_fold_const, 0
            
    # Default action if no specific logic met (should be rare with "Weak" as a catch-all)
    print(f"Preflop default: Category {preflop_category}, Pos {position}. Check/Fold.")
    return action_check_const if can_check else action_fold_const, 0

# Note: The function make_preflop_decision is now fully defined with enhanced logic and debugging prints.
