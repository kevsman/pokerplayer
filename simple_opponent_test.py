#!/usr/bin/env python3
"""
Simple test to isolate opponent tracking issue
"""

print("Starting opponent tracking test...")

try:
    print("1. Importing modules...")
    from opponent_tracking import OpponentTracker
    print("   OpponentTracker imported successfully")
    
    from decision_engine import DecisionEngine
    print("   DecisionEngine imported successfully")
    
    from hand_evaluator import HandEvaluator
    print("   HandEvaluator imported successfully")
    
    print("2. Creating instances...")
    hand_evaluator = HandEvaluator()
    print("   HandEvaluator created")
    
    config = {'big_blind': 0.02, 'small_blind': 0.01}
    decision_engine = DecisionEngine(hand_evaluator, config)
    print("   DecisionEngine created")
    print(f"   Initial opponents tracked: {len(decision_engine.opponent_tracker.opponents)}")
    
    print("3. Testing direct opponent tracker...")
    tracker = OpponentTracker()
    print(f"   New tracker created with {len(tracker.opponents)} opponents")
    
    # Add a test action
    tracker.update_opponent_action("TestPlayer", "raise", "preflop", "BTN", 6.0, 2.0)
    print(f"   After adding action: {len(tracker.opponents)} opponents")
    
    if len(tracker.opponents) > 0:
        for name, profile in tracker.opponents.items():
            print(f"   Player {name}: {profile.hands_seen} hands seen")
    
    print("4. Testing game state update...")
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
    
    print("   Calling update_opponents_from_game_state...")
    decision_engine.update_opponents_from_game_state(test_game_state, 0)
    print(f"   After game state update: {len(decision_engine.opponent_tracker.opponents)} opponents")
    
    if len(decision_engine.opponent_tracker.opponents) > 0:
        for name, profile in decision_engine.opponent_tracker.opponents.items():
            print(f"   Player {name}: {profile.hands_seen} hands seen")
    else:
        print("   No opponents tracked after game state update")
    
    print("Test completed successfully!")
    
except Exception as e:
    print(f"Error occurred: {e}")
    import traceback
    traceback.print_exc()
