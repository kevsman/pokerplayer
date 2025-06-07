#!/usr/bin/env python3
"""
Test the opponent counting fix to verify it correctly counts active opponents
"""

import sys
sys.path.append('.')

from decision_engine import DecisionEngine
from hand_evaluator import HandEvaluator

def test_opponent_counting():
    """Test that the fixed opponent counting logic works correctly"""
    print("=== Testing Opponent Counting Fix ===\n")
    
    # Initialize decision engine
    hand_evaluator = HandEvaluator()
    config = {'big_blind': 0.02, 'small_blind': 0.01}
    decision_engine = DecisionEngine(hand_evaluator, config)
    
    # Test case 1: Game with 1 active opponent (the reported issue)
    print("Test 1: Game with only 1 active opponent")
    game_state_1_opponent = {
        'players': [
            {  # Player 0 (us)
                'name': 'Hero',
                'hand': [('A', 'SPADES'), ('K', 'HEARTS')],
                'position': 'BTN',
                'stack': 100.0,
                'current_bet': 0.0,
                'has_turn': True,
                'is_active': True,
                'is_my_player': True
            },
            {  # Player 1 (active opponent)
                'name': 'Villain1',
                'position': 'BB',
                'stack': 95.0,
                'current_bet': 2.0,
                'has_turn': False,
                'is_active': True,
                'is_my_player': False
            },
            {  # Player 2 (folded - should not be counted)
                'name': 'Folded1',
                'position': 'SB',
                'stack': 98.0,
                'current_bet': 0.0,
                'has_turn': False,
                'is_active': False,
                'is_my_player': False
            },
            {  # Player 3 (folded - should not be counted)
                'name': 'Folded2',
                'position': 'CO',
                'stack': 97.0,
                'current_bet': 0.0,
                'has_turn': False,
                'is_active': False,
                'is_my_player': False
            }
        ],
        'community_cards': [('A', 'CLUBS'), ('7', 'HEARTS'), ('2', 'DIAMONDS')],
        'current_round': 'flop',
        'pot_size': 4.0,
        'big_blind': 2.0
    }
    
    try:
        action, amount = decision_engine.make_decision(game_state_1_opponent, 0)
        print(f"   ✓ Decision made successfully: {action} {amount}")
        print("   Expected: Should show 1 opponent in multiway adjustment logs")
    except Exception as e:
        print(f"   ✗ Error making decision: {e}")
    
    # Test case 2: Game with multiple active opponents
    print("\nTest 2: Game with 3 active opponents")
    game_state_3_opponents = {
        'players': [
            {  # Player 0 (us)
                'name': 'Hero',
                'hand': [('K', 'SPADES'), ('K', 'HEARTS')],
                'position': 'BTN',
                'stack': 100.0,
                'current_bet': 0.0,
                'has_turn': True,
                'is_active': True,
                'is_my_player': True
            },
            {  # Player 1 (active opponent)
                'name': 'Villain1',
                'position': 'BB',
                'stack': 95.0,
                'current_bet': 2.0,
                'has_turn': False,
                'is_active': True,
                'is_my_player': False
            },
            {  # Player 2 (active opponent)
                'name': 'Villain2',
                'position': 'SB',
                'stack': 98.0,
                'current_bet': 2.0,
                'has_turn': False,
                'is_active': True,
                'is_my_player': False
            },
            {  # Player 3 (active opponent)
                'name': 'Villain3',
                'position': 'CO',
                'stack': 97.0,
                'current_bet': 2.0,
                'has_turn': False,
                'is_active': True,
                'is_my_player': False
            },
            {  # Player 4 (folded - should not be counted)
                'name': 'Folded1',
                'position': 'MP',
                'stack': 96.0,
                'current_bet': 0.0,
                'has_turn': False,
                'is_active': False,
                'is_my_player': False
            }
        ],
        'community_cards': [('A', 'CLUBS'), ('7', 'HEARTS'), ('2', 'DIAMONDS')],
        'current_round': 'flop',
        'pot_size': 8.0,
        'big_blind': 2.0
    }
    
    try:
        action, amount = decision_engine.make_decision(game_state_3_opponents, 0)
        print(f"   ✓ Decision made successfully: {action} {amount}")
        print("   Expected: Should show 3 opponents in multiway adjustment logs")
    except Exception as e:
        print(f"   ✗ Error making decision: {e}")
    
    # Test case 3: Heads-up game (only 1 opponent total)
    print("\nTest 3: True heads-up game")
    game_state_heads_up = {
        'players': [
            {  # Player 0 (us)
                'name': 'Hero',
                'hand': [('Q', 'SPADES'), ('Q', 'HEARTS')],
                'position': 'BTN',
                'stack': 100.0,
                'current_bet': 0.0,
                'has_turn': True,
                'is_active': True,
                'is_my_player': True
            },
            {  # Player 1 (only opponent)
                'name': 'Villain',
                'position': 'BB',
                'stack': 95.0,
                'current_bet': 2.0,
                'has_turn': False,
                'is_active': True,
                'is_my_player': False
            }
        ],
        'community_cards': [('A', 'CLUBS'), ('7', 'HEARTS'), ('2', 'DIAMONDS')],
        'current_round': 'flop',
        'pot_size': 4.0,
        'big_blind': 2.0
    }
    
    try:
        action, amount = decision_engine.make_decision(game_state_heads_up, 0)
        print(f"   ✓ Decision made successfully: {action} {amount}")
        print("   Expected: Should show 1 opponent and 'heads-up' in logs")
    except Exception as e:
        print(f"   ✗ Error making decision: {e}")
    
    print("\n" + "=" * 50)
    print("Test completed! Check the logs above to verify:")
    print("- Test 1 should show '1 opponent' not '5 opponents'")  
    print("- Test 2 should show '3 opponents' for multiway adjustment")
    print("- Test 3 should show '1 opponent' and heads-up message")
    print("=" * 50)

if __name__ == "__main__":
    test_opponent_counting()
