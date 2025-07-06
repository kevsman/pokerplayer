#!/usr/bin/env python3
"""
Test the improved hand strength estimator with trips scenario
"""
import sys
import logging
from monte_carlo_solver import MonteCarloSolver
from hand_evaluator import HandEvaluator
from gpu_accelerated_equity import GPUEquityCalculator
from hand_abstraction import HandAbstraction

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

def test_trips_scenario():
    """Test the exact trips scenario from the log"""
    
    print("🧪 Testing Trips Scenario - The Critical Bug Fix")
    print("=" * 60)
    
    # Initialize components
    hand_evaluator = HandEvaluator()
    equity_calculator = GPUEquityCalculator(use_gpu=True)
    abstraction = HandAbstraction(hand_evaluator, equity_calculator)
    monte_carlo = MonteCarloSolver(abstraction, hand_evaluator, equity_calculator)
    
    # The exact scenario from the log: K4 with trip 4s on river
    hole_cards = ['4♦', 'K♠']
    community_cards = ['8♠', '3♠', '7♦', '4♥', '4♣']  # Board with pair of 4s
    pot_size = 1.58
    actions = ['fold', 'check', 'bet']
    stage = 'river'
    num_opponents = 5
    
    print(f"Hand: {hole_cards}")
    print(f"Board: {community_cards}")
    print(f"Made Hand: Trip 4s (4♦ in hand + 4♥ 4♣ on board)")
    print(f"Pot Size: {pot_size}")
    print(f"Stage: {stage}")
    print()
    
    # Test the hand strength estimator directly
    print("🔧 Testing improved hand strength estimator:")
    estimated_strength = monte_carlo._simple_hand_strength_estimate(hole_cards, community_cards, stage)
    print(f"Hand strength estimate: {estimated_strength:.3f} ({estimated_strength:.1%})")
    
    if estimated_strength >= 0.75:
        print("✅ Good: Trips recognized as strong hand!")
    elif estimated_strength >= 0.50:
        print("⚠️  Okay: Trips recognized as decent hand")
    else:
        print(f"❌ Problem: Trips only rated {estimated_strength:.1%} - too low!")
    
    print()
    
    # Test multiple Monte Carlo runs
    bet_count = 0
    check_count = 0
    fold_count = 0
    total_tests = 10
    
    print(f"🎲 Running {total_tests} Monte Carlo simulations with trips:")
    
    for i in range(total_tests):
        try:
            strategy = monte_carlo.solve(
                player_hole_cards=hole_cards,
                community_cards=community_cards,
                pot_size=pot_size,
                actions=actions,
                stage=stage,
                num_opponents=num_opponents,
                iterations=50
            )
            
            # Sample action using probabilistic selection
            import random
            total_prob = sum(strategy.values())
            if total_prob > 0:
                normalized_strategy = {a: p/total_prob for a, p in strategy.items()}
            else:
                normalized_strategy = {a: 1.0/len(strategy) for a in strategy}
            
            rand_val = random.random()
            cumulative_prob = 0.0
            selected_action = 'fold'
            
            for action, prob in normalized_strategy.items():
                cumulative_prob += prob
                if rand_val <= cumulative_prob:
                    selected_action = action
                    break
            
            if selected_action == 'bet':
                bet_count += 1
            elif selected_action == 'check':
                check_count += 1
            else:
                fold_count += 1
                
            if i < 3:  # Show first 3 strategies
                fold_prob = strategy.get('fold', 0.0)
                check_prob = strategy.get('check', 0.0)
                bet_prob = strategy.get('bet', 0.0)
                print(f"  Test {i+1}: Fold={fold_prob:.1%}, Check={check_prob:.1%}, Bet={bet_prob:.1%} → Selected: {selected_action}")
                
        except Exception as e:
            print(f"  ❌ Error in test {i+1}: {e}")
    
    print(f"\n📊 Results after {total_tests} tests with trips:")
    print(f"  Bets: {bet_count} ({bet_count/total_tests:.1%})")
    print(f"  Checks: {check_count} ({check_count/total_tests:.1%})")
    print(f"  Folds: {fold_count} ({fold_count/total_tests:.1%})")
    
    if bet_count == 0:
        print("❌ CRITICAL: Bot never bet with trips on the river!")
    elif bet_count < total_tests * 0.4:  # Less than 40% bets
        print("⚠️  WARNING: Bot should bet more aggressively with trips on river")
    else:
        print("✅ Good: Bot is betting appropriately with trips!")
    
    print("\n" + "=" * 60)
    print("🏁 Trips scenario testing complete!")

if __name__ == "__main__":
    test_trips_scenario()
