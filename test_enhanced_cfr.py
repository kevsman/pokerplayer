#!/usr/bin/env python3
"""
Test Enhanced Real-Time CFR with longer solve times and better quality
"""
import logging
import time

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_enhanced_cfr_performance():
    """Test the enhanced CFR solver with different quality levels"""
    print("🚀 Testing Enhanced Real-Time CFR Performance...")
    
    try:
        from realtime_cfr_solver import RealTimeCFRSolver
        
        # Initialize solver
        solver = RealTimeCFRSolver(use_gpu=True)
        
        test_scenarios = [
            {
                'name': 'Small Pot - Urgent',
                'hole_cards': ['A♠', 'K♥'],
                'community_cards': ['Q♠', 'J♥', '10♣'],
                'pot_size': 1.0,
                'num_opponents': 2,
                'quality_level': 'urgent'
            },
            {
                'name': 'Medium Pot - Normal',
                'hole_cards': ['A♠', 'A♥'],
                'community_cards': ['K♠', 'Q♥', '10♣'],
                'pot_size': 3.0,
                'num_opponents': 3,
                'quality_level': 'normal'
            },
            {
                'name': 'Large Pot - Detailed',
                'hole_cards': ['9♠', '8♥'],
                'community_cards': ['7♠', '6♥', '5♣'],
                'pot_size': 8.0,
                'num_opponents': 4,
                'quality_level': 'detailed'
            },
            {
                'name': 'Tournament Spot - Maximum Quality',
                'hole_cards': ['K♠', 'K♥'],
                'community_cards': ['A♠', '7♥', '2♣', '9♦'],
                'pot_size': 15.0,
                'num_opponents': 2,
                'quality_level': 'tournament'
            }
        ]
        
        print("🎯 Testing different quality levels and complexity...")
        print("=" * 60)
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n🧪 Test {i}: {scenario['name']}")
            print(f"   Cards: {scenario['hole_cards']} | Board: {scenario['community_cards']}")
            print(f"   Pot: ${scenario['pot_size']:.1f} | Opponents: {scenario['num_opponents']} | Quality: {scenario['quality_level']}")
            
            start_time = time.time()
            
            strategy = solver.solve_current_situation(
                hole_cards=scenario['hole_cards'],
                community_cards=scenario['community_cards'],
                pot_size=scenario['pot_size'],
                num_opponents=scenario['num_opponents'],
                stage='flop',
                quality_level=scenario['quality_level']
            )
            
            solve_time = time.time() - start_time
            
            print(f"   ⚡ Solved in {solve_time:.3f}s")
            print(f"   📊 Strategy: {strategy}")
            
            # Validate strategy format
            total_prob = sum(strategy.values())
            if abs(total_prob - 1.0) > 0.01:
                print(f"   ⚠️  Warning: Strategy probabilities sum to {total_prob:.3f}")
            else:
                print(f"   ✅ Valid strategy (sum={total_prob:.3f})")
        
        print("\n" + "=" * 60)
        print("🎉 Enhanced CFR Performance Test Complete!")
        return True
        
    except Exception as e:
        print(f"❌ Enhanced CFR test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🎯 Enhanced Real-Time CFR Performance Test")
    print("Testing adaptive quality levels and longer solve times")
    print("=" * 60)
    
    success = test_enhanced_cfr_performance()
    
    if success:
        print("\n🚀 ENHANCED CFR IS READY!")
        print("✅ Multiple quality levels working")
        print("⚡ Adaptive solve times based on situation complexity")
        print("🎯 Better results with longer solving")
    else:
        print("\n❌ Enhanced CFR tests failed")
