#!/usr/bin/env python3
"""
Extended test script for the Monte Carlo solver with more scenarios.
"""
import logging
from monte_carlo_solver import MonteCarloSolver
from hand_evaluator import HandEvaluator
from gpu_accelerated_equity import GPUEquityCalculator
from hand_abstraction import HandAbstraction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_extended_scenarios():
    """Test the Monte Carlo solver with additional edge case scenarios."""
    
    # Initialize components
    hand_evaluator = HandEvaluator()
    equity_calculator = GPUEquityCalculator(use_gpu=True)
    abstraction = HandAbstraction(hand_evaluator, equity_calculator)
    solver = MonteCarloSolver(abstraction, hand_evaluator, equity_calculator, logger)
    
    print("🎲 Extended Monte Carlo Solver Testing")
    print("=" * 60)
    
    # Additional test scenarios
    test_scenarios = [
        {
            'name': 'Medium pair preflop (99)',
            'hole_cards': ['9♠', '9♥'],
            'community': [],
            'pot': 0.06,
            'actions': ['fold', 'call', 'raise'],
            'expected': 'Strong preflop hand - should mostly raise'
        },
        {
            'name': 'Suited connectors preflop (8♠7♠)',
            'hole_cards': ['8♠', '7♠'],
            'community': [],
            'pot': 0.06,
            'actions': ['fold', 'call', 'raise'],
            'expected': 'Speculative hand - mix of fold/call'
        },
        {
            'name': 'Top pair weak kicker',
            'hole_cards': ['A♦', '3♣'],
            'community': ['A♠', '8♥', '5♦'],
            'pot': 0.12,
            'actions': ['check', 'raise'],
            'expected': 'Decent but vulnerable - mix of check/raise'
        },
        {
            'name': 'Flush draw on turn',
            'hole_cards': ['K♠', 'Q♠'],
            'community': ['A♠', '7♠', '2♥', '9♦'],
            'pot': 0.30,
            'actions': ['check', 'raise'],
            'expected': 'Strong draw - often raise for equity'
        },
        {
            'name': 'Gut shot on river (missed)',
            'hole_cards': ['J♦', 'T♣'],
            'community': ['A♠', '9♥', '7♦', '2♠', 'K♦'],
            'pot': 0.50,
            'actions': ['check', 'raise'],
            'stage': 'river',
            'expected': 'Missed draw - should mostly check'
        },
        {
            'name': 'Two pair on river',
            'hole_cards': ['A♦', '8♣'],
            'community': ['A♠', '8♥', '2♦', '5♠', 'K♦'],
            'pot': 0.50,
            'actions': ['check', 'raise'],
            'stage': 'river',
            'expected': 'Strong hand - should often raise'
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n🃏 {scenario['name']}")
        print(f"   Hand: {', '.join(scenario['hole_cards'])}")
        if scenario['community']:
            print(f"   Board: {', '.join(scenario['community'])}")
        print(f"   Expected: {scenario['expected']}")
        
        # Determine stage automatically if not specified
        stage = scenario.get('stage')
        if not stage:
            if not scenario['community']:
                stage = 'preflop'
            elif len(scenario['community']) == 3:
                stage = 'flop'
            elif len(scenario['community']) == 4:
                stage = 'turn'
            else:
                stage = 'river'
        
        # Run solver
        strategy = solver.solve(
            scenario['hole_cards'],
            scenario['community'],
            scenario['pot'],
            scenario['actions'],
            stage,
            num_opponents=1,
            iterations=100  # More iterations for extended test
        )
        
        # Check if probabilities sum to 1.0
        total_prob = sum(strategy.values())
        print(f"   Strategy: {strategy}")
        print(f"   Total probability: {total_prob:.3f}")
        
        # Analyze strategy quality
        if 'raise' in strategy and 'fold' in strategy:
            raise_ratio = strategy['raise'] / (strategy['raise'] + strategy['fold'])
            print(f"   Raise/(Raise+Fold) ratio: {raise_ratio:.2f}")
        elif 'raise' in strategy and 'check' in strategy:
            raise_ratio = strategy['raise'] / (strategy['raise'] + strategy['check'])
            print(f"   Raise/(Raise+Check) ratio: {raise_ratio:.2f}")
        
        # Show most likely action
        best_action = max(strategy.items(), key=lambda x: x[1])
        print(f"   Most likely action: {best_action[0]} ({best_action[1]:.1%})")
        
        print("   " + "=" * 50)

if __name__ == "__main__":
    test_extended_scenarios()
