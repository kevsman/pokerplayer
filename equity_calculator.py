import random
from itertools import combinations
from hand_evaluator import HandEvaluator

class EquityCalculator:
    def __init__(self):
        self.hand_evaluator = HandEvaluator()
        self.all_cards = self._generate_deck()
    
    def _generate_deck(self):
        """Generate a standard 52-card deck"""
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        suits = ['♠', '♥', '♦', '♣']
        return [rank + suit for rank in ranks for suit in suits]
    
    def _get_unknown_cards(self, known_cards):
        """Get cards that are not in the known cards list"""
        return [card for card in self.all_cards if card not in known_cards]
    
    def calculate_equity_monte_carlo(self, hero_cards, community_cards, num_opponents=1, simulations=1000):
        """
        Calculate equity using Monte Carlo simulation
        Returns: (win_probability, tie_probability, expected_value_multiplier)
        """
        if not hero_cards or len(hero_cards) != 2:
            return 0.0, 0.0, 0.0
        
        known_cards = hero_cards + community_cards
        unknown_cards = self._get_unknown_cards(known_cards)
        
        wins = 0
        ties = 0
        total_simulations = 0
        
        for _ in range(simulations):
            # Shuffle unknown cards
            random.shuffle(unknown_cards)
            
            # Deal remaining community cards if needed
            cards_needed = 5 - len(community_cards)
            sim_community = community_cards + unknown_cards[:cards_needed]
            remaining_unknown = unknown_cards[cards_needed:]
            
            # Deal opponent cards
            opponent_hands = []
            for i in range(num_opponents):
                if len(remaining_unknown) >= 2:
                    opp_cards = remaining_unknown[i*2:(i+1)*2]
                    opponent_hands.append(opp_cards)
                    
            if len(opponent_hands) != num_opponents:
                continue  # Skip if not enough cards
                
            # Evaluate all hands
            hero_hand = self.hand_evaluator.calculate_best_hand(hero_cards, sim_community)
            opponent_evaluations = []
            for opp_cards in opponent_hands:
                opp_eval = self.hand_evaluator.calculate_best_hand(opp_cards, sim_community)
                opponent_evaluations.append(opp_eval)
            
            # Compare hands
            hero_wins = True
            is_tie = False
            
            for opp_eval in opponent_evaluations:
                comparison = self._compare_hands(hero_hand, opp_eval)
                if comparison < 0:  # Hero loses
                    hero_wins = False
                    break
                elif comparison == 0:  # Tie
                    is_tie = True
            
            if hero_wins and not is_tie:
                wins += 1
            elif hero_wins and is_tie:
                ties += 1
                
            total_simulations += 1
        
        if total_simulations == 0:
            return 0.0, 0.0, 0.0
            
        win_prob = wins / total_simulations
        tie_prob = ties / total_simulations
        
        # Expected value multiplier: full pot for win, half pot for tie
        ev_multiplier = win_prob + (tie_prob * 0.5)
        
        return win_prob, tie_prob, ev_multiplier
    
    def _compare_hands(self, hand1, hand2):
        """
        Compare two hand evaluations
        Returns: 1 if hand1 wins, -1 if hand2 wins, 0 if tie
        """
        if hand1[0] > hand2[0]:  # hand1 has better rank
            return 1
        elif hand1[0] < hand2[0]:  # hand2 has better rank
            return -1
        else:  # Same rank, compare tie breakers
            return self.hand_evaluator._compare_tie_breakers(hand1[2], hand2[2])
    
    def estimate_outs(self, hero_cards, community_cards):
        """
        Estimate the number of outs (cards that improve the hand)
        """
        if len(community_cards) < 3:
            return 0  # Can't estimate outs pre-flop
            
        current_hand = self.hand_evaluator.calculate_best_hand(hero_cards, community_cards)
        known_cards = hero_cards + community_cards
        unknown_cards = self._get_unknown_cards(known_cards)
        
        outs = 0
        cards_to_come = 5 - len(community_cards)
        
        if cards_to_come == 0:
            return 0
            
        # Test each unknown card to see if it improves our hand
        for card in unknown_cards:
            test_community = community_cards + [card]
            if len(test_community) <= 5:
                test_hand = self.hand_evaluator.calculate_best_hand(hero_cards, test_community)
                if self._compare_hands(test_hand, current_hand) > 0:
                    outs += 1
        
        return outs
    
    def calculate_implied_odds(self, pot_size, bet_to_call, estimated_future_winnings):
        """
        Calculate implied odds considering future betting rounds
        """
        if bet_to_call <= 0:
            return float('inf')
            
        total_potential_winnings = pot_size + estimated_future_winnings
        return total_potential_winnings / bet_to_call
    
    def get_hand_strength_percentile(self, hero_cards, community_cards, num_opponents=1):
        """
        Get hand strength as percentile (0.0 to 1.0)
        Higher values indicate stronger hands relative to random opponent hands
        """
        win_prob, _, _ = self.calculate_equity_monte_carlo(
            hero_cards, community_cards, num_opponents, simulations=500
        )
        return win_prob
