#!/usr/bin/env python3
"""
Comprehensive equity test to verify the fixes work in various scenarios
"""

from equity_calculator import EquityCalculator

def test_comprehensive_equity():
    print("=== Comprehensive Equity Calculator Test ===")
    calc = EquityCalculator()
    
    test_cases = [
        {
            'name': 'Pocket Aces preflop',
            'hole_cards': ['A♠', 'A♥'],
            'community_cards': [],
            'expected_range': (0.80, 0.90)  # Should be around 85%
        },
        {
            'name': 'Pocket Kings preflop', 
            'hole_cards': ['K♠', 'K♥'],
            'community_cards': [],
            'expected_range': (0.75, 0.85)  # Should be around 82%
        },
        {
            'name': 'AK suited preflop',
            'hole_cards': ['A♠', 'K♠'],
            'community_cards': [],
            'expected_range': (0.25, 0.35)  # Should be around 31%
        },
        {
            'name': 'Pocket Aces on flop',
            'hole_cards': ['A♠', 'A♥'],
            'community_cards': ['2♦', '7♣', 'J♠'],
            'expected_range': (0.85, 0.95)  # Should be very high
        },
        {
            'name': 'Weak hand on flop',
            'hole_cards': ['2♠', '7♥'],
            'community_cards': ['A♦', 'K♣', 'Q♠'],
            'expected_range': (0.0, 0.15)   # Should be very low
        }
    ]
    
    all_passed = True
    
    for i, test in enumerate(test_cases):
        print(f"\nTest {i+1}: {test['name']}")
        print(f"Cards: {test['hole_cards']} | Board: {test['community_cards']}")
        
        try:
            win_prob = calc.calculate_win_probability(
                test['hole_cards'], 
                test['community_cards'], 
                1
            )
            
            min_expected, max_expected = test['expected_range']
            passed = min_expected <= win_prob <= max_expected
            
            print(f"Win probability: {win_prob:.3f} ({win_prob*100:.1f}%)")
            print(f"Expected range: {min_expected:.3f}-{max_expected:.3f} ({min_expected*100:.1f}%-{max_expected*100:.1f}%)")
            print(f"Result: {'PASS' if passed else 'FAIL'}")
            
            if not passed:
                all_passed = False
                
        except Exception as e:
            print(f"ERROR: {e}")
            all_passed = False
    
    print(f"\n=== Overall Result: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'} ===")
    return all_passed

if __name__ == "__main__":
    test_comprehensive_equity()
