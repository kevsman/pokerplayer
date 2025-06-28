#!/usr/bin/env python3
"""
Simple test to verify CFR infinite recursion fixes work correctly.
"""

import numpy as np
from gpu_cfr_trainer import GPUCFRTrainer

def test_simple_recursion():
    """Test that CFR recursion terminates in a simple scenario."""
    print("=== Testing Simple CFR Recursion ===")
    
    trainer = GPUCFRTrainer(num_players=2)
    
    # Simple 2-player scenario
    player_hands = [['Ah', 'Ad'], ['Ks', 'Kd']]
    board = []
    pot = 3.0
    bets = np.array([1.0, 2.0])  # SB and BB
    reach_probs = np.ones(2)
    active_players = np.array([True, True])
    player_stacks = np.array([199.0, 198.0])
    street = 0
    num_actions_this_street = 0
    
    try:
        # This should terminate without infinite recursion
        result = trainer._cfr_recursive(
            player_hands, "", board, pot, bets, reach_probs, 
            active_players, player_stacks, street, num_actions_this_street, 
            recursion_depth=0
        )
        print(f"✓ CFR recursion completed successfully")
        print(f"✓ Final recursion depth: {trainer.recursion_depth}")
        print(f"✓ Result shape: {result.shape}")
        print(f"✓ Result: {np.round(result, 2)}")
        return True
        
    except Exception as e:
        print(f"✗ CFR recursion failed: {e}")
        return False

def test_all_in_scenario():
    """Test that all-in scenarios are handled correctly."""
    print("\n=== Testing All-In Scenario ===")
    
    trainer = GPUCFRTrainer(num_players=2)
    
    # One player goes all-in
    bets = np.array([30.0, 0.0])  # P0 is all-in
    active_players = np.array([True, True])
    stacks = np.array([0.0, 70.0])  # P0 all-in, P1 has chips
    
    # This should NOT end the betting round (P1 can still call or fold)
    result = trainer._is_betting_round_over("", bets, active_players, 0, 1, stacks)
    if not result:
        print("✓ All-in scenario correctly allows other player to act")
        return True
    else:
        print("✗ All-in scenario incorrectly ended betting round")
        return False

def test_only_one_active_player():
    """Test that when only one player is active, the game terminates."""
    print("\n=== Testing One Active Player ===")
    
    trainer = GPUCFRTrainer(num_players=2)
    
    # Only one player active (other folded)
    bets = np.array([30.0, 5.0])
    active_players = np.array([True, False])  # P1 folded
    stacks = np.array([70.0, 95.0])
    
    # This should end the betting round
    result = trainer._is_betting_round_over("", bets, active_players, 0, 2, stacks)
    if result:
        print("✓ One active player scenario correctly ends betting round")
        return True
    else:
        print("✗ One active player scenario should end betting round")
        return False

if __name__ == "__main__":
    print("Testing CFR infinite recursion fixes...\n")
    
    tests = [
        test_all_in_scenario,
        test_only_one_active_player,
        test_simple_recursion,  # This one last as it's most intensive
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n=== SUMMARY ===")
    print(f"Tests passed: {passed}/{total}")
    if passed == total:
        print("🎉 All tests passed! CFR fixes are working correctly.")
    else:
        print("⚠️ Some tests failed. Please review the fixes.")
