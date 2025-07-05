#!/usr/bin/env python3
"""
Debug script to check equity calculation for the missed draw scenario.
"""
import logging
from monte_carlo_solver import MonteCarloSolver
from hand_evaluator import HandEvaluator
from gpu_accelerated_equity import GPUEquityCalculator
from hand_abstraction import HandAbstraction

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_missed_draw():
    """Debug the missed draw scenario."""
    
    # Initialize components
    hand_evaluator = HandEvaluator()
    equity_calculator = GPUEquityCalculator(use_gpu=True)
    abstraction = HandAbstraction(hand_evaluator, equity_calculator)
    solver = MonteCarloSolver(abstraction, hand_evaluator, equity_calculator, logger)
    
    print("🔍 Debugging Missed Draw Scenario")
    print("=" * 50)
    
    hole_cards = ['A♠', 'K♠']
    community = ['2♥', '7♦', 'Q♣', '3♥', '9♦']
    
    # Check equity directly
    win_prob, _, _ = equity_calculator.calculate_equity_monte_carlo(
        [hole_cards], community, None, 
        num_simulations=1000, num_opponents=1
    )
    
    print(f"Hand: {', '.join(hole_cards)}")
    print(f"Board: {', '.join(community)}")
    print(f"Equity: {win_prob:.1%}")
    
    # Determine hand strength classification
    if win_prob >= 0.85:
        hand_strength = "nuts"
    elif win_prob >= 0.70:
        hand_strength = "strong"
    elif win_prob >= 0.45:
        hand_strength = "medium"
    elif win_prob >= 0.20:
        hand_strength = "weak"
    else:
        hand_strength = "trash"
    
    print(f"Hand strength: {hand_strength}")
    
    # Test solver
    strategy = solver.solve(hole_cards, community, 0.50, ['check', 'raise'], 'river', num_opponents=1, iterations=50)
    print(f"Strategy: {strategy}")

if __name__ == "__main__":
    debug_missed_draw()
