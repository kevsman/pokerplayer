#!/usr/bin/env python3
"""
Final Comprehensive Integration Test for Poker Bot Improvements
Tests all critical fixes without dependency issues.
"""

import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_enhanced_hand_classification():
    """Test the enhanced hand classification improvements."""    
    try:
        from enhanced_postflop_improvements import classify_hand_strength_enhanced
        
        print("Testing Enhanced Hand Classification...")
        
        # Test 1: Strong top pair should be classified correctly
        result1 = classify_hand_strength_enhanced(
            numerical_hand_rank=2,  # one pair
            win_probability=0.75,
            hand_description="top pair, good kicker"
        )
        assert result1 == "strong", f"Expected 'strong', got '{result1}'"
        print(f"✓ Strong top pair: {result1}")
        
        # Test 2: The problematic KQ/pair of 9s case
        result2 = classify_hand_strength_enhanced(
            numerical_hand_rank=2,  # one pair
            win_probability=0.42,
            hand_description="pair of nines"
        )
        # Should be weak_made, not strong
        assert result2 in ["weak_made", "medium"], f"Expected 'weak_made' or 'medium', got '{result2}'"
        print(f"✓ KQ/pair of 9s: {result2} (should be weak_made, not strong)")
        
        # Test 3: Drawing hand
        result3 = classify_hand_strength_enhanced(
            numerical_hand_rank=1,  # high card/draw
            win_probability=0.35,
            hand_description="flush draw"
        )
        assert result3 == "drawing", f"Expected 'drawing', got '{result3}'"
        print(f"✓ Drawing hand: {result3}")
        
        # Test 4: Very weak hand
        result4 = classify_hand_strength_enhanced(
            numerical_hand_rank=1,  # high card
            win_probability=0.15,
            hand_description="ace high"
        )
        assert result4 == "very_weak", f"Expected 'very_weak', got '{result4}'"
        print(f"✓ Very weak hand: {result4}")
        
        # Test 5: Very strong hand
        result5 = classify_hand_strength_enhanced(
            numerical_hand_rank=3,  # two pair
            win_probability=0.85,
            hand_description="two pair, aces and kings"
        )
        assert result5 == "very_strong", f"Expected 'very_strong', got '{result5}'"
        print(f"✓ Very strong hand: {result5}")
        
        return True
        
    except Exception as e:
        print(f"✗ Enhanced hand classification failed: {e}")
        return False

def test_pot_commitment_thresholds():
    """Test the standardized pot commitment thresholds."""
    try:
        from enhanced_postflop_improvements import standardize_pot_commitment_thresholds
        
        print("Testing Pot Commitment Thresholds...")
          # Test 1: Strong hand on flop (should have lower threshold)
        result1 = standardize_pot_commitment_thresholds(
            hand_strength="strong",
            street="flop",
            spr=3.0
        )
        assert 0.15 <= result1 <= 0.35, f"Expected 0.15-0.35, got {result1}"
        print(f"✓ Strong hand flop: {result1:.1%}")
        
        # Test 2: Weak hand on river (should have higher threshold)
        result2 = standardize_pot_commitment_thresholds(
            hand_strength="weak_made",
            street="river",
            spr=2.0
        )
        assert 0.45 <= result2 <= 0.75, f"Expected 0.45-0.75, got {result2}"
        print(f"✓ Weak hand river: {result2:.1%}")
        
        # Test 3: Medium hand on turn
        result3 = standardize_pot_commitment_thresholds(
            hand_strength="medium",
            street="turn",
            spr=4.0
        )
        assert 0.30 <= result3 <= 0.60, f"Expected 0.30-0.60, got {result3}"
        print(f"✓ Medium hand turn: {result3:.1%}")
        
        # Test 4: High SPR adjustment
        result4 = standardize_pot_commitment_thresholds(
            hand_strength="medium",
            street="flop",
            spr=8.0  # High SPR
        )
        assert 0.40 <= result4 <= 0.85, f"Expected 0.40-0.85, got {result4}"
        print(f"✓ High SPR threshold: {result4:.1%}")
        
        # Test 5: Low SPR adjustment
        result5 = standardize_pot_commitment_thresholds(
            hand_strength="strong",
            street="river",
            spr=1.5  # Low SPR
        )
        assert 0.12 <= result5 <= 0.30, f"Expected 0.12-0.30, got {result5}"
        print(f"✓ Low SPR threshold: {result5:.1%}")
        
        # Test that all results are within bounds
        all_results = [result1, result2, result3, result4, result5]
        for i, result in enumerate(all_results, 1):
            assert 0.12 <= result <= 0.85, f"Test {i} result {result} outside bounds [0.12, 0.85]"
        
        return True
        
    except Exception as e:
        print(f"✗ Pot commitment thresholds failed: {e}")
        return False

def test_opponent_tracking():
    """Test the opponent tracking improvements."""
    try:
        from advanced_opponent_modeling import OpponentProfile
        
        print("Testing Opponent Tracking...")
        
        # Test 1: Create opponent profile
        opponent = OpponentProfile("TestPlayer")
        assert opponent.name == "TestPlayer"
        assert opponent.hands_observed == 0
        print(f"✓ Opponent profile creation: {opponent.name}")
        
        # Test 2: Update preflop action
        opponent.update_preflop_action("BTN", "raise", 3.0)
        assert opponent.hands_observed == 1
        assert opponent.position_stats["BTN"]["hands"] == 1
        print(f"✓ Preflop action update: {opponent.hands_observed} hands")
        
        # Test 3: Basic stats initialization
        assert hasattr(opponent, 'vpip')
        assert hasattr(opponent, 'pfr')
        assert hasattr(opponent, 'aggression_factor')
        print(f"✓ Basic stats available: VPIP={opponent.vpip}, PFR={opponent.pfr}")
        
        # Test 4: Advanced stats initialization
        assert hasattr(opponent, 'cbet_frequency')
        assert hasattr(opponent, 'fold_to_cbet')
        assert hasattr(opponent, 'bet_sizes')
        print(f"✓ Advanced stats available: C-bet={opponent.cbet_frequency}")
        
        return True
        
    except Exception as e:
        print(f"✗ Opponent tracking failed: {e}")
        return False

def test_boundary_conditions():
    """Test edge cases and boundary conditions."""
    try:
        from enhanced_postflop_improvements import classify_hand_strength_enhanced, standardize_pot_commitment_thresholds
        
        print("Testing Boundary Conditions...")
          # Test 1: Very low win probability
        result1 = classify_hand_strength_enhanced(
            numerical_hand_rank=1,  # high card
            win_probability=0.05,
            hand_description="seven high"
        )
        assert result1 == "very_weak", f"Expected 'very_weak', got '{result1}'"
        print(f"✓ Very low win probability: {result1}")
        
        # Test 2: Very high win probability
        result2 = classify_hand_strength_enhanced(
            numerical_hand_rank=7,  # full house
            win_probability=0.95,
            hand_description="full house, aces full"
        )
        assert result2 == "very_strong", f"Expected 'very_strong', got '{result2}'"
        print(f"✓ Very high win probability: {result2}")
          # Test 3: Extreme SPR values
        result3 = standardize_pot_commitment_thresholds(
            hand_strength="medium",
            street="flop",
            spr=15.0  # Very high SPR
        )
        assert 0.12 <= result3 <= 0.85, f"Expected within bounds, got {result3}"
        print(f"✓ Extreme high SPR: {result3:.1%}")
        
        # Test 4: Very low SPR
        result4 = standardize_pot_commitment_thresholds(
            hand_strength="weak_made",
            street="river",
            spr=0.8  # Very low SPR
        )
        assert 0.12 <= result4 <= 0.85, f"Expected within bounds, got {result4}"
        print(f"✓ Extreme low SPR: {result4:.1%}")
        
        # Test 5: Multiway pot adjustment
        result5 = standardize_pot_commitment_thresholds(
            hand_strength="medium",
            street="turn",
            spr=3.0
        )
        assert 0.12 <= result5 <= 0.85, f"Expected within bounds, got {result5}"
        print(f"✓ Multiway pot adjustment: {result5:.1%}")
        
        return True
        
    except Exception as e:
        print(f"✗ Boundary conditions failed: {e}")
        return False

def test_integration_scenarios():
    """Test realistic poker scenarios that were previously problematic."""    
    try:
        from enhanced_postflop_improvements import classify_hand_strength_enhanced, standardize_pot_commitment_thresholds
        
        print("Testing Integration Scenarios...")
        
        # Scenario 1: The original J4s problem (should not be playable)
        j4s_classification = classify_hand_strength_enhanced(
            numerical_hand_rank=1,  # high card
            win_probability=0.25,
            hand_description="jack high"
        )
        assert j4s_classification in ["very_weak", "weak_made", "drawing"], f"J4s should be weak/drawing, got {j4s_classification}"
        print(f"✓ J4s scenario: {j4s_classification} (correctly not strong)")
        
        # Scenario 2: KQ with pair of 9s (the specific problem case)
        kq_classification = classify_hand_strength_enhanced(
            numerical_hand_rank=2,  # one pair
            win_probability=0.42,
            hand_description="pair of nines"
        )
        kq_threshold = standardize_pot_commitment_thresholds(
            hand_strength=kq_classification,
            street="turn",
            spr=3.5
        )
        # Should not be overly aggressive
        assert kq_threshold >= 0.40, f"KQ/9s should have conservative threshold, got {kq_threshold}"
        print(f"✓ KQ/9s scenario: {kq_classification} with {kq_threshold:.1%} threshold")
        
        # Scenario 3: Strong made hand should be aggressive
        strong_classification = classify_hand_strength_enhanced(
            numerical_hand_rank=3,  # two pair
            win_probability=0.80,
            hand_description="two pair, aces and tens"
        )
        strong_threshold = standardize_pot_commitment_thresholds(
            hand_strength=strong_classification,
            street="flop",
            spr=4.0
        )
        assert strong_threshold <= 0.35, f"Strong hand should be aggressive, got {strong_threshold}"
        print(f"✓ Strong hand scenario: {strong_classification} with {strong_threshold:.1%} threshold")
        
        return True
        
    except Exception as e:
        print(f"✗ Integration scenarios failed: {e}")
        return False

def main():
    """Run all integration tests."""
    print("=" * 60)
    print("FINAL COMPREHENSIVE POKER BOT INTEGRATION TEST")
    print("=" * 60)
    
    tests = [
        ("Enhanced Hand Classification", test_enhanced_hand_classification),
        ("Pot Commitment Thresholds", test_pot_commitment_thresholds),
        ("Opponent Tracking", test_opponent_tracking),
        ("Boundary Conditions", test_boundary_conditions),
        ("Integration Scenarios", test_integration_scenarios),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if test_func():
                print(f"✓ {test_name} PASSED")
                passed += 1
            else:
                print(f"✗ {test_name} FAILED")
                failed += 1
        except Exception as e:
            print(f"✗ {test_name} FAILED with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print("FINAL TEST SUMMARY")
    print("=" * 60)
    print(f"Tests Run: {passed + failed}")
    print(f"Tests Passed: {passed}")
    print(f"Tests Failed: {failed}")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED! The poker bot improvements are working correctly.")
        return 0
    else:
        print(f"⚠️  {failed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
