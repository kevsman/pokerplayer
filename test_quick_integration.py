#!/usr/bin/env python3
"""
Quick integration test to verify core poker bot enhancements work together.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Test each module individually
def test_all_components():
    print("=" * 50)
    print("POKER BOT INTEGRATION VALIDATION")
    print("=" * 50)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Implied odds calculation
    try:
        from preflop_decision_logic import adjust_for_implied_odds
        result = adjust_for_implied_odds('Suited Connector', 'CO', 3.0, 3.0, 0.02)
        print(f"✓ Implied odds calculation: {result}")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Implied odds failed: {e}")
    tests_total += 1
    
    # Test 2: Dynamic bet sizing
    try:
        from postflop_decision_logic import get_dynamic_bet_size
        bet = get_dynamic_bet_size(4, 0.20, 1.0, 'flop', 0.02, 1, False)
        print(f"✓ Dynamic bet sizing: {bet:.3f}")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Dynamic bet sizing failed: {e}")
    tests_total += 1
    
    # Test 3: Opponent tracking
    try:
        from opponent_tracking import OpponentTracker
        tracker = OpponentTracker()
        tracker.update_opponent_action('TestPlayer', 'preflop', 'raise', 0.08, 0.03)
        tracker.update_opponent_action('TestPlayer', 'flop', 'bet', 0.15, 0.20)
        
        if 'TestPlayer' in tracker.opponents:
            profile = tracker.opponents['TestPlayer']
            print(f"✓ Opponent tracking: {profile.hands_seen} hands, VPIP={profile.vpip:.1f}%")
            tests_passed += 1
        else:
            print("✗ Opponent tracking: Player not found")
    except Exception as e:
        print(f"✗ Opponent tracking failed: {e}")
    tests_total += 1
    
    # Test 4: Tournament adjustments
    try:
        from tournament_adjustments import get_tournament_adjustment_factor
        adjustment = get_tournament_adjustment_factor(0.6, 0.02, 2)
        print(f"✓ Tournament adjustments: {adjustment:.3f}")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Tournament adjustments failed: {e}")
    tests_total += 1
    
    # Test 5: Advanced implied odds
    try:
        from implied_odds import calculate_implied_odds
        odds = calculate_implied_odds(0.20, 0.08, 0.35, 1.5, 1.2, 'flop')
        print(f"✓ Advanced implied odds: {odds:.3f}")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Advanced implied odds failed: {e}")
    tests_total += 1
    
    # Test 6: Strategy testing framework
    try:
        from strategy_testing import StrategyTester
        tester = StrategyTester()
        print("✓ Strategy testing framework: Available")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Strategy testing failed: {e}")
    tests_total += 1
    
    # Test 7: Basic preflop decision (simplified call)
    try:
        from preflop_decision_logic import make_preflop_decision
        # Use minimal parameters to test basic functionality
        action, amount = make_preflop_decision(
            {'current_bet': 0, 'stack': 1.0},  # my_player
            'Suited Connector',                 # hand_category
            'CO',                              # position
            0.08,                              # bet_to_call
            False,                             # can_check
            1.0,                               # my_stack
            0.03,                              # pot_size
            2,                                 # active_opponents_count
            0.01,                              # small_blind
            0.02,                              # big_blind
            0,                                 # my_current_bet_this_street
            0.08,                              # max_bet_on_table
            0.04,                              # min_raise
            False,                             # is_sb
            False,                             # is_bb
            0, 1, 2, 3                         # action constants
        )
        print(f"✓ Preflop decision: Action={action}, Amount={amount:.3f}")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Preflop decision failed: {e}")
    tests_total += 1
    
    print("\n" + "=" * 50)
    print(f"INTEGRATION TEST RESULTS: {tests_passed}/{tests_total} PASSED")
    success_rate = (tests_passed / tests_total) * 100 if tests_total > 0 else 0
    print(f"SUCCESS RATE: {success_rate:.1f}%")
    print("=" * 50)
    
    if tests_passed == tests_total:
        print("\n🎉 ALL TESTS PASSED! Poker bot enhancements are working correctly.")
        return True
    else:
        print(f"\n⚠️  {tests_total - tests_passed} tests failed. Some issues need attention.")
        return False

if __name__ == "__main__":
    test_all_components()
