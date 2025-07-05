#!/usr/bin/env python3
"""
Test the KK folding fix directly using Monte Carlo solver
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

def test_kk_scenario():
    """Test specifically the KK folding scenario that was problematic"""
    
    print("🧪 Testing KK Scenario - The Critical Fix")
    print("=" * 60)
    
    # Initialize components
    hand_evaluator = HandEvaluator()
    equity_calculator = GPUEquityCalculator(use_gpu=True)
    abstraction = HandAbstraction(hand_evaluator, equity_calculator)
    monte_carlo = MonteCarloSolver(abstraction, hand_evaluator, equity_calculator)
    
    # The exact scenario from the log where KK was folding
    hole_cards = ['K♠', 'K♥']
    community_cards = ['8♠', '5♥', '4♥']
    pot_size = 0.28
    actions = ['fold', 'call', 'raise']
    stage = 'flop'
    num_opponents = 5
    
    print(f"Hand: {hole_cards}")
    print(f"Board: {community_cards}")
    print(f"Pot Size: {pot_size}")
    print(f"Stage: {stage}")
    print(f"Opponents: {num_opponents}")
    print()
    
    # Test multiple iterations to see consistency
    for i in range(3):
        print(f"🎲 Test Run {i+1}:")
        try:
            strategy = monte_carlo.solve(
                player_hole_cards=hole_cards,
                community_cards=community_cards,
                pot_size=pot_size,
                actions=actions,
                stage=stage,
                num_opponents=num_opponents,
                iterations=100
            )
            
            fold_prob = strategy.get('fold', 0.0)
            call_prob = strategy.get('call', 0.0)
            raise_prob = strategy.get('raise', 0.0) + strategy.get('bet', 0.0)
            
            print(f"  Strategy: Fold={fold_prob:.1%}, Call={call_prob:.1%}, Raise={raise_prob:.1%}")
            
            # Check if the strategy is reasonable for KK
            if fold_prob > 0.20:  # Should rarely fold KK on this board
                print(f"  ⚠️  WARNING: High fold probability ({fold_prob:.1%}) for KK!")
            else:
                print(f"  ✅ Good: Reasonable fold probability ({fold_prob:.1%}) for KK")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print()
    
    # Test heads-up scenario (which should be even stronger for KK)
    print("🎯 Testing Heads-Up KK Scenario:")
    try:
        strategy = monte_carlo.solve(
            player_hole_cards=hole_cards,
            community_cards=community_cards,
            pot_size=pot_size,
            actions=actions,
            stage=stage,
            num_opponents=1,  # Heads-up
            iterations=100
        )
        
        fold_prob = strategy.get('fold', 0.0)
        call_prob = strategy.get('call', 0.0)
        raise_prob = strategy.get('raise', 0.0) + strategy.get('bet', 0.0)
        
        print(f"Heads-up Strategy: Fold={fold_prob:.1%}, Call={call_prob:.1%}, Raise={raise_prob:.1%}")
        
        if fold_prob > 0.10:  # Should almost never fold KK heads-up
            print(f"⚠️  WARNING: High fold probability ({fold_prob:.1%}) for heads-up KK!")
        else:
            print(f"✅ Excellent: Very low fold probability ({fold_prob:.1%}) for heads-up KK")
            
    except Exception as e:
        print(f"❌ Error in heads-up test: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🏁 KK scenario testing complete!")
    print("The bot should now be much safer with strong hands like KK.")

if __name__ == "__main__":
    test_kk_scenario()
