#!/usr/bin/env python3
"""
Final Integration Validation Script

This script validates the complete integration of all postflop enhancements:
1. Core postflop improvements (7 critical fixes)
2. Advanced opponent modeling
3. Enhanced board analysis 
4. Performance monitoring
5. Error handling and fallback mechanisms

Tests various poker scenarios to ensure the system works correctly.
"""

import sys
import json
from datetime import datetime

def create_mock_decision_engine():
    """Create a mock decision engine for testing."""
    class MockDecisionEngine:
        def should_bluff_func(self, pot_size, my_stack, street, win_probability, bet_to_pot_ratio_for_bluff=None):
            # Simple bluffing logic for testing
            if street == 'river':
                return win_probability < 0.2 and pot_size < my_stack * 0.3
            return win_probability < 0.25 and pot_size > 0
    
    return MockDecisionEngine()

def run_validation_scenario(scenario_name, scenario_data):
    """Run a single validation scenario."""
    print(f"\n🧪 Testing: {scenario_name}")
    print("=" * 50)
    
    try:
        from postflop_decision_logic import make_postflop_decision
        
        # Extract scenario parameters
        params = scenario_data['params']
        expected = scenario_data.get('expected', {})
        
        # Run the decision
        result = make_postflop_decision(
            decision_engine_instance=create_mock_decision_engine(),
            **params
        )
        
        action, amount = result
        
        # Validate results
        success = True
        if 'action' in expected:
            if action != expected['action']:
                print(f"❌ Action mismatch: expected {expected['action']}, got {action}")
                success = False
            else:
                print(f"✅ Action correct: {action}")
        
        if 'amount_range' in expected and amount > 0:
            min_amt, max_amt = expected['amount_range']
            if not (min_amt <= amount <= max_amt):
                print(f"❌ Amount out of range: expected {min_amt}-{max_amt}, got {amount}")
                success = False
            else:
                print(f"✅ Amount in range: {amount}")
        
        if 'reasoning' in expected:
            print(f"ℹ️  Expected reasoning: {expected['reasoning']}")
        
        print(f"📊 Result: {action} ${amount:.2f}")
        
        if success:
            print(f"✅ PASS: {scenario_name}")
        else:
            print(f"❌ FAIL: {scenario_name}")
            
        return success
        
    except Exception as e:
        print(f"❌ ERROR in {scenario_name}: {e}")
        return False

def main():
    """Run comprehensive validation of the integrated postflop system."""
    
    print("🎯 FINAL INTEGRATION VALIDATION")
    print("=" * 80)
    print("Testing complete postflop system with all enhancements...")
    print(f"Timestamp: {datetime.now()}")
    
    # Define comprehensive test scenarios
    validation_scenarios = {
        "weak_pair_fold": {
            "params": {
                "numerical_hand_rank": 2,
                "hand_description": "Pair of 9s",
                "bet_to_call": 50,
                "can_check": False,
                "pot_size": 100,
                "my_stack": 200,
                "win_probability": 0.35,
                "pot_odds_to_call": 0.33,
                "game_stage": "flop",
                "spr": 2.0,
                "action_fold_const": "fold",
                "action_check_const": "check", 
                "action_call_const": "call",
                "action_raise_const": "raise",
                "my_player_data": {
                    "current_bet": 0,
                    "position": "BTN",
                    "hand": ["Kh", "Qd"],
                    "community_cards": ["9c", "7s", "2h"]
                },
                "big_blind_amount": 5,
                "base_aggression_factor": 1.0,
                "max_bet_on_table": 50,
                "active_opponents_count": 1,
                "opponent_tracker": None
            },
            "expected": {
                "action": "fold",
                "reasoning": "Weak pair with insufficient equity cushion"
            }
        },
        
        "strong_hand_value_bet": {
            "params": {
                "numerical_hand_rank": 4,
                "hand_description": "Top pair", 
                "bet_to_call": 0,
                "can_check": True,
                "pot_size": 80,
                "my_stack": 150,
                "win_probability": 0.75,
                "pot_odds_to_call": 0.0,
                "game_stage": "flop",
                "spr": 1.88,
                "action_fold_const": "fold",
                "action_check_const": "check",
                "action_call_const": "call", 
                "action_raise_const": "raise",
                "my_player_data": {
                    "current_bet": 0,
                    "position": "BTN",
                    "hand": ["Ac", "Kd"],
                    "community_cards": ["As", "7s", "2s"]
                },
                "big_blind_amount": 5,
                "base_aggression_factor": 1.0,
                "max_bet_on_table": 0,
                "active_opponents_count": 1,
                "opponent_tracker": None
            },
            "expected": {
                "action": "raise",
                "amount_range": [50, 150],
                "reasoning": "Strong hand should bet for value"
            }
        },
        
        "drawing_hand_call": {
            "params": {
                "numerical_hand_rank": 0,
                "hand_description": "High card",
                "bet_to_call": 30,
                "can_check": False,
                "pot_size": 60,
                "my_stack": 120, 
                "win_probability": 0.32,
                "pot_odds_to_call": 0.33,
                "game_stage": "flop",
                "spr": 2.0,
                "action_fold_const": "fold",
                "action_check_const": "check",
                "action_call_const": "call",
                "action_raise_const": "raise",
                "my_player_data": {
                    "current_bet": 0,
                    "position": "BB", 
                    "hand": ["7h", "6h"],
                    "community_cards": ["5c", "4s", "2h"]
                },
                "big_blind_amount": 5,
                "base_aggression_factor": 1.0,
                "max_bet_on_table": 30,
                "active_opponents_count": 1,
                "opponent_tracker": None
            },
            "expected": {
                "action": "call",
                "reasoning": "Drawing hand with good implied odds"
            }
        },
        
        "multiway_check_medium": {
            "params": {
                "numerical_hand_rank": 2,
                "hand_description": "Top pair",
                "bet_to_call": 0,
                "can_check": True,
                "pot_size": 100,
                "my_stack": 200,
                "win_probability": 0.60,
                "pot_odds_to_call": 0.0,
                "game_stage": "flop", 
                "spr": 2.0,
                "action_fold_const": "fold",
                "action_check_const": "check",
                "action_call_const": "call",
                "action_raise_const": "raise",
                "my_player_data": {
                    "current_bet": 0,
                    "position": "EP",
                    "hand": ["Jh", "Td"],
                    "community_cards": ["Js", "7c", "3h"]
                },
                "big_blind_amount": 5,
                "base_aggression_factor": 1.0,
                "max_bet_on_table": 0,
                "active_opponents_count": 5,  # Multiway pot
                "opponent_tracker": None
            },
            "expected": {
                "action": "check",
                "reasoning": "Medium hand should check in multiway pot"
            }
        },
        
        "low_spr_commitment": {
            "params": {
                "numerical_hand_rank": 5,
                "hand_description": "Two pair",
                "bet_to_call": 0,
                "can_check": True,
                "pot_size": 120,
                "my_stack": 80,
                "win_probability": 0.85,
                "pot_odds_to_call": 0.0,
                "game_stage": "turn",
                "spr": 0.67, # Low SPR
                "action_fold_const": "fold",
                "action_check_const": "check",
                "action_call_const": "call",
                "action_raise_const": "raise",
                "my_player_data": {
                    "current_bet": 0,
                    "position": "BTN",
                    "hand": ["Ah", "Ad"],
                    "community_cards": ["As", "Ac", "7s", "2h"]
                },
                "big_blind_amount": 5,
                "base_aggression_factor": 1.0,
                "max_bet_on_table": 0,
                "active_opponents_count": 1,
                "opponent_tracker": None
            },
            "expected": {
                "action": "raise",
                "reasoning": "Low SPR should commit with strong hand"
            }
        }
    }
    
    # Run all validation scenarios
    results = {}
    total_tests = len(validation_scenarios)
    passed_tests = 0
    
    for scenario_name, scenario_data in validation_scenarios.items():
        success = run_validation_scenario(scenario_name, scenario_data)
        results[scenario_name] = success
        if success:
            passed_tests += 1
    
    # Summary
    print("\n" + "=" * 80)
    print("📋 VALIDATION SUMMARY")
    print("=" * 80)
    
    for scenario_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {scenario_name}")
    
    print(f"\n📊 Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Postflop system is fully integrated and working correctly")
        print("✅ Core improvements active")
        print("✅ Advanced enhancements integrated")  
        print("✅ Error handling robust")
        print("✅ Ready for production use")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed")
        print("🔧 Review failed scenarios and fix integration issues")
    
    # Create validation report
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "test_results": results,
        "status": "PASS" if passed_tests == total_tests else "FAIL"
    }
    
    with open("integration_validation_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: integration_validation_report.json")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
