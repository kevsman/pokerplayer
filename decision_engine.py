# filepath: c:\\GitRepositories\\pokerplayer\\decision_engine.py
from equity_calculator import EquityCalculator
import math

# Action definitions
ACTION_FOLD = "FOLD"
ACTION_CHECK = "CHECK"
ACTION_CALL = "CALL"
ACTION_RAISE = "RAISE"

class DecisionEngine:
    def __init__(self, big_blind=0.02, small_blind=0.01):
        self.big_blind = big_blind
        self.small_blind = small_blind
        self.equity_calculator = EquityCalculator()
        # Opponent modeling data structure (example: by player name or seat)
        self.opponent_models = {} 
        # Hand rank values (higher is better) - from HandEvaluator's first element of tuple
        # 0: Pre-flop/Invalid, 1: High Card, ..., 9: Straight Flush (Royal Flush is a type of Straight Flush)
        self.HAND_RANK_STRENGTH = {
            "Royal Flush": 10,
            "Straight Flush": 9,
            "Four of a Kind": 8,
            "Full House": 7,
            "Flush": 6,            "Straight": 5,
            "Three of a Kind": 4,
            "Two Pair": 3,
            "One Pair": 2,
            "High Card": 1,
            "N/A": 0 # Default for pre-flop or unknown
        }
        # More aggressive - increased for better suited hand calling
        self.base_aggression_factor = 1.3  # Increased from 0.95 to make bot more aggressive with suited hands

    def _get_hand_strength_value(self, hand_evaluation_tuple):
        if not hand_evaluation_tuple or not isinstance(hand_evaluation_tuple, tuple) or len(hand_evaluation_tuple) < 1:
            return 0
        # The first element of the tuple is the numerical rank from HandEvaluator
        return hand_evaluation_tuple[0]

    def calculate_expected_value(self, action, amount, pot_size, win_probability, bet_to_call=0):
        """
        Calculate Expected Value (EV) for a given action
        Returns the EV in chips/currency units
        """
        if action == ACTION_FOLD:
            return 0.0  # No gain or loss from folding
            
        elif action == ACTION_CHECK:
            # EV of checking = probability of winning * current pot
            return win_probability * pot_size
            
        elif action == ACTION_CALL:
            # EV of calling = (win_prob * (pot + bet_to_call)) - bet_to_call
            return (win_probability * (pot_size + bet_to_call)) - bet_to_call
            
        elif action == ACTION_RAISE:
            # Simplified EV for raising - assumes opponent folds fold_equity% of time
            # and calls (1-fold_equity)% of time
            fold_equity = self._estimate_fold_equity(amount, pot_size)
            
            # If opponent folds: we win the current pot immediately
            ev_if_fold = fold_equity * pot_size
            
            # If opponent calls: we need to win at showdown
            # Pot becomes pot_size + amount + opponent_call_amount
            opponent_call_amount = amount  # Simplified assumption
            new_pot = pot_size + amount + opponent_call_amount
            ev_if_call = (1 - fold_equity) * ((win_probability * new_pot) - amount)
            
            return ev_if_fold + ev_if_call
            
        return 0.0
    
    def _estimate_fold_equity(self, bet_size, pot_size):
        """
        Estimate the probability that opponents will fold to our bet
        Based on bet size relative to pot
        """
        if pot_size <= 0:
            return 0.1  # Conservative estimate
            
        bet_to_pot_ratio = bet_size / pot_size
        
        # Rough estimates based on common poker theory
        if bet_to_pot_ratio <= 0.3:
            return 0.1  # Small bets rarely make opponents fold
        elif bet_to_pot_ratio <= 0.5:
            return 0.2
        elif bet_to_pot_ratio <= 0.75:
            return 0.3
        elif bet_to_pot_ratio <= 1.0:
            return 0.4
        elif bet_to_pot_ratio <= 1.5:
            return 0.5
        else:
            return 0.6  # Large overbets have higher fold equity
    
    def calculate_stack_to_pot_ratio(self, stack_size, pot_size):
        """Calculate Stack-to-Pot Ratio (SPR) - important for post-flop decisions"""
        if pot_size <= 0:
            return float('inf')
        return stack_size / pot_size
    
    def get_optimal_bet_size(self, hand_strength, pot_size, stack_size, game_stage, bluff=False):
        """
        Calculate optimal bet size based on hand strength and situation
        Returns bet size as a fraction of pot
        """
        if pot_size <= 0: # Avoid division by zero or nonsensical bets if pot is 0
            return min(self.big_blind * 2.5, stack_size) # Default to a standard open if pot is 0 for some reason

        if bluff:
            # Bluff sizes are typically 50-66% of pot
            # Ensure bluff bet is not too small, at least 1/2 of pot if possible, or min 1 BB
            bet = pot_size * 0.5 # Target 50% pot for bluffs
            bet = max(bet, self.big_blind) # Ensure at least 1 BB
            return min(round(bet,2), stack_size)
            
        # Value betting sizes based on hand strength (win_probability)
        if hand_strength >= 0.8:  # Very strong hands (e.g., nuts, near nuts)
            bet = pot_size * 0.70 # Target 70% pot (adjusted from 0.75)
        elif hand_strength >= 0.65:  # Strong hands (e.g., good top pair, overpair, strong draws on turn)
            bet = pot_size * 0.60 # Target 60% pot
        elif hand_strength >= 0.5:  # Medium hands (e.g., decent pair, weaker top pair, good draws on flop)
            bet = pot_size * 0.50 # Target 50% pot (standard half pot)
        else:
            # Weaker hands that might still bet for thin value or protection
            bet = pot_size * 0.33 # Target 1/3 pot
        
        bet = max(bet, self.big_blind if game_stage != "Preflop" else self.big_blind * 2) # Ensure min bet (2BB for preflop open)
        return min(round(bet,2), stack_size)
    
    def should_bluff(self, fold_equity, pot_size, bet_size):
        """
        Determine if bluffing is profitable
        A bluff is profitable if: fold_equity > bet_size / (pot_size + bet_size)
        """
        if pot_size + bet_size <= 0:
            return False
        
        required_fold_equity = bet_size / (pot_size + bet_size)
        return fold_equity > required_fold_equity

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
            return "Suited Connector"        # Suited Aces (e.g., A5s+) - simplified
        if is_suited and rank1_val == 14 and rank2_val >= 5: # A5s+
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
        """
        Enhanced decision making with EV calculations, win probability, and proper pot odds
        """
        pot_odds_to_call = 0.0
        if not my_player or not my_player.get('has_turn'):
            return "Not my turn or player data missing."

        # Use more conservative aggression factor by default
        aggression_factor = self.base_aggression_factor

        hand_evaluation_tuple = my_player.get('hand_evaluation') 
        if not hand_evaluation_tuple or not isinstance(hand_evaluation_tuple, tuple) or len(hand_evaluation_tuple) < 3:
            return ACTION_FOLD, 0

        numerical_hand_rank = self._get_hand_strength_value(hand_evaluation_tuple)
        hand_description = hand_evaluation_tuple[1]
        my_hole_cards_str_list = my_player.get('cards', [])

        # Parse pot size and stack information
        pot_size_str = table_data.get('pot_size', "0").replace('$', '').replace(',', '').replace('€', '')
        try:
            pot_size = float(pot_size_str)
        except ValueError:
            pot_size = 0.0
        
        my_stack_str = my_player.get('stack', '0').replace('$', '').replace(',', '').replace('€', '')
        try:
            my_stack = float(my_stack_str)
        except ValueError:
            my_stack = self.big_blind * 100

        # Calculate opponents and betting information
        active_opponents_count = 0
        max_bet_on_table = 0.0
        
        for p in all_players_data:
            if p.get('is_empty', False) or p.get('name') == my_player.get('name'):
                continue
            if p.get('bet', '0') != 'folded':
                active_opponents_count += 1
            try:
                player_bet_str = p.get('bet', '0').replace('$', '').replace(',', '').replace('€', '')
                player_bet = float(player_bet_str)
                max_bet_on_table = max(max_bet_on_table, player_bet)
            except ValueError:
                pass 

        my_current_bet_str = my_player.get('bet', '0').replace('$', '').replace(',', '').replace('€', '')
        try:
            my_current_bet = float(my_current_bet_str)
        except ValueError:
            my_current_bet = 0.0
            
        bet_to_call = round(max(0, max_bet_on_table - my_current_bet), 2)
        
        # Prioritize parser's bet_to_call if available
        parsed_bet_to_call = my_player.get('bet_to_call', 0)
        if parsed_bet_to_call > 0:
            bet_to_call = parsed_bet_to_call

        can_check = (bet_to_call == 0)
        game_stage = table_data.get('game_stage', 'Preflop')
        community_cards = table_data.get('community_cards', [])

        # Calculate win probability using equity calculator
        win_probability = 0.0
        if my_hole_cards_str_list and len(my_hole_cards_str_list) == 2:
            win_prob, tie_prob, ev_multiplier = self.equity_calculator.calculate_equity_monte_carlo(
                my_hole_cards_str_list, community_cards, active_opponents_count, simulations=500
            )
            win_probability = win_prob
            print(f"DecisionEngine: Win probability: {win_probability:.3f}, Tie probability: {tie_prob:.3f}")

        # Calculate pot odds
        if bet_to_call > 0:
            pot_odds_to_call = bet_to_call / (pot_size + bet_to_call) if (pot_size + bet_to_call) > 0 else 0
        else:
            pot_odds_to_call = 0

        print(f"DecisionEngine: Pot odds: {pot_odds_to_call:.3f}, Bet to call: {bet_to_call}, Pot size: {pot_size}")

        # Calculate SPR (Stack-to-Pot Ratio)
        spr = self.calculate_stack_to_pot_ratio(my_stack, pot_size)
        print(f"DecisionEngine: SPR: {spr:.2f}")

        # Handle all-in situations with proper EV analysis
        is_facing_all_in = (bet_to_call >= my_stack * 0.9)  # Consider it all-in if calling most of our stack
        
        if is_facing_all_in:
            print(f"DecisionEngine: Facing all-in situation. Hand rank: {numerical_hand_rank}, Win prob: {win_probability:.3f}")
            
            # Calculate EV for calling all-in
            ev_call = self.calculate_expected_value(ACTION_CALL, bet_to_call, pot_size, win_probability, bet_to_call)
            ev_fold = 0.0  # EV of folding is always 0
            
            print(f"DecisionEngine: EV of calling all-in: {ev_call:.2f}, EV of folding: {ev_fold:.2f}")
            
            # Call if EV is positive and we have reasonable equity
            if ev_call > ev_fold and win_probability > 0.3:  # Need at least 30% equity for all-in calls
                return ACTION_CALL, min(my_stack, bet_to_call)
            else:
                return ACTION_FOLD, 0

        # Pre-flop decision making with enhanced logic
        if game_stage == 'Preflop':
            return self._make_preflop_decision(
                my_player, hand_evaluation_tuple, my_hole_cards_str_list, bet_to_call, 
                can_check, pot_size, my_stack, active_opponents_count, win_probability, pot_odds_to_call,
                max_bet_on_table, game_stage, hand_description # Pass hand_description
            )

        # Post-flop decision making with EV calculations
        return self._make_postflop_decision(
            numerical_hand_rank, hand_description, bet_to_call, can_check, 
            pot_size, my_stack, win_probability, pot_odds_to_call, game_stage, spr
        )

    def _make_preflop_decision(self, my_player, hand_evaluation_tuple, my_hole_cards_str_list, 
                              bet_to_call, can_check, pot_size, my_stack, active_opponents_count, 
                              win_probability, pot_odds_to_call, max_bet_on_table, game_stage, hand_description):
        """Enhanced pre-flop decision making"""
        preflop_category = self._get_preflop_hand_category(hand_evaluation_tuple, my_hole_cards_str_list)
        
        num_limpers = 0
        my_investment_this_round = 0
        if my_player:
            player_investment_str = str(my_player.get('bet', '0')).replace('$', '').replace(',', '').replace('€', '')
            try:
                my_investment_this_round = float(player_investment_str)
            except ValueError:
                my_investment_this_round = 0

            # If we are SB or BB, our blind is part of our investment
            if my_player.get('is_sb') and my_investment_this_round < self.small_blind:
                 my_investment_this_round = self.small_blind
            if my_player.get('is_bb') and my_investment_this_round < self.big_blind:
                 my_investment_this_round = self.big_blind

        # Estimate limpers if we are about to act and pot indicates more than blinds + our investment
        # This is a simplification. True limper count requires tracking actions.
        if bet_to_call == 0 or (my_player.get('is_bb') and bet_to_call == 0): # If we can open or check BB
            # Expected pot from blinds if no action yet: SB + BB
            expected_pot_blinds_only = self.small_blind + self.big_blind
            # If current pot is greater than blinds + our own forced bet (if any)
            # This logic is tricky because 'pot_size' includes blinds already.
            # A simpler limper estimation: if pot_size > SB + BB + our_current_bet (if we are not BB)
            # and no one has raised yet (max_bet_on_table is just BB or 0 if we are first to act)
            if max_bet_on_table <= self.big_blind: # No raise yet
                # Amount in pot beyond blinds and our current bet (if we are not a blind)
                excess_in_pot = pot_size - (self.small_blind + self.big_blind)
                if not my_player.get('is_sb') and not my_player.get('is_bb'):
                    excess_in_pot -= my_investment_this_round
                
                if excess_in_pot > 0:
                    num_limpers = int(round(excess_in_pot / self.big_blind))
                num_limpers = max(0, num_limpers)

        # --- Standard Raise Sizing --- #
        if bet_to_call == 0: # We are opening
            open_raise_size = self.big_blind * 3 + (num_limpers * self.big_blind)
            base_raise_size = max(open_raise_size, self.big_blind * 2.5) # Min open 2.5bb
        elif max_bet_on_table > 0 : # Facing a bet/raise, so we are considering a 3-bet or more
            # Standard 3-bet sizing: 3x the previous bet/raise size.
            # If opponent raised to X (max_bet_on_table), we want our total bet to be 3X.
            # The amount to add is 3X - my_current_bet.
            # If my_current_bet is 0, then raise_amount_to_add = 3X.
            # If I posted BB (my_current_bet = BB) and opponent raised to 3BB (max_bet_on_table = 3BB),
            # I need to call 2BB. A 3x raise (to 9BB) means I add 8BB.
            # So, raise_amount = (3 * max_bet_on_table) - my_investment_this_round
            # This is the total size of our bet. The amount to *add* is this minus what we already put in.
            three_bet_total_size = 3 * max_bet_on_table
            base_raise_size = three_bet_total_size
            # Ensure it's at least a valid min-raise (previous bet + size of last raise)
            # Size of last raise = max_bet_on_table - previous_bet_before_that_raise
            # This is complex to get accurately without full history. Simpler: min re-raise is 2x the bet_to_call.
            min_reraise_total = my_investment_this_round + bet_to_call + bet_to_call # Call + raise by at least bet_to_call
            base_raise_size = max(base_raise_size, min_reraise_total)
        else: # Fallback, should ideally not be hit if bet_to_call > 0
            base_raise_size = self.big_blind * 3

        raise_amount = min(base_raise_size * self.base_aggression_factor, my_stack) # Apply aggression
        raise_amount = round(max(raise_amount, self.big_blind * 2), 2) # Ensure at least 2BB and round
        # If facing a bet, ensure our raise_amount (total bet) is at least current_bet + min_raise_increment
        if bet_to_call > 0:
            min_total_after_raise = max_bet_on_table + max(bet_to_call, self.big_blind) # Old: bet_to_call + self.big_blind
            # The raise must be at least the size of the previous bet or raise.
            # If opponent bet X (max_bet_on_table = X), our raise must make our total bet at least 2X.
            min_total_after_raise = max_bet_on_table + max_bet_on_table # Raise to at least 2x the current bet level
            if my_investment_this_round > 0: # If we had a blind or previous bet
                 min_total_after_raise = max_bet_on_table + (max_bet_on_table - my_investment_this_round) 
            min_total_after_raise = max(min_total_after_raise, max_bet_on_table + self.big_blind) # Must be at least BB more

            raise_amount = max(raise_amount, min_total_after_raise)
        raise_amount = round(min(raise_amount, my_stack), 2) # Final cap at stack and round


        print(f"DecisionEngine Preflop: Category: {preflop_category}, WinP: {win_probability:.3f}, BetToCall: {bet_to_call}, CalcRaise: {raise_amount}, MyStack: {my_stack}, Opponents: {active_opponents_count}")

        if preflop_category == "Premium Pair":  # AA, KK, QQ
            if bet_to_call == 0: # Open raising
                return ACTION_RAISE, min(raise_amount * 1.1, my_stack) # Slightly larger for premium
            elif bet_to_call <= my_stack * 0.45:  # Willing to commit up to 45% of stack with premium pairs via 3-bet/call
                ev_call = self.calculate_expected_value(ACTION_CALL, bet_to_call, pot_size, win_probability, bet_to_call)
                # Use the calculated raise_amount for EV_raise, as it's our intended 3-bet size
                ev_raise = self.calculate_expected_value(ACTION_RAISE, raise_amount, pot_size, win_probability)
                
                if ev_raise > ev_call and raise_amount < my_stack * 0.85 : # Prefer to raise if EV is better and not committing most of stack
                    return ACTION_RAISE, raise_amount
                # If EV to raise isn't better, or raise is too large a commitment, consider calling
                elif win_probability > pot_odds_to_call or win_probability > 0.38: # Adjusted win_prob from 0.4
                    return ACTION_CALL, bet_to_call
                else:
                    return ACTION_FOLD # If facing a large bet and EV/equity doesn't support raise/call
            else: # Bet to call is very large (more than 45% of stack)
                if win_probability > pot_odds_to_call or win_probability > 0.45: # Need very good equity for huge calls. Adj from 0.5
                    return ACTION_CALL, bet_to_call 
                return ACTION_FOLD
        
        elif preflop_category in ["Strong Pair", "Suited Ace", "Offsuit Broadway"]:
            # AK, AQs, AJs, KQs, JJ, TT
            # Specific boost for AJ offsuit and KQ offsuit
            is_aj_offsuit = "AJ offsuit" in hand_description
            is_kq_offsuit = "KQ offsuit" in hand_description

            win_prob_threshold_open = 0.33
            win_prob_threshold_call = 0.28
            
            if is_aj_offsuit or is_kq_offsuit:
                win_prob_threshold_open = 0.30 # Be more willing to open AJ/KQo
                win_prob_threshold_call = 0.25 # Be more willing to call with AJ/KQo

            if bet_to_call == 0 and win_probability > win_prob_threshold_open:
                return ACTION_RAISE, raise_amount
            elif bet_to_call > 0 and (win_probability > pot_odds_to_call or win_probability > win_prob_threshold_call):
                # Consider a light 3-bet if facing a small raise and we have position or good equity
                # Adjusted win_probability from 0.40 to 0.37 for 3-bet consideration
                if bet_to_call <= self.big_blind * 4 and win_probability > 0.37 and raise_amount > bet_to_call and raise_amount < my_stack * 0.5:
                    ev_call = self.calculate_expected_value(ACTION_CALL, bet_to_call, pot_size, win_probability, bet_to_call)
                    ev_raise = self.calculate_expected_value(ACTION_RAISE, raise_amount, pot_size, win_probability)
                    if ev_raise > ev_call:
                        return ACTION_RAISE, raise_amount # Ensure 3-bet is returned
                return ACTION_CALL, bet_to_call
            elif can_check:
                return ACTION_CHECK, 0
            else:
                return ACTION_FOLD

        elif preflop_category in ["Playable Broadway", "Medium Pair", "Suited Connector"]:
            # KJs, QJs, JTs, Axs (smaller suited aces), 99-77, T9s, 98s, 87s
            position_factor = 1.0 # Placeholder
            # Adjusted win_probability from 0.20 to 0.18 for opening, and raise_amount from *0.95 to full amount
            if bet_to_call == 0 and win_probability > (0.18 / position_factor) and active_opponents_count <= 4:
                return ACTION_RAISE, raise_amount
            # Adjusted win_probability from 0.18 to 0.16 for calling
            elif bet_to_call > 0 and (win_probability > pot_odds_to_call or win_probability > 0.16):
                # Ensure re-raise logic correctly returns action and amount
                if bet_to_call <= self.big_blind * 3.5 and win_probability > 0.28 and active_opponents_count <= 2 and raise_amount > bet_to_call and raise_amount < my_stack * 0.4:
                    ev_call = self.calculate_expected_value(ACTION_CALL, bet_to_call, pot_size, win_probability, bet_to_call)
                    ev_raise = self.calculate_expected_value(ACTION_RAISE, raise_amount, pot_size, win_probability)
                    if ev_raise > ev_call:
                        return ACTION_RAISE, raise_amount # Ensure re-raise is returned
                return ACTION_CALL, bet_to_call
            elif can_check:
                return ACTION_CHECK, 0
            else:
                return ACTION_FOLD

        else:  # Weak hands
            if can_check:
                return ACTION_CHECK, 0
            is_big_blind_player = my_player.get('is_bb', False)
            if is_big_blind_player and bet_to_call <= self.big_blind * 2.5 and pot_size <= 5 * self.big_blind : # Defend BB vs small raises. Adj bet_to_call from 2BB, pot from 4.5BB
                 if win_probability > 0.16 or pot_odds_to_call < 0.25: # Adj win_prob from 0.18, pot_odds from 0.22
                    return ACTION_CALL, bet_to_call
            elif bet_to_call <= self.big_blind * 1 and pot_odds_to_call < 0.22 and win_probability > 0.18: # Call tiny bets. Adj pot_odds from 0.20, win_prob from 0.20
                return ACTION_CALL, bet_to_call
            else:
                return ACTION_FOLD

    def _make_postflop_decision(self, numerical_hand_rank, hand_description, bet_to_call, can_check, 
                               pot_size, my_stack, win_probability, pot_odds_to_call, game_stage, spr):
        """Post-flop decision making with EV calculations"""
        
        # Calculate optimal bet size for value betting
        value_bet_size = self.get_optimal_bet_size(win_probability, pot_size, my_stack, game_stage, bluff=False)

        # Post-flop decision logic
        # numerical_hand_rank = self.HAND_RANK_STRENGTH.get(hand_description.split(' ')[0], 0) # e.g. "Two Pair" -> 2
        # if 'High Card' in hand_description: numerical_hand_rank = self.HAND_RANK_STRENGTH['High Card']
        # elif 'Pair' in hand_description and 'Two Pair' not in hand_description : numerical_hand_rank = self.HAND_RANK_STRENGTH['One Pair']

        # Calculate pot odds
        pot_odds_to_call = 0
        if pot_size + bet_to_call > 0: # Avoid division by zero
            pot_odds_to_call = bet_to_call / (pot_size + bet_to_call)

        # Estimate fold equity
        # Using opponent models if available
        rates = [m['fold_to_cbet_count']/m['fold_to_cbet_opportunities'] for m in self.opponent_models.values() if m.get('fold_to_cbet_opportunities',0)>0]
        if rates:
            fold_equity_estimate = sum(rates)/len(rates)
        else:
            fold_equity_estimate = self._estimate_fold_equity(value_bet_size, pot_size)
        can_bluff = self.should_bluff(fold_equity_estimate, pot_size, value_bet_size)

        is_draw = any(x in hand_description for x in ("Flush Draw","Straight Draw","Open Ended"))

        # Semi-bluff with strong draws
        if can_check and is_draw and win_probability > 0.30:
            bluff_bet = self.get_optimal_bet_size(win_probability, pot_size, my_stack, game_stage, bluff=True)
            # Ensure bluff_bet is not None and is a valid amount
            if bluff_bet and bluff_bet > 0:
                return ACTION_RAISE, bluff_bet

        # Value bet Two Pair or better on Turn/River
        if game_stage in ['Turn','River'] and numerical_hand_rank >= self.HAND_RANK_STRENGTH['Two Pair']:
            if can_check:
                return ACTION_RAISE, value_bet_size
            if bet_to_call > 0:
                # If facing a bet, call if we have a strong hand, consider raising if very strong or opponent is likely to fold to a re-raise
                # For now, simple call for Two Pair+
                return ACTION_CALL, bet_to_call 
            return ACTION_CHECK, 0 # Should not happen if can_check is false and bet_to_call is 0

        # Logic for One Pair hands, especially Top Pair
        if 'Pair' in hand_description and 'Two Pair' not in hand_description:
            is_top_pair = 'Top Pair' in hand_description # Assuming hand_description includes this detail
            
            if is_top_pair:
                if can_check: # If checked to us
                    if win_probability > 0.5:
                        return ACTION_RAISE, value_bet_size 
                    else:
                        return ACTION_CHECK, 0
                elif bet_to_call > 0: # If facing a bet
                    required_equity = 0
                    if pot_size + bet_to_call + bet_to_call > 0: # Avoid division by zero for required_equity
                        required_equity = bet_to_call / (pot_size + bet_to_call + bet_to_call)
                    
                    if win_probability > required_equity + 0.10: # Adding a margin
                        return ACTION_CALL, bet_to_call
                    elif bet_to_call <= pot_size * 0.5 and win_probability > 0.35: # Call smaller bets with reasonable equity
                        return ACTION_CALL, bet_to_call
                    elif win_probability < 0.25 and bet_to_call > pot_size * 0.75: # Fold if win probability is too low and bet is significant
                        return ACTION_FOLD, 0
                    # Fallback logic if none of the above specific conditions were met:
                    # Be a bit more sticky if the bet isn't too large and we have some showdown value.
                    elif bet_to_call <= pot_size * 0.66 and win_probability > 0.30: # Call medium bets if equity is not terrible
                         return ACTION_CALL, bet_to_call
                    else: # Default to fold if facing a bet and conditions aren't met
                        return ACTION_FOLD, 0
                else: # No bet to call, not checked to us (should not happen in standard poker flow if it's our turn)
                    return ACTION_CHECK, 0

            # Logic for other pairs (Middle Pair, Bottom Pair)
            else: # Not Top Pair
                if can_check:
                    return ACTION_CHECK, 0 # Generally check with weaker pairs if checked to
                elif bet_to_call > 0:
                    required_equity = 0
                    if pot_size + bet_to_call + bet_to_call > 0: # Avoid division by zero
                        required_equity = bet_to_call / (pot_size + bet_to_call + bet_to_call)
                    if win_probability > required_equity + 0.15 and bet_to_call < pot_size * 0.34: # Call small bets with good odds
                        return ACTION_CALL, bet_to_call
                    return ACTION_FOLD, 0
                else:
                    return ACTION_CHECK, 0

        # Fallback for hands not covered by specific logic above (e.g., High Card, weak draws not meeting semi-bluff criteria)
        if can_check:
            print(f"DecisionEngine Postflop: Fallback to CHECK for hand: {hand_description}, WinP: {win_probability:.3f}")
            return ACTION_CHECK, 0
        else:
            # If facing a bet and the hand is very weak (e.g., High Card not caught by other logic)
            # and no other decision was made (call/raise for a draw or made hand)
            print(f"DecisionEngine Postflop: Fallback to FOLD for hand: {hand_description}, WinP: {win_probability:.3f}, BetToCall: {bet_to_call}")
            return ACTION_FOLD, 0
