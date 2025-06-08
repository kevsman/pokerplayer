#!/usr/bin/env python3
"""
Simple integration validation for enhanced postflop improvements.
"""

import sys
import os
from unittest.mock import Mock

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from postflop_decision_logic import make_postflop_decision
from config import *

def test_enhanced_integration():
    """Test integration of all enhanced features."""
    print("Testing Enhanced Postflop Integration...")
    
    # Mock opponent tracker
    mock_opponent_tracker = Mock()
    mock_opponent_tracker.get_aggression_factor.return_value = 2.0
    mock_opponent_tracker.get_vpip.return_value = 25.0
    mock_opponent_tracker.get_pfr.return_value = 20.0
    mock_opponent_tracker.get_3bet_percent.return_value = 5.0
    mock_opponent_tracker.get_fold_to_cbet_percent.return_value = 65.0
    
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Strong hand consistent sizing
    total_tests += 1
    try:
        decision, amount = make_postflop_decision(
            numerical_hand_rank=4,  # Strong hand
            win_probability=0.85,
            pot_size=100,
            bet_to_call=0,
            my_stack=1000,
            opponent_tracker=mock_opponent_tracker,
            active_opponents_count=1,
            street="flop",
            position="button",
            actions_taken_this_street=[],
            pot_odds_to_call=0,
            aggression_factor=2.0,
            bluff_frequency=0.1
        )
        
        if decision == action_bet_const and 60 <= amount <= 75:  # ~2/3 pot sizing
            print("✓ Test 1 PASSED: Strong hand uses consistent bet sizing")
            tests_passed += 1
        else:
            print(f"✗ Test 1 FAILED: Expected bet ~67, got {decision}/{amount}")
    except Exception as e:
        print(f"✗ Test 1 ERROR: {e}")
    
    # Test 2: Drawing hand analysis
    total_tests += 1
    try:
        decision, amount = make_postflop_decision(
            numerical_hand_rank=8,  # Drawing hand
            win_probability=0.35,  # Good draw
            pot_size=200,
            bet_to_call=50,
            my_stack=800,
            opponent_tracker=mock_opponent_tracker,
            active_opponents_count=1,
            street="flop",
            position="button",
            actions_taken_this_street=[],
            pot_odds_to_call=0.20,
            aggression_factor=2.0,
            bluff_frequency=0.1
        )
        
        if decision == action_call_const and amount == 50:
            print("✓ Test 2 PASSED: Drawing hand with good implied odds calls")
            tests_passed += 1
        else:
            print(f"✗ Test 2 FAILED: Expected call 50, got {decision}/{amount}")
    except Exception as e:
        print(f"✗ Test 2 ERROR: {e}")
    
    # Test 3: Multiway conservative play
    total_tests += 1
    try:
        decision, amount = make_postflop_decision(
            numerical_hand_rank=6,  # Medium hand
            win_probability=0.45,
            pot_size=150,
            bet_to_call=0,
            my_stack=850,
            opponent_tracker=mock_opponent_tracker,
            active_opponents_count=3,  # Multiway
            street="flop",
            position="cutoff",
            actions_taken_this_street=[],
            pot_odds_to_call=0,
            aggression_factor=2.0,
            bluff_frequency=0.1
        )
        
        if decision == action_check_const:
            print("✓ Test 3 PASSED: Medium hand checks in multiway pot")
            tests_passed += 1
        else:
            print(f"✗ Test 3 FAILED: Expected check, got {decision}/{amount}")
    except Exception as e:
        print(f"✗ Test 3 ERROR: {e}")
    
    # Test 4: All-in scenario
    total_tests += 1
    try:
        decision, amount = make_postflop_decision(
            numerical_hand_rank=2,  # Very strong hand
            win_probability=0.90,
            pot_size=300,
            bet_to_call=500,  # All-in call
            my_stack=500,
            opponent_tracker=mock_opponent_tracker,
            active_opponents_count=1,
            street="turn",
            position="big_blind",
            actions_taken_this_street=[],
            pot_odds_to_call=0.375,
            aggression_factor=2.0,
            bluff_frequency=0.1
        )
        
        if decision == action_call_const and amount == 500:
            print("✓ Test 4 PASSED: Very strong hand calls all-in")
            tests_passed += 1
        else:
            print(f"✗ Test 4 FAILED: Expected call 500, got {decision}/{amount}")
    except Exception as e:
        print(f"✗ Test 4 ERROR: {e}")
    
    # Test 5: Fallback logic
    total_tests += 1
    try:
        decision, amount = make_postflop_decision(
            numerical_hand_rank=5,
            win_probability=0.60,
            pot_size=120,
            bet_to_call=0,
            my_stack=880,
            opponent_tracker=None,  # Test fallback
            active_opponents_count=1,
            street="flop",
            position="button",
            actions_taken_this_street=[],
            pot_odds_to_call=0,
            aggression_factor=2.0,
            bluff_frequency=0.1
        )
        
        if decision in [action_bet_const, action_check_const, action_call_const]:
            print("✓ Test 5 PASSED: Fallback logic works correctly")
            tests_passed += 1
        else:
            print(f"✗ Test 5 FAILED: Invalid decision {decision}")
    except Exception as e:
        print(f"✗ Test 5 ERROR: {e}")
    
    print(f"\nIntegration Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        return True
    else:
        print("⚠️  Some integration tests failed")
        return False

if __name__ == "__main__":
    success = test_enhanced_integration()
    sys.exit(0 if success else 1)
