#!/usr/bin/env python3

"""
Final integration test to verify that the DecisionEngine now properly uses 
the equity calculator when win_probability is not provided in game state.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hand_evaluator import HandEvaluator
from decision_engine import DecisionEngine
import logging

# Set up logging to see the integration in action
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def test_integration_fixed():
    """Test that DecisionEngine now uses equity calculator for win probability"""
    print("=== Testing Final Integration Fix ===")
    
    # Initialize components
    hand_evaluator = HandEvaluator()
    config = {
        'big_blind': 2.0,
        'small_blind': 1.0
    }
    decision_engine = DecisionEngine(hand_evaluator, config)
    
    # Test scenario: Strong hand without win_probability in game state
    print("\n1. Testing strong hand (AA) without win_probability in game state:")
    game_state_strong = {
        'current_round': 'preflop',
        'pot_size': 5.0,
        'community_cards': [],
        'players': [
            {
                'name': 'Hero',
                'hand': ['A♠', 'A♥'],  # Pocket Aces
                'stack': 100.0,
                'current_bet': 2.0,
                'position': 'BTN',
                'has_turn': True,
                'is_active': True,
                'is_my_player': True,
                'bet_to_call': 0.0
                # Note: NO win_probability provided
            },
            {
                'name': 'Villain',
                'hand': ['hidden', 'hidden'],
                'stack': 98.0,
                'current_bet': 2.0,
                'position': 'BB',
                'has_turn': False,
                'is_active': True,
                'last_action': 'call'
            }
        ]
    }
    
    action, amount = decision_engine.make_decision(game_state_strong, 0)
    print(f"Decision with AA (no win_prob provided): {action} {amount}")
    
    # Test scenario: Weak hand without win_probability
    print("\n2. Testing weak hand (27o) without win_probability in game state:")
    game_state_weak = {
        'current_round': 'preflop',
        'pot_size': 5.0,
        'community_cards': [],
        'players': [
            {
                'name': 'Hero',
                'hand': ['2♠', '7♣'],  # 27 offsuit (worst hand)
                'stack': 100.0,
                'current_bet': 2.0,
                'position': 'BTN',
                'has_turn': True,
                'is_active': True,
                'is_my_player': True,
                'bet_to_call': 10.0  # Facing a raise
                # Note: NO win_probability provided
            },
            {
                'name': 'Villain',
                'hand': ['hidden', 'hidden'],
                'stack': 88.0,
                'current_bet': 12.0,
                'position': 'BB',
                'has_turn': False,
                'is_active': True,
                'last_action': 'raise'
            }
        ]
    }
    
    action, amount = decision_engine.make_decision(game_state_weak, 0)
    print(f"Decision with 27o facing raise (no win_prob provided): {action} {amount}")
    
    # Test scenario: Postflop with medium hand
    print("\n3. Testing postflop decision without win_probability:")
    game_state_postflop = {
        'current_round': 'flop',
        'pot_size': 20.0,
        'community_cards': ['9♦', 'J♠', '7♠'],
        'players': [
            {
                'name': 'Hero',
                'hand': ['9♠', 'J♦'],  # Two pair
                'stack': 80.0,
                'current_bet': 0.0,
                'position': 'BTN',
                'has_turn': True,
                'is_active': True,
                'is_my_player': True,
                'bet_to_call': 0.0
                # Note: NO win_probability provided
            },
            {
                'name': 'Villain',
                'hand': ['hidden', 'hidden'],
                'stack': 78.0,
                'current_bet': 0.0,
                'position': 'BB',
                'has_turn': False,
                'is_active': True,
                'last_action': 'check'
            }
        ]
    }
    
    action, amount = decision_engine.make_decision(game_state_postflop, 0)
    print(f"Decision with two pair on flop (no win_prob provided): {action} {amount}")
    
    print("\n" + "="*60)
    print("✅ INTEGRATION TEST COMPLETE!")
    print("If you see calculated win probabilities in the logs above,")
    print("the integration is working correctly!")
    print("="*60)

if __name__ == "__main__":
    test_integration_fixed()
