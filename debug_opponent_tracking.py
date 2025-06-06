#!/usr/bin/env python3
"""
Debug opponent tracking to understand why opponents show as "0 opponents tracked"
"""

import sys
sys.path.append('.')

from decision_engine import DecisionEngine
from hand_evaluator import HandEvaluator
from opponent_tracking import OpponentTracker
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_opponent_tracking_debug():
    """Debug opponent tracking integration"""
    print("=== Debugging Opponent Tracking ===")
    
    # Initialize components
    hand_evaluator = HandEvaluator()
    config = {'big_blind': 0.02, 'small_blind': 0.01}
    decision_engine = DecisionEngine(hand_evaluator, config)
    
    print(f"Initial opponent tracker state: {len(decision_engine.opponent_tracker.opponents)} opponents")
    
    # Test 1: Direct opponent tracker test
    print("\n--- Test 1: Direct OpponentTracker Usage ---")
    tracker = OpponentTracker()
    
    # Add some test actions
    tracker.update_opponent_action("Alice", "raise", "preflop", "BTN", 6.0, 2.0)
    tracker.update_opponent_action("Alice", "bet", "flop", "BTN", 4.5, 8.5)
    tracker.update_opponent_action("Bob", "call", "preflop", "CO", 6.0, 2.0)
    tracker.update_opponent_action("Bob", "fold", "flop", "CO", 0.0, 13.0)
    
    print(f"After manual updates: {len(tracker.opponents)} opponents tracked")
    for name, profile in tracker.opponents.items():
        print(f"  {name}: {profile.hands_seen} hands, VPIP={profile.get_vpip():.1f}%, Type={profile.classify_player_type()}")
    
    # Test 2: Game state simulation
    print("\n--- Test 2: Game State Simulation ---")
    
    test_game_state = {
        'players': [
            {  # Player 0 (us)
                'name': 'Hero',
                'hand': [('A', 'SPADES'), ('K', 'HEARTS')],
                'position': 'BTN',
                'stack': 100.0,
                'current_bet': 0.0,
                'has_turn': True,
                'has_acted': False,
                'last_action': None
            },
            {  # Player 1 (opponent)
                'name': 'Alice',
                'position': 'SB',
                'stack': 95.0,
                'current_bet': 6.0,
                'has_turn': False,
                'has_acted': True,
                'last_action': 'raise'
            },
            {  # Player 2 (opponent)
                'name': 'Bob',
                'position': 'BB',
                'stack': 94.0,
                'current_bet': 6.0,
                'has_turn': False,
                'has_acted': True,
                'last_action': 'call'
            }
        ],
        'community_cards': [('A', 'CLUBS'), ('7', 'HEARTS'), ('2', 'DIAMONDS')],
        'current_round': 'flop',
        'pot_size': 14.0,
        'big_blind': 2.0
    }
    
    # Call update_opponents_from_game_state
    decision_engine.update_opponents_from_game_state(test_game_state, 0)
    
    print(f"After game state update: {len(decision_engine.opponent_tracker.opponents)} opponents tracked")
    for name, profile in decision_engine.opponent_tracker.opponents.items():
        print(f"  {name}: {profile.hands_seen} hands, VPIP={profile.get_vpip():.1f}%, Type={profile.classify_player_type()}")
    
    # Test 3: Make a decision to see tracking in action
    print("\n--- Test 3: Decision Making with Tracking ---")
    
    action, amount = decision_engine.make_decision(test_game_state, 0)
    print(f"Decision: {action} {amount}")
    
    # Check final tracking state
    print(f"Final tracking state: {len(decision_engine.opponent_tracker.opponents)} opponents tracked")
    
    # Test 4: Check table dynamics
    print("\n--- Test 4: Table Dynamics ---")
    dynamics = decision_engine.opponent_tracker.get_table_dynamics()
    print(f"Table dynamics: {dynamics}")

if __name__ == "__main__":
    test_opponent_tracking_debug()
