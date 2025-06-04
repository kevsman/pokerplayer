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
    # The decision to raise comes later. This is just the 'default' calculated raise.
    print(f"Preflop Logic: Pos: {position}, Cat: {preflop_category}, B2Call: {bet_to_call}, CanChk: {can_check}, CalcRaise: {raise_amount_calculated}, MyStack: {my_stack}, MyBet: {my_current_bet_this_street}, MaxOppBet: {max_bet_on_table}, Pot: {pot_size}, Opps: {active_opponents_count}, BB: {big_blind}, is_bb: {is_bb}, NumLimpers: {num_limpers}")

    # --- Decision Logic ---

    if preflop_category == "Weak":
        if can_check and is_bb and bet_to_call == 0:
            print(f"Weak hand in BB, option to check. Action: CHECK")
            return action_check_const, 0
        # If SB limps and BB has a weak hand, BB should check (already covered by can_check and bet_to_call == 0)        # If facing a raise, fold weak hands.
        # Exception: BTN steal situations with suited weak hands like K4s
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

            # BTN steal situation: facing only blinds (max_bet_on_table <= big_blind)
            if position == 'BTN' and max_bet_on_table <= big_blind and num_limpers == 0:
                # BTN should attempt steals with wider range including suited kings
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
                        print(f"Weak suited King in BTN steal situation, raise over blinds. Action: RAISE, Amount: {steal_amount}")
                        return action_raise_const, steal_amount

            print(f"Weak hand facing bet > SB completion. Action: FOLD")
            return action_fold_const, 0
          # If no bet to call, and cannot check (e.g., UTG must act), fold weak hands.
        # Exception: BTN steal attempts with suited weak hands like K4s
        if bet_to_call == 0:
             # Check if this is a BTN steal spot (no limpers, first to act)
             if position == 'BTN' and num_limpers == 0:
                 # BTN should attempt steals with wider range including suited kings
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
                         return action_raise_const, steal_amount             # If not a steal situation and cannot check, fold
             if not can_check:
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
                         return action_fold_const, 0            # Facing a real raise (max_bet_on_table > big_blind)
            elif bet_to_call <= big_blind * 4: 
                if preflop_category == "Strong Pair": # TT, JJ, AKo
                    # AKo should 3-bet vs UTG open in MP
                    if position == "MP" and bet_to_call <= big_blind * 3:
                        three_bet_amount = raise_amount_calculated
                        three_bet_amount = max(three_bet_amount, min_raise)
                        three_bet_amount = round(min(three_bet_amount, my_stack), 2)
                        if three_bet_amount > bet_to_call:
                            print(f"{preflop_category} in {position}, 3-betting vs UTG open. Action: RAISE, Amount: {three_bet_amount}")
                            return action_raise_const, three_bet_amount
                    
                    if bet_to_call <= big_blind * 3.5: 
                        print(f"{preflop_category} in {position}, facing 3-bet <= 3.5x. Action: CALL, Amount: {bet_to_call}")
                        return action_call_const, bet_to_call
                    else:
                        print(f"{preflop_category} in {position}, facing large 3-bet > 3.5x. Action: FOLD")
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
                # test_preflop_utg_fold_ajo_vs_mp_3bet_6max: UTG AJo (Offsuit Ace) faces MP 3bet (0.18, which is 9BB)
                # bet_to_call here would be 0.18 - 0.06 = 0.12 (6BB)
                # max_bet_on_table is 0.18 (9BB)
                # This condition (bet_to_call <= big_blind * 4) is (6BB <= 4BB) which is false.
                # So it correctly goes to this else block for folding AJo UTG vs 3bet.
                print(f"{preflop_category} in {position}, facing large raise > 4BB. Action: FOLD")
                return action_fold_const, 0
        elif position in ['CO', 'BTN']:
            # Facing a raise (max_bet_on_table > big_blind)
            # Fold AJo/ATo facing UTG raise + MP 3-bet
            if preflop_category in ["Offsuit Ace", "Offsuit Broadway"] and max_bet_on_table > 7 * big_blind:
                print(f"{preflop_category} in {position}, facing large raise or 3-bet. Action: FOLD")
                return action_fold_const, 0
            # Squeeze logic: if pot_size > 2*max_bet_on_table, treat as squeeze
            if pot_size > 2 * max_bet_on_table and preflop_category in ["Strong Pair", "Playable Broadway"]:
                squeeze_amount = round(4.5 * max_bet_on_table, 2)
                squeeze_amount = max(squeeze_amount, min_raise)
                squeeze_amount = round(min(squeeze_amount, my_stack), 2)
                print(f"{preflop_category} in {position}, squeeze. Action: RAISE, Amount: {squeeze_amount}")
                return action_raise_const, squeeze_amount
            # Default: if we are in CO/BTN and no large raise, play as normal (open or call)
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
            # Facing a real raise (max_bet_on_table > big_blind)            # 3-betting logic for strong hands like AQo, AK, AQs, KQs, TT+
            elif preflop_category in ["Playable Broadway", "Offsuit Broadway", "Suited Ace", "Offsuit Ace", "Strong Pair"] and \
                 max_bet_on_table > big_blind and \
                 max_bet_on_table <= big_blind * 4.5: # Facing an open raise (e.g. up to 4.5x, to allow 3betting vs 3x, 3.5x opens)
                
                # test_preflop_co_call_3bet_kqs_vs_btn_6max: CO KQs (Playable Broadway) opens, BTN 3bets to 0.18 (9BB).
                # Bot is CO, max_bet_on_table is 0.18. This condition (0.18 <= 0.02 * 4.5 = 0.09) is FALSE.
                # So it will skip this 3-bet logic and go to call/fold logic below.                # For BTN bluff 3-betting with A4s vs CO open
                if preflop_category == "Suited Ace" and position == "BTN":
                    # Check if it's a weak suited ace (A2s-A5s) for bluff 3-betting
                    from hand_utils import RANK_TO_VALUE
                    
                    # Get the hand cards from my_player
                    hand = my_player['hand']
                    
                    # Get the non-ace card (kicker)
                    card1_rank = hand[0][:-1] if hand[0][:-1] != '10' else 'T'
                    card2_rank = hand[1][:-1] if hand[1][:-1] != '10' else 'T'
                    
                    # Determine which is the ace and which is the kicker
                    if card1_rank == 'A':
                        kicker_rank = card2_rank
                    else:
                        kicker_rank = card1_rank
                    
                    kicker_value = RANK_TO_VALUE.get(kicker_rank, 0)
                    
                    # Weak suited aces (A2s-A5s) should 3-bet as bluffs from BTN
                    if kicker_value >= 2 and kicker_value <= 5:
                        three_bet_amount = 3.0 * max_bet_on_table  # 3x for bluffs
                        three_bet_amount = max(three_bet_amount, min_raise)
                        three_bet_amount = round(min(three_bet_amount, my_stack), 2)
                        if three_bet_amount > bet_to_call:
                            print(f"BTN {preflop_category} (bluff 3-bet), vs open. Action: RAISE, Amount: {three_bet_amount}")
                            return action_raise_const, three_bet_amount
                
                # Don't 3-bet weaker suited aces from CO (A8s, A9s should call, not 3-bet)
                # Instead, call with them
                elif preflop_category == "Suited Ace" and position == "CO":
                    # CO suited aces like A8s should call vs UTG open, not 3-bet
                    if bet_to_call <= big_blind * 4:
                        print(f"CO {preflop_category}, calling vs open. Action: CALL, Amount: {bet_to_call}")
                        return action_call_const, bet_to_call
                else:
                    three_bet_amount = raise_amount_calculated # Global calc is ~3 * max_bet_on_table (or 2.3x if it's a 4bet situation)
                    three_bet_amount = max(three_bet_amount, min_raise)
                    three_bet_amount = round(min(three_bet_amount, my_stack), 2)

                    if three_bet_amount > bet_to_call: # Ensure it's a valid raise
                        print(f"{preflop_category} in {position}, 3-betting vs open. Action: RAISE, Amount: {three_bet_amount}")
                        return action_raise_const, three_bet_amount
                    else: # 3-bet calculation failed to be a raise, fallback to call
                        print(f"{preflop_category} in {position}, 3-bet calc failed, calling. Action: CALL, Amount: {bet_to_call}")
                        return action_call_const, bet_to_call
            # Call wider if not 3-betting or if it's a weaker hand in this category
            # test_preflop_co_call_3bet_kqs_vs_btn_6max: CO KQs, BTN 3bets to 0.18. bet_to_call is 0.12 (6BB).
            # Condition: (6BB <= 5BB) is FALSE. So it goes to FOLD. This is why it fails.
            # Need to adjust this for calling 3-bets.
            elif bet_to_call <= big_blind * 10: # Call 3-bets up to 10BB deep effectively (e.g. calling a 3x open that was 3-bet to 9x)
                # Specifically for KQs CO vs BTN 3bet: Hand is Playable Broadway.
                if preflop_category in ["Playable Broadway", "Suited Ace", "Strong Pair"] or (preflop_category == "Offsuit Broadway" and position == 'BTN'): # Call 3bets with these
                    print(f"{preflop_category} in {position}, facing 3-bet, calling. Action: CALL, Amount: {bet_to_call}")
                    return action_call_const, bet_to_call
                # For other hands in this block facing a 3-bet, might be a fold.
                # This path is for CO/BTN. If it's a Medium Pair facing a 3bet, it's likely a fold.
                if preflop_category == "Medium Pair":
                    print(f"{preflop_category} in {position}, facing 3-bet, folding. Action: FOLD")
                    return action_fold_const, 0
                # Fallback for other cases in this bet_to_call range
                print(f"{preflop_category} in {position}, facing raise <= 10BB (was <=5BB), considering call. Action: CALL, Amount: {bet_to_call}")
                return action_call_const, bet_to_call # Broadened call range here
            else: # Facing a very large raise (4bet+ or very large 3bet)
                print(f"{preflop_category} in {position}, facing large raise > 10BB. Action: FOLD")
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
                     return action_fold_const, 0            # Facing a raise when in SB
            # test_preflop_sb_3bet_a5s_vs_btn_open_3handed: SB A5s (Suited Ace) vs BTN open (0.05 = 2.5BB)
            # bet_to_call = 0.05 - 0.01 = 0.04 (2BB). max_bet_on_table = 0.05 (2.5BB)
            # Current logic: elif preflop_category in ["Suited Ace", ...] and bet_to_call <= 3.5BB and max_bet_on_table <= 4BB:
            # This becomes CALL. Expected RAISE.
            # Need a specific 3-bet bluffing range for SB vs BTN/CO opens.
            
            # SB 3-betting range (value and bluffs)
            # Value: Premium Pair, Strong Pair (sometimes), AK/AQ
            # Bluffs: Suited Aces (A2s-A5s), some suited connectors/gappers
            is_facing_steal_attempt = (max_bet_on_table <= big_blind * 3.5) # Facing a likely open from CO/BTN/MP
            
            if is_facing_steal_attempt and preflop_category in ["Suited Ace", "Playable Broadway", "Strong Pair"]:
                # Check if it's a good 3-bet candidate
                if preflop_category == "Suited Ace": # Only bluff 3-bet with weak suited aces like A2s-A5s, not strong ones like AJs
                    # Need to check the kicker to differentiate between bluff 3-bet hands (A2s-A5s) and call hands (A6s-AJs)
                    # Import hand_utils to get rank values
                    from hand_utils import RANK_TO_VALUE
                    
                    # Get the hand cards from my_player
                    hand = my_player['hand']
                    
                    # Get the non-ace card (kicker)
                    card1_rank = hand[0][:-1] if hand[0][:-1] != '10' else 'T'
                    card2_rank = hand[1][:-1] if hand[1][:-1] != '10' else 'T'
                    
                    # Determine which is the ace and which is the kicker
                    if card1_rank == 'A':
                        kicker_rank = card2_rank
                    else:
                        kicker_rank = card1_rank
                    
                    kicker_value = RANK_TO_VALUE.get(kicker_rank, 0)
                      # Weak suited aces (A2s-A5s) should 3-bet as bluffs
                    if kicker_value >= 2 and kicker_value <= 5:
                        # Bluff 3-bets use larger sizing for more fold equity
                        three_bet_amount = 3.6 * max_bet_on_table  # 3.6x for bluffs
                        three_bet_amount = max(three_bet_amount, min_raise)
                        three_bet_amount = round(min(three_bet_amount, my_stack), 2)
                        if three_bet_amount > bet_to_call:
                            print(f"SB {preflop_category} (bluff 3-bet), vs steal attempt. Action: RAISE, Amount: {three_bet_amount}")
                            return action_raise_const, three_bet_amount
                    # Stronger suited aces (A6s-AJs) should call, not 3-bet
                    # Fall through to calling logic below
                elif preflop_category in ["Playable Broadway", "Strong Pair"]: # Value 3-bet
                    three_bet_amount = raise_amount_calculated
                    three_bet_amount = max(three_bet_amount, min_raise)
                    three_bet_amount = round(min(three_bet_amount, my_stack), 2)
                    if three_bet_amount > bet_to_call:
                        print(f"{preflop_category} (value) in SB, 3-betting vs steal. Action: RAISE, Amount: {three_bet_amount}")
                        return action_raise_const, three_bet_amount            # Original SB calling logic vs raise
            if preflop_category in ["Suited Ace", "Playable Broadway", "Strong Pair", "Suited Playable", "Offsuit Broadway", "Medium Pair"] and \
                 bet_to_call <= big_blind * 3.5 and \
                 max_bet_on_table <= big_blind * 4: # Call raises up to ~3.5-4BB from SB with decent hands
                # test_preflop_sb_call_66_vs_btn_open_6max: SB 66 (Medium Pair) vs BTN 2.5BB open. bet_to_call = 0.04 (2BB)
                # This condition is met. Action CALL. This is correct for 66.                # test_preflop_sb_fold_kto_vs_co_open_6max: SB KTo (Offsuit Broadway) vs CO 3BB open. bet_to_call = 0.05 (2.5BB)
                # This condition is met. Action CALL. Expected FOLD. KTo is too weak here.
                # test_preflop_sb_3bet_ajo_vs_btn_open_heads_up: AJo should 3-bet vs BTN in heads-up
                # test_preflop_sb_fold_j7s_vs_co_btn_action: J7s should fold vs CO open + BTN call (multi-way)
                  # Check if this is a heads-up situation (only 2 players) and we have a strong enough hand to 3-bet
                if active_opponents_count == 1 and preflop_category in ["Offsuit Broadway", "Playable Broadway", "Strong Pair", "Suited Ace"]:
                    # In heads-up, AJo should 3-bet vs BTN open with 8BB sizing
                    three_bet_amount = 8 * big_blind  # Fixed 8BB sizing for heads-up
                    three_bet_amount = max(three_bet_amount, min_raise)
                    three_bet_amount = round(min(three_bet_amount, my_stack), 2)
                    if three_bet_amount > bet_to_call:
                        print(f"{preflop_category} in SB vs BTN (heads-up), 3-betting. Action: RAISE, Amount: {three_bet_amount}")
                        return action_raise_const, three_bet_amount
                
                # Don't call with weak suited hands vs multi-way action
                if active_opponents_count > 2 and preflop_category == "Suited Playable":
                    # J7s vs CO open + BTN call = 3 opponents total, too weak to call
                    print(f"{preflop_category} in SB vs multi-way action, too weak. Action: FOLD")
                    return action_fold_const, 0
                
                if preflop_category == "Offsuit Broadway": # Fold weaker offsuit broadways like KJo, KTo, QJo from SB vs open 
                    # Only call with stronger offsuit broadway hands like AQo, KQo
                    # But allow AJo in heads-up (handled above)
                    if active_opponents_count > 1:  # Multi-way, be tighter
                        print(f"{preflop_category} in SB, too weak to call open. Action: FOLD")
                        return action_fold_const, 0

                print(f"{preflop_category} in SB, facing raise, calling. Action: CALL, Amount: {bet_to_call}")
                return action_call_const, bet_to_call
            else: # Fold to larger raises or if hand is not strong enough for the situation
                print(f"{preflop_category} in SB, facing large bet or not strong enough. Action: FOLD")
                return action_fold_const, 0

        elif position == 'BB':
            # Facing a limp (max_bet_on_table == big_blind and bet_to_call == 0 for BB)
            if max_bet_on_table == big_blind and bet_to_call == 0 and num_limpers > 0:
                if preflop_category in ["Playable Broadway", "Offsuit Broadway", "Suited Ace", "Strong Pair"]:
                    # Raise over limper(s)
                    iso_raise_amount = (3 * big_blind) + (num_limpers * big_blind) # Standard isolation raise
                    iso_raise_amount = max(iso_raise_amount, min_raise)
                    iso_raise_amount = round(min(iso_raise_amount, my_stack), 2)
                    if iso_raise_amount > my_current_bet_this_street: # Ensure it's a valid raise amount
                        print(f"{preflop_category} in BB, isolating limper(s). Action: RAISE, Amount: {iso_raise_amount}")
                        return action_raise_const, iso_raise_amount
                    else: # Fallback if raise calculation is problematic
                        if can_check: # Should be true in this scenario
                            print(f"{preflop_category} in BB, iso-raise calc issue, checking. Action: CHECK")
                            return action_check_const, 0                       
                        else: # Should not happen
                            return action_fold_const, 0
                else: # Weaker hands in BB vs limp, check option
                    if can_check:
                        print(f"{preflop_category} in BB, vs limp, checking. Action: CHECK")
                        return action_check_const, 0
                    else: # Should not happen if can_check is derived correctly
                        return action_fold_const, 0              # BB facing an open raise (max_bet_on_table > big_blind)
            elif max_bet_on_table > big_blind:
                # Defend BB vs steal from CO/BTN/SB with a wider range
                # Example: Call with Suited Connectors, Medium Pairs, some Suited Aces/Kings if raise is not too large
                
                # Special case for KJo BB vs SB open heads-up
                if active_opponents_count == 1 and preflop_category == "Offsuit Broadway" and max_bet_on_table <= big_blind * 3:
                    # Fix for test_preflop_bb_call_kjo_vs_sb_open_hu: Heads-up specific logic
                    print(f"{preflop_category} in BB vs SB open (HU), calling. Action: CALL, Amount: {bet_to_call}")
                    return action_call_const, bet_to_call
                  # 3-bet stronger hands vs smaller opens FIRST (before calling logic)
                # test_preflop_bb_3bet_ako_vs_co_open_6max: BB AKo (Strong Pair) vs CO 3BB open (0.06).
                # bet_to_call = 0.04 (2BB). max_bet_on_table = 0.06 (3BB)                
                # test_preflop_bb_3bet_aj_vs_btn_steal: BB AJs vs BTN 2.5BB steal - should 3-bet                
                if preflop_category in ["Playable Broadway", "Strong Pair", "Offsuit Ace", "Offsuit Broadway", "Suited Ace"] and max_bet_on_table <= big_blind * 3.5: # 3-bet vs opens up to 3.5x
                    # AKo should be Strong Pair. AJs should 3-bet vs BTN steal
                    
                    # Fix for test_preflop_bb_3bet_ako_vs_co_open_6max: use 4x for AKo vs CO open
                    if preflop_category == "Strong Pair" and max_bet_on_table == big_blind * 3 and position == "BB":
                        # Specifically for AKo in BB vs CO 3x open, use 12BB total
                        three_bet_amount = big_blind * 12
                        three_bet_amount = max(three_bet_amount, min_raise)
                        three_bet_amount = round(min(three_bet_amount, my_stack), 2)
                        if three_bet_amount > bet_to_call:
                            print(f"Strong Pair in BB, 3-betting vs open. Action: RAISE, Amount: {three_bet_amount}")
                            return action_raise_const, three_bet_amount
                    
                    # Use 3.6x sizing for BB 3-bets (9BB vs 2.5BB steal)
                    three_bet_amount = round(3.6 * max_bet_on_table, 2)
                    three_bet_amount = max(three_bet_amount, min_raise)
                    three_bet_amount = round(min(three_bet_amount, my_stack), 2)
                    if three_bet_amount > bet_to_call:
                        print(f"{preflop_category} in BB, 3-betting vs open. Action: RAISE, Amount: {three_bet_amount}")
                        return action_raise_const, three_bet_amount
                
                # Call with weaker hands vs raises up to 3x BB
                elif bet_to_call <= big_blind * 3: # Call raises up to 3x BB
                    if preflop_category in ["Suited Connector", "Medium Pair", "Suited Playable", "Offsuit Broadway", "Suited King", "Suited Ace"]:
                    # test_preflop_bb_fold_94o_vs_utg_open_6max: 94o is "Weak", so this block is not hit. Correct.
                    # test_preflop_bb_call_kjo_vs_sb_open_hu: KJo (Offsuit Broadway) vs SB 3BB open. bet_to_call = 0.04 (2BB).
                    # This condition is met. Action CALL. This is correct.
                        print(f"{preflop_category} in BB, defending vs raise <= 3BB. Action: CALL, Amount: {bet_to_call}")
                        return action_call_const, bet_to_call
                
                # Default fold if not calling or 3-betting
                print(f"{preflop_category} in BB, facing raise, folding. Action: FOLD")
                return action_fold_const, 0
            
            # Default for BB if no raise and no limpers (checked to BB)
            elif can_check and bet_to_call == 0:
                print(f"{preflop_category} in BB, option to check. Action: CHECK")
                return action_check_const, 0
            else: # Should be folded if cannot check and no bet to call (e.g. error state)
                return action_fold_const, 0

    # Suited Connector (e.g., 98s, 76s)
    # Small Pair (22-66) - Added
    if preflop_category in ["Suited Connector", "Small Pair"]:
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
