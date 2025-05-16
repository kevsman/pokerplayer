# filepath: c:\\GitRepositories\\pokerplayer\\decision_engine.py
# Action definitions
ACTION_FOLD = "FOLD"
ACTION_CHECK = "CHECK"
ACTION_CALL = "CALL"
ACTION_RAISE = "RAISE"

class DecisionEngine:
    def __init__(self, big_blind=0.02, small_blind=0.01):
        self.big_blind = big_blind
        self.small_blind = small_blind
        # Opponent modeling data structure (example: by player name or seat)
        self.opponent_models = {} 
        # Hand rank values (higher is better) - from HandEvaluator's first element of tuple
        # 0: Pre-flop/Invalid, 1: High Card, ..., 9: Straight Flush (Royal Flush is a type of Straight Flush)
        self.HAND_RANK_STRENGTH = {
            "Royal Flush": 10,
            "Straight Flush": 9,
            "Four of a Kind": 8,
            "Full House": 7,
            "Flush": 6,
            "Straight": 5,
            "Three of a Kind": 4,
            "Two Pair": 3,
            "One Pair": 2,
            "High Card": 1,
            "N/A": 0 # Default for pre-flop or unknown
        }

    def _get_hand_strength_value(self, hand_evaluation_tuple):
        if not hand_evaluation_tuple or not isinstance(hand_evaluation_tuple, tuple) or len(hand_evaluation_tuple) < 1:
            return 0
        # The first element of the tuple is the numerical rank from HandEvaluator
        return hand_evaluation_tuple[0]

    def _get_preflop_hand_category(self, hand_evaluation_tuple, hole_cards_str):
        # hole_cards_str is a list like ['As', 'Kd']
        # hand_evaluation_tuple for preflop is (0, "AK suited/offsuit" or "Pair of As", [rank_A, rank_K])
        if not hand_evaluation_tuple or hand_evaluation_tuple[0] != 0: # Ensure it's a pre-flop eval
             return "Weak"
        if len(hand_evaluation_tuple[2]) != 2: # Ensure two cards in tiebreakers
            return "Weak"

        rank1_val, rank2_val = hand_evaluation_tuple[2][0], hand_evaluation_tuple[2][1] # Already sorted high to low
        is_pair = (rank1_val == rank2_val)
        is_suited = False
        if len(hole_cards_str) == 2 and len(hole_cards_str[0]) > 1 and len(hole_cards_str[1]) > 1:
            is_suited = (hole_cards_str[0][-1] == hole_cards_str[1][-1])

        # Premium Pairs (AA-QQ)
        if is_pair and rank1_val >= 12: # Q=12, K=13, A=14
            return "Premium Pair"
        # Strong Pairs (JJ-TT)
        if is_pair and rank1_val >= 10: # T=10, J=11
            return "Strong Pair"
        # Suited Connectors (e.g., T9s, 87s) - simplified
        if is_suited and abs(rank1_val - rank2_val) == 1 and (rank1_val >= 8 or rank2_val >=8): # e.g. 87s+
            return "Suited Connector" 
        # Suited Aces (e.g., A9s, ATs) - simplified
        if is_suited and rank1_val == 14 and rank2_val >= 9: # A9s+
            return "Suited Ace"
        # Offsuit Broadway (e.g., AKo, KQo) - simplified
        if not is_suited and rank1_val >= 10 and rank2_val >= 10: # Both cards T+
            return "Offsuit Broadway"
        # Medium Pairs (99-77)
        if is_pair and rank1_val >= 7:
            return "Medium Pair"
        # Other playable hands (can be expanded)
        if rank1_val >= 10 or rank2_val >= 10: # At least one broadway card
            return "Playable Broadway"
        
        return "Weak"

    def update_opponent_model(self, player_name, action, amount, game_stage, pot_size, num_active_opponents_in_hand):
        if player_name not in self.opponent_models:
            self.opponent_models[player_name] = {
                'vpip_opportunities': 0, # Times player could voluntarily put money in pre-flop
                'vpip_count': 0,        # Times player did VPIP
                'pfr_opportunities': 0,  # Times player could raise pre-flop
                'pfr_count': 0,          # Times player did PFR
                'aggression_actions': 0, # Bets + Raises post-flop
                'passive_actions': 0,    # Calls post-flop
                'fold_to_cbet_opportunities': 0, 
                'fold_to_cbet_count': 0,
                'cbet_opportunities': 0, # Chance to continuation bet
                'cbet_count': 0, # Made a CBet
                'hands_observed': 0,
                'action_history': [] # (game_stage, action, amount, pot_size_at_action)
            }
        
        model = self.opponent_models[player_name]
        model['action_history'].append((game_stage, action, amount, pot_size)) # For more detailed analysis later

        # This update logic is simplified. Accurate stats require tracking opportunities vs actual actions.
        # For VPIP/PFR, this would typically be updated once per hand when pre-flop action is complete for that player.
        # For post-flop stats, it depends on the specific situation (e.g., facing a bet for fold_to_cbet).
        # The current call point of this function in make_decision is not ideal for accurate stat accumulation.
        # It should ideally be called as each opponent action is observed by PokerBot.

        if game_stage == 'Preflop':
            # Simplified: Assume an opportunity if they act
            model['vpip_opportunities'] += 1 
            if action == ACTION_CALL or action == ACTION_RAISE:
                model['vpip_count'] += 1
                model['pfr_opportunities'] +=1 # If they VPIP, they had a chance to PFR (if not already a raise)
                if action == ACTION_RAISE:
                    model['pfr_count'] += 1
        elif game_stage in ['Flop', 'Turn', 'River']:
            if action == ACTION_RAISE: # Using RAISE for bets too for now
                model['aggression_actions'] += 1
            elif action == ACTION_CALL:
                model['passive_actions'] += 1
        
        # Increment hands_observed (simplification, better to do this once per hand concluded for the player)
        # model['hands_observed'] += 1 

    def get_opponent_tendencies(self, player_name):
        model = self.opponent_models.get(player_name)
        # Provide default average stats if no model or not enough data
        if not model or model['vpip_opportunities'] < 10: # Need some data for meaningful stats
            return {
                'vpip_rate': 0.25, 'pfr_rate': 0.15, 'agg_factor': 1.5, 
                'fold_to_cbet_rate': 0.5, 'cbet_rate': 0.6 
            } 
        
        vpip_rate = model['vpip_count'] / model['vpip_opportunities'] if model['vpip_opportunities'] > 0 else 0
        pfr_rate = model['pfr_count'] / model['pfr_opportunities'] if model['pfr_opportunities'] > 0 else 0
        
        total_postflop_actions = model['aggression_actions'] + model['passive_actions']
        agg_factor = (model['aggression_actions'] / model['passive_actions']) if model['passive_actions'] > 0 else (model['aggression_actions'] if model['aggression_actions'] > 0 else 1.5) # Avoid div by zero, default if no passive actions
        
        cbet_rate = model['cbet_count'] / model['cbet_opportunities'] if model['cbet_opportunities'] > 0 else 0.6
        fold_to_cbet_rate = model['fold_to_cbet_count'] / model['fold_to_cbet_opportunities'] if model['fold_to_cbet_opportunities'] > 0 else 0.5

        return {
            'vpip_rate': round(vpip_rate, 2), 'pfr_rate': round(pfr_rate, 2), 'agg_factor': round(agg_factor, 2),
            'fold_to_cbet_rate': round(fold_to_cbet_rate, 2), 'cbet_rate': round(cbet_rate, 2)
        }

    def make_decision(self, my_player, table_data, all_players_data):
        pot_odds_to_call = 0.0 # Initialize pot_odds_to_call at the beginning
        if not my_player or not my_player.get('has_turn'):
            return "Not my turn or player data missing."

        # --- Aggression Factor ---
        # Higher value means more aggression. Base is 1.0.
        # Values > 1.0 increase raise amounts and bluffing frequency.
        # Values < 1.0 make the bot play tighter/more passively.
        # This can be adjusted based on table dynamics or overall strategy.
        aggression_factor = 1.2 # Default aggression factor (e.g., 1.0 for normal, 1.2 for more aggressive)


        # Note: Opponent modeling updates should ideally happen as actions are observed by PokerBot,
        # not just at the start of our decision. This is a placeholder for that process.
        # for p_data in all_players_data: # This loop needs actual last action data to be useful here
        #     if not p_data.get('is_my_player') and p_data.get('name') != 'N/A':
        #         # self.update_opponent_model(p_data.get('name'), p_data.get('last_action'), ...)
        #         pass

        hand_evaluation_tuple = my_player.get('hand_evaluation') 
        if not hand_evaluation_tuple or not isinstance(hand_evaluation_tuple, tuple) or len(hand_evaluation_tuple) < 3:
            return ACTION_FOLD # Invalid hand eval

        numerical_hand_rank = self._get_hand_strength_value(hand_evaluation_tuple) # 0-9
        hand_description = hand_evaluation_tuple[1]
        tie_breaker_ranks = hand_evaluation_tuple[2]
        my_hole_cards_str_list = my_player.get('cards', [])

        pot_size_str = table_data.get('pot_size', "0").replace('$', '').replace(',', '').replace('€', '').replace('€', '') # Corrected euro symbol replacement
        try:
            pot_size = float(pot_size_str)
        except ValueError:
            pot_size = 0.0
        
        max_bet_on_table = 0.0
        active_opponents_count = 0
        # Get player who made the current max bet for opponent modeling lookup
        player_to_act_on = None 
        
        for p in all_players_data:
            if p.get('is_empty', False) or p.get('stack', '0') == '0':
                continue # Skip empty or busted players
            if p.get('name') == my_player.get('name'): # Skip self
                continue
            
            # This check is basic. A player is active if they haven't folded and have chips.
            # A more robust check would involve looking at their status in the current hand if available.
            if p.get('bet', '0') != 'folded': # Assuming 'folded' is a status, or check stack > 0 and not explicitly folded
                active_opponents_count += 1
            
            try:
                player_bet_str = p.get('bet', '0').replace('$', '').replace(',', '').replace('€', '').replace('€', '') # Corrected euro symbol replacement
                player_bet = float(player_bet_str)
                if player_bet > max_bet_on_table:
                    max_bet_on_table = player_bet
                    player_to_act_on = p.get('name') # Name of player who made the current highest bet
            except ValueError:
                pass 
        
        my_current_bet_str = my_player.get('bet', '0').replace('$', '').replace(',', '').replace('€', '').replace('€', '') # Corrected euro symbol replacement
        try:
            my_current_bet = float(my_current_bet_str)
        except ValueError:
            my_current_bet = 0.0
            
        bet_to_call = round(max(0, max_bet_on_table - my_current_bet), 2)
        # can_check = (bet_to_call == 0) # Define can_check # Moved lower

        print(f"DecisionEngine: Initial bet_to_call calculated by engine: {bet_to_call} (max_bet_on_table: {max_bet_on_table}, my_current_bet: {my_current_bet})")
        
        parsed_bet_to_call_from_parser = my_player.get('bet_to_call', 0) # This is the value from the button text
        is_all_in_call_available_from_parser = my_player.get('is_all_in_call_available', False)
        print(f"DecisionEngine: From html_parser - player_info['bet_to_call']: {parsed_bet_to_call_from_parser}")
        print(f"DecisionEngine: From html_parser - player_info['is_all_in_call_available']: {is_all_in_call_available_from_parser}")

        # Prioritize bet_to_call from parser if it's greater than 0, as it reflects button states.
        # This is crucial if the buttons show a call amount but table scan didn't pick it up (e.g. complex bet scenarios)
        # or if the parser correctly identifies a "Call X" amount that differs from simple calculation.
        if parsed_bet_to_call_from_parser > 0:
            if bet_to_call == 0: # Engine thought it was a check, but parser found a call button
                print(f"DecisionEngine: Overriding engine's bet_to_call (0) with parser's value ({parsed_bet_to_call_from_parser}) as a call option was found.")
                bet_to_call = parsed_bet_to_call_from_parser
            elif parsed_bet_to_call_from_parser != bet_to_call:
                 # This case means both engine and parser found a bet_to_call, but they differ.
                 # Generally, the parser's value from the button should be more reliable for the immediate action.
                 print(f"DecisionEngine: Discrepancy. Engine bet_to_call: {bet_to_call}, Parser bet_to_call: {parsed_bet_to_call_from_parser}. Using parser's value.")
                 bet_to_call = parsed_bet_to_call_from_parser
        
        can_check = (bet_to_call == 0) # Now define can_check based on the potentially updated bet_to_call

        my_stack_str = my_player.get('stack', '0').replace('$', '').replace(',', '').replace('€', '')
        try:
            my_stack = float(my_stack_str)
        except ValueError:
            my_stack = self.big_blind * 100 
        print(f"DecisionEngine: My stack: {my_stack}")

        # Determine if we are facing an all-in situation based on calculated bet_to_call vs our stack
        is_facing_effective_all_in = (bet_to_call > 0 and bet_to_call >= my_stack)
        print(f"DecisionEngine: Calculated is_facing_effective_all_in (bet_to_call ({bet_to_call}) >= my_stack ({my_stack})): {is_facing_effective_all_in}")

        # If the parser specifically identified an "All In" button with an amount, 
        # and that amount is what we need to call (i.e., it's our remaining stack or less if opponent is shorter),
        # this implies the `bet_to_call` should align with `parsed_bet_to_call_from_parser` if it's an all-in call for us.
        # The `is_all_in_call_available_from_parser` flag is crucial here.

        # If the parser says an all-in call is available, and the amount on that button is our stack,
        # it means the actual bet to call IS our stack.
        if is_all_in_call_available_from_parser and parsed_bet_to_call_from_parser == my_stack:
            print(f"DecisionEngine: Parser indicates all-in call matching my stack. Overriding bet_to_call to {my_stack}")
            bet_to_call = my_stack 
            is_facing_effective_all_in = True # Reinforce this, as it's an explicit all-in call
            print(f"DecisionEngine: Updated is_facing_effective_all_in: {is_facing_effective_all_in}")

        # Calculate pot odds using the potentially updated bet_to_call
        if bet_to_call > 0:
            # Denominator: current pot size + the amount we need to call.
            # pot_size should represent the money already in the middle from previous streets and current street up to the last action.
            # bet_to_call is the additional amount we must contribute to match the current bet.
            denominator = pot_size + bet_to_call 
            if denominator > 0:
                pot_odds_to_call = bet_to_call / denominator
            else:
                pot_odds_to_call = 0 # Should not happen if bet_to_call > 0
        else:
            pot_odds_to_call = 0 # No bet to call, so pot odds are not directly applicable for calling
        print(f"DecisionEngine: Pot odds to call: {pot_odds_to_call} (bet_to_call: {bet_to_call}, pot_size: {pot_size}, denominator: {denominator if bet_to_call > 0 else 'N/A'})")

        # If facing an all-in bet from opponent that covers my stack
        if is_facing_effective_all_in:
            print(f"DecisionEngine: Evaluating ALL-IN call. My hand rank: {numerical_hand_rank}, Pot odds: {pot_odds_to_call}")
            # Decision to call all-in: based on hand strength and pot odds
            if numerical_hand_rank >= 4: # Three of a Kind or better
                return ACTION_CALL, my_stack # Call the all-in (amount will be my remaining stack)
            elif numerical_hand_rank >= 2 and pot_odds_to_call > 0.33: # One Pair with good pot odds
                return ACTION_CALL, my_stack
            elif ("Flush Draw" in hand_description or "Straight Draw" in hand_description) and pot_odds_to_call > 0.25:
                return ACTION_CALL, my_stack # Call with good draws if odds are there
            else:
                return ACTION_FOLD

        min_raise_amount = bet_to_call + self.big_blind # Simplified: current bet + 1 BB, or just 2BB if opening
        if bet_to_call == 0: # If opening
            min_raise_amount = self.big_blind * 2 
        else: # If re-raising, it should be at least the size of the last raise.
            # This needs more state (tracking last raise size). For now, bet_to_call + BBs.
            min_raise_amount = max_bet_on_table + self.big_blind * 2 # Simplified: raise to current max bet + 2BB

        game_stage = table_data.get('game_stage', 'Preflop')
        position = my_player.get('position_category', 'Late') # Early, Middle, Late, Blinds

        # --- Pre-flop Adjustments for Aggression ---
        limpers = 0
        if game_stage == 'Preflop':
            for p_data in all_players_data:
                if p_data.get('name') == my_player.get('name') or p_data.get('is_empty'):
                    continue
                p_bet_str = p_data.get('bet', '0').replace('$', '').replace('€', '')
                try:
                    p_bet = float(p_bet_str)
                    # A limper is someone who called the big blind but hasn't raised.
                    # This condition assumes max_bet_on_table is currently the big blind if there are limpers.
                    if p_bet == self.big_blind and p_data.get('actions_in_street', 0) == 1: # Simplified: first action was a call
                        limpers += 1
                except ValueError:
                    pass
            print(f"DecisionEngine: Detected {limpers} limper(s).")


        # --- Basic Bet Sizing ---
        # Standard raise: 2.5-3.5 BB. Adjust based on position, limpers, etc.
        # Add 1 BB for each limper.
        # Increase if out of position.
        standard_raise_bb = 3 * aggression_factor # Base raise in BBs
        if limpers > 0:
            standard_raise_bb += limpers * aggression_factor # Add 1 BB per limper, scaled by aggression

        if position in ['Early', 'Middle'] and game_stage == 'Preflop':
            standard_raise_bb += 0.5 * aggression_factor # Raise slightly more from earlier positions

        min_raise_amount = bet_to_call + self.big_blind # Minimum legal raise
        preferred_raise_amount = max(min_raise_amount, round(standard_raise_bb * self.big_blind, 2))
        
        # Ensure raise amount is not more than stack (will be capped later if it is)
        my_stack_str = my_player.get('stack', '0').replace('$', '').replace('€', '')
        try:
            my_stack = float(my_stack_str)
        except ValueError:
            my_stack = 0.0
        
        preferred_raise_amount = min(preferred_raise_amount, my_stack)


        # --- Pre-flop Decision Logic ---
        opponent_tendencies = self.get_opponent_tendencies(player_to_act_on) if player_to_act_on else self.get_opponent_tendencies(None) # Get default if no specific opponent

        # --- Pre-flop Strategy ---
        if game_stage == 'Preflop':
            preflop_category = self._get_preflop_hand_category(hand_evaluation_tuple, my_hole_cards_str_list)
            num_players_behind = active_opponents_count # Simplified: assumes all active opponents are behind. Needs position info.

            # Standard open raise sizing: 2.5-3BB, +1BB for each limper, +1BB for OOP
            open_raise_size = round(self.big_blind * (2.5 + max(0, active_opponents_count -1) ),2) # Basic sizing
            open_raise_size = max(self.big_blind * 2, open_raise_size) # Ensure at least 2BB

            # Adjust pre-flop strategy based on hand category and limpers
            if preflop_category == "Premium Pair": # AA, KK, QQ
                # Always raise, size depends on limpers/prior raises
                if bet_to_call == 0: # No prior raise, we are opening
                    # Strong open, especially with limpers
                    raise_amount = preferred_raise_amount 
                    if limpers > 0:
                         raise_amount = max(min_raise_amount, round((3 + limpers * 1.5) * self.big_blind * aggression_factor, 2))
                    print(f"DecisionEngine: Premium Pair, opening raise to {raise_amount}")
                    return ACTION_RAISE, min(my_stack, raise_amount)
                elif bet_to_call > 0: # Facing a raise
                    # 3-bet strong. Size: 3x the previous raise usually.
                    # If previous raise was small, make it at least preferred_raise_amount
                    three_bet_size = max(preferred_raise_amount, round(bet_to_call * 3 * aggression_factor, 2))
                    print(f"DecisionEngine: Premium Pair, 3-betting to {three_bet_size}")
                    return ACTION_RAISE, min(my_stack, three_bet_size)
            
            elif preflop_category == "Strong Pair": # JJ, TT
                if bet_to_call == 0: # Open raise
                    raise_amount = preferred_raise_amount
                    if limpers > 1: # Be more aggressive against multiple limpers
                        raise_amount = max(min_raise_amount, round((3 + limpers * 1.2) * self.big_blind * aggression_factor, 2))
                    print(f"DecisionEngine: Strong Pair, opening raise to {raise_amount}")
                    return ACTION_RAISE, min(my_stack, raise_amount)
                elif bet_to_call <= self.big_blind * 4 * aggression_factor: # Call smaller raises, consider 3-betting vs very small raises
                    # If facing a small raise and there were limpers, consider a squeeze play
                    if limpers > 0 and bet_to_call < self.big_blind * 3:
                         squeeze_raise = max(min_raise_amount, round((bet_to_call + (3 + limpers) * self.big_blind) * aggression_factor,2))
                         print(f"DecisionEngine: Strong Pair, squeeze raising limpers and small raiser to {squeeze_raise}")
                         return ACTION_RAISE, min(my_stack, squeeze_raise)
                    print(f"DecisionEngine: Strong Pair, calling raise of {bet_to_call}")
                    return ACTION_CALL, bet_to_call 
                else: # Facing a larger raise
                    print(f"DecisionEngine: Strong Pair, folding to large raise of {bet_to_call}")
                    return ACTION_FOLD, 0

            elif preflop_category == "Suited Connector" or preflop_category == "Suited Ace":
                if bet_to_call == 0: # Open raise, especially from late position or if many limpers
                    if position in ['Late', 'Blinds'] or limpers >= 1:
                        raise_amount = preferred_raise_amount
                        print(f"DecisionEngine: {preflop_category}, opening raise to {raise_amount}")
                        return ACTION_RAISE, min(my_stack, raise_amount)
                    else: # More cautious from early/mid if no limpers
                        print(f"DecisionEngine: {preflop_category} from {position}, checking/folding if option not available.")
                        return ACTION_CHECK if can_check else ACTION_FOLD, 0
                elif bet_to_call <= self.big_blind * 3 * aggression_factor and pot_odds_to_call > 0.2: # Call small raises if odds are good
                    print(f"DecisionEngine: {preflop_category}, calling raise of {bet_to_call} with pot odds {pot_odds_to_call:.2f}")
                    return ACTION_CALL, bet_to_call
                else:
                    print(f"DecisionEngine: {preflop_category}, folding to raise of {bet_to_call}")
                    return ACTION_FOLD, 0
            
            elif preflop_category == "Offsuit Broadway": # AKo, KQo, etc.
                if bet_to_call == 0: # Open raise, more likely with fewer players or late position
                    if active_opponents_count <= 4 or position in ['Late', 'Blinds'] or limpers > 0:
                        raise_amount = preferred_raise_amount
                        print(f"DecisionEngine: {preflop_category}, opening raise to {raise_amount}")
                        return ACTION_RAISE, min(my_stack, raise_amount)
                    else:
                        print(f"DecisionEngine: {preflop_category} from {position} with many players, checking/folding.")
                        return ACTION_CHECK if can_check else ACTION_FOLD, 0
                elif bet_to_call <= self.big_blind * 3.5 * aggression_factor : # Call moderate raises
                    print(f"DecisionEngine: {preflop_category}, calling raise of {bet_to_call}")
                    return ACTION_CALL, bet_to_call
                else: # Fold to larger 3-bets unless very strong Broadway (AK)
                    if hand_description in ["AK offsuit", "AK suited"] and bet_to_call < my_stack * 0.2: # AK can sometimes call more
                        print(f"DecisionEngine: {hand_description}, calling larger raise of {bet_to_call}")
                        return ACTION_CALL, bet_to_call
                    print(f"DecisionEngine: {preflop_category}, folding to large raise of {bet_to_call}")
                    return ACTION_FOLD, 0

            elif preflop_category == "Medium Pair": # 99-77
                if bet_to_call == 0: # Open raise if few limpers or late position
                    if limpers <= 1 or position in ['Late', 'Blinds']:
                        raise_amount = preferred_raise_amount
                        print(f"DecisionEngine: Medium Pair, opening raise to {raise_amount}")
                        return ACTION_RAISE, min(my_stack, raise_amount)
                    else: # Limp or fold if many limpers and early position (Set mining)
                        # For now, we avoid limping as per user request to be aggressive
                        # If we want to set-mine, we might call here.
                        # Let's try raising small to isolate one limper if there's exactly one.
                        if limpers == 1 and position not in ['Early']:
                             raise_amount = max(min_raise_amount, round( (2.5 + limpers) * self.big_blind * aggression_factor, 2))
                             print(f"DecisionEngine: Medium Pair, small isolation raise vs 1 limper to {raise_amount}")
                             return ACTION_RAISE, min(my_stack, raise_amount)
                        print(f"DecisionEngine: Medium Pair, too many limpers or bad position, folding.")
                        return ACTION_FOLD, 0
                elif bet_to_call <= self.big_blind * 4 * aggression_factor and pot_odds_to_call > 0.2: # Call small raises for set value
                    print(f"DecisionEngine: Medium Pair, calling raise of {bet_to_call} for set value.")
                    return ACTION_CALL, bet_to_call
                else:
                    print(f"DecisionEngine: Medium Pair, folding to raise of {bet_to_call}")
                    return ACTION_FOLD, 0
            
            elif preflop_category == "Playable Broadway": # Single broadway card, not covered above
                if bet_to_call == 0 and position in ['Late', 'Blinds'] and limpers < 2:
                    raise_amount = preferred_raise_amount * 0.8 # Slightly smaller raise
                    print(f"DecisionEngine: Playable Broadway ({hand_description}), late position open to {raise_amount}")
                    return ACTION_RAISE, min(my_stack, raise_amount)
                elif bet_to_call == 0 and limpers >=1 and position in ['Late', 'Blinds']: # Try to punish limpers
                    raise_amount = max(min_raise_amount, round((2.5 + limpers) * self.big_blind * aggression_factor, 2))
                    print(f"DecisionEngine: Playable Broadway ({hand_description}), raising limpers to {raise_amount}")
                    return ACTION_RAISE, min(my_stack, raise_amount)
                elif bet_to_call <= self.big_blind * 2 * aggression_factor and position in ['Blinds'] and pot_odds_to_call > 0.25: # Defend blinds vs small steal
                    print(f"DecisionEngine: Playable Broadway ({hand_description}), defending blind vs small raise {bet_to_call}")
                    return ACTION_CALL, bet_to_call
                else:
                    print(f"DecisionEngine: Playable Broadway ({hand_description}), folding.")
                    return ACTION_CHECK if can_check else ACTION_FOLD, 0

            else: # Weak hands
                if can_check:
                    print(f"DecisionEngine: Weak hand ({preflop_category} / {hand_description}), checking.")
                    return ACTION_CHECK, 0
                else: # Must call or fold
                    # If facing a very small bet (e.g. min bet from SB when BB) and pot odds are huge, might call.
                    if bet_to_call <= self.big_blind * 0.5 and pot_odds_to_call > 0.33 and position == 'Big Blind': # Simplified check for BB defense vs min-raise
                        print(f"DecisionEngine: Weak hand, but good pot odds in BB to call tiny bet {bet_to_call}")
                        return ACTION_CALL, bet_to_call
                    print(f"DecisionEngine: Weak hand ({preflop_category} / {hand_description}), folding to bet {bet_to_call}.")
                    return ACTION_FOLD, 0

        # --- Post-flop Strategy ---
        # numerical_hand_rank: 1 (High Card) to 9 (Straight Flush)
        
        # Calculate pot odds
        if bet_to_call > 0:
            # Ensure denominator is not zero before division
            denominator = pot_size + bet_to_call
            if denominator > 0:
                pot_odds_to_call = bet_to_call / denominator
            else:
                pot_odds_to_call = 0 # Or handle as an edge case, e.g., infinite if pot is 0 and facing a bet

        # Continuation Bet (C-Bet) logic
        # Need to know if I was the pre-flop aggressor. This state is missing.
        # Assume for now, if it's checked to us on the flop, and we raised pre-flop, we can C-Bet.
        can_cbet = False # Placeholder: (self.was_preflop_aggressor and game_stage == 'Flop' and bet_to_call == 0)
        if can_cbet:
            cbet_amount = round(pot_size * (0.4 if active_opponents_count > 1 else 0.6) ,2) # Smaller if multiway
            cbet_amount = max(self.big_blind, cbet_amount) # At least 1 BB
            # C-bet with strong hands, good draws, or as a bluff on certain board textures vs certain opponents
            if numerical_hand_rank >= 3 or "Flush Draw" in hand_description or "Straight Draw" in hand_description: # Two Pair+ or good draw
                return ACTION_RAISE, min(my_stack, cbet_amount) # ACTION_RAISE is used for betting
            elif opponent_tendencies['fold_to_cbet_rate'] > 0.6 and active_opponents_count == 1: # Bluff C-bet vs one opponent who folds a lot
                return ACTION_RAISE, min(my_stack, cbet_amount)
            else:
                return ACTION_CHECK # Check if not C-betting
        
        # Responding to bets post-flop
        if numerical_hand_rank >= 7: # Full House or better - very strong
            if bet_to_call == 0:
                return ACTION_RAISE, min(my_stack, round(pot_size * 0.7, 2)) # Value bet strong
            else: # Facing a bet, raise for value
                # Raise sizing: 2.5-3x the bet, or more if pot is large
                raise_value = round(max(min_raise_amount, bet_to_call * 2.5 + pot_size),2)
                return ACTION_RAISE, min(my_stack, raise_value)
        
        elif numerical_hand_rank >= 5: # Straight or Flush
            if bet_to_call == 0:
                return ACTION_RAISE, min(my_stack, round(pot_size * 0.6, 2)) # Value bet
            else: # Facing a bet
                if bet_to_call < my_stack * 0.4: # Call if bet is not too large portion of stack
                    return ACTION_CALL, bet_to_call
                else: # If bet is very large, re-evaluate (could be vs stronger or a bluff)
                    return ACTION_FOLD # Simplified: fold to huge overbets without nutted hand

        elif numerical_hand_rank >= 3: # Two Pair or Three of a Kind
            if bet_to_call == 0:
                return ACTION_RAISE, min(my_stack, round(pot_size * 0.5, 2))
            else:
                # Consider opponent tendencies: call more vs aggressive, fold more vs passive if bet is large
                if pot_odds_to_call > 0 and pot_odds_to_call < 0.35: # Decent pot odds
                    return ACTION_CALL, bet_to_call
                elif bet_to_call <= self.big_blind * 5: # Call moderately sized bets
                    return ACTION_CALL, bet_to_call
                else:
                    return ACTION_FOLD

        elif numerical_hand_rank == 2: # One Pair
            # Need to assess kicker strength and if it's top/middle/bottom pair.
            # This requires community card info and comparing tie_breaker_ranks[0] (pair rank) and tie_breaker_ranks[1] (kicker)
            # For simplicity, assume any pair has some showdown value.
            if bet_to_call == 0:
                return ACTION_CHECK # Check, hope to see next card or showdown cheaply
            else:
                if pot_odds_to_call > 0 and pot_odds_to_call < 0.25 and active_opponents_count == 1: # Good odds vs one player
                    return ACTION_CALL, bet_to_call
                elif bet_to_call <= self.big_blind * 3: # Call small bets
                    return ACTION_CALL, bet_to_call
                else:
                    return ACTION_FOLD
        
        else: # High Card or only a weak draw (draw logic needs specific identification)
            # Bluffing considerations:
            # - On scare cards (e.g., Ace on turn/river if we were aggressor)
            # - Vs tight opponents who fold often (from opponent_tendencies)
            # - If we have blockers to strong hands
            # Semi-bluffing with draws:
            # if "Flush Draw" in hand_description or "Straight Draw" in hand_description:
            #     draw_outs = ... # Calculate outs
            #     equity = draw_outs / (52 - len(my_hole_cards_str_list) - len(table_data.get('community_cards',[])))
            #     if bet_to_call == 0:
            #         return ACTION_RAISE, min(my_stack, round(pot_size * 0.4,2)) # Semi-bluff bet
            #     elif pot_odds_to_call > equity: # Calling if direct odds are good
            #         return ACTION_CALL, bet_to_call
            #     # Consider implied odds for draws too

            if bet_to_call == 0:
                return ACTION_CHECK
            else:
                # Fold to most bets if we have nothing
                if game_stage == 'River' and bet_to_call > pot_size * 0.5 and opponent_tendencies['agg_factor'] < 1.5: 
                    # Consider a hero call if opponent is passive and makes an uncharacteristic large bet (potential bluff)
                    # This is risky and needs very good reads.
                    pass # For now, stick to folding weak hands to bets.
                
                if bet_to_call <= self.small_blind * 2: # Call very small bets / probes
                    return ACTION_CALL, bet_to_call
                return ACTION_FOLD

        return ACTION_FOLD # Default fallback action
