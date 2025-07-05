#!/usr/bin/env python3
"""
Final comprehensive test of the Monte Carlo solver with key scenarios.
"""
import logging
from monte_carlo_solver import MonteCarloSolver
from hand_evaluator import HandEvaluator
from gpu_accelerated_equity import GPUEquityCalculator
from hand_abstraction import HandAbstraction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def final_comprehensive_test():
    """Final test of the Monte Carlo solver with critical poker scenarios."""
    
    # Initialize components
    hand_evaluator = HandEvaluator()
    equity_calculator = GPUEquityCalculator(use_gpu=True)
    abstraction = HandAbstraction(hand_evaluator, equity_calculator)
    solver = MonteCarloSolver(abstraction, hand_evaluator, equity_calculator, logger)
    
    print("🎯 FINAL Monte Carlo Solver Comprehensive Test")
    print("=" * 70)
    
    # Critical test scenarios that represent key poker decisions
    test_scenarios = [
        {
            'name': 'Premium Pocket Pair (AA)',
            'hole_cards': ['A♠', 'A♥'],
            'community': [],
            'pot': 0.06,
            'actions': ['fold', 'call', 'raise'],
            'expected_action': 'raise',
            'target_raise_rate': '>70%'
        },
        {
            'name': 'Trash Hand (72o)',
            'hole_cards': ['7♦', '2♣'],
            'community': [],
            'pot': 0.06,
            'actions': ['fold', 'call', 'raise'],
            'expected_action': 'fold',
            'target_fold_rate': '>80%'
        },
        {
            'name': 'Medium Pocket Pair (99)',
            'hole_cards': ['9♠', '9♥'],
            'community': [],
            'pot': 0.06,
            'actions': ['fold', 'call', 'raise'],
            'expected_action': 'raise',
            'target_raise_rate': '>60%'
        },
        {
            'name': 'Monster Hand (Set)',
            'hole_cards': ['8♦', '8♣'],
            'community': ['8♠', '2♥', '4♦'],
            'pot': 0.12,
            'actions': ['check', 'raise'],
            'expected_action': 'raise',
            'target_raise_rate': '>85%'
        },
        {
            'name': 'Missed Draw (AK on river)',
            'hole_cards': ['A♠', 'K♠'],
            'community': ['2♥', '7♦', 'Q♣', '3♥', '9♦'],
            'pot': 0.50,
            'actions': ['check', 'raise'],
            'expected_action': 'check',
            'target_check_rate': '>95%'
        },
        {
            'name': 'Top Pair Good Kicker',
            'hole_cards': ['A♦', 'K♣'],
            'community': ['A♠', '8♥', '5♦'],
            'pot': 0.12,
            'actions': ['check', 'raise'],
            'expected_action': 'raise',
            'target_raise_rate': '>60%'
        }
    ]
    
    results_summary = []
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{i}. 🃏 {scenario['name']}")
        print(f"   Hand: {', '.join(scenario['hole_cards'])}")
        if scenario['community']:
            print(f"   Board: {', '.join(scenario['community'])}")
        print(f"   Expected: {scenario['expected_action']} ({scenario.get('target_raise_rate', scenario.get('target_fold_rate', scenario.get('target_check_rate', 'N/A')))})")
        
        # Determine stage automatically
        if not scenario['community']:
            stage = 'preflop'
        elif len(scenario['community']) == 3:
            stage = 'flop'
        elif len(scenario['community']) == 4:
            stage = 'turn'
        else:
            stage = 'river'
        
        # Run solver with higher iterations for final test
        strategy = solver.solve(
            scenario['hole_cards'],
            scenario['community'],
            scenario['pot'],
            scenario['actions'],
            stage,
            num_opponents=1,
            iterations=100
        )
        
        # Analyze results
        best_action = max(strategy.items(), key=lambda x: x[1])
        action_rates = {action: f"{prob:.1%}" for action, prob in strategy.items()}
        
        print(f"   Strategy: {action_rates}")
        print(f"   Best action: {best_action[0]} ({best_action[1]:.1%})")
        
        # Check if result meets expectations
        expected = scenario['expected_action']
        if expected in strategy:
            actual_rate = strategy[expected]
            if expected == 'raise' and 'target_raise_rate' in scenario:
                target = float(scenario['target_raise_rate'].replace('>', '').replace('%', '')) / 100
                result = "✅ PASS" if actual_rate >= target else "❌ FAIL"
            elif expected == 'fold' and 'target_fold_rate' in scenario:
                target = float(scenario['target_fold_rate'].replace('>', '').replace('%', '')) / 100
                result = "✅ PASS" if actual_rate >= target else "❌ FAIL"
            elif expected == 'check' and 'target_check_rate' in scenario:
                target = float(scenario['target_check_rate'].replace('>', '').replace('%', '')) / 100
                result = "✅ PASS" if actual_rate >= target else "❌ FAIL"
            else:
                result = "✅ PASS" if best_action[0] == expected else "❌ FAIL"
            
            print(f"   Result: {result}")
            results_summary.append((scenario['name'], result))
        
        print("   " + "-" * 60)
    
    # Final summary
    print(f"\n🏁 FINAL RESULTS SUMMARY")
    print("=" * 70)
    passed = sum(1 for _, result in results_summary if "PASS" in result)
    total = len(results_summary)
    
    for name, result in results_summary:
        print(f"   {result} {name}")
    
    print(f"\n🎯 Overall Score: {passed}/{total} ({passed/total:.1%}) tests passed")
    
    if passed == total:
        print("🏆 EXCELLENT! Monte Carlo solver is performing optimally!")
    elif passed >= total * 0.8:
        print("🔥 GOOD! Monte Carlo solver is performing well!")
    else:
        print("⚠️  Needs improvement - some core scenarios failing")

if __name__ == "__main__":
    final_comprehensive_test()
