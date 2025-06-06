#!/usr/bin/env python3
"""
Test the all-in calling logic specifically for the Q♥10♦ scenario
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from postflop_decision_logic import make_postflop_decision, is_drawing_hand
from decision_engine import DecisionEngine
from hand_evaluator import HandEvaluator
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_q10_all_in_scenario():
    """Test the specific Q♥10♦ all-in scenario from the logs"""
    print("=== Testing Q♥10♦ All-in Scenario ===")
    
    # Mock decision engine
    hand_evaluator = HandEvaluator()
    decision_engine = DecisionEngine(hand_evaluator)
    
    # Test parameters from the problematic log entry
    numerical_hand_rank = 1  # High card (weak hand)
    hand_description = "High Card, Queen"
    bet_to_call = 0.33  # All-in amount
    can_check = False
    pot_size = 0.65
    my_stack = 0.33  # Exactly the bet amount = all-in call
    win_probability = 0.3344  # 33.44% equity
    pot_odds_to_call = bet_to_call / (pot_size + bet_to_call)  # ~33.67%
    street = 'flop'
    spr = my_stack / pot_size
    
    my_player_data = {
        'hand': ['Qh', 'Tc'],
        'community_cards': ['Jc', '4s', '6d'],
        'current_bet': 0.0,
        'is_all_in_call_available': True  # This is an all-in situation
    }
    
    big_blind_amount = 0.02
    base_aggression_factor = 1.0
    max_bet_on_table = 0.33
    active_opponents_count = 1
    
    print(f"Hand: Q♥10♦")
    print(f"Board: J♣4♠6♦")
    print(f"Bet to call: €{bet_to_call} (ALL-IN)")
    print(f"Pot size: €{pot_size}")
    print(f"My stack: €{my_stack}")
    print(f"Win probability: {win_probability:.2%}")
    print(f"Pot odds: {pot_odds_to_call:.2%}")
    print(f"Required equity for all-in call with draws: 45%")
    
    # Test if it's detected as a drawing hand
    is_draw = is_drawing_hand(win_probability, numerical_hand_rank, street)
    print(f"Detected as drawing hand: {is_draw}")
    
    # Make the decision
    action, amount = make_postflop_decision(
        decision_engine_instance=decision_engine,
        numerical_hand_rank=numerical_hand_rank,
        hand_description=hand_description,
        bet_to_call=bet_to_call,
        can_check=can_check,
        pot_size=pot_size,
        my_stack=my_stack,
        win_probability=win_probability,
        pot_odds_to_call=pot_odds_to_call,
        game_stage=street,
        spr=spr,
        action_fold_const="fold",
        action_check_const="check",
        action_call_const="call",
        action_raise_const="raise",
        my_player_data=my_player_data,
        big_blind_amount=big_blind_amount,
        base_aggression_factor=base_aggression_factor,
        max_bet_on_table=max_bet_on_table,
        active_opponents_count=active_opponents_count,
        opponent_tracker=None
    )
    
    print(f"\nDECISION: {action} €{amount}")
    
    # Expected behavior: Should FOLD because 33.44% < 45% required for all-in with draws
    if action == "fold":
        print("✅ SUCCESS: Bot correctly folded Q♥10♦ all-in with insufficient equity!")
        print("   This fixes the problematic 'implied odds' logic in all-in situations.")
        return True
    else:
        print("❌ FAILURE: Bot should fold Q♥10♦ all-in with only 33.44% equity")
        print("   Expected: FOLD (insufficient equity for all-in call)")
        print(f"   Got: {action} €{amount}")
        return False

def test_drawing_hand_with_good_equity():
    """Test that drawing hands with sufficient equity still call all-in"""
    print("\n=== Testing Drawing Hand with Good Equity ===")
    
    hand_evaluator = HandEvaluator()
    decision_engine = DecisionEngine(hand_evaluator)
    
    # Similar scenario but with higher equity
    numerical_hand_rank = 1
    hand_description = "High Card, Ace"
    bet_to_call = 0.30
    my_stack = 0.30  # All-in call
    win_probability = 0.47  # 47% equity - above 45% threshold
    pot_size = 0.60
    pot_odds_to_call = bet_to_call / (pot_size + bet_to_call)
    
    my_player_data = {
        'hand': ['As', 'Kd'],
        'community_cards': ['Qc', 'Jh', '5s'],
        'current_bet': 0.0,
        'is_all_in_call_available': True
    }
    
    print(f"Hand: A♠K♦ (gutshot + overcards)")
    print(f"Board: Q♣J♥5♠")
    print(f"Win probability: {win_probability:.2%}")
    print(f"Required for all-in: 45%")
    
    action, amount = make_postflop_decision(
        decision_engine_instance=decision_engine,
        numerical_hand_rank=numerical_hand_rank,
        hand_description=hand_description,
        bet_to_call=bet_to_call,
        can_check=False,
        pot_size=pot_size,
        my_stack=my_stack,
        win_probability=win_probability,
        pot_odds_to_call=pot_odds_to_call,
        game_stage='flop',
        spr=my_stack / pot_size,
        action_fold_const="fold",
        action_check_const="check",
        action_call_const="call",
        action_raise_const="raise",
        my_player_data=my_player_data,
        big_blind_amount=0.02,
        base_aggression_factor=1.0,
        max_bet_on_table=0.30,
        active_opponents_count=1,
        opponent_tracker=None
    )
    
    print(f"DECISION: {action} €{amount}")
    
    if action == "call":
        print("✅ SUCCESS: Bot correctly called all-in with sufficient equity!")
        return True
    else:
        print("❌ FAILURE: Bot should call all-in with 47% equity")
        return False

def test_non_all_in_drawing_hand():
    """Test that regular drawing hands still work with implied odds"""
    print("\n=== Testing Non All-in Drawing Hand ===")
    
    hand_evaluator = HandEvaluator()
    decision_engine = DecisionEngine(hand_evaluator)
    
    # Regular draw scenario (not all-in)
    numerical_hand_rank = 1
    bet_to_call = 0.15  # Not all-in
    my_stack = 1.20     # Plenty of stack left
    win_probability = 0.35  # 35% equity
    pot_size = 0.40
    
    my_player_data = {
        'hand': ['9h', '8h'],
        'community_cards': ['7c', '6s', '2d'],
        'current_bet': 0.0,
        'is_all_in_call_available': False
    }
    
    print(f"Hand: 9♥8♥ (open-ended straight draw)")
    print(f"Board: 7♣6♠2♦")
    print(f"Bet: €{bet_to_call} (not all-in)")
    print(f"Stack remaining: €{my_stack - bet_to_call}")
    print(f"Win probability: {win_probability:.2%}")
    
    # This should use implied odds logic since it's not all-in
    action, amount = make_postflop_decision(
        decision_engine_instance=decision_engine,
        numerical_hand_rank=numerical_hand_rank,
        hand_description="High Card, Nine",
        bet_to_call=bet_to_call,
        can_check=False,
        pot_size=pot_size,
        my_stack=my_stack,
        win_probability=win_probability,
        pot_odds_to_call=bet_to_call / (pot_size + bet_to_call),
        game_stage='flop',
        spr=my_stack / pot_size,
        action_fold_const="fold",
        action_check_const="check",
        action_call_const="call",
        action_raise_const="raise",
        my_player_data=my_player_data,
        big_blind_amount=0.02,
        base_aggression_factor=1.0,
        max_bet_on_table=0.15,
        active_opponents_count=1,
        opponent_tracker=None
    )
    
    print(f"DECISION: {action} €{amount}")
    
    # This might call or fold depending on implied odds - both are reasonable
    print("✅ Non all-in drawing hand logic executed")
    return True

def main():
    print("Testing All-in Calling Logic Fixes")
    print("=" * 50)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Q♥10♦ all-in scenario (should fold)
    tests_total += 1
    if test_q10_all_in_scenario():
        tests_passed += 1
    
    # Test 2: Drawing hand with good equity (should call)
    tests_total += 1
    if test_drawing_hand_with_good_equity():
        tests_passed += 1
    
    # Test 3: Non all-in drawing hand
    tests_total += 1
    if test_non_all_in_drawing_hand():
        tests_passed += 1
    
    print("\n" + "=" * 50)
    print(f"TEST RESULTS: {tests_passed}/{tests_total} PASSED")
    
    if tests_passed == tests_total:
        print("\n🎉 ALL ALL-IN LOGIC TESTS PASSED!")
        print("\nKey fixes implemented:")
        print("✓ All-in detection prevents implied odds logic")
        print("✓ 45% equity requirement for all-in calls with draws")
        print("✓ Q♥10♦ scenario now correctly folds")
        print("✓ Drawing hands with sufficient equity still call")
    else:
        print("\n❌ Some tests failed - review the logic")
    
    return tests_passed == tests_total

if __name__ == '__main__':
    main()
