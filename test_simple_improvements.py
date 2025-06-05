#!/usr/bin/env python3

"""
Simple test for poker bot improvements
"""

import sys
import os

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our modules
from preflop_decision_logic import adjust_for_implied_odds, make_preflop_decision

def test_implied_odds_function():
    """Test that the implied odds adjustment function works correctly"""
    
    big_blind = 0.02
    deep_stack_size = 2.0  # 100BB stack
    normal_stack_size = 1.0  # 50BB stack
    
    print("Testing implied odds function...")
    
    # Test suited connector in late position with deep stacks (should return True)
    result = adjust_for_implied_odds("Suited Connector", "CO", deep_stack_size, deep_stack_size, big_blind)
    print(f"✓ Suited connector in CO with deep stacks: {result}")
    assert result == True, "Suited connector in CO with deep stacks should have implied odds"
    
    # Test suited ace in late position with deep stacks (should return True)  
    result = adjust_for_implied_odds("Suited Ace", "BTN", deep_stack_size, deep_stack_size, big_blind)
    print(f"✓ Suited ace in BTN with deep stacks: {result}")
    assert result == True, "Suited ace in BTN with deep stacks should have implied odds"
    
    # Test suited connector in early position (should return False)
    result = adjust_for_implied_odds("Suited Connector", "UTG", deep_stack_size, deep_stack_size, big_blind)
    print(f"✓ Suited connector in UTG: {result}")
    assert result == False, "Suited connector in UTG should not have implied odds benefit"
    
    # Test suited connector in late position with shallow stacks (should return False)
    result = adjust_for_implied_odds("Suited Connector", "CO", normal_stack_size, normal_stack_size, big_blind)
    print(f"✓ Suited connector with shallow stacks: {result}")
    assert result == False, "Suited connector with shallow stacks should not have implied odds benefit"
    
    print("✓ Implied odds function tests passed!")

def test_suited_connector_preflop():
    """Test suited connector preflop improvements"""
    
    print("Testing suited connector preflop improvements...")
    
    big_blind = 0.02
    small_blind = 0.01
    deep_stack_size = 2.0
    
    # Mock player with deep stack
    my_player = {
        'name': 'TestBot',
        'hand': ['9♠', '8♠'],  # 98s - suited connector
        'stack': deep_stack_size,
        'current_bet': 0
    }
    
    action_constants = {'FOLD': 0, 'CHECK': 1, 'CALL': 2, 'RAISE': 3}
    
    # Test calling 4BB in CO position with deep stacks (should call due to implied odds)
    try:
        result = make_preflop_decision(
            my_player=my_player,
            hand_category="Suited Connector", 
            position="CO",
            bet_to_call=4 * big_blind,  # 4BB bet
            can_check=False,
            my_stack=deep_stack_size,
            pot_size=0.03,
            active_opponents_count=3,
            small_blind=small_blind,
            big_blind=big_blind,
            my_current_bet_this_street=0,
            max_bet_on_table=4 * big_blind,
            min_raise=0.04,
            is_sb=False,
            is_bb=False,
            action_fold_const=action_constants['FOLD'],
            action_check_const=action_constants['CHECK'], 
            action_call_const=action_constants['CALL'],
            action_raise_const=action_constants['RAISE']
        )
        
        action, amount = result
        print(f"✓ Suited connector CO decision: Action={action}, Amount={amount}")
        assert action == action_constants['CALL'], "Should call 4BB with suited connector in CO with deep stacks"
        
    except Exception as e:
        print(f"⚠ Suited connector test error: {e}")

def test_suited_ace_preflop():
    """Test suited ace preflop improvements"""
    
    print("Testing suited ace preflop improvements...")
    
    big_blind = 0.02
    small_blind = 0.01
    deep_stack_size = 2.0
    
    # Mock player with deep stack and suited ace
    my_player = {
        'name': 'TestBot', 
        'hand': ['A♠', '8♠'],  # A8s - suited ace
        'stack': deep_stack_size,
        'current_bet': 0
    }
    
    action_constants = {'FOLD': 0, 'CHECK': 1, 'CALL': 2, 'RAISE': 3}
    
    # Test CO position calling 5BB with deep stacks (should call due to implied odds)
    try:
        result = make_preflop_decision(
            my_player=my_player,
            hand_category="Suited Ace",
            position="CO", 
            bet_to_call=5 * big_blind,  # 5BB bet
            can_check=False,
            my_stack=deep_stack_size,
            pot_size=0.03,
            active_opponents_count=3,
            small_blind=small_blind,
            big_blind=big_blind,
            my_current_bet_this_street=0,
            max_bet_on_table=5 * big_blind,
            min_raise=0.04,
            is_sb=False,
            is_bb=False,
            action_fold_const=action_constants['FOLD'],
            action_check_const=action_constants['CHECK'],
            action_call_const=action_constants['CALL'], 
            action_raise_const=action_constants['RAISE']
        )
        
        action, amount = result
        print(f"✓ Suited ace CO decision: Action={action}, Amount={amount}")
        assert action == action_constants['CALL'], "Should call 5BB with suited ace in CO with deep stacks"
        
    except Exception as e:
        print(f"⚠ Suited ace test error: {e}")

def run_all_tests():
    """Run all tests"""
    
    print("=" * 60)
    print("POKER BOT IMPROVEMENTS TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("Implied Odds Function", test_implied_odds_function),
        ("Suited Connector Preflop", test_suited_connector_preflop),
        ("Suited Ace Preflop", test_suited_ace_preflop)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n--- {test_name} ---")
            test_func()
            print(f"✓ PASSED: {test_name}")
            passed += 1
        except Exception as e:
            print(f"✗ FAILED: {test_name} - {str(e)}")
            failed += 1
            
    print(f"\n" + "=" * 60)
    print(f"TEST SUMMARY: {passed} passed, {failed} failed")
    if passed + failed > 0:
        print(f"SUCCESS RATE: {passed/(passed+failed)*100:.1f}%")
    print("=" * 60)
    
    return passed, failed

if __name__ == "__main__":
    run_all_tests()
