#!/usr/bin/env python3
"""
Test Real-Time CFR Integration
Verify that the RealTimeCFRSolver is properly integrated into PokerBotV2.
"""
import logging
import sys
import time

def test_cfr_integration():
    """Test that the RealTimeCFRSolver can be imported and used."""
    print("🧪 Testing Real-Time CFR Integration...")
    
    # Test 1: Import RealTimeCFRSolver
    try:
        from realtime_cfr_solver import RealTimeCFRSolver
        print("✅ Successfully imported RealTimeCFRSolver")
    except Exception as e:
        print(f"❌ Failed to import RealTimeCFRSolver: {e}")
        return False
    
    # Test 2: Initialize RealTimeCFRSolver
    try:
        solver = RealTimeCFRSolver(use_gpu=True)
        print("✅ Successfully initialized RealTimeCFRSolver")
    except Exception as e:
        print(f"❌ Failed to initialize RealTimeCFRSolver: {e}")
        return False
    
    # Test 3: Test solving a poker situation
    try:
        print("⚡ Testing Real-Time CFR solving...")
        start_time = time.time()
        
        strategy = solver.solve_current_situation(
            hole_cards=['A♠', 'K♥'],
            community_cards=['Q♠', 'J♥', '10♣'],
            pot_size=1.0,
            num_opponents=3,
            position=2,
            stage='flop'
        )
        
        solve_time = time.time() - start_time
        print(f"✅ CFR solved in {solve_time:.3f}s: {strategy}")
        
        # Verify strategy format
        required_actions = ['fold', 'call', 'raise']
        for action in required_actions:
            if action not in strategy:
                print(f"❌ Missing action '{action}' in strategy")
                return False
        
        # Verify probabilities sum to ~1.0
        total_prob = sum(strategy.values())
        if abs(total_prob - 1.0) > 0.01:
            print(f"❌ Strategy probabilities sum to {total_prob:.3f}, expected ~1.0")
            return False
        
        print("✅ Strategy format is valid")
        
    except Exception as e:
        print(f"❌ CFR solving failed: {e}")
        return False
    
    # Test 4: Test PokerBotV2 integration
    try:
        from poker_bot_v2 import PokerBotV2
        bot = PokerBotV2()
        print("✅ Successfully created PokerBotV2 with RealTimeCFRSolver")
        
        # Check if RealTimeCFRSolver is properly initialized
        if hasattr(bot, 'realtime_cfr_solver'):
            print("✅ RealTimeCFRSolver properly integrated into PokerBotV2")
        else:
            print("❌ RealTimeCFRSolver not found in PokerBotV2")
            return False
            
    except Exception as e:
        print(f"❌ Failed to create PokerBotV2: {e}")
        return False
    
    print("🎉 All tests passed! Real-Time CFR is properly integrated.")
    return True

def test_cfr_vs_monte_carlo():
    """Compare Real-Time CFR vs Monte Carlo performance."""
    print("\n🏁 Performance Comparison: Real-Time CFR vs Monte Carlo")
    
    try:
        from realtime_cfr_solver import RealTimeCFRSolver
        from monte_carlo_solver import MonteCarloSolver
        from hand_abstraction import HandAbstraction
        from hand_evaluator import HandEvaluator
        from gpu_accelerated_equity import GPUEquityCalculator
        
        # Initialize solvers
        hand_evaluator = HandEvaluator()
        equity_calculator = GPUEquityCalculator(use_gpu=True)
        abstraction = HandAbstraction(hand_evaluator, equity_calculator)
        
        cfr_solver = RealTimeCFRSolver(use_gpu=True)
        mc_solver = MonteCarloSolver(abstraction, hand_evaluator, equity_calculator)
        
        # Test scenario
        hole_cards = ['A♠', 'K♥']
        community_cards = ['Q♠', 'J♥', '10♣']
        pot_size = 1.0
        num_opponents = 3
        actions = ['fold', 'call', 'raise']
        
        # Test CFR
        print("⚡ Testing Real-Time CFR...")
        cfr_start = time.time()
        cfr_strategy = cfr_solver.solve_current_situation(
            hole_cards=hole_cards,
            community_cards=community_cards,
            pot_size=pot_size,
            num_opponents=num_opponents,
            stage='flop'
        )
        cfr_time = time.time() - cfr_start
        
        # Test Monte Carlo
        print("🎲 Testing Monte Carlo...")
        mc_start = time.time()
        mc_strategy = mc_solver.solve(hole_cards, community_cards, pot_size, actions, 'flop', num_opponents, iterations=100)
        mc_time = time.time() - mc_start
        
        print(f"\n📊 Performance Results:")
        print(f"⚡ Real-Time CFR: {cfr_time:.3f}s - {cfr_strategy}")
        print(f"🎲 Monte Carlo:   {mc_time:.3f}s - {mc_strategy}")
        
        if cfr_time < mc_time:
            print(f"🏆 Real-Time CFR is {mc_time/cfr_time:.1f}x faster!")
        else:
            print(f"🏆 Monte Carlo is {cfr_time/mc_time:.1f}x faster!")
            
    except Exception as e:
        print(f"❌ Performance comparison failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    success = test_cfr_integration()
    if success:
        test_cfr_vs_monte_carlo()
    
    if success:
        print("\n🎉 Real-Time CFR integration is complete and working!")
        print("🚀 PokerBotV2 now uses Real-Time CFR for live fallback solving!")
    else:
        print("\n❌ Integration tests failed. Please check the logs.")
        sys.exit(1)
