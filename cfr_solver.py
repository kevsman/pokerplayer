"""
CFR solver module for PokerBotV2.
Implements simple Counterfactual Regret Minimization solver using abstraction.
"""
import random
import logging
from hand_evaluator import HandEvaluator
from equity_calculator import EquityCalculator
from hand_abstraction import HandAbstraction

logger = logging.getLogger(__name__)

class CFRSolver:
    def __init__(self, abstraction: 'HandAbstraction', hand_evaluator: HandEvaluator, equity_calculator: EquityCalculator, logger_instance=None):
        self.abstraction = abstraction
        self.hand_evaluator = hand_evaluator
        self.equity_calculator = equity_calculator
        self.logger = logger_instance if logger_instance else logger

    def solve(self, player_hole_cards, community_cards, pot_size, actions, stage, num_opponents=2, iterations=500):
        """
        A simplified solver that uses Monte Carlo simulation to estimate action values.
        This is not a full CFR implementation but a functional placeholder.
        Enhanced with higher simulation counts for better accuracy.
        """
        action_values = {action: 0.0 for action in actions}

        for _ in range(iterations):
            # Simulate multiple opponent hands
            opponent_hands = []
            deck = self.equity_calculator.all_cards[:]
            deck = [c for c in deck if c not in player_hole_cards and c not in community_cards]
            
            # Deal 2 cards to each opponent
            for _ in range(num_opponents):  # Use actual number of opponents
                if len(deck) >= 2:
                    opponent_hand = random.sample(deck, 2)
                    opponent_hands.append(opponent_hand)
                    deck = [c for c in deck if c not in opponent_hand]

            # Estimate equity for each action with proper poker logic
            if 'raise' in actions:
                # Calculate win probability first
                win_prob, _, _ = self.equity_calculator.calculate_equity_monte_carlo(
                    [player_hole_cards], community_cards, None, 
                    num_simulations=500, num_opponents=len(opponent_hands)
                )
                
                # Model opponent response based on hand strength and pot odds
                pot_odds = pot_size / (pot_size * 2)  # Simplified pot odds after raise
                
                # Strong hands (>70% equity) should raise aggressively
                if win_prob > 0.7:
                    fold_probability = 0.6 + (0.3 * random.random())  # 60-90% fold
                # Medium hands (40-70% equity) get some folds
                elif win_prob > 0.4:
                    fold_probability = 0.3 + (0.4 * random.random())  # 30-70% fold
                # Weak hands (<40% equity) get fewer folds
                else:
                    fold_probability = 0.1 + (0.3 * random.random())  # 10-40% fold
                
                if random.random() < fold_probability:
                    action_values['raise'] += pot_size  # Win current pot
                else:
                    # They call/re-raise, we need to win at showdown
                    action_values['raise'] += win_prob * (pot_size * 2) - pot_size  # Account for our bet

            if 'call' in actions:
                win_prob, _, _ = self.equity_calculator.calculate_equity_monte_carlo(
                    [player_hole_cards], community_cards, None, num_simulations=500, num_opponents=len(opponent_hands)
                )
                action_values['call'] += win_prob * pot_size

            if 'check' in actions:
                win_prob, _, _ = self.equity_calculator.calculate_equity_monte_carlo(
                    [player_hole_cards], community_cards, None, num_simulations=500, num_opponents=len(opponent_hands)
                )
                action_values['check'] += win_prob * pot_size

            # Fold has an EV of 0, so we don't add to it.

        # Normalize values to get a strategy distribution
        total_value = sum(action_values.values())
        if total_value == 0:
            # If all actions have 0 value (e.g., only fold is possible or all sims lose),
            # prefer checking over folding. If we can't check and have no equity, fold.
            strategy = {action: 0.0 for action in actions}
            if 'check' in actions:
                strategy['check'] = 1.0
            elif 'fold' in actions:
                strategy['fold'] = 1.0
            else:  # Should not happen if fold is always an option
                strategy[actions[0]] = 1.0
            self.logger.debug(f"CFR Solver calculated strategy (zero total value): {strategy}")
            return strategy

        strategy = {action: value / total_value for action, value in action_values.items()}
        self.logger.debug(f"CFR Solver calculated strategy: {strategy}")
        return strategy
