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
        if bluff:
            # Bluff sizes are typically 50-75% of pot
            return min(pot_size * 0.6, stack_size)
            
        # Value betting sizes based on hand strength
        if hand_strength >= 0.85:  # Very strong hands
            return min(pot_size * 0.75, stack_size)  # Large value bet
        elif hand_strength >= 0.7:  # Strong hands  
            return min(pot_size * 0.6, stack_size)  # Medium value bet
        elif hand_strength >= 0.6:  # Medium hands
            return min(pot_size * 0.4, stack_size)  # Small value bet
        else:
            # Weak hands - check or small bet for protection
            return min(pot_size * 0.3, stack_size)
    
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
            return ACTION_FOLD

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
                return ACTION_CALL, min(bet_to_call, my_stack)
            else:
                return ACTION_FOLD

        # Pre-flop decision making with enhanced logic
        if game_stage == 'Preflop':
            return self._make_preflop_decision(
                my_player, hand_evaluation_tuple, my_hole_cards_str_list, bet_to_call, 
                can_check, pot_size, my_stack, active_opponents_count, win_probability, pot_odds_to_call
            )

        # Post-flop decision making with EV calculations
        return self._make_postflop_decision(
            numerical_hand_rank, hand_description, bet_to_call, can_check, 
            pot_size, my_stack, win_probability, pot_odds_to_call, game_stage, spr
        )

    def _make_preflop_decision(self, my_player, hand_evaluation_tuple, my_hole_cards_str_list, 
                              bet_to_call, can_check, pot_size, my_stack, active_opponents_count, 
                              win_probability, pot_odds_to_call):
        """Enhanced pre-flop decision making"""
        preflop_category = self._get_preflop_hand_category(hand_evaluation_tuple, my_hole_cards_str_list)
        
        # Conservative raise sizing
        base_raise_size = max(self.big_blind * 2.5, bet_to_call + self.big_blind)
        raise_amount = min(base_raise_size * self.base_aggression_factor, my_stack)

        print(f"DecisionEngine: Preflop category: {preflop_category}, Win prob: {win_probability:.3f}")

        if preflop_category == "Premium Pair":  # AA, KK, QQ
            if bet_to_call == 0:
                return ACTION_RAISE, min(raise_amount * 1.2, my_stack)
            elif bet_to_call <= my_stack * 0.3:  # Don't commit too much with premium pairs
                ev_call = self.calculate_expected_value(ACTION_CALL, bet_to_call, pot_size, win_probability, bet_to_call)
                ev_raise = self.calculate_expected_value(ACTION_RAISE, raise_amount, pot_size, win_probability)
                
                if ev_raise > ev_call and raise_amount < my_stack:
                    return ACTION_RAISE, min(raise_amount * 1.5, my_stack)
                else:
                    return ACTION_CALL, bet_to_call
            else:
                return ACTION_FOLD  # Don't commit too much even with premium pairs
        
        elif preflop_category in ["Strong Pair", "Suited Ace", "Offsuit Broadway", "Playable Broadway"]:
            if bet_to_call == 0 and win_probability > 0.4:  # More reasonable threshold
                return ACTION_RAISE, raise_amount
            elif bet_to_call > 0 and (pot_odds_to_call < 0.25 or win_probability > 0.25):  # More aggressive calling conditions - lowered from 0.35
                return ACTION_CALL, bet_to_call
            elif can_check:
                return ACTION_CHECK, 0
            else:
                return ACTION_FOLD

        elif preflop_category in ["Medium Pair", "Suited Connector"]:
            # Play more aggressively with speculative hands
            if bet_to_call == 0 and active_opponents_count <= 4:  # Increased from 3 to be more aggressive
                return ACTION_RAISE, raise_amount * 0.9  # Increased from 0.8
            elif bet_to_call > 0 and (pot_odds_to_call < 0.25 or win_probability > 0.25):  # More aggressive - lowered from 0.3
                return ACTION_CALL, bet_to_call
            elif can_check:
                return ACTION_CHECK, 0
            else:
                return ACTION_FOLD

        else:  # Weak hands
            if can_check:
                return ACTION_CHECK, 0
            elif bet_to_call <= self.big_blind * 0.5 and pot_odds_to_call > 0.33:
                return ACTION_CALL, bet_to_call  # Defend with good odds
            else:
                return ACTION_FOLD

    def _make_postflop_decision(self, numerical_hand_rank, hand_description, bet_to_call, 
                               can_check, pot_size, my_stack, win_probability, pot_odds_to_call, 
                               game_stage, spr):
        """Enhanced post-flop decision making with proper EV calculations"""
        
        # Calculate different action EVs
        ev_fold = 0.0
        ev_check = win_probability * pot_size if can_check else float('-inf')
        ev_call = self.calculate_expected_value(ACTION_CALL, bet_to_call, pot_size, win_probability, bet_to_call) if bet_to_call > 0 else float('-inf')
        
        # Determine optimal bet size for value betting or bluffing
        optimal_bet = self.get_optimal_bet_size(win_probability, pot_size, my_stack, game_stage)
        ev_raise = self.calculate_expected_value(ACTION_RAISE, optimal_bet, pot_size, win_probability) if optimal_bet > 0 else float('-inf')

        print(f"DecisionEngine: Hand rank: {numerical_hand_rank}, Win prob: {win_probability:.3f}")
        print(f"DecisionEngine: EV - Fold: {ev_fold:.2f}, Check: {ev_check:.2f}, Call: {ev_call:.2f}, Raise: {ev_raise:.2f}")

        # Strong hands (Straight or better)
        if numerical_hand_rank >= 5:
            if bet_to_call == 0:
                return ACTION_RAISE, min(optimal_bet, my_stack)
            elif ev_raise > ev_call and optimal_bet < my_stack * 0.8:
                return ACTION_RAISE, min(optimal_bet, my_stack)
            else:
                return ACTION_CALL, bet_to_call

        # Medium strength hands (Two Pair, Three of a Kind)  
        elif numerical_hand_rank >= 3:
            if bet_to_call == 0 and win_probability > 0.7:
                return ACTION_RAISE, min(optimal_bet * 0.8, my_stack)
            elif bet_to_call > 0:
                if pot_odds_to_call < win_probability * 0.8:  # Need better than fair odds
                    return ACTION_CALL, bet_to_call
                else:
                    return ACTION_FOLD
            else:
                return ACTION_CHECK, 0

        # One pair
        elif numerical_hand_rank == 2:
            has_draw = "Draw" in hand_description
            
            if bet_to_call == 0:
                if win_probability > 0.6:
                    return ACTION_RAISE, min(optimal_bet * 0.6, my_stack)
                else:
                    return ACTION_CHECK, 0
            elif has_draw and pot_odds_to_call < 0.25:  # Good odds for draws
                return ACTION_CALL, bet_to_call
            elif not has_draw and pot_odds_to_call < 0.3 and win_probability > 0.5:
                return ACTION_CALL, bet_to_call
            else:
                return ACTION_FOLD

        # Draws and weak hands
        else:
            has_draw = "Draw" in hand_description
            
            if has_draw and bet_to_call == 0 and game_stage != 'River':
                # Semi-bluff with draws
                bluff_profitable = self.should_bluff(0.3, pot_size, optimal_bet * 0.5)
                if bluff_profitable:
                    return ACTION_RAISE, min(optimal_bet * 0.5, my_stack)
                else:
                    return ACTION_CHECK, 0
            elif has_draw and bet_to_call > 0 and pot_odds_to_call < 0.25:
                return ACTION_CALL, bet_to_call
            elif can_check:
                return ACTION_CHECK, 0
            else:
                return ACTION_FOLD

        # Default to most profitable action
        best_ev = max(ev_fold, ev_check, ev_call, ev_raise)
        if best_ev == ev_raise and optimal_bet > 0:
            return ACTION_RAISE, min(optimal_bet, my_stack)
        elif best_ev == ev_call and bet_to_call > 0:
            return ACTION_CALL, bet_to_call
        elif best_ev == ev_check and can_check:
            return ACTION_CHECK, 0
        else:
            return ACTION_FOLD


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
                        return (ACTION_CHECK, 0) if can_check else (ACTION_FOLD, 0)
                elif bet_to_call <= self.big_blind * 4 * aggression_factor and (pot_odds_to_call < 0.25 or win_probability > 0.25): # Call raises with good odds or win probability
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
                elif bet_to_call <= self.big_blind * 4 * aggression_factor and (pot_odds_to_call < 0.25 or win_probability > 0.25): # Call raises for set value with good odds
                    print(f"DecisionEngine: Medium Pair, calling raise of {bet_to_call} for set value.")
                    return ACTION_CALL, bet_to_call
                else:
                    print(f"DecisionEngine: Medium Pair, folding to raise of {bet_to_call}")
                    return ACTION_FOLD, 0
            
            elif preflop_category == "Playable Broadway": # Single broadway card, not covered above
                if bet_to_call == 0: # Unopened pot
                    if position in ['Late', 'Blinds'] or limpers < 2: # Open from late, blinds, or vs few limpers
                        raise_amount = preferred_raise_amount * 0.9 # Standard open size for these hands
                        print(f"DecisionEngine: Playable Broadway ({hand_description}), opening to {raise_amount}")
                        return ACTION_RAISE, min(my_stack, raise_amount)
                    elif position == 'Middle' and limpers < 1: # Consider opening from middle if no limpers
                        raise_amount = preferred_raise_amount * 0.8
                        print(f"DecisionEngine: Playable Broadway ({hand_description}), Middle position open to {raise_amount}")
                        return ACTION_RAISE, min(my_stack, raise_amount)
                    else:
                        print(f"DecisionEngine: Playable Broadway ({hand_description}) from {position} with {limpers} limpers, checking/folding.")
                        return ACTION_CHECK if can_check else ACTION_FOLD, 0
                # Facing a bet
                elif bet_to_call <= self.big_blind * 3.5 * aggression_factor : # Call small to moderate raises
                    # Consider position and pot odds more carefully
                    if position in ['Blinds'] and pot_odds_to_call > 0.25: # Defend blinds more liberally
                        print(f"DecisionEngine: Playable Broadway ({hand_description}), defending blind vs raise {bet_to_call}")
                        return ACTION_CALL, bet_to_call
                    elif position in ['Late', 'Middle'] and pot_odds_to_call > 0.20 and bet_to_call <= self.big_blind * 3 * aggression_factor :
                         print(f"DecisionEngine: Playable Broadway ({hand_description}), calling raise {bet_to_call} in position with odds.")
                         return ACTION_CALL, bet_to_call
                    elif bet_to_call <= self.big_blind * 2 * aggression_factor: # Call very small raises generally
                        print(f"DecisionEngine: Playable Broadway ({hand_description}), calling small raise {bet_to_call}")
                        return ACTION_CALL, bet_to_call
                    else:
                        print(f"DecisionEngine: Playable Broadway ({hand_description}), folding to raise {bet_to_call} - conditions not met.")
                        return ACTION_FOLD, 0
                else: # Facing a larger bet
                    print(f"DecisionEngine: Playable Broadway ({hand_description}), folding to larger raise of {bet_to_call}.")
                    return ACTION_FOLD, 0
            
            elif preflop_category == "Weak": # Weak hands
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

        elif numerical_hand_rank >= 5: # Straight or Flush
            if bet_to_call == 0:
                value_bet_amount = round(pot_size * 0.7, 2) # Bet 70% of pot
                value_bet_amount = max(self.big_blind, value_bet_amount)
                value_bet_amount = min(value_bet_amount, my_stack)
                if value_bet_amount > 0:
                    print(f"DecisionEngine: Straight/Flush ({hand_description}), betting {value_bet_amount} for value.")
                    return ACTION_RAISE, value_bet_amount
                else:
                    print(f"DecisionEngine: Straight/Flush ({hand_description}), pot/bet is 0, checking.")
                    return ACTION_CHECK, 0
            else: # Facing a bet
                # With a made straight or flush, usually call or raise.
                # This assumes not an all-in situation, which is handled earlier.
                raise_amount = max(min_raise_amount, round(bet_to_call * 2.5 + pot_size, 2)) # Pot-sized raise over current pot + call
                raise_amount = min(raise_amount, my_stack)

                if bet_to_call < pot_size * 0.75 and raise_amount > bet_to_call and raise_amount > 0: # If facing a reasonable bet, consider raising
                    print(f"DecisionEngine: Straight/Flush ({hand_description}), raising bet {bet_to_call} to {raise_amount}.")
                    return ACTION_RAISE, raise_amount
                elif bet_to_call < my_stack : # Call if bet is not an overbet all-in (that we didn't already decide to call)
                    print(f"DecisionEngine: Straight/Flush ({hand_description}), calling bet {bet_to_call}.")
                    return ACTION_CALL, bet_to_call
                else: 
                    # If is_facing_effective_all_in was true, it's handled. This is for large bets not quite all-in.
                    print(f"DecisionEngine: Straight/Flush ({hand_description}), calling large bet {bet_to_call} (or was already handled by all-in).")
                    return ACTION_CALL, bet_to_call # Default to call if very strong and not folding to all-in

        elif numerical_hand_rank >= 3: # Two Pair or Three of a Kind (numerical_hand_rank 3 or 4)
                                       # Assumes not an all-in situation we must call (handled by earlier is_facing_effective_all_in logic)
            if bet_to_call == 0:
                value_bet_amount = round(pot_size * 0.6, 2) # Bet 60% of pot
                value_bet_amount = max(self.big_blind, value_bet_amount)
                value_bet_amount = min(value_bet_amount, my_stack)
                if value_bet_amount > 0:
                    print(f"DecisionEngine: Two Pair/Three of a Kind ({hand_description}), betting {value_bet_amount} for value.")
                    return ACTION_RAISE, value_bet_amount
                else:
                    print(f"DecisionEngine: Two Pair/Three of a Kind ({hand_description}), pot/bet is 0, checking.")
                    return ACTION_CHECK, 0
            else: # Facing a bet
                raise_amount = max(min_raise_amount, round(bet_to_call * 2.5 + pot_size, 2))
                raise_amount = min(raise_amount, my_stack)

                if numerical_hand_rank == 4: # Three of a Kind
                    # Trips are strong, usually raise or call. All-in calls handled earlier.
                    if raise_amount > bet_to_call and bet_to_call < my_stack * 0.5 and raise_amount > 0 : # Don't raise into a huge bet if raise is small part of stack
                        print(f"DecisionEngine: Three of a Kind ({hand_description}), raising bet {bet_to_call} to {raise_amount}.")
                        return ACTION_RAISE, raise_amount
                    else:
                        print(f"DecisionEngine: Three of a Kind ({hand_description}), calling bet {bet_to_call}.")
                        return ACTION_CALL, bet_to_call
                else: # Two Pair (numerical_hand_rank == 3)
                    if bet_to_call < pot_size * 0.5 and raise_amount > bet_to_call and raise_amount > 0: # Facing a smaller bet, raise
                        print(f"DecisionEngine: Two Pair ({hand_description}), raising small bet {bet_to_call} to {raise_amount}.")
                        return ACTION_RAISE, raise_amount
                    elif pot_odds_to_call > 0.20 or bet_to_call <= pot_size * 0.75 : # Call reasonable bets
                        print(f"DecisionEngine: Two Pair ({hand_description}), calling bet {bet_to_call} with pot odds {pot_odds_to_call:.2f}.")
                        return ACTION_CALL, bet_to_call
                    else:
                        print(f"DecisionEngine: Two Pair ({hand_description}), folding to large bet {bet_to_call} with pot odds {pot_odds_to_call:.2f}.")
                        return ACTION_FOLD, 0

        elif numerical_hand_rank == 2: # One Pair
            is_flush_draw = "Flush Draw" in hand_description
            is_straight_draw = "Straight Draw" in hand_description 
            has_significant_draw = (is_flush_draw or is_straight_draw) and game_stage != 'River'

            if bet_to_call == 0: 
                if game_stage in ['Turn', 'River'] and pot_size > 0:
                    value_bet_amount = round(pot_size * 0.33, 2)
                    value_bet_amount = max(self.big_blind, value_bet_amount)
                    value_bet_amount = min(value_bet_amount, my_stack)
                    if value_bet_amount > 0:
                        print(f"DecisionEngine: One Pair ({hand_description}), betting {value_bet_amount} for value/protection on {game_stage}.")
                        return ACTION_RAISE, value_bet_amount
                    else:
                        print(f"DecisionEngine: One Pair ({hand_description}), calculated bet 0, checking on {game_stage}.")
                        return ACTION_CHECK, 0
                else: 
                    print(f"DecisionEngine: One Pair ({hand_description}), checking on {game_stage} when checked to.")
                    return ACTION_CHECK, 0
            else: # Facing a bet
                if has_significant_draw:
                    # Combined odds for pair + draw. Let's use a threshold like 22-25% pot odds.
                    # A pair + 9-out flush draw has good equity.
                    if pot_odds_to_call > 0.22: # Threshold for calling with pair + good draw
                        print(f"DecisionEngine: One Pair with Draw ({hand_description}), calling bet {bet_to_call} with pot odds {pot_odds_to_call:.2f} (met >0.22).")
                        return ACTION_CALL, bet_to_call
                    else:
                        print(f"DecisionEngine: One Pair with Draw ({hand_description}), folding bet {bet_to_call}. Pot odds {pot_odds_to_call:.2f} (needed >0.22).")
                        return ACTION_FOLD, 0
                else: # Just a pair
                    if pot_odds_to_call > 0.25: 
                        print(f"DecisionEngine: One Pair ({hand_description}), calling bet {bet_to_call} with pot odds {pot_odds_to_call:.2f} (met >0.25).")
                        return ACTION_CALL, bet_to_call
                    elif pot_odds_to_call > 0.20 and pot_size > 0 and bet_to_call < (pot_size / 3): # Call small bets with slightly worse odds
                        print(f"DecisionEngine: One Pair ({hand_description}), calling small bet {bet_to_call} ({(bet_to_call/pot_size*100) if pot_size > 0 else 0:.0f}% of pot) with pot odds {pot_odds_to_call:.2f} (met >0.20).")
                        return ACTION_CALL, bet_to_call
                    else:
                        print(f"DecisionEngine: One Pair ({hand_description}), folding bet {bet_to_call}. Pot odds {pot_odds_to_call:.2f} not sufficient.")
                        return ACTION_FOLD, 0
        
        else: # High Card (rank 1) or No Made Hand (rank 0)
            is_significant_draw = ("Flush Draw" in hand_description or "Straight Draw" in hand_description) and game_stage != 'River'
            
            if is_significant_draw:
                if bet_to_call == 0: 
                    if game_stage in ['Flop', 'Turn'] and pot_size > 0:
                        semibluff_amount = round(pot_size * 0.5, 2) # Semi-bluff 1/2 pot
                        semibluff_amount = max(self.big_blind, semibluff_amount)
                        semibluff_amount = min(semibluff_amount, my_stack)
                        if semibluff_amount > 0:
                             print(f"DecisionEngine: Draw ({hand_description}), semi-bluffing {semibluff_amount} on {game_stage}.")
                             return ACTION_RAISE, semibluff_amount
                        else:
                             print(f"DecisionEngine: Draw ({hand_description}), calculated semi-bluff 0, checking.")
                             return ACTION_CHECK, 0
                    else: 
                        print(f"DecisionEngine: Draw ({hand_description}), checking on {game_stage}.")
                        return ACTION_CHECK, 0
                else: # Facing a bet with a draw
                    required_odds_for_draw = 0.25 # Default, can be adjusted
                    if "Flush Draw" in hand_description: required_odds_for_draw = 0.20 # ~9 outs
                    elif "Straight Draw" in hand_description: required_odds_for_draw = 0.20 # ~8 outs OESD

                    if pot_odds_to_call > required_odds_for_draw:
                        print(f"DecisionEngine: Draw ({hand_description}), calling bet {bet_to_call} with pot odds {pot_odds_to_call:.2f} (req > {required_odds_for_draw:.2f}).")
                        return ACTION_CALL, bet_to_call
                    else:
                        print(f"DecisionEngine: Draw ({hand_description}), folding bet {bet_to_call}, pot odds {pot_odds_to_call:.2f} (req > {required_odds_for_draw:.2f}).")
                        return ACTION_FOLD, 0
            elif can_check: 
                print(f"DecisionEngine: High Card/No Hand ({hand_description}), checking.")
                return ACTION_CHECK, 0
            else: 
                print(f"DecisionEngine: High Card/No Hand ({hand_description}), folding to bet {bet_to_call}.")
                return ACTION_FOLD, 0

        return ACTION_FOLD # Default fallback action
