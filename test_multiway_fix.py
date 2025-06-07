#!/usr/bin/env python3
"""
Simple test to verify the opponent counting fix shows correct logs
"""

import sys
import logging
sys.path.append('.')

# Set up logging to see the multiway adjustment messages
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

from decision_engine import DecisionEngine
from hand_evaluator import HandEvaluator

def test_multiway_logs():
    """Test that multiway adjustment logs show correct opponent count"""
    try:
        # Create decision engine
        hand_evaluator = HandEvaluator()
        config = {'big_blind': 0.02, 'small_blind': 0.01}
        decision_engine = DecisionEngine(hand_evaluator, config)
        
        print("=== Testing Multiway Adjustment Logs ===")
        
        # Test game with strong hand to trigger value betting and multiway adjustments
        game_state = {
            'players': [
                {
                    'name': 'Hero',
                    'hand': [('A', 'SPADES'), ('A', 'HEARTS')],  # Pocket Aces - strong hand
                    'position': 'BTN', 
                    'stack': 100.0,
                    'current_bet': 0.0,
                    'has_turn': True,
                    'is_active': True,
                    'is_my_player': True,
                    'win_probability': 0.85  # High win probability to trigger value bet
                },
                {
                    'name': 'Villain',
                    'position': 'BB',
                    'stack': 95.0, 
                    'current_bet': 0.0,  # Can check
                    'has_turn': False,
                    'is_active': True,
                    'is_my_player': False
                },
                {
                    'name': 'Folded1',
                    'position': 'SB',
                    'stack': 98.0,
                    'current_bet': 0.0, 
                    'has_turn': False,
                    'is_active': False,  # Not active - should not be counted
                    'is_my_player': False
                },
                {
                    'name': 'Folded2', 
                    'position': 'CO',
                    'stack': 97.0,
                    'current_bet': 0.0,
                    'has_turn': False,
                    'is_active': False,  # Not active - should not be counted
                    'is_my_player': False
                }
            ],
            'community_cards': [('A', 'CLUBS'), ('7', 'HEARTS'), ('2', 'DIAMONDS')],
            'current_round': 'flop',
            'pot_size': 4.0,
            'big_blind': 2.0,
            'bet_to_call': 0.0  # Can check
        }
        
        print(f"Game setup: {len(game_state['players'])} total players")
        print("Active players:")
        for i, player in enumerate(game_state['players']):
            if player.get('is_active', False):
                print(f"  - {player['name']} (index {i})")
        
        print("\nMaking decision... (look for 'Heads-up' or '1 opponent' in logs)")
        action, amount = decision_engine.make_decision(game_state, 0)
        
        print(f"Decision: {action} {amount}")
        print("\n" + "="*50)
        print("SUCCESS: If you see 'Heads-up: 1 opponent' in the logs above,")
        print("the fix is working! The old bug would have shown '5 opponents'.")
        print("="*50)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_multiway_logs()
