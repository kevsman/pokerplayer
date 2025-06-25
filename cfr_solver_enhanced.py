"""
CFR solver module for PokerBotV2.
Implements a simple Counterfactual Regret Minimization solver using abstraction.
Enhanced with GPU acceleration support and optimized simulation counts.
"""
import random
import logging
from hand_evaluator import HandEvaluator
from equity_calculator import EquityCalculator
from hand_abstraction import HandAbstraction

# Try to import GPU acceleration
try:
    from gpu_accelerated_equity import GPUEquityCalculator
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

logger = logging.getLogger(__name__)

class CFRSolver:
    def __init__(self, abstraction: 'HandAbstraction', hand_evaluator: HandEvaluator, equity_calculator: EquityCalculator, logger_instance=None, use_gpu=True):
        self.abstraction = abstraction
        self.hand_evaluator = hand_evaluator
        
        # Use GPU equity calculator if available and requested
        if use_gpu and GPU_AVAILABLE:
            try:
                self.equity_calculator = GPUEquityCalculator(use_gpu=True)
                self.gpu_accelerated = True
                if logger_instance:
                    logger_instance.info("CFR Solver initialized with GPU acceleration")
            except Exception as e:
                if logger_instance:
                    logger_instance.warning(f"Failed to initialize GPU acceleration: {e}")
                self.equity_calculator = equity_calculator
                self.gpu_accelerated = False
        else:
            self.equity_calculator = equity_calculator
            self.gpu_accelerated = False
            
        self.logger = logger_instance if logger_instance else logger

    def solve(self, player_hole_cards, community_cards, pot_size, actions, stage, num_opponents=2, iterations=1000):
        """
        A simplified solver that uses Monte Carlo simulation to estimate action values.
        This is not a full CFR implementation but a functional placeholder.
        Enhanced with higher simulation counts and GPU acceleration for better accuracy.
        """
        action_values = {action: 0.0 for action in actions}

        # Use higher simulation counts for better accuracy
        sim_count = 1000 if self.gpu_accelerated else 500

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

            # Estimate equity for each action
            if 'raise' in actions:
                # Simplified: assume opponents fold based on hand strength
                fold_probability = 0.3 + (0.4 * random.random())  # 30-70% fold probability
                if random.random() < fold_probability:
                    action_values['raise'] += pot_size
                else:
                    # Use batch calculation if GPU is available
                    if self.gpu_accelerated and hasattr(self.equity_calculator, 'calculate_equity_batch'):
                        try:
                            equities, _, _ = self.equity_calculator.calculate_equity_batch(
                                [player_hole_cards], community_cards, num_simulations=sim_count
                            )
                            win_prob = equities[0] if equities else 0.5
                        except Exception:
                            # Fallback to regular calculation
                            win_prob, _, _ = self.equity_calculator.calculate_equity_monte_carlo(
                                [player_hole_cards], community_cards, None, 
                                num_simulations=sim_count, num_opponents=len(opponent_hands)
                            )
                    else:
                        win_prob, _, _ = self.equity_calculator.calculate_equity_monte_carlo(
                            [player_hole_cards], community_cards, None, 
                            num_simulations=sim_count, num_opponents=len(opponent_hands)
                        )
                    action_values['raise'] += win_prob * (pot_size * 2)  # Simplified EV

            if 'call' in actions:
                if self.gpu_accelerated and hasattr(self.equity_calculator, 'calculate_equity_batch'):
                    try:
                        equities, _, _ = self.equity_calculator.calculate_equity_batch(
                            [player_hole_cards], community_cards, num_simulations=sim_count
                        )
                        win_prob = equities[0] if equities else 0.5
                    except Exception:
                        win_prob, _, _ = self.equity_calculator.calculate_equity_monte_carlo(
                            [player_hole_cards], community_cards, None, 
                            num_simulations=sim_count, num_opponents=num_opponents
                        )
                else:
                    win_prob, _, _ = self.equity_calculator.calculate_equity_monte_carlo(
                        [player_hole_cards], community_cards, None, 
                        num_simulations=sim_count, num_opponents=num_opponents
                    )
                action_values['call'] += win_prob * pot_size

            if 'check' in actions:
                if self.gpu_accelerated and hasattr(self.equity_calculator, 'calculate_equity_batch'):
                    try:
                        equities, _, _ = self.equity_calculator.calculate_equity_batch(
                            [player_hole_cards], community_cards, num_simulations=sim_count
                        )
                        win_prob = equities[0] if equities else 0.5
                    except Exception:
                        win_prob, _, _ = self.equity_calculator.calculate_equity_monte_carlo(
                            [player_hole_cards], community_cards, None, 
                            num_simulations=sim_count, num_opponents=num_opponents
                        )
                else:
                    win_prob, _, _ = self.equity_calculator.calculate_equity_monte_carlo(
                        [player_hole_cards], community_cards, None, 
                        num_simulations=sim_count, num_opponents=num_opponents
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
