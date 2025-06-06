#!/usr/bin/env python3
"""
Simple Integration Test - Quick validation
"""

import sys
print("Starting integration test...")

try:
    from hand_evaluator import HandEvaluator
    from decision_engine import DecisionEngine
    print("✅ Imports successful")
    
    # Initialize components
    hand_evaluator = HandEvaluator()
    config = {'big_blind': 2.0, 'small_blind': 1.0}
    engine = DecisionEngine(hand_evaluator, config)
    print("✅ Components initialized")
    
    # Test basic functionality
    game_state = {
        'current_round': 'preflop',
        'pot_size': 3.0,
        'community_cards': [],
        'players': [
            {
                'name': 'Hero',
                'hand': ['A♠', 'A♥'],
                'stack': 100.0,
                'current_bet': 1.0,
                'position': 'BTN',
                'has_turn': True,
                'is_active': True,
            },
            {
                'name': 'Villain',
                'hand': ['hidden', 'hidden'],
                'stack': 98.0,
                'current_bet': 2.0,
                'position': 'BB',
                'has_turn': False,
                'is_active': True,
            }
        ]
    }
    
    print("Making decision...")
    action, amount = engine.make_decision(game_state, 0)
    print(f"✅ Decision made: {action} {amount}")
    
    # Test equity calculator directly
    print("Testing equity calculator...")
    win_prob = engine.equity_calculator.calculate_win_probability(['A♠', 'A♥'], [], 1)
    print(f"✅ AA win probability: {win_prob:.3f} ({win_prob*100:.1f}%)")
    
    print("🎉 INTEGRATION TEST PASSED!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
