#!/usr/bin/env python3
"""
Test raising behavior - check if bot will raise with strong hands
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

def test_raising_behavior():
    """Test if the bot will actually raise with strong hands"""
    
    print("🧪 Testing Raising Behavior")
    print("=" * 60)
    
    # Initialize components
    hand_evaluator = HandEvaluator()
    equity_calculator = GPUEquityCalculator(use_gpu=True)
    abstraction = HandAbstraction(hand_evaluator, equity_calculator)
    monte_carlo = MonteCarloSolver(abstraction, hand_evaluator, equity_calculator)
    
    # Test with a very strong hand that should raise frequently
    hole_cards = ['A♠', 'A♥']  # Pocket Aces
    community_cards = ['9♠', '6♥', '2♣']  # Safe dry board
    pot_size = 0.30
    actions = ['fold', 'call', 'raise']
    stage = 'flop'
    num_opponents = 3
    
    print(f"Hand: {hole_cards} (Pocket Aces)")
    print(f"Board: {community_cards} (Safe dry board)")
    print(f"Pot Size: {pot_size}")
    print(f"Actions: {actions}")
    print()
    
    # Test multiple iterations to see raise frequency
    raise_count = 0
    call_count = 0
    fold_count = 0
    total_tests = 20
    
    print(f"🎲 Running {total_tests} Monte Carlo simulations:")
    
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
            
            # Check what action would be selected using probabilistic sampling
            import random
            total_prob = sum(strategy.values())
            if total_prob > 0:
                normalized_strategy = {a: p/total_prob for a, p in strategy.items()}
            else:
                normalized_strategy = {a: 1.0/len(strategy) for a in strategy}
            
            # Sample action
            rand_val = random.random()
            cumulative_prob = 0.0
            selected_action = 'fold'  # fallback
            
            for action, prob in normalized_strategy.items():
                cumulative_prob += prob
                if rand_val <= cumulative_prob:
                    selected_action = action
                    break
            
            if selected_action == 'raise':
                raise_count += 1
            elif selected_action == 'call':
                call_count += 1
            else:
                fold_count += 1
                
            if i < 5:  # Show first 5 strategies
                fold_prob = strategy.get('fold', 0.0)
                call_prob = strategy.get('call', 0.0)
                raise_prob = strategy.get('raise', 0.0) + strategy.get('bet', 0.0)
                print(f"  Test {i+1}: Strategy: Fold={fold_prob:.1%}, Call={call_prob:.1%}, Raise={raise_prob:.1%} → Selected: {selected_action}")
                
        except Exception as e:
            print(f"  ❌ Error in test {i+1}: {e}")
    
    print(f"\n📊 Results after {total_tests} tests:")
    print(f"  Raises: {raise_count} ({raise_count/total_tests:.1%})")
    print(f"  Calls: {call_count} ({call_count/total_tests:.1%})")
    print(f"  Folds: {fold_count} ({fold_count/total_tests:.1%})")
    
    if raise_count == 0:
        print("⚠️  WARNING: Bot never raised with pocket aces! This indicates a problem.")
    elif raise_count < total_tests * 0.3:  # Less than 30% raises
        print("⚠️  WARNING: Bot raised less than expected with pocket aces.")
    else:
        print("✅ Good: Bot is raising appropriately with strong hands!")
    
    print("\n" + "=" * 60)
    print("🏁 Raising behavior test complete!")

if __name__ == "__main__":
    test_raising_behavior()
