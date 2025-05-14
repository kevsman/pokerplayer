\
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

    def make_decision(self, my_player, table_data, all_players_data):
        if not my_player or not my_player.get('has_turn'):
            return "Not my turn or player data missing."

        # Basic information for decision making
        hand_rank_info = my_player.get('hand_rank', "N/A") # This is a string description
        # For more advanced logic, we'd want the structured hand evaluation 
        # (e.g., (rank_value, description, tie_breaker_ranks)) from HandEvaluator.
        # This would require PokerBot to store and pass this richer info.

        pot_size_str = table_data.get('pot_size', "0").replace('$', '').replace(',', '')
        try:
            pot_size = float(pot_size_str)
        except ValueError:
            pot_size = 0.0
        
        # Determine current bet to call
        max_bet_on_table = 0.0
        for p in all_players_data:
            if not p.get('is_my_player'):
                try:
                    player_bet = float(p.get('bet', '0').replace('$', '').replace(',', ''))
                    if player_bet > max_bet_on_table:
                        max_bet_on_table = player_bet
                except ValueError:
                    pass 
        
        my_current_bet_str = my_player.get('bet', '0').replace('$', '').replace(',', '')
        try:
            my_current_bet = float(my_current_bet_str)
        except ValueError:
            my_current_bet = 0.0
            
        bet_to_call = max_bet_on_table - my_current_bet
        bet_to_call = round(max(0, bet_to_call), 2) # Cannot be negative, round to 2 decimal places

        # Basic strategy (very simplified)
        game_stage = table_data.get('game_stage')

        # Pre-flop strategy
        if game_stage == 'Preflop':
            # Example: Strong starting hands
            if "Pair" in hand_rank_info or "A" in hand_rank_info or "K" in hand_rank_info: 
                if bet_to_call == 0:
                    return ACTION_RAISE, round(self.big_blind * 3, 2)
                elif bet_to_call <= self.big_blind * 4:
                    return ACTION_CALL, bet_to_call
                else:
                    return ACTION_FOLD
            elif bet_to_call == 0: # Can check if no bet
                return ACTION_CHECK
            else: # Fold if there's a bet and hand is not strong
                return ACTION_FOLD

        # Post-flop strategy (example)
        # This part ideally uses numerical hand rank from HandEvaluator for better logic.
        # Current `hand_rank_info` is a string like "Two Pair, Ks and Qs".
        
        # Simplified strength assessment based on string description
        is_strong_hand = False
        strong_keywords = [
            "Two Pair", "Three of a Kind", "Straight", "Flush", 
            "Full House", "Four of a Kind", "Royal Flush", "Straight Flush"
        ]
        if any(keyword in hand_rank_info for keyword in strong_keywords):
            is_strong_hand = True
        
        is_decent_hand = "One Pair" in hand_rank_info

        if is_strong_hand:
            if bet_to_call == 0:
                return ACTION_RAISE, round(pot_size * 0.5, 2) # Bet half pot
            else:
                # Consider re-raise logic here if hand is very strong
                return ACTION_CALL, bet_to_call 
        elif is_decent_hand: # One Pair
            if bet_to_call == 0:
                return ACTION_CHECK
            elif bet_to_call <= pot_size * 0.25: # Call small bets
                return ACTION_CALL, bet_to_call
            else:
                return ACTION_FOLD
        else: # High card or worse
            if bet_to_call == 0:
                return ACTION_CHECK
            else: # Fold to any bet if hand is weak
                return ACTION_FOLD

        return ACTION_FOLD # Default action
