# preflop_decision_logic.py
import math # For round

# Note: ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE are passed as arguments (e.g., action_fold_const)
# get_preflop_hand_category_func and calculate_expected_value_func are also passed as arguments.

def make_preflop_decision(
    decision_engine_instance, my_player, hand_evaluation_tuple, my_hole_cards_str_list, 
    bet_to_call, can_check, pot_size, my_stack, active_opponents_count, 
    win_probability, pot_odds_to_call, max_bet_on_table, game_stage, hand_description,
    action_fold_const, action_check_const, action_call_const, action_raise_const,
    get_preflop_hand_category_func, 
    calculate_expected_value_func
    ):
    """Enhanced pre-flop decision making"""
    
    small_blind = decision_engine_instance.small_blind
    big_blind = decision_engine_instance.big_blind
    base_aggression_factor = decision_engine_instance.base_aggression_factor

    preflop_category = get_preflop_hand_category_func(hand_evaluation_tuple, my_hole_cards_str_list)
    
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

    if bet_to_call == 0 or (my_player.get('is_bb') and bet_to_call == 0):
        if max_bet_on_table <= big_blind: 
            excess_in_pot = pot_size - (small_blind + big_blind)
            if not my_player.get('is_sb') and not my_player.get('is_bb'):
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

    raise_amount = min(base_raise_size * base_aggression_factor, my_stack) 
    raise_amount = round(max(raise_amount, big_blind * 2), 2) 
    
    if bet_to_call > 0:
        min_total_after_raise = max_bet_on_table + max_bet_on_table 
        if my_investment_this_round > 0: 
            min_total_after_raise = max_bet_on_table + (max_bet_on_table - my_investment_this_round) 
        min_total_after_raise = max(min_total_after_raise, max_bet_on_table + big_blind)
        raise_amount = max(raise_amount, min_total_after_raise)
    raise_amount = round(min(raise_amount, my_stack), 2)

    print(f"Preflop Logic: Category: {preflop_category}, WinP: {win_probability:.3f}, BetToCall: {bet_to_call}, CalcRaise: {raise_amount}, MyStack: {my_stack}")

    if preflop_category == "Premium Pair":
        if bet_to_call == 0:
            return action_raise_const, min(raise_amount * 1.2, my_stack)  # More aggressive with premium
        elif bet_to_call <= my_stack * 0.5:  # Increased from 0.45
            ev_call = calculate_expected_value_func(action_call_const, bet_to_call, pot_size, win_probability, action_fold_const, action_check_const, action_call_const, action_raise_const, bet_to_call)
            ev_raise = calculate_expected_value_func(action_raise_const, raise_amount, pot_size, win_probability, action_fold_const, action_check_const, action_call_const, action_raise_const)
            if ev_raise > ev_call and raise_amount < my_stack * 0.9 :  # Increased willingness to raise
                return action_raise_const, raise_amount
            elif win_probability > pot_odds_to_call or win_probability > 0.35:  # Lowered threshold
                return action_call_const, bet_to_call
            else:
                return action_fold_const, 0        else: 
            if win_probability > pot_odds_to_call or win_probability > 0.4:  # Lowered from 0.45                   
                return action_call_const, min(my_stack, bet_to_call)
            return action_fold_const, 0
    
    elif preflop_category in ["Strong Pair", "Suited Ace", "Offsuit Broadway"]:
        is_aj_offsuit = "AJ offsuit" in hand_description
        is_kq_offsuit = "KQ offsuit" in hand_description
        win_prob_threshold_open = 0.18 if (is_aj_offsuit or is_kq_offsuit) else 0.22  # Lowered thresholds
        win_prob_threshold_call = 0.16 if (is_aj_offsuit or is_kq_offsuit) else 0.20  # Lowered thresholds

        if bet_to_call == 0 and win_probability > win_prob_threshold_open:
            return action_raise_const, raise_amount
        elif bet_to_call > 0 and (win_probability > pot_odds_to_call or win_probability > win_prob_threshold_call):
            if win_probability > win_prob_threshold_open + 0.03 and raise_amount < my_stack * 0.6:  # More willing to 3-bet
                return action_raise_const, raise_amount
            return action_call_const, bet_to_call
        elif can_check:
            return action_check_const, 0
        else:
            return action_fold_const, 0

    elif preflop_category in ["Playable Broadway", "Medium Pair", "Suited Connector"]:
        win_prob_open_playable = 0.18 
        win_prob_call_playable = 0.15
        if bet_to_call == 0 and win_probability > win_prob_open_playable:
            return action_raise_const, raise_amount 
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
