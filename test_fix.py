#!/usr/bin/env python3
"""
Test script to verify the DecisionEngine fix works correctly
"""

from decision_engine import DecisionEngine
from hand_evaluator import HandEvaluator

def test_decision_engine_fix():
    """Test that the EV function calls work correctly after the fix"""
    print("Testing DecisionEngine after function signature fix...")
    
    hand_evaluator = HandEvaluator()
    decision_engine = DecisionEngine(hand_evaluator, big_blind=0.02, small_blind=0.01)
    
    # Create test scenario similar to the error case
    my_player = {
        'hole_cards': ['9♠', 'J♦'],  # Pair of 9s on a 9♦ J♠ 7♠ board
        'cards': ['9s', 'Jd'],
        'chips': 2.00,
        'current_bet': 0.08,
        'is_active': True,
        'is_my_player': True,
        'has_turn': True,
        'bet_to_call': 0.08,
        'hand_evaluation': (2, "One Pair", [9])  # Pair of 9s
    }
    
    table_data = {
        'community_cards': ['9♦', 'J♠', '7♠'],
        'pot_size': '€0.24',
        'current_bet_level': 0.08,
        'game_stage': 'Flop'
    }
    
    all_players = [
        my_player,
        {'chips': 1.50, 'current_bet': 0.08, 'is_active': True, 'bet': '€0.08'},
        {'chips': 2.20, 'current_bet': 0.00, 'is_active': True, 'bet': '€0.00'},
    ]
    
    try:
        # This should work without throwing the TypeError we fixed
        action, amount = decision_engine.make_decision(my_player, table_data, all_players)
        print(f"✓ Decision made successfully: {action}, amount: {amount}")
        print("✓ Function signature fix is working correctly!")
        return True
        
    except Exception as e:
        print(f"✗ Error still present: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_decision_engine_fix()
    if success:
        print("\n" + "="*50)
        print("SUCCESS: The TypeError has been fixed!")
        print("The bot should now work correctly in postflop situations.")
    else:
        print("\n" + "="*50)
        print("FAILURE: There are still issues to resolve.")
