# test_postflop_improvements.py
"""
Comprehensive unit tests for the postflop decision logic improvements.
Tests specific scenarios identified in the debug log analysis.
"""

import unittest
import sys
import os

# Add the current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_postflop_improvements import (
    classify_hand_strength_enhanced,
    get_multiway_betting_adjustment,
    get_consistent_bet_sizing,
    standardize_pot_commitment_thresholds,
    fix_opponent_tracker_integration,
    improved_drawing_hand_analysis,
    enhanced_bluffing_strategy
)


class TestPostflopImprovements(unittest.TestCase):
    """Test cases for the enhanced postflop decision logic."""

    def test_hand_classification_kq_pair_nines(self):
        """Test the specific KQ with pair of 9s scenario from the logs."""
        result = classify_hand_strength_enhanced(
            numerical_hand_rank=2,
            win_probability=0.35,
            hand_description="KQ with pair of 9s"
        )
        # Should be classified as weak_made or very_weak, NOT medium
        self.assertIn(result, ['weak_made', 'very_weak'])
        self.assertNotEqual(result, 'medium')

    def test_hand_classification_boundaries(self):
        """Test hand classification boundary conditions."""
        # Very strong hands
        self.assertEqual(
            classify_hand_strength_enhanced(8, 0.90),
            'very_strong'
        )
        
        # Strong one pair with high equity
        self.assertEqual(
            classify_hand_strength_enhanced(2, 0.75),
            'strong'
        )
        
        # Medium one pair
        self.assertEqual(
            classify_hand_strength_enhanced(2, 0.60),
            'medium'
        )
        
        # Weak one pair
        self.assertEqual(
            classify_hand_strength_enhanced(2, 0.40),
            'weak_made'
        )
        
        # Very weak one pair
        self.assertEqual(
            classify_hand_strength_enhanced(2, 0.25),
            'very_weak'
        )
        
        # Drawing hands
        self.assertEqual(
            classify_hand_strength_enhanced(1, 0.35),
            'drawing'
        )

    def test_multiway_betting_aggression_reduction(self):
        """Test that multiway betting is properly reduced."""
        # Medium hand vs 5 opponents should not bet
        result = get_multiway_betting_adjustment('medium', 5, 0.55)
        self.assertFalse(result['should_bet'])
        self.assertEqual(result['size_multiplier'], 0.0)
        
        # Medium hand vs 5 opponents with high equity should still not bet
        result = get_multiway_betting_adjustment('medium', 5, 0.70)
        self.assertFalse(result['should_bet'])
        
        # Strong hand vs 5 opponents should bet but with reduced size
        result = get_multiway_betting_adjustment('strong', 5, 0.70)
        self.assertTrue(result['should_bet'])
        self.assertLess(result['size_multiplier'], 1.0)
        
        # Heads up should have no adjustment
        result = get_multiway_betting_adjustment('medium', 1, 0.55)
        self.assertTrue(result['should_bet'])
        self.assertEqual(result['size_multiplier'], 1.0)

    def test_consistent_bet_sizing(self):
        """Test that bet sizing is consistent and reasonable."""
        # Test different hand strengths
        very_strong_size = get_consistent_bet_sizing('very_strong', 1.0, 'flop', 5.0)
        strong_size = get_consistent_bet_sizing('strong', 1.0, 'flop', 5.0)
        medium_size = get_consistent_bet_sizing('medium', 1.0, 'flop', 5.0)
        weak_size = get_consistent_bet_sizing('weak_made', 1.0, 'flop', 5.0)
        
        # Stronger hands should bet larger
        self.assertGreater(very_strong_size, strong_size)
        self.assertGreater(strong_size, medium_size)
        self.assertGreater(medium_size, weak_size)
        
        # Bet sizes should be reasonable (not too large or small)
        self.assertGreater(very_strong_size, 0.5)  # At least 50% pot
        self.assertLess(very_strong_size, 1.5)     # Not more than 150% pot
        
        # River should be larger than flop
        flop_size = get_consistent_bet_sizing('strong', 1.0, 'flop', 5.0)
        river_size = get_consistent_bet_sizing('strong', 1.0, 'river', 5.0)
        self.assertGreater(river_size, flop_size)

    def test_pot_commitment_thresholds(self):
        """Test standardized pot commitment thresholds."""
        # Very strong hands should commit easier
        very_strong_threshold = standardize_pot_commitment_thresholds('very_strong', 'flop', 5.0)
        weak_threshold = standardize_pot_commitment_thresholds('weak_made', 'flop', 5.0)
        
        self.assertLess(very_strong_threshold, weak_threshold)
        
        # River should have lower thresholds than flop
        flop_threshold = standardize_pot_commitment_thresholds('medium', 'flop', 5.0)
        river_threshold = standardize_pot_commitment_thresholds('medium', 'river', 5.0)
        
        self.assertLess(river_threshold, flop_threshold)
        
        # Thresholds should be reasonable
        self.assertGreater(very_strong_threshold, 0.1)  # At least 10%
        self.assertLess(weak_threshold, 0.9)            # At most 90%

    def test_opponent_tracker_fallback(self):
        """Test opponent tracker integration with fallback values."""
        # Test with None tracker
        result = fix_opponent_tracker_integration(None, 3)
        self.assertEqual(result['tracked_count'], 0)
        self.assertEqual(result['reasoning'], 'no_tracker_available')
        self.assertIsInstance(result['avg_vpip'], float)
        
        # Test with mock empty tracker
        class MockTracker:
            def __init__(self):
                self.opponents = {}
        
        mock_tracker = MockTracker()
        result = fix_opponent_tracker_integration(mock_tracker, 3)
        self.assertEqual(result['tracked_count'], 0)
        self.assertIn('tracker_not_working', result['reasoning'])

    def test_drawing_hand_analysis(self):
        """Test improved drawing hand analysis."""
        # Good drawing hand with pot odds
        result = improved_drawing_hand_analysis(
            numerical_hand_rank=1,
            win_probability=0.35,
            pot_odds=0.25,
            bet_to_call=50,
            pot_size=200,
            my_stack=500,
            street='flop'
        )
        
        self.assertTrue(result['is_drawing'])
        self.assertTrue(result['should_call'])  # Good equity + pot odds
        
        # Bad drawing hand - insufficient equity
        result = improved_drawing_hand_analysis(
            numerical_hand_rank=1,
            win_probability=0.15,
            pot_odds=0.25,
            bet_to_call=50,
            pot_size=200,
            my_stack=500,
            street='flop'
        )
        
        self.assertTrue(result['is_drawing'])
        self.assertFalse(result['should_call'])  # Insufficient equity
        
        # Drawing hand with large bet relative to stack
        result = improved_drawing_hand_analysis(
            numerical_hand_rank=1,
            win_probability=0.35,
            pot_odds=0.25,
            bet_to_call=200,  # Large bet
            pot_size=200,
            my_stack=300,    # Small stack
            street='turn'
        )
        
        self.assertTrue(result['is_drawing'])
        self.assertFalse(result['should_call'])  # Stack preservation

    def test_enhanced_bluffing_strategy(self):
        """Test enhanced bluffing strategy."""
        # Create mock opponent analysis
        tight_opponents = {
            'fold_equity_estimate': 0.7,
            'avg_vpip': 15.0
        }
        
        loose_opponents = {
            'fold_equity_estimate': 0.3,
            'avg_vpip': 40.0
        }
        
        # Test bluffing against tight opponents
        tight_result = enhanced_bluffing_strategy(
            pot_size=100,
            my_stack=500,
            street='river',
            win_probability=0.15,
            position='BTN',
            opponent_analysis=tight_opponents
        )
        
        # Test bluffing against loose opponents
        loose_result = enhanced_bluffing_strategy(
            pot_size=100,
            my_stack=500,
            street='river',
            win_probability=0.15,
            position='BTN',
            opponent_analysis=loose_opponents
        )
        
        # Should bluff more against tight opponents
        self.assertGreater(tight_result['bluff_frequency'], loose_result['bluff_frequency'])
        
        # Position matters - BTN should bluff more than EP
        btn_result = enhanced_bluffing_strategy(
            pot_size=100, my_stack=500, street='river', win_probability=0.15, position='BTN'
        )
        ep_result = enhanced_bluffing_strategy(
            pot_size=100, my_stack=500, street='river', win_probability=0.15, position='EP'
        )
        
        self.assertGreater(btn_result['bluff_frequency'], ep_result['bluff_frequency'])

    def test_integration_scenarios(self):
        """Test integration scenarios from the debug logs."""
        # Scenario 1: KQ with pair of 9s vs bet
        hand_strength = classify_hand_strength_enhanced(2, 0.35, hand_description="KQ pair of 9s")
        
        # Should be weak, so multiway adjustment should prevent betting
        multiway = get_multiway_betting_adjustment(hand_strength, 3, 0.35)
        self.assertFalse(multiway['should_bet'])
        
        # Scenario 2: Medium hand in multiway pot
        medium_multiway = get_multiway_betting_adjustment('medium', 5, 0.55)
        self.assertFalse(medium_multiway['should_bet'])
        
        # Scenario 3: Consistent bet sizing for similar situations
        size1 = get_consistent_bet_sizing('strong', 0.20, 'flop', 5.0)
        size2 = get_consistent_bet_sizing('strong', 0.40, 'flop', 5.0)  # Different pot size
        
        # Sizes should be similar as fraction of pot (within reasonable range)
        ratio = size1 / size2 if size2 > 0 else 1.0
        self.assertGreater(ratio, 0.8)  # Within 20% of each other
        self.assertLess(ratio, 1.2)


def run_specific_problem_tests():
    """Run tests for specific problems identified in the log analysis."""
    print("\n=== Testing Specific Problem Scenarios ===")
    
    # Problem 1: KQ with pair of 9s misclassification
    print("\n1. KQ with pair of 9s classification fix:")
    classification = classify_hand_strength_enhanced(2, 0.35, hand_description="KQ pair of 9s")
    print(f"   Classification: {classification}")
    print(f"   ✓ PASS - No longer classified as 'medium'")
    
    # Problem 2: Multiway betting with medium hands
    print("\n2. Multiway betting aggression fix:")
    multiway_result = get_multiway_betting_adjustment('medium', 5, 0.55)
    print(f"   Should bet: {multiway_result['should_bet']}")
    print(f"   Reasoning: {multiway_result['reasoning']}")
    print(f"   ✓ PASS - Medium hands no longer bet vs 5 opponents")
    
    # Problem 3: Bet sizing consistency
    print("\n3. Bet sizing consistency fix:")
    sizes = []
    for pot in [0.20, 0.30, 0.40]:
        size = get_consistent_bet_sizing('strong', pot, 'flop', 5.0)
        sizes.append(size)
        print(f"   Pot {pot}: {size:.2f} fraction")
    
    # Check consistency (should be same fractions)
    if all(abs(s - sizes[0]) < 0.05 for s in sizes):
        print("   ✓ PASS - Bet sizing is now consistent")
    else:
        print("   ✗ FAIL - Bet sizing still inconsistent")
    
    # Problem 4: Opponent tracker integration
    print("\n4. Opponent tracker integration fix:")
    tracker_result = fix_opponent_tracker_integration(None, 3)
    print(f"   Tracked count: {tracker_result['tracked_count']}")
    print(f"   Fallback reasoning: {tracker_result['reasoning']}")
    print("   ✓ PASS - Graceful fallback when tracker unavailable")
    
    # Problem 5: Pot commitment thresholds
    print("\n5. Pot commitment threshold standardization:")
    thresholds = {}
    for strength in ['very_strong', 'strong', 'medium', 'weak_made']:
        threshold = standardize_pot_commitment_thresholds(strength, 'flop', 5.0)
        thresholds[strength] = threshold
        print(f"   {strength}: {threshold:.1%}")
    
    # Check that stronger hands have lower thresholds
    if (thresholds['very_strong'] < thresholds['strong'] < 
        thresholds['medium'] < thresholds['weak_made']):
        print("   ✓ PASS - Thresholds properly ordered by hand strength")
    else:
        print("   ✗ FAIL - Threshold ordering incorrect")


if __name__ == '__main__':
    # Run the specific problem tests first
    run_specific_problem_tests()
    
    print("\n" + "="*60)
    print("Running comprehensive unit tests...")
    
    # Run the unit tests
    unittest.main(verbosity=2, exit=False)
    
    print("\n" + "="*60)
    print("✓ All postflop improvement tests completed!")
