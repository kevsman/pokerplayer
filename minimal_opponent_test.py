#!/usr/bin/env python3
import sys
sys.stdout.flush()

print("TEST: Starting opponent tracking test")
sys.stdout.flush()

from opponent_tracking import OpponentTracker
from decision_engine import DecisionEngine  
from hand_evaluator import HandEvaluator

print("TEST: Imports successful")
sys.stdout.flush()

# Create instances
hand_evaluator = HandEvaluator()
config = {'big_blind': 0.02, 'small_blind': 0.01}
decision_engine = DecisionEngine(hand_evaluator, config)

print(f"TEST: DecisionEngine created with {len(decision_engine.opponent_tracker.opponents)} opponents")
sys.stdout.flush()

# Test direct opponent tracker
tracker = OpponentTracker()
tracker.update_opponent_action("TestPlayer", "raise", "preflop", "BTN", 6.0, 2.0)

print(f"TEST: Direct tracker has {len(tracker.opponents)} opponents after update")
sys.stdout.flush()

# Test game state
test_game_state = {
    'players': [
        {
            'name': 'Hero',
            'hand': [('A', 'SPADES'), ('K', 'HEARTS')],
            'position': 'BTN',
            'stack': 100.0,
            'current_bet': 0.0,
            'has_turn': True,
            'has_acted': False,
            'last_action': None
        },
        {
            'name': 'Alice',
            'position': 'SB',
            'stack': 95.0,
            'current_bet': 6.0,
            'has_turn': False,
            'has_acted': True,
            'last_action': 'raise'
        }
    ],
    'community_cards': [],
    'current_round': 'preflop',
    'pot_size': 8.0,
    'big_blind': 2.0
}

print("TEST: About to call update_opponents_from_game_state")
sys.stdout.flush()

decision_engine.update_opponents_from_game_state(test_game_state, 0)

print(f"TEST: After game state update: {len(decision_engine.opponent_tracker.opponents)} opponents")
sys.stdout.flush()

print("TEST: Complete")
