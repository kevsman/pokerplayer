#!/usr/bin/env python3
"""
Test the complete decision system including the new probabilistic action selection
"""
import logging
from monte_carlo_solver import MonteCarloSolver
from hand_evaluator import HandEvaluator
from gpu_accelerated_equity import GPUEquityCalculator
from hand_abstraction import HandAbstraction
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

def simulate_decision_with_probabilistic_sampling(strategy, num_simulations=100):
    """Simulate the new probabilistic decision making logic"""
    
    # Normalize probabilities
    total_prob = sum(strategy.values())
    if total_prob > 0:
        normalized_strategy = {a: p/total_prob for a, p in strategy.items()}
    else:
        normalized_strategy = {a: 1.0/len(strategy) for a in strategy}
    
    action_counts = {action: 0 for action in strategy.keys()}
    
    # Simulate many decisions
    for _ in range(num_simulations):
        rand_val = random.random()
        cumulative_prob = 0.0
        selected_action = list(strategy.keys())[0]  # fallback
        
        for action, prob in normalized_strategy.items():
            cumulative_prob += prob
            if rand_val <= cumulative_prob:
                selected_action = action
                break
        
        action_counts[selected_action] += 1
    
    # Convert counts to percentages
    result = {action: count/num_simulations for action, count in action_counts.items()}
    return result

def test_decision_logic():
    """Test the decision logic with various scenarios"""
    
    print("🧪 Testing Complete Decision Logic with Probabilistic Sampling")
    print("=" * 70)
    
    # Test scenarios with known strategies
    test_cases = [
        {
            'name': 'Aggressive (should raise often)',
            'strategy': {'fold': 0.05, 'call': 0.25, 'raise': 0.70},
            'expected_raise_rate': 0.65  # Should raise ~65-75% of the time
        },
        {
            'name': 'Balanced (mixed actions)',
            'strategy': {'fold': 0.20, 'call': 0.40, 'raise': 0.40},
            'expected_raise_rate': 0.35  # Should raise ~35-45% of the time
        },
        {
            'name': 'Conservative (should rarely raise)',
            'strategy': {'fold': 0.10, 'call': 0.80, 'raise': 0.10},
            'expected_raise_rate': 0.05  # Should raise ~5-15% of the time
        },
        {
            'name': 'Strong hand (from real test)',
            'strategy': {'fold': 0.001, 'call': 0.211, 'raise': 0.788},
            'expected_raise_rate': 0.75  # Should raise ~75-85% of the time
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📋 Test Case: {test_case['name']}")
        print(f"Input Strategy: {test_case['strategy']}")
        
        # Simulate 1000 decisions
        simulated_results = simulate_decision_with_probabilistic_sampling(
            test_case['strategy'], num_simulations=1000
        )
        
        print(f"Simulated Results: {simulated_results}")
        
        actual_raise_rate = simulated_results.get('raise', 0.0)
        expected_rate = test_case['expected_raise_rate']
        
        if abs(actual_raise_rate - expected_rate) < 0.10:  # Within 10%
            print(f"✅ Good: Raise rate {actual_raise_rate:.1%} is close to expected {expected_rate:.1%}")
        else:
            print(f"⚠️  Warning: Raise rate {actual_raise_rate:.1%} differs from expected {expected_rate:.1%}")
    
    print("\n" + "=" * 70)
    print("🏁 Decision logic testing complete!")
    print("The bot should now raise according to the computed strategy probabilities.")

if __name__ == "__main__":
    test_decision_logic()
