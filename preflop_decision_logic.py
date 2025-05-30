# preflop_decision_logic.py
import math # For round

# Note: ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE are passed as arguments (e.g., action_fold_const)
# get_preflop_hand_category_func and calculate_expected_value_func are also passed as arguments.

def make_preflop_decision(
    decision_engine_instance, my_player, hand_evaluation_tuple, my_hole_cards_str_list, 
    bet_to_call, can_check, pot_size, my_stack, active_opponents_count, 
    win_probability, pot_odds_to_call, max_bet_on_table, game_stage, hand_description, # hand_description is from hand_evaluation_tuple[1]
    action_fold_const, action_check_const, action_call_const, action_raise_const,
    get_preflop_hand_category_func, 
    calculate_expected_value_func
    ):
    """Enhanced pre-flop decision making"""
    
    # Debug: Print entry and key initial values
    # print(f"--- ENTERING make_preflop_decision ---")
    # print(f"Hole Cards: {my_hole_cards_str_list}, Hand Eval: {hand_evaluation_tuple}, Hand Desc: {hand_description}")
    # print(f"BetToCall: {bet_to_call}, MyStack: {my_stack}, ActiveOpps: {active_opponents_count}, WinProb: {win_probability}, PotOdds: {pot_odds_to_call}")
    
    small_blind = decision_engine_instance.small_blind
    big_blind = decision_engine_instance.big_blind
    base_aggression_factor = decision_engine_instance.base_aggression_factor

    preflop_category = get_preflop_hand_category_func(hand_evaluation_tuple, my_hole_cards_str_list)
    # print(f"Preflop Category from get_preflop_hand_category: {preflop_category}")

    # Specific Set Mining Logic for small to medium pocket pairs (e.g., 22-77)
    is_setmining_candidate_pair = False
    if hand_description: 
        low_pairs_for_setmining = ["Pair of Twos", "Pair of Threes", "Pair of Fours", "Pair of Fives", "Pair of Sixes", "Pair of Sevens"]
        if any(pair_desc in hand_description for pair_desc in low_pairs_for_setmining):
            is_setmining_candidate_pair = True
    
    # print(f"Set Mining Check: is_setmining_candidate_pair = {is_setmining_candidate_pair} (based on hand_description: '{hand_description}')")

    if is_setmining_candidate_pair and bet_to_call > 0:
        can_set_mine_stack_wise = (bet_to_call <= my_stack * 0.10) 
        has_decent_equity_for_set_mine = win_probability > 0.15 # Overall equity check

        # print(f"Set Mining Conditions: active_opponents_count={active_opponents_count}, can_set_mine_stack_wise={can_set_mine_stack_wise}, has_decent_equity_for_set_mine={has_decent_equity_for_set_mine}")

        if active_opponents_count >= 2 and can_set_mine_stack_wise and has_decent_equity_for_set_mine:
            # print(f"Preflop Logic: Applying SET MINING CALL for {my_hole_cards_str_list} ({hand_description}). Bet: {bet_to_call}, Stack: {my_stack}, ActiveOpps: {active_opponents_count}")
            return action_call_const, bet_to_call

    num_limpers = 0
    my_investment_this_round = 0
    if my_player:
        player_investment_str = str(my_player.get('bet', '0')).replace('$', '').replace(',', '').replace('€', '')
        try:
            my_investment_this_round = float(player_investment_str)
        except ValueError:
            my_investment_this_round = 0

        if my_player.get('is_sb') and my_investment_this_round < small_blind:
                my_investment_this_round = small_blind
        if my_player.get('is_bb') and my_investment_this_round < big_blind:
                my_investment_this_round = big_blind

    if bet_to_call == 0 or (my_player.get('is_bb', False) and bet_to_call == 0 and max_bet_on_table <= big_blind):
        if max_bet_on_table <= big_blind: 
            excess_in_pot = pot_size - (small_blind + big_blind)
            if not my_player.get('is_sb', False) and not my_player.get('is_bb', False):
                excess_in_pot -= my_investment_this_round
            if excess_in_pot > 0:
                num_limpers = int(round(excess_in_pot / big_blind))
            num_limpers = max(0, num_limpers)

    if bet_to_call == 0: 
        open_raise_size = big_blind * 3 + (num_limpers * big_blind)
        base_raise_size = max(open_raise_size, big_blind * 2.5) 
    elif max_bet_on_table > 0 : 
        three_bet_total_size = 3 * max_bet_on_table
        base_raise_size = three_bet_total_size
        min_reraise_total = my_investment_this_round + bet_to_call + bet_to_call 
        base_raise_size = max(base_raise_size, min_reraise_total)
    else: 
        base_raise_size = big_blind * 3

    raise_amount_calculated = min(base_raise_size * base_aggression_factor, my_stack) 
    raise_amount_calculated = round(max(raise_amount_calculated, big_blind * 2), 2) 
    
    if bet_to_call > 0:
        min_total_after_raise = max_bet_on_table + max_bet_on_table 
        if my_investment_this_round > 0: 
            min_total_after_raise = max_bet_on_table + (max_bet_on_table - my_investment_this_round) 
        min_total_after_raise = max(min_total_after_raise, max_bet_on_table + big_blind)
        raise_amount_calculated = max(raise_amount_calculated, min_total_after_raise)
    raise_amount_calculated = round(min(raise_amount_calculated, my_stack), 2)

    # This print was moved down, after set mining logic and raise_amount calculation
    print(f"Preflop Logic: Cat: {preflop_category}, WinP: {win_probability:.3f}, B2Call: {bet_to_call}, CalcRaise: {raise_amount_calculated}, MyStack: {my_stack}, MyInv: {my_investment_this_round}, MaxBet: {max_bet_on_table}, Pot: {pot_size}, Opps: {active_opponents_count}, BB: {my_player.get('is_bb', False)}")

    if preflop_category == "Premium Pair":
        if bet_to_call == 0:
            return action_raise_const, min(raise_amount_calculated * 1.25, my_stack)  # Increased aggression
        elif bet_to_call <= my_stack * 0.6: # Increased threshold for considering a raise/call vs all-in
            # If facing a bet, always re-raise with premium pairs if not too much of stack
            # Ensure raise_amount is a significant re-raise
            reraise_amount = max(raise_amount_calculated, bet_to_call * 3) # Standard 3x reraise
            reraise_amount = min(reraise_amount, my_stack)

            if reraise_amount > bet_to_call and reraise_amount < my_stack * 0.85: # Ensure it's a valid raise and not committing too much
                return action_raise_const, reraise_amount
            elif win_probability > pot_odds_to_call or win_probability > 0.33: # Lowered win_prob for call
                return action_call_const, bet_to_call
            else:
                return action_fold_const, 0
        else: 
            # Facing a large bet (potentially all-in)
            if win_probability > pot_odds_to_call or win_probability > 0.38: # Slightly more conservative for all-in calls
                return action_call_const, min(my_stack, bet_to_call)
            return action_fold_const, 0
    
    elif preflop_category in ["Strong Pair", "Suited Ace", "Offsuit Broadway"]:
        is_aj_offsuit = "AJ offsuit" in hand_description
        is_kq_offsuit = "KQ offsuit" in hand_description
        # Scenario 28: Preflop all-in short stack (AJs, 10BB)
        # Hand description for AJs is 'Suited Ace-Jack'
        is_premium_suited_ace_for_shove = ("Suited Ace-Jack" in hand_description or "Suited Ace-Queen" in hand_description or "Suited Ace-King" in hand_description)
        is_short_stack_for_shove = (my_stack <= big_blind * 12) # 10-12BB is typical short stack for shove/fold

        win_prob_threshold_open = 0.18 if (is_aj_offsuit or is_kq_offsuit) else 0.22
        win_prob_threshold_call = 0.16 if (is_aj_offsuit or is_kq_offsuit) else 0.20

        if is_premium_suited_ace_for_shove and is_short_stack_for_shove and bet_to_call > 0 and max_bet_on_table > 0:
            # Facing a raise, short stacked with premium suited Ace -> Shove
            shove_amount = my_stack
            # Ensure shove is a valid raise over the current max_bet_on_table
            # Min raise = current bet + (current bet - previous bet for this player)
            # If I have already invested, min raise is max_bet_on_table + (max_bet_on_table - my_investment_this_round)
            # If I have not invested (e.g. I am BB and it was raised to me), min raise is max_bet_on_table * 2 (roughly)
            min_reraise_to_make = max_bet_on_table + (max_bet_on_table - my_investment_this_round) if my_investment_this_round < max_bet_on_table else max_bet_on_table + big_blind
            min_reraise_to_make = max(min_reraise_to_make, max_bet_on_table + big_blind) # Absolute minimum raise
            
            # The amount to raise is the total amount we want our bet to be.
            # So, if we shove for `my_stack`, this must be >= min_reraise_to_make.
            if shove_amount >= min_reraise_to_make:
                 print(f"Preflop Logic: Short stack ({my_stack/big_blind:.1f}BB) premium suited Ace ({hand_description}) SHOVE. ShoveAmt: {shove_amount}, MinRaiseTotal: {min_reraise_to_make}, MaxBet: {max_bet_on_table}, MyInv: {my_investment_this_round}")
                 return action_raise_const, shove_amount
            elif win_probability > pot_odds_to_call or win_probability > 0.3: 
                print(f"Preflop Logic: Short stack ({my_stack/big_blind:.1f}BB) premium suited Ace ({hand_description}) CALL (shove not valid raise). BetToCall: {bet_to_call}")
                return action_call_const, min(my_stack, bet_to_call)
            else:
                print(f"Preflop Logic: Short stack ({my_stack/big_blind:.1f}BB) premium suited Ace ({hand_description}) FOLD (shove not valid, call not good odds).")
                return action_fold_const, 0

        if bet_to_call == 0 and win_probability > win_prob_threshold_open:
            return action_raise_const, raise_amount_calculated
        elif bet_to_call > 0 and (win_probability > pot_odds_to_call or win_probability > win_prob_threshold_call):
            is_bb_player = my_player.get('is_bb', False)
            is_facing_small_steal_raise = (max_bet_on_table > 0 and max_bet_on_table <= big_blind * 2.5) # max_bet_on_table is the raise size we are facing
            is_kto_like = ("KTo" in hand_description or ("King" in hand_description and "Ten" in hand_description and "Offsuit" in hand_description))

            # Scenario 20: BB defense vs steal with KTo (Offsuit Broadway)
            # We are in BB, facing a small steal raise (e.g. min-raise from BTN/SB)
            # Hand is KTo (or similar like QTo, JTo if we extend)
            should_prefer_call_bb_defense = (is_bb_player and 
                                             is_facing_small_steal_raise and
                                             preflop_category == "Offsuit Broadway" and
                                             is_kto_like and
                                             bet_to_call <= big_blind * 1.5) # Call if the amount to call is small (e.g. completing SB for BB, or calling a min-raise)
            
            print(f"Preflop S20 Check: is_bb_player={is_bb_player}, is_facing_small_steal_raise={is_facing_small_steal_raise} (max_bet_on_table={max_bet_on_table}), is_kto_like={is_kto_like}, bet_to_call={bet_to_call}, big_blind={big_blind}")

            if should_prefer_call_bb_defense:
                print(f"Preflop Logic: Scenario 20 (KTo BB defense) - Preferring CALL. BetToCall: {bet_to_call}")
                return action_call_const, bet_to_call
            
            # Standard raise/call logic if not the specific BB defense scenario
            if (win_probability > (win_prob_threshold_open + 0.03) and
                raise_amount_calculated < my_stack * 0.6 and
                raise_amount_calculated > bet_to_call): 
                return action_raise_const, raise_amount_calculated
            
            return action_call_const, bet_to_call
        elif can_check:
            return action_check_const, 0
        else:
            return action_fold_const, 0

    elif preflop_category in ["Playable Broadway", "Medium Pair", "Suited Connector"]:
        win_prob_open_playable = 0.18 
        win_prob_call_playable = 0.15
        is_facing_3bet_or_more = False
        if max_bet_on_table > big_blind * 4 and bet_to_call > max_bet_on_table: 
            is_facing_3bet_or_more = True
        elif bet_to_call > big_blind * 8: 
            is_facing_3bet_or_more = True

        if is_facing_3bet_or_more:
            if preflop_category == "Suited Connector" and win_probability > 0.28 and win_probability > pot_odds_to_call and bet_to_call < my_stack * 0.20:
                 return action_call_const, bet_to_call
            elif win_probability > 0.30 and win_probability > pot_odds_to_call and bet_to_call < my_stack * 0.15:
                 return action_call_const, bet_to_call
            if can_check: 
                return action_check_const, 0
            return action_fold_const, 0

        if bet_to_call == 0 and win_probability > win_prob_open_playable:
            return action_raise_const, raise_amount_calculated 
        elif bet_to_call > 0 and bet_to_call <= pot_size * 0.5 and \
             (win_probability > pot_odds_to_call or win_probability > win_prob_call_playable):
            return action_call_const, bet_to_call
        elif can_check:
            return action_check_const, 0
        else:
            return action_fold_const, 0
            
    if can_check:
        return action_check_const, 0
    return action_fold_const, 0
