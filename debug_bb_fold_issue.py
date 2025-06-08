#!/usr/bin/env python3

"""
Debug script to reproduce the BB folding issue with bet_to_call = 0.00
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from decision_engine import DecisionEngine
from hand_evaluator import HandEvaluator

def test_bb_fold_with_debug():
    """Test the specific scenario where BB folds with bet_to_call = 0.00"""
    
    print("=== Testing BB Fold Issue with Debug Logging ===")
    
    # Initialize the decision engine
    hand_evaluator = HandEvaluator()
    config = {
        'big_blind': 0.02,
        'small_blind': 0.01,
        'base_aggression_factor_postflop': 1.0
    }
    decision_engine = DecisionEngine(hand_evaluator, config)
    
    # Create game state that matches the problematic log entry
    game_state = {
        'current_round': 'preflop',
        'pot_size': 0.07,  # €0.07 from the log
        'community_cards': [],
        'big_blind': 0.02,
        'min_raise': 0.04,
        'players': [
            None,  # Empty seat
            None,  # Empty seat
            None,  # Empty seat
            {   # Player at index 3 (our bot, BB position)
                'name': 'warriorwonder25',
                'seat': 4,
                'hand': ['7♠', '3♥'],  # The exact hand from the log
                'stack': 1.24,  # €1.24 from the log
                'position': 'BB',
                'current_bet': 0.02,  # BB has posted the blind
                'bet_to_call': 0.00,  # This is the key - should be able to check
                'is_active': True,
                'is_my_player': True,
                'has_turn': True,
                'win_probability': 0.15  # Low probability for 73o
            },
            None,  # Empty seat
            None   # Empty seat
        ]
    }
    
    print(f"Testing decision for BB with hand {game_state['players'][3]['hand']}")
    print(f"Bet to call: {game_state['players'][3]['bet_to_call']}")
    print(f"Position: {game_state['players'][3]['position']}")
    print(f"Stack: {game_state['players'][3]['stack']}")
    print()
    
    # Make the decision
    try:
        action, amount = decision_engine.make_decision(game_state, 3)
        print(f"RESULT: action={action}, amount={amount}")
        
        if action == 'fold' and game_state['players'][3]['bet_to_call'] == 0.00:
            print("❌ BUG REPRODUCED: Bot folded when it could check for free!")
            return False
        elif action == 'check':
            print("✅ CORRECT: Bot checked when bet_to_call = 0.00")
            return True
        else:
            print(f"? UNEXPECTED: Bot chose {action} (expected check or fold)")
            return False
            
    except Exception as e:
        print(f"ERROR during decision making: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_bb_fold_with_debug()
    if not success:
        print("\n=== BUG STILL EXISTS ===")
        sys.exit(1)
    else:
        print("\n=== BUG APPEARS FIXED ===")
        sys.exit(0)
