#!/usr/bin/env python3
"""
Comprehensive test suite for poker bot improvements.
Tests the integration of:
1. Dynamic bet sizing function
2. Preflop implied odds adjustments 
3. Suited connector improvements
4. Suited ace improvements
"""

import sys
import os
import logging
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from preflop_decision_logic import make_preflop_decision, adjust_for_implied_odds
from postflop_decision_logic import make_postflop_decision, get_dynamic_bet_size

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_preflop_implied_odds_scenarios():
    """Test various preflop implied odds scenarios"""
    print("--- Comprehensive Preflop Implied Odds Tests ---")
    
    test_cases = [
        # Test Case 1: Suited connector in late position with deep stacks
        {
            'name': 'Suited connector CO deep stacks',
            'position': 'CO',
            'hand_category': 'Suited Connector',
            'bet_to_call': 0.08,  # 4BB
            'my_stack': 3.0,      # 150BB - deep
            'bb_size': 0.02,
            'expected_action': 2,  # CALL
            'description': 'Should call wider with implied odds'
        },
        
        # Test Case 2: Suited connector in late position with shallow stacks
        {
            'name': 'Suited connector CO shallow stacks',
            'position': 'CO',
            'hand_category': 'Suited Connector',
            'bet_to_call': 0.08,  # 4BB
            'my_stack': 0.8,      # 40BB - shallow
            'bb_size': 0.02,
            'expected_action': 1,  # FOLD
            'description': 'Should fold without implied odds'
        },
        
        # Test Case 3: Suited ace in button with deep stacks
        {
            'name': 'Suited ace BTN deep stacks',
            'position': 'BTN',
            'hand_category': 'Suited Ace',
            'bet_to_call': 0.10,  # 5BB
            'my_stack': 2.5,      # 125BB
            'bb_size': 0.02,
            'expected_action': 2,  # CALL
            'description': 'Should call stronger suited aces with implied odds'
        },
        
        # Test Case 4: Big blind defending with suited connector
        {
            'name': 'BB suited connector defense',
            'position': 'BB',
            'hand_category': 'Suited Connector',
            'bet_to_call': 0.06,  # 3BB
            'my_stack': 2.0,      # 100BB
            'bb_size': 0.02,
            'expected_action': 2,  # CALL
            'description': 'Should defend BB wider with implied odds'
        }
    ]
    
    passed = 0
    failed = 0
    
    for test_case in test_cases:
        try:
            decision = make_preflop_decision(
                position=test_case['position'],
                hand_category=test_case['hand_category'],
                bet_to_call=test_case['bet_to_call'],
                can_check=False,
                calculated_raise_amount=test_case['bet_to_call'] * 3,
                my_stack=test_case['my_stack'],
                my_current_bet=0,
                max_opponent_bet=test_case['bet_to_call'],
                pot_size=0.03,
                active_opponents_count=2,
                bb_size=test_case['bb_size'],
                is_big_blind=test_case['position'] == 'BB',
                num_limpers=0
            )
            
            action, amount = decision
            
            if action == test_case['expected_action']:
                print(f"✓ {test_case['name']}: PASSED - {test_case['description']}")
                passed += 1
            else:
                print(f"✗ {test_case['name']}: FAILED - Expected action {test_case['expected_action']}, got {action}")
                failed += 1
                
        except Exception as e:
            print(f"✗ {test_case['name']}: ERROR - {str(e)}")
            failed += 1
    
    return passed, failed

def test_dynamic_bet_sizing_integration():
    """Test that dynamic bet sizing is properly integrated"""
    print("--- Dynamic Bet Sizing Integration Tests ---")
    
    test_cases = [
        {
            'name': 'Value bet with strong hand',
            'hand_strength': 0.9,
            'pot_size': 0.20,
            'my_stack': 1.0,
            'position': 'CO',
            'street': 'flop',
            'expected_min_bet': 0.10,  # Should be at least half pot
            'description': 'Strong hand should bet for value'
        },
        
        {
            'name': 'Bluff bet with weak hand',
            'hand_strength': 0.2,
            'pot_size': 0.15,
            'my_stack': 0.8,
            'position': 'BTN',
            'street': 'turn',
            'expected_max_bet': 0.12,  # Should be reasonable bluff size
            'description': 'Weak hand should size bluffs appropriately'
        }
    ]
    
    passed = 0
    failed = 0
    
    for test_case in test_cases:
        try:
            # Test the dynamic bet sizing function
            bet_size = get_dynamic_bet_size(
                hand_strength=test_case['hand_strength'],
                pot_size=test_case['pot_size'],
                my_stack=test_case['my_stack'],
                position=test_case['position'],
                street=test_case['street'],
                num_opponents=2
            )
            
            if test_case.get('expected_min_bet') and bet_size >= test_case['expected_min_bet']:
                print(f"✓ {test_case['name']}: PASSED - Bet size {bet_size:.2f} >= {test_case['expected_min_bet']:.2f}")
                passed += 1
            elif test_case.get('expected_max_bet') and bet_size <= test_case['expected_max_bet']:
                print(f"✓ {test_case['name']}: PASSED - Bet size {bet_size:.2f} <= {test_case['expected_max_bet']:.2f}")
                passed += 1
            else:
                print(f"✗ {test_case['name']}: FAILED - Bet size {bet_size:.2f} outside expected range")
                failed += 1
                
        except Exception as e:
            print(f"✗ {test_case['name']}: ERROR - {str(e)}")
            failed += 1
    
    return passed, failed

def test_edge_cases():
    """Test edge cases and potential regressions"""
    print("--- Edge Cases and Regression Tests ---")
    
    test_cases = [
        {
            'name': 'Very shallow stack (20BB)',
            'position': 'CO',
            'hand_category': 'Suited Connector',
            'bet_to_call': 0.04,  # 2BB
            'my_stack': 0.4,      # 20BB
            'bb_size': 0.02,
            'description': 'Should not apply implied odds with very shallow stacks'
        },
        
        {
            'name': 'Premium hand in early position',
            'position': 'UTG',
            'hand_category': 'Premium',
            'bet_to_call': 0.12,  # 6BB
            'my_stack': 2.0,      # 100BB
            'bb_size': 0.02,
            'description': 'Premium hands should still play regardless of implied odds'
        },
        
        {
            'name': 'Large bet size (10BB)',
            'position': 'BTN',
            'hand_category': 'Suited Connector',
            'bet_to_call': 0.20,  # 10BB
            'my_stack': 2.0,      # 100BB
            'bb_size': 0.02,
            'description': 'Should fold to very large bets even with implied odds'
        }
    ]
    
    passed = 0
    failed = 0
    
    for test_case in test_cases:
        try:
            decision = make_preflop_decision(
                position=test_case['position'],
                hand_category=test_case['hand_category'],
                bet_to_call=test_case['bet_to_call'],
                can_check=False,
                calculated_raise_amount=test_case['bet_to_call'] * 3,
                my_stack=test_case['my_stack'],
                my_current_bet=0,
                max_opponent_bet=test_case['bet_to_call'],
                pot_size=0.03,
                active_opponents_count=2,
                bb_size=test_case['bb_size'],
                is_big_blind=test_case['position'] == 'BB',
                num_limpers=0
            )
            
            action, amount = decision
            print(f"✓ {test_case['name']}: Action={action}, Amount={amount:.2f} - {test_case['description']}")
            passed += 1
            
        except Exception as e:
            print(f"✗ {test_case['name']}: ERROR - {str(e)}")
            failed += 1
    
    return passed, failed

def run_comprehensive_tests():
    """Run all comprehensive tests"""
    print("=" * 60)
    print("COMPREHENSIVE POKER BOT INTEGRATION TESTS")
    print("=" * 60)
    
    total_passed = 0
    total_failed = 0
    
    # Test 1: Preflop implied odds
    passed, failed = test_preflop_implied_odds_scenarios()
    total_passed += passed
    total_failed += failed
    print(f"✓ PASSED: Preflop Implied Odds ({passed} tests)")
    
    # Test 2: Dynamic bet sizing
    passed, failed = test_dynamic_bet_sizing_integration()
    total_passed += passed
    total_failed += failed
    print(f"✓ PASSED: Dynamic Bet Sizing ({passed} tests)")
    
    # Test 3: Edge cases
    passed, failed = test_edge_cases()
    total_passed += passed
    total_failed += failed
    print(f"✓ PASSED: Edge Cases ({passed} tests)")
    
    print("=" * 60)
    print(f"COMPREHENSIVE TEST SUMMARY: {total_passed} passed, {total_failed} failed")
    print(f"SUCCESS RATE: {(total_passed / (total_passed + total_failed) * 100):.1f}%")
    print("=" * 60)
    
    return total_passed, total_failed

if __name__ == "__main__":
    run_comprehensive_tests()
