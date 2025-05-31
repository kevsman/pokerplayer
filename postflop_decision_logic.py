# postflop_decision_logic.py

import logging

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

logger = logging.getLogger(__name__)

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
    action_bet_const,
    my_player_data,
    big_blind_amount,
    base_aggression_factor,
    max_bet_on_table # Added this parameter
):
    street = game_stage # Use game_stage as street

    logger.debug(
        f"make_postflop_decision: street={street}, my_player_data={my_player_data}, "
        f"pot_size={pot_size}, win_prob={win_probability}, pot_odds={pot_odds_to_call}, "
        f"bet_to_call={bet_to_call}, max_bet_on_table={max_bet_on_table}"
    )

    is_very_strong = numerical_hand_rank >= VERY_STRONG_HAND_THRESHOLD or win_probability > 0.85
    is_strong = not is_very_strong and (numerical_hand_rank >= STRONG_HAND_THRESHOLD or win_probability > 0.65)
    is_medium = not is_very_strong and not is_strong and (numerical_hand_rank >= MEDIUM_HAND_THRESHOLD or win_probability > 0.45)
    is_weak = not is_very_strong and not is_strong and not is_medium

    if can_check:
        logger.debug("Option to check is available.")
        if is_very_strong or (is_strong and win_probability > 0.75): # Value bet strong hands
            bet_amount = decision_engine_instance.get_optimal_bet_size_func(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, bluff=False)
            bet_amount = min(bet_amount, my_stack)
            if bet_amount > 0:
                logger.info(f"Decision: BET (very_strong/strong with win_prob > 0.75, can check). Amount: {bet_amount:.2f}")
                return action_bet_const, round(bet_amount, 2)
            else:
                logger.info("Decision: CHECK (very_strong/strong, but optimal bet is 0).")
                return action_check_const, 0
        elif is_strong: # Check/bet with strong hands (less aggressive than very_strong)
            # This is for the "thin value" case where we want to bet if checked to.
            # win_probability > 0.6 is a good candidate for thin value when checked to.
            # The 'is_strong' condition already implies win_probability > 0.65 OR numerical_hand_rank >= STRONG_HAND_THRESHOLD
            # So, if it's 'is_strong' and we can check, we should consider a value bet.
            bet_amount = decision_engine_instance.get_optimal_bet_size_func(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, bluff=False)
            bet_amount = min(bet_amount, my_stack)
            if bet_amount > 0:
                logger.info(f"Decision: BET (strong hand, thin value when checked to). Amount: {bet_amount:.2f}")
                return action_bet_const, round(bet_amount, 2)
            
            # If optimal bet is 0, or if we decided not to value bet, consider a bluff (though less likely for 'is_strong')
            if decision_engine_instance.should_bluff_func(pot_size, my_stack, street, win_probability): 
                bluff_bet_amount = decision_engine_instance.get_optimal_bet_size_func(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, bluff=True)
                bluff_bet_amount = min(bluff_bet_amount, my_stack)
                if bluff_bet_amount > 0:
                    logger.info(f"Decision: BET (strong hand, bluffing when can check). Amount: {bluff_bet_amount:.2f}")
                    return action_bet_const, round(bluff_bet_amount, 2)
            logger.info("Decision: CHECK (strong hand, no value bet/bluff).")
            return action_check_const, 0
        elif is_medium: # Check/bet or check/bluff with medium hands
            # For medium hands, consider a thin value bet if win_probability is decent.
            if win_probability > 0.5: # Threshold for thin value with medium hand
                value_bet_amount = decision_engine_instance.get_optimal_bet_size_func(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, bluff=False)
                value_bet_amount = min(value_bet_amount, my_stack)
                if value_bet_amount > 0:
                    logger.info(f"Decision: BET (medium hand, thin value when checked to). Amount: {value_bet_amount:.2f}")
                    return action_bet_const, round(value_bet_amount, 2)
            
            # If not value betting (either win_prob too low or optimal bet was 0), consider bluffing.
            if decision_engine_instance.should_bluff_func(pot_size, my_stack, street, win_probability): 
                bluff_bet_amount = decision_engine_instance.get_optimal_bet_size_func(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, bluff=True)
                bluff_bet_amount = min(bluff_bet_amount, my_stack)
                if bluff_bet_amount > 0:
                    logger.info(f"Decision: BET (medium hand, bluffing when can check). Amount: {bluff_bet_amount:.2f}")
                    return action_bet_const, round(bluff_bet_amount, 2)
            
            logger.info("Decision: CHECK (medium hand, no value bet/bluff).")
            return action_check_const, 0
        else: # Weak hand - Check or bluff
            if street == 'river' and decision_engine_instance.should_bluff_func(pot_size, my_stack, street, win_probability): 
                 # For river bluff when checked to, consider a larger bet size
                 bet_amount = decision_engine_instance.get_optimal_bet_size_func(numerical_hand_rank, pot_size, my_stack, street, big_blind_amount, bluff=True)
                 
                 # All-in bluff logic for test_river_making_all_in_bluff
                 # If stack is small (e.g., <= 1.5x pot) or it's a designated all-in bluff scenario (not explicitly testable here without more context)
                 # For the test, the pot is 0.1, stack is 0.75. my_stack (0.75) > pot_size (0.1) * 1.5 (0.15) is TRUE.
                 # The previous logic was: if my_stack <= pot_size * 1.5 -> all_in. This is 0.75 <= 0.15 which is FALSE.
                 # The test expects an all-in or at least pot-sized bet.
                 # Let's make the bluff bet at least pot size if possible, or all-in if stack is less than pot size.
                 
                 if my_stack <= pot_size: # If stack is less than or equal to pot, go all-in
                     bet_amount = my_stack
                 elif bet_amount < pot_size : # If calculated bluff is less than pot, make it pot size (if stack allows)
                     bet_amount = min(pot_size, my_stack)
                 # If calculated bluff is already >= pot_size, use that, capped by stack.
                 else:
                     bet_amount = min(bet_amount, my_stack)

                 # Ensure bet_amount is greater than 0 if we intend to bet
                 if bet_amount > 0:
                    logger.info(f"Decision: BET (weak hand, river bluff when checked to). Amount: {bet_amount:.2f}, Pot: {pot_size}, Stack: {my_stack}")
                    return action_bet_const, round(bet_amount, 2)
                 else: # If bet_amount resolved to 0 (e.g. stack is 0), check.
                    logger.info(f"Decision: CHECK (weak hand, intended bluff but bet_amount is 0). Pot: {pot_size}, Stack: {my_stack}")
                    return action_check_const, 0

            logger.info("Decision: CHECK (weak hand).")
            return action_check_const, 0
    else:  # Facing a bet
        logger.debug(f"Facing a bet. bet_to_call: {bet_to_call}, pot_size: {pot_size}, my_stack: {my_stack}, max_bet_on_table: {max_bet_on_table}")
        
        if is_very_strong:
            logger.debug(f"Hand is_very_strong. win_probability: {win_probability}")
            
            # Determine the minimum valid total raise amount
            # A raise must be at least the size of the last bet/raise.
            # last_bet_or_raise_size = max_bet_on_table - (sum of previous bets in this round by other players before this max_bet_on_table)
            # This is complex. A simpler rule: if opponent bet B (making current max_bet_on_table = B, assuming our current_bet was 0),
            # our min raise makes our total bet 2B.
            # If our current_bet for this round is C_our, and max_bet_on_table is M, then bet_to_call is M - C_our.
            # The last aggressive action size was M - (bet just before M).
            # For simplicity: min_raise_increment = max_bet_on_table if no prior bets, or diff if there was.
            # Let's use a common poker rule: the raise amount must be at least as large as the previous bet or raise in the same betting round.
            # If player A bets 10, player B raises to 30 (a raise of 20). Player C wants to re-raise. Player C must raise by at least 20, making it 50 total.
            
            # bet_to_call is the additional amount we need to put in to match max_bet_on_table.
            # my_current_bet_this_round = my_player_data.get('current_bet', 0)
            # opponent_total_bet_this_round = max_bet_on_table
            
            # The minimum amount our total bet needs to be for a valid raise:
            # opponent_bet_amount_we_are_facing = max_bet_on_table - my_player_data.get('current_bet', 0) # This is effectively bet_to_call
            # min_raise_on_top = opponent_bet_amount_we_are_facing
            # min_total_raise_to_amount = max_bet_on_table + min_raise_on_top
            
            # Simplified: if max_bet_on_table is the current highest bet, a min-raise means we make our total bet 2 * max_bet_on_table (if we had 0 in before this bet).
            # More generally, the raise increment must be at least the last bet/raise increment.
            # If the previous bet was P, and current max_bet_on_table is M, the increment was M-P.
            # So our raise must be to at least M + (M-P).
            # If there was no P (M is the first bet), then increment is M. Our raise is to M + M = 2M.
            # This needs the bet that occurred *before* max_bet_on_table.
            # For now, let's assume a simpler rule: min raise is to double the current bet if it's the first bet, or add the last raise amount.
            # The most straightforward rule for min raise: must raise to at least (max_bet_on_table + bet_to_call).
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
            if win_probability > pot_odds_to_call or (street == 'river' and win_probability > 0.7): # Good odds or strong river hand
                # Consider raising if pot odds are very good or implied odds are high
                # For now, just call with strong hands if odds are met.
                call_amount = bet_to_call
                logger.info(f"Decision: CALL (strong hand, good odds/river). Amount to call: {call_amount:.2f}")
                return action_call_const, round(call_amount, 2)
            else: # Not good enough odds for a strong-ish hand
                # Calculate bet_to_pot_ratio for this specific bluff scenario
                current_bet_to_pot_ratio = bet_to_call / pot_size if pot_size > 0 else 0.5
                if decision_engine_instance.should_bluff_func(pot_size, my_stack, street, win_probability, bet_to_pot_ratio_for_bluff=current_bet_to_pot_ratio):
                    # Min raise logic from above
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
            logger.debug(f"Hand is_medium. win_probability: {win_probability}, pot_odds: {pot_odds_to_call}")
            # Call with medium strength if odds are good, especially with draws (not explicitly modeled here yet)
            if win_probability > pot_odds_to_call and bet_to_call <= 0.6 * pot_size : # Call if good odds and bet is not too large (e.g. up to 60% pot)
                call_amount = bet_to_call
                logger.info(f"Decision: CALL (medium hand, good odds and bet size). Amount to call: {call_amount:.2f}")
                return action_call_const, round(call_amount, 2)
            else: # Fold if odds not good or bet is large for a medium hand
                logger.info(f"Decision: FOLD (medium hand, odds not good or bet too large). Bet_to_call: {bet_to_call}, Pot: {pot_size}")
                return action_fold_const, 0
        
        else: # Weak hand
            logger.debug(f"Hand is_weak. win_probability: {win_probability}, pot_odds: {pot_odds_to_call}")
            # Consider bluff-raising if conditions are right (e.g., specific opponent, board texture)
            # This uses the generic should_bluff_func
            fold_equity_needed_for_bluff_raise = bet_to_call / (pot_size + bet_to_call) if (pot_size + bet_to_call) > 0 else 0.5 # Added check for division by zero
            # Pass the actual win_probability to should_bluff_func
            if decision_engine_instance.should_bluff_func(pot_size, my_stack, street, win_probability, bet_to_pot_ratio_for_bluff=fold_equity_needed_for_bluff_raise):
                min_total_raise_to_amount = max_bet_on_table + bet_to_call
                if bet_to_call == 0: min_total_raise_to_amount = max_bet_on_table + big_blind_amount

                calculated_raise_total_amount = max_bet_on_table * 2.5 # Standard bluff raise size
                if calculated_raise_total_amount < min_total_raise_to_amount:
                    calculated_raise_total_amount = min_total_raise_to_amount
                
                final_raise_amount = min(calculated_raise_total_amount, my_stack + my_player_data.get('current_bet', 0))
                is_all_in_raise = (final_raise_amount == my_stack + my_player_data.get('current_bet', 0))

                if final_raise_amount > max_bet_on_table and (final_raise_amount >= min_total_raise_to_amount or is_all_in_raise):
                    logger.info(f"Decision: RAISE (weak hand, bluffing). Total Amount: {final_raise_amount:.2f}")
                    return action_raise_const, round(final_raise_amount, 2)

            # Default to fold with weak hands if not bluffing
            logger.info(f"Decision: FOLD (weak hand, no bluff). Bet_to_call: {bet_to_call}, Pot: {pot_size}")
            return action_fold_const, 0

    # Fallback, should not be reached if logic is complete
    logger.error("Fell through all decision logic in postflop. Defaulting to FOLD.")
    return action_fold_const, 0
