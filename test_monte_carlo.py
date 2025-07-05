#!/usr/bin/env python3
"""
Test script for the Monte Carlo solver t        # Run solver
        stage = 'preflop' if not scenario['community'] else ('flop' if len(scenario['community']) == 3 else ('turn' if len(scenario['community']) == 4 else 'river'))
        strategy = solver.solve(
            scenario['hole_cards'],
            scenario['community'],
            scenario['pot'],
            scenario['actions'],
            stage,  # Pass the correct stage
            num_opponents=1,
            iterations=50
        )t makes reasonable decisions.
"""
import logging
from monte_carlo_solver import MonteCarloSolver
from hand_evaluator import HandEvaluator
from gpu_accelerated_equity import GPUEquityCalculator
from hand_abstraction import HandAbstraction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_monte_carlo_solver():
    """Test the Monte Carlo solver with various scenarios."""
    
    # Initialize components
    hand_evaluator = HandEvaluator()
    equity_calculator = GPUEquityCalculator(use_gpu=True)
    abstraction = HandAbstraction(hand_evaluator, equity_calculator)
    solver = MonteCarloSolver(abstraction, hand_evaluator, equity_calculator, logger)
    
    print("🎲 Testing Monte Carlo Solver Decision Quality")
    print("=" * 60)
    
    # Test scenarios
    test_scenarios = [
        {
            'name': 'AA Preflop',
            'hole_cards': ['A♠', 'A♥'],
            'community': [],
            'pot': 0.06,
            'actions': ['fold', 'call', 'raise'],
            'expected': 'Strong hand should mostly raise'
        },
        {
            'name': '72o Preflop (worst hand)',
            'hole_cards': ['7♦', '2♣'],
            'community': [],
            'pot': 0.06,
            'actions': ['fold', 'call', 'raise'],
            'expected': 'Weak hand should mostly fold'
        },
        {
            'name': 'Set on dry board',
            'hole_cards': ['8♦', '8♣'],
            'community': ['8♠', '2♥', '4♦'],
            'pot': 0.12,
            'actions': ['check', 'raise'],
            'expected': 'Very strong hand should mostly raise'
        },
        {
            'name': 'Missed draw on river',
            'hole_cards': ['A♠', 'K♠'],
            'community': ['2♥', '7♦', 'Q♣', '3♥', '9♦'],
            'pot': 0.50,
            'actions': ['check', 'raise'],
            'stage': 'river',
            'expected': 'Missed draw should mostly check'
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n🃏 {scenario['name']}")
        print(f"   Hand: {', '.join(scenario['hole_cards'])}")
        if scenario['community']:
            print(f"   Board: {', '.join(scenario['community'])}")
        print(f"   Expected: {scenario['expected']}")
        
        # Run solver
        strategy = solver.solve(
            scenario['hole_cards'],
            scenario['community'],
            scenario['pot'],
            scenario['actions'],
            scenario.get('stage', 'preflop' if not scenario['community'] else 'flop'),
            num_opponents=1,
            iterations=50
        )
        
        # Check if probabilities sum to 1.0
        total_prob = sum(strategy.values())
        print(f"   Strategy: {strategy}")
        print(f"   Total probability: {total_prob:.3f}")
        
        # Analyze strategy quality
        if 'raise' in strategy and 'fold' in strategy:
            raise_ratio = strategy['raise'] / (strategy['raise'] + strategy['fold'])
            print(f"   Raise/(Raise+Fold) ratio: {raise_ratio:.2f}")
        
        print("   " + "=" * 50)

if __name__ == "__main__":
    test_monte_carlo_solver()
