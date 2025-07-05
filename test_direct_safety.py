#!/usr/bin/env python3
"""
Test the SafeStrategyLookup and Monte Carlo solver directly
"""
import sys
import logging
from safe_strategy_lookup import SafeStrategyLookup
from monte_carlo_solver import MonteCarloSolver
from hand_evaluator import HandEvaluator
from gpu_accelerated_equity import GPUAcceleratedEquityCalculator
from hand_abstraction import HandAbstraction

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s:%(name)s:%(message)s'
)

def test_direct_safety():
    """Test the strategy lookup and monte carlo solver directly"""
    
    # Initialize components
    equity_calculator = GPUAcceleratedEquityCalculator()
    hand_evaluator = HandEvaluator()
    abstraction = HandAbstraction()
    
    safe_lookup = SafeStrategyLookup()
    monte_carlo = MonteCarloSolver(abstraction, hand_evaluator, equity_calculator)
    
    scenarios = [
        # Strong hands - should never fold on safe boards
        {
            'name': 'KK on dry board',
            'hole_cards': ['K♠', 'K♥'],
            'community_cards': ['8♠', '5♥', '4♣'],
            'stage': 'flop',
            'actions': ['fold', 'call', 'raise'],
            'pot_size': 0.28,
            'expected': 'Should rarely fold KK'
        },
        {
            'name': 'AA on safe board',
            'hole_cards': ['A♠', 'A♥'],
            'community_cards': ['9♠', '6♥', '2♣'],
            'stage': 'flop',
            'actions': ['fold', 'call', 'raise'],
            'pot_size': 0.30,
            'expected': 'Should almost never fold AA'
        },
        # Weak hands - should fold frequently 
        {
            'name': 'Trash on river',
            'hole_cards': ['7♠', '2♥'],
            'community_cards': ['K♠', 'Q♥', 'J♣', '9♠', '5♦'],
            'stage': 'river',
            'actions': ['fold', 'call'],
            'pot_size': 1.50,
            'expected': 'Should fold trash frequently'
        }
    ]
    
    print("🧪 Testing Direct Strategy Components")
    print("=" * 60)
    
    for scenario in scenarios:
        print(f"\n📋 Scenario: {scenario['name']}")
        print(f"Hand: {scenario['hole_cards']}")
        print(f"Board: {scenario['community_cards']}")
        print(f"Expected: {scenario['expected']}")
        
        try:
            # First try SafeStrategyLookup
            print("\n🔍 Trying SafeStrategyLookup...")
            safe_strategy = safe_lookup.get_strategy(
                player_hole_cards=scenario['hole_cards'],
                community_cards=scenario['community_cards'],
                stage=scenario['stage'],
                actions=scenario['actions'],
                pot_size=scenario['pot_size'],
                num_opponents=3
            )
            
            if safe_strategy:
                print(f"✅ SafeStrategyLookup found safe strategy: {safe_strategy}")
                strategy = safe_strategy
            else:
                print("⚠️  SafeStrategyLookup found no safe match, using Monte Carlo...")
                # Use Monte Carlo solver
                strategy = monte_carlo.solve(
                    player_hole_cards=scenario['hole_cards'],
                    community_cards=scenario['community_cards'],
                    pot_size=scenario['pot_size'],
                    actions=scenario['actions'],
                    stage=scenario['stage'],
                    num_opponents=3
                )
                print(f"🎲 Monte Carlo strategy: {strategy}")
            
            # Analyze strategy safety
            fold_prob = strategy.get('fold', 0.0)
            raise_prob = strategy.get('raise', 0.0) + strategy.get('bet', 0.0)
            
            if 'KK' in scenario['name'] or 'AA' in scenario['name']:
                if fold_prob > 0.15:  # Should rarely fold strong hands
                    print(f"⚠️  WARNING: High fold probability ({fold_prob:.1%}) for strong hand!")
                else:
                    print(f"✅ Good: Low fold probability ({fold_prob:.1%}) for strong hand")
                    
            elif 'Trash' in scenario['name']:
                if fold_prob < 0.50:  # Should often fold weak hands
                    print(f"⚠️  WARNING: Low fold probability ({fold_prob:.1%}) for weak hand!")
                else:
                    print(f"✅ Good: High fold probability ({fold_prob:.1%}) for weak hand")
                    
        except Exception as e:
            print(f"❌ Error in scenario: {e}")
            import traceback
            traceback.print_exc()
            
    print("\n" + "=" * 60)
    print("🏁 Direct safety testing complete!")

if __name__ == "__main__":
    test_direct_safety()
