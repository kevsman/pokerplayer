#!/usr/bin/env python3
"""
Debug the specific KK scenario that caused the fold.
"""
import logging
from monte_carlo_solver import MonteCarloSolver
from hand_evaluator import HandEvaluator
from gpu_accelerated_equity import GPUEquityCalculator
from hand_abstraction import HandAbstraction

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_kk_fold():
    """Debug the KK fold scenario."""
    
    # Initialize components
    hand_evaluator = HandEvaluator()
    equity_calculator = GPUEquityCalculator(use_gpu=True)
    abstraction = HandAbstraction(hand_evaluator, equity_calculator)
    solver = MonteCarloSolver(abstraction, hand_evaluator, equity_calculator, logger)
    
    print("🔍 Debugging KK Fold Scenario")
    print("=" * 60)
    
    # The exact scenario that caused the fold
    hole_cards = ['K♠', 'K♥']
    community_cards = ['8♠', '5♥', '4♥']
    pot_size = 0.28
    actions = ['fold', 'call', 'raise']
    stage = 'flop'
    num_opponents = 5  # 6 players total - 1 (us) = 5 opponents
    
    print(f"Hand: {hole_cards}")
    print(f"Board: {community_cards}")
    print(f"Pot: {pot_size}")
    print(f"Stage: {stage}")
    print(f"Opponents: {num_opponents}")
    
    # Calculate equity to see what the solver is seeing
    win_prob, tie_prob, lose_prob = equity_calculator.calculate_equity_monte_carlo(
        [hole_cards], community_cards, None, 
        num_simulations=1000, num_opponents=num_opponents
    )
    
    print(f"\nEquity Analysis:")
    print(f"Win probability: {win_prob:.3f}")
    print(f"Tie probability: {tie_prob:.3f}")
    print(f"Lose probability: {lose_prob:.3f}")
    print(f"Total: {win_prob + tie_prob + lose_prob:.3f}")
    
    # Run the solver with debug logging
    print(f"\nRunning Monte Carlo solver...")
    strategy = solver.solve(
        hole_cards,
        community_cards,
        pot_size,
        actions,
        stage,
        num_opponents,
        iterations=25  # Fewer iterations for debugging
    )
    
    print(f"\nResult Strategy: {strategy}")
    
    # Analyze what went wrong
    if win_prob < 0.5:
        print("🚨 PROBLEM: KK has less than 50% equity - this seems wrong!")
    
    if strategy.get('fold', 0) > 0.5:
        print("🚨 PROBLEM: Solver is folding KK more than 50% of the time!")
    
    # Test with fewer opponents to see if that helps
    print(f"\n" + "=" * 40)
    print("Testing with fewer opponents (heads-up):")
    
    win_prob_hu, _, _ = equity_calculator.calculate_equity_monte_carlo(
        [hole_cards], community_cards, None, 
        num_simulations=1000, num_opponents=1
    )
    
    strategy_hu = solver.solve(
        hole_cards,
        community_cards,
        pot_size,
        actions,
        stage,
        1,  # heads-up
        iterations=25
    )
    
    print(f"Heads-up equity: {win_prob_hu:.3f}")
    print(f"Heads-up strategy: {strategy_hu}")

if __name__ == "__main__":
    debug_kk_fold()
