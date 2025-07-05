#!/usr/bin/env python3
"""
Debug specific scenarios to understand hand strength classification.
"""
import logging
from monte_carlo_solver import MonteCarloSolver
from hand_evaluator import HandEvaluator
from gpu_accelerated_equity import GPUEquityCalculator
from hand_abstraction import HandAbstraction

logging.basicConfig(level=logging.DEBUG)  # Enable debug logging
logger = logging.getLogger(__name__)

def debug_specific_scenarios():
    """Debug specific problematic scenarios."""
    
    # Initialize components
    hand_evaluator = HandEvaluator()
    equity_calculator = GPUEquityCalculator(use_gpu=True)
    abstraction = HandAbstraction(hand_evaluator, equity_calculator)
    solver = MonteCarloSolver(abstraction, hand_evaluator, equity_calculator, logger)
    
    print("🔍 Debugging Specific Monte Carlo Scenarios")
    print("=" * 60)
    
    # Debug scenarios
    debug_scenarios = [
        {
            'name': 'Pocket 99 preflop',
            'hole_cards': ['9♠', '9♥'],
            'community': [],
            'pot': 0.06,
            'actions': ['fold', 'call', 'raise'],
            'stage': 'preflop'
        },
        {
            'name': 'Gut shot missed (JT on A9-7-2-K)',
            'hole_cards': ['J♦', 'T♣'],
            'community': ['A♠', '9♥', '7♦', '2♠', 'K♦'],
            'pot': 0.50,
            'actions': ['check', 'raise'],
            'stage': 'river'
        }
    ]
    
    for scenario in debug_scenarios:
        print(f"\n🃏 Debugging: {scenario['name']}")
        print(f"   Hand: {', '.join(scenario['hole_cards'])}")
        if scenario['community']:
            print(f"   Board: {', '.join(scenario['community'])}")
        
        # Calculate equity to see hand strength classification
        win_prob, _, _ = equity_calculator.calculate_equity_monte_carlo(
            [scenario['hole_cards']], scenario['community'], None, 
            num_simulations=1000, num_opponents=1
        )
        print(f"   Win probability: {win_prob:.3f}")
        
        # Run solver with debug enabled
        strategy = solver.solve(
            scenario['hole_cards'],
            scenario['community'],
            scenario['pot'],
            scenario['actions'],
            scenario['stage'],
            num_opponents=1,
            iterations=50
        )
        
        print(f"   Strategy: {strategy}")
        print("   " + "=" * 50)

if __name__ == "__main__":
    debug_specific_scenarios()
