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
        if not my_player or not my_player.get('has_turn'):
            return "Not my turn or player data missing."

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

        pot_size_str = table_data.get('pot_size', "0").replace('$', '').replace(',', '')
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
                player_bet = float(p.get('bet', '0').replace('$', '').replace(',', ''))
                if player_bet > max_bet_on_table:
                    max_bet_on_table = player_bet
                    player_to_act_on = p.get('name') # Name of player who made the current highest bet
            except ValueError:
                pass 
        
        my_current_bet_str = my_player.get('bet', '0').replace('$', '').replace(',', '')
        try:
            my_current_bet = float(my_current_bet_str)
        except ValueError:
            my_current_bet = 0.0
            
        bet_to_call = round(max(0, max_bet_on_table - my_current_bet), 2)
        
        # Effective stack (simplified - vs largest stack if multiple opponents, or vs single opponent)
        # For now, just use our stack as a reference for bet sizing.
        my_stack_str = my_player.get('stack', '0').replace('$', '').replace(',', '')
        try:
            my_stack = float(my_stack_str)
        except ValueError:
            my_stack = self.big_blind * 100 # Default if stack parsing fails

        min_raise_amount = bet_to_call + self.big_blind # Simplified: current bet + 1 BB, or just 2BB if opening
        if bet_to_call == 0: # If opening
            min_raise_amount = self.big_blind * 2 
        else: # If re-raising, it should be at least the size of the last raise.
            # This needs more state (tracking last raise size). For now, bet_to_call + BBs.
            min_raise_amount = max_bet_on_table + self.big_blind * 2 # Simplified: raise to current max bet + 2BB

        game_stage = table_data.get('game_stage')
        opponent_tendencies = self.get_opponent_tendencies(player_to_act_on) if player_to_act_on else self.get_opponent_tendencies(None) # Get default if no specific opponent

        # --- Pre-flop Strategy ---
        if game_stage == 'Preflop':
            preflop_category = self._get_preflop_hand_category(hand_evaluation_tuple, my_hole_cards_str_list)
            num_players_behind = active_opponents_count # Simplified: assumes all active opponents are behind. Needs position info.

            # Standard open raise sizing: 2.5-3BB, +1BB for each limper, +1BB for OOP
            open_raise_size = round(self.big_blind * (2.5 + max(0, active_opponents_count -1) ),2) # Basic sizing
            open_raise_size = max(self.big_blind * 2, open_raise_size) # Ensure at least 2BB

            if preflop_category == "Premium Pair": # AA, KK, QQ
                # Always raise or re-raise
                raise_amount = round(self.big_blind * (3 + active_opponents_count), 2)
                raise_amount = max(min_raise_amount, raise_amount) 
                if bet_to_call == 0:
                    return ACTION_RAISE, min(my_stack, raise_amount) # Don't bet more than stack
                elif bet_to_call < raise_amount * 1.5 : # Re-raise if facing a smaller bet
                    # 3-bet sizing: 3x original raise if IP, 4x if OOP. Pot size if multiway.
                    # Simplified: pot-sized raise or 3x the bet_to_call
                    three_bet_size = round(max(pot_size, bet_to_call * 3),2)
                    return ACTION_RAISE, min(my_stack, max(min_raise_amount, three_bet_size)) 
                else: # Facing a large 3-bet or 4-bet
                    # Consider stack sizes, pot odds for calling all-in. For now, call up to a certain % of stack.
                    if bet_to_call < my_stack * 0.33: 
                        return ACTION_CALL, bet_to_call
                    else: # If too large, might be all-in or fold (AA might go all-in)
                        return ACTION_RAISE, my_stack # Shove with AA/KK vs huge bet
            
            elif preflop_category == "Strong Pair" or preflop_category == "Suited Ace" or preflop_category == "Offsuit Broadway": # JJ,TT, AKs, AQs, AJs, KQs, AKo, AQo
                if bet_to_call == 0:
                    return ACTION_RAISE, min(my_stack, open_raise_size)
                elif bet_to_call <= self.big_blind * 4: # Call smaller 3-bets
                    return ACTION_CALL, bet_to_call
                else: # Fold to large 3-bets
                    return ACTION_FOLD
            
            elif preflop_category == "Medium Pair" or preflop_category == "Suited Connector": # 99-77, T9s, etc.
                # Playable, especially for set mining or if suited and can hit draws
                if bet_to_call == 0: # Open limp or small raise in late position
                    # Positional awareness is key here. For now, simple call.
                    return ACTION_CALL, self.big_blind # Limp
                elif bet_to_call <= self.big_blind * 3 and (pot_size / bet_to_call > 10 if bet_to_call > 0 else True): # Set mining odds
                    return ACTION_CALL, bet_to_call
                else:
                    return ACTION_FOLD
            else: # Weak hands
                if bet_to_call == 0: # Can check if in big blind and no raise
                    # This needs to know if I AM the big blind. Assume if bet_to_call is 0, it's a checkable spot.
                    return ACTION_CHECK
                # Fold to any raise unless it's just completing the SB
                elif my_current_bet == self.small_blind and bet_to_call == self.small_blind:
                    return ACTION_CALL, bet_to_call # Complete SB
                else:
                    return ACTION_FOLD

        # --- Post-flop Strategy ---
        # numerical_hand_rank: 1 (High Card) to 9 (Straight Flush)
        
        # Calculate pot odds
        pot_odds_to_call = 0.0
        if bet_to_call > 0:
            pot_odds_to_call = bet_to_call / (pot_size + bet_to_call + my_current_bet)

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
