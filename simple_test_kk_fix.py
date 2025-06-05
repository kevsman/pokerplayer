#!/usr/bin/env python3
"""
Simple test script to validate the pocket kings all-in fix.
"""

import sys
import os

from decision_engine import DecisionEngine, ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE
from hand_evaluator import HandEvaluator

def test_pocket_kings_allin():
    print("Testing Pocket Kings All-In Fix...")
    print("=" * 50)
    
    # Set up the decision engine
    hand_evaluator = HandEvaluator()
    config = {'big_blind': 0.02, 'small_blind': 0.01}
    decision_engine = DecisionEngine(hand_evaluator, config)
      # Simulate the exact scenario from the log
    my_player = {
        'hole_cards': ['Kc', 'Kh'],  # Pocket Kings
        'cards': ['Kc', 'Kh'],
        'hand': ['Kc', 'Kh'],  # This is what decision_engine expects
        'stack': 2.59,  # Remaining stack from log
        'current_bet': 0.84,    # Already committed €0.84
        'is_active': True,
        'is_my_player': True,
        'has_turn': True,
        'hand_evaluation': (2, "Pair of Kings", [13, 13]),
        'position': 'UTG',
        'seat': '1',
        'name': 'TestBot',
        'id': 'player1',
        'isActive': True,
        'isFolded': False
    }
    
    # Opponent who went all-in
    opponent = {
        'cards': ['XX', 'XX'],  # Hidden
        'hand': ['XX', 'XX'],   # Hidden
        'stack': 0.0,  # All-in
        'current_bet': 2.59,  # All-in amount
        'is_active': True, 
        'is_my_player': False,
        'has_turn': False,
        'position': 'BB',
        'seat': '2',
        'name': 'Opponent',
        'id': 'player2',
        'isActive': True,
        'isFolded': False
    }
    
    # Create game state in the expected format
    game_state = {
        'players': [my_player, opponent],
        'pot_size': 3.43,  # Pot from log  
        'community_cards': [],
        'current_round': 'preflop',
        'big_blind': 0.02,
        'small_blind': 0.01,
        'min_raise': 0.04,
        'board': [],
        'street': 'preflop'
    }
    
    my_player_index = 0  # Our bot is the first player
    
    try:
        action, amount = decision_engine.make_decision(game_state, my_player_index)
        
        bet_to_call = 2.59 - 0.84  # All-in amount minus what we've already bet
        
        print(f"Result: ACTION = {action}, AMOUNT = {amount}")
        print(f"Stack: {my_player['stack']}, Current bet: {my_player['current_bet']}")
        print(f"Bet to call: {bet_to_call}")
        
        if action == ACTION_CALL:
            print("✅ SUCCESS: Pocket Kings correctly CALLED the all-in!")
            print("   The fix is working - KK no longer folds to all-ins preflop.")
        elif action == ACTION_RAISE:
            print("✅ SUCCESS: Pocket Kings raised (also acceptable)")
        elif action == ACTION_FOLD:
            print("❌ FAILED: Pocket Kings still folding to all-in!")
            print("   The fix did not resolve the issue.")
        else:
            print(f"❓ UNEXPECTED: Action was {action}")
            
        return action == ACTION_CALL or action == ACTION_RAISE
        
    except Exception as e:
        print(f"❌ ERROR running test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_other_premium_pairs():
    print("\nTesting other premium pairs...")
    print("-" * 30)
    
    hand_evaluator = HandEvaluator()
    config = {'big_blind': 0.02, 'small_blind': 0.01}
    decision_engine = DecisionEngine(hand_evaluator, config)
      # Test Aces
    my_player_aa = {
        'hole_cards': ['As', 'Ah'],
        'cards': ['As', 'Ah'],
        'hand': ['As', 'Ah'],  # This is what decision_engine expects
        'stack': 5.00,
        'current_bet': 0.20,
        'is_active': True,
        'is_my_player': True,
        'has_turn': True,
        'hand_evaluation': (2, "Pair of Aces", [14, 14]),
        'position': 'MP',
        'seat': '1',
        'name': 'TestBot',
        'id': 'player1',
        'isActive': True,
        'isFolded': False
    }
    
    opponent_aa = {
        'cards': ['XX', 'XX'],
        'hand': ['XX', 'XX'],
        'stack': 0.0, 
        'current_bet': 5.00, 
        'is_active': True,
        'is_my_player': False,
        'has_turn': False,
        'position': 'BTN',
        'seat': '2',
        'name': 'Opponent',
        'id': 'player2',
        'isActive': True,
        'isFolded': False
    }
    
    game_state_aa = {
        'players': [my_player_aa, opponent_aa],
        'pot_size': 5.20,
        'community_cards': [],
        'current_round': 'preflop',
        'big_blind': 0.02,
        'small_blind': 0.01,
        'min_raise': 0.04,
        'board': [],
        'street': 'preflop'
    }
    
    try:
        action_aa, amount_aa = decision_engine.make_decision(game_state_aa, 0)
        print(f"Pocket Aces vs All-in: {action_aa}")
        
        if action_aa in [ACTION_CALL, ACTION_RAISE]:
            print("✅ Aces correctly call/raise all-in")
        else:
            print("❌ Aces incorrectly fold to all-in")
            
    except Exception as e:
        print(f"Error testing Aces: {e}")

if __name__ == '__main__':
    print("Starting test execution...")
    try:
        success = test_pocket_kings_allin()
        test_other_premium_pairs()
        
        if success:
            print("\n🎉 OVERALL: Fix appears to be working!")
        else:
            print("\n💥 OVERALL: Fix needs more work.")
    except Exception as e:
        print(f"Error in main: {e}")
        import traceback
        traceback.print_exc()
