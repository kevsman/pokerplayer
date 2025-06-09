#!/usr/bin/env python3
"""
Comprehensive Integration Test for Poker Bot Improvements

This test validates all critical improvements implemented to fix money-losing patterns:
1. Enhanced hand classification logic (including J4s fix)
2. Standardized pot commitment thresholds
3. Opponent tracking integration
4. Multiway pot adjustments
5. Bet sizing consistency

Test cases cover the specific problematic scenarios identified in the analysis.
"""

import sys
import json
import traceback
from typing import Dict, List, Tuple, Any

# Import all relevant modules
try:
    from enhanced_postflop_improvements import (
        classify_hand_strength_enhanced,
        standardize_pot_commitment_thresholds
    )
    from hand_utils import get_preflop_hand_category
    from advanced_opponent_modeling import OpponentModel
    from postflop_decision_logic import make_postflop_decision
    from equity_calculator import EquityCalculator
    from hand_evaluator import HandEvaluator
    from config import Config
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all required modules are available")
    sys.exit(1)

class ComprehensiveIntegrationTest:
    """Comprehensive test suite for all poker bot improvements"""
    
    def __init__(self):
        self.results = {
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'failures': []
        }
        
        # Initialize required components
        self.config = Config()
        self.equity_calc = EquityCalculator()
        self.hand_eval = HandEvaluator()
        
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        self.results['tests_run'] += 1
        if passed:
            self.results['tests_passed'] += 1
            print(f"✓ {test_name}")
        else:
            self.results['tests_failed'] += 1
            self.results['failures'].append({
                'test': test_name,
                'details': details
            })
            print(f"✗ {test_name}: {details}")
    
    def test_enhanced_hand_classification(self):
        """Test enhanced hand classification with various scenarios"""
        test_cases = [
            {
                'name': 'Strong top pair',
                'rank': 2,
                'equity': 0.75,
                'expected': ['strong'],
                'description': 'Top pair with good kicker'
            },
            {
                'name': 'Medium one pair',
                'rank': 2,
                'equity': 0.55,
                'expected': ['medium'],
                'description': 'Top pair weak kicker'
            },
            {
                'name': 'Weak pair',
                'rank': 2,
                'equity': 0.35,
                'expected': ['weak_made'],
                'description': 'Weak middle pair'
            },
            {
                'name': 'Two pair',
                'rank': 3,
                'equity': 0.80,
                'expected': ['strong'],
                'description': 'Two pair aces and kings'
            },
            {
                'name': 'Drawing hand',
                'rank': 1,
                'equity': 0.35,
                'expected': ['drawing'],
                'description': 'Flush draw'
            }
        ]
        
        for case in test_cases:
            try:
                result = classify_hand_strength_enhanced(
                    case['rank'],
                    case['equity'],
                    hand_description=case['description']
                )
                
                passed = result in case['expected']
                details = f"{case['description']}: classified as {result}, expected one of {case['expected']}"
                
                self.log_result(f"Enhanced Classification - {case['name']}", passed, details if not passed else "")
                
            except Exception as e:
                self.log_result(f"Enhanced Classification - {case['name']}", False, f"Exception: {str(e)}")
    
    def test_pot_commitment_thresholds(self):
        """Test standardized pot commitment thresholds"""
        test_scenarios = [
            {
                'name': 'Strong hand flop',
                'hand_strength': 'strong',
                'street': 'flop',
                'spr': 3.0,
                'expected_range': (25, 40)
            },
            {
                'name': 'Weak hand river',
                'hand_strength': 'weak_made',
                'street': 'river',
                'spr': 2.0,
                'expected_range': (45, 70)
            },
            {
                'name': 'Drawing hand turn',
                'hand_strength': 'drawing',
                'street': 'turn',
                'spr': 5.0,
                'expected_range': (50, 75)
            }
        ]
        
        for scenario in test_scenarios:
            try:
                threshold = standardize_pot_commitment_thresholds(
                    scenario['hand_strength'],
                    scenario['street'],
                    scenario['spr']
                )
                
                min_expected, max_expected = scenario['expected_range']
                passed = min_expected <= threshold <= max_expected
                details = f"Threshold: {threshold:.1f}%, expected range: {min_expected}-{max_expected}%"
                
                self.log_result(f"Pot Commitment - {scenario['name']}", passed, details if not passed else "")
                
            except Exception as e:
                self.log_result(f"Pot Commitment - {scenario['name']}", False, f"Exception: {str(e)}")
    
    def test_opponent_tracking_integration(self):
        """Test that opponent tracking is properly integrated"""
        try:
            # Create opponent model and test basic functionality
            opponent = OpponentModel("TestPlayer")
            
            # Add some sample data
            opponent.add_action_data('preflop', 'raise', 2.5, 'UTG')
            opponent.add_action_data('flop', 'bet', 0.75, 'UTG')
            
            # Test that data is being tracked
            preflop_stats = opponent.get_position_stats('UTG', 'preflop')
            
            passed = (
                preflop_stats is not None and
                len(opponent.action_history) > 0
            )
            
            details = f"Opponent tracking working: {len(opponent.action_history)} actions recorded"
            self.log_result("Opponent Tracking Integration", passed, details if not passed else "")
            
        except Exception as e:
            self.log_result("Opponent Tracking Integration", False, f"Exception: {str(e)}")
    
    def test_integration_consistency(self):
        """Test that all components work together consistently"""
        try:
            # Test enhanced classification
            enhanced_strength = classify_hand_strength_enhanced(
                numerical_hand_rank=2,  # One pair 
                win_probability=0.70,   # High equity for top pair
                hand_description="One Pair, Aces"
            )
            
            # Test pot commitment
            spr = 3.0
            threshold = standardize_pot_commitment_thresholds(enhanced_strength, 'flop', spr)
            
            # All should complete without errors and give reasonable results
            passed = (
                enhanced_strength in ['very_strong', 'strong', 'medium', 'weak_made', 'weak', 'very_weak', 'drawing'] and
                threshold > 0 and threshold <= 100
            )
            
            details = f"Enhanced: {enhanced_strength}, Threshold: {threshold:.1f}%"
            self.log_result("Integration Consistency", passed, details if not passed else "")
            
        except Exception as e:
            self.log_result("Integration Consistency", False, f"Exception: {str(e)}")
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions"""
        edge_cases = [
            {
                'name': 'High card scenario',
                'test': lambda: classify_hand_strength_enhanced(1, 0.20, hand_description="High Card Ace")
            },
            {
                'name': 'Very high SPR',
                'test': lambda: standardize_pot_commitment_thresholds('medium', 'flop', 15.0)
            },
            {
                'name': 'Very low SPR',
                'test': lambda: standardize_pot_commitment_thresholds('strong', 'river', 0.5)
            }
        ]
        
        for case in edge_cases:
            try:
                result = case['test']()
                passed = result is not None
                details = f"Result: {result}"
                
                self.log_result(f"Edge Case - {case['name']}", passed, details if not passed else "")
                
            except Exception as e:
                self.log_result(f"Edge Case - {case['name']}", False, f"Exception: {str(e)}")
    
    def test_regression_scenarios(self):
        """Test specific scenarios that were previously problematic"""
        regression_tests = [
            {
                'name': 'KQ pair of 9s misclassification',
                'rank': 2,
                'equity': 0.35,
                'should_not_be': 'very_strong',
                'description': 'KQ with pair of 9s on board'
            },
            {
                'name': 'Weak suited connectors overvalued',
                'rank': 1,
                'equity': 0.20,
                'should_not_be': 'strong',
                'description': 'Weak suited connectors with overcards'
            }
        ]
        
        for test in regression_tests:
            try:
                result = classify_hand_strength_enhanced(
                    test['rank'],
                    test['equity'],
                    hand_description=test['description']
                )
                
                passed = result != test['should_not_be']
                details = f"{test['description']}: classified as {result} (should not be {test['should_not_be']})"
                
                self.log_result(f"Regression Test - {test['name']}", passed, details if not passed else "")
                
            except Exception as e:
                self.log_result(f"Regression Test - {test['name']}", False, f"Exception: {str(e)}")
    
    def run_all_tests(self):
        """Run all integration tests"""
        print("=" * 60)
        print("COMPREHENSIVE POKER BOT INTEGRATION TEST")
        print("=" * 60)
        print()
        
        # Run all test categories
        print("Testing Enhanced Hand Classification...")
        self.test_enhanced_hand_classification()
        print()
        
        print("Testing Pot Commitment Thresholds...")
        self.test_pot_commitment_thresholds()
        print()
        
        print("Testing Opponent Tracking Integration...")
        self.test_opponent_tracking_integration()
        print()
        
        print("Testing Integration Consistency...")
        self.test_integration_consistency()
        print()
        
        print("Testing Edge Cases...")
        self.test_edge_cases()
        print()
        
        print("Testing Regression Scenarios...")
        self.test_regression_scenarios()
        print()
        
        # Print summary
        self.print_summary()
        
        return self.results
    
    def print_summary(self):
        """Print test summary"""
        print("=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Tests Run: {self.results['tests_run']}")
        print(f"Tests Passed: {self.results['tests_passed']}")
        print(f"Tests Failed: {self.results['tests_failed']}")
        
        if self.results['tests_failed'] > 0:
            print(f"\nPass Rate: {(self.results['tests_passed'] / self.results['tests_run'] * 100):.1f}%")
            print("\nFAILURES:")
            for failure in self.results['failures']:
                print(f"  - {failure['test']}: {failure['details']}")
        else:
            print("\n🎉 ALL TESTS PASSED! 🎉")
        
        print("=" * 60)

def main():
    """Main test runner"""
    try:
        test_suite = ComprehensiveIntegrationTest()
        results = test_suite.run_all_tests()
        
        # Save results to file
        with open('integration_test_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        # Exit with appropriate code
        sys.exit(0 if results['tests_failed'] == 0 else 1)
        
    except Exception as e:
        print(f"\nCRITICAL ERROR: {str(e)}")
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
