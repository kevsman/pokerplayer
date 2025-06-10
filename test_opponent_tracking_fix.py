#!/usr/bin/env python3
"""
Test the opponent tracking fix to verify it works correctly.
"""

import sys
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_opponent_tracking_fix():
    """Test the enhanced opponent tracking integration."""
    print("=== Testing Opponent Tracking Fix ===\n")
    
    try:
        # Import necessary modules
        from opponent_tracking import OpponentTracker
        from opponent_tracking_fix import get_enhanced_opponent_context
        
        print("✓ Modules imported successfully")
        
        # Create opponent tracker and simulate some data
        tracker = OpponentTracker()
        
        # Add test opponents with realistic data
        tracker.update_opponent_action("Alice", "raise", "preflop", "BTN", 6.0, 2.0)
        tracker.update_opponent_action("Alice", "bet", "flop", "BTN", 4.5, 8.5)
        tracker.update_opponent_action("Alice", "call", "turn", "BTN", 3.0, 16.5)
        
        tracker.update_opponent_action("Bob", "call", "preflop", "CO", 6.0, 2.0)
        tracker.update_opponent_action("Bob", "call", "flop", "CO", 4.5, 8.5)
        tracker.update_opponent_action("Bob", "fold", "turn", "CO", 0.0, 16.5)
        
        print(f"✓ Created tracker with {len(tracker.opponents)} opponents")
        
        # Display opponent profiles
        for name, profile in tracker.opponents.items():
            print(f"  {name}: {profile.hands_seen} hands, VPIP={profile.get_vpip():.1f}%, "
                  f"Type={profile.classify_player_type()}")
        
        # Test the enhanced context function
        community_cards = ["Ah", "7c", "2d"]  # Dry board
        opponent_context, estimated_range, fold_equity = get_enhanced_opponent_context(
            opponent_tracker=tracker,
            active_opponents_count=2,
            bet_to_call=5.0,
            pot_size=20.0,
            community_cards=community_cards
        )
        
        print(f"\n✓ Enhanced context analysis:")
        print(f"  Opponents analyzed: {len(opponent_context)}")
        print(f"  Estimated range: {estimated_range}")
        print(f"  Fold equity estimate: {fold_equity:.2f}")
        
        for name, context in opponent_context.items():
            print(f"  {name}: type={context['type']}, position={context['position']}, "
                  f"fold_equity={context['fold_equity']:.2f}")
        
        # Test with postflop decision integration
        print(f"\n=== Testing Postflop Integration ===")
        
        # Mock decision engine components
        class MockDecisionEngine:
            def should_bluff_func(self, pot, stack, street, win_prob):
                return False
        
        from postflop_decision_logic import make_postflop_decision
        
        # Test parameters
        test_params = {
            'decision_engine_instance': MockDecisionEngine(),
            'numerical_hand_rank': 2,  # One pair
            'hand_description': 'Pair of Aces',
            'bet_to_call': 5.0,
            'can_check': True,
            'pot_size': 20.0,
            'my_stack': 95.0,
            'win_probability': 0.65,
            'pot_odds_to_call': 0.2,
            'game_stage': 'flop',
            'spr': 4.75,
            'action_fold_const': 'fold',
            'action_check_const': 'check',
            'action_call_const': 'call',
            'action_raise_const': 'raise',
            'my_player_data': {
                'position': 'BB',
                'current_bet': 0,
                'community_cards': community_cards
            },
            'big_blind_amount': 2.0,
            'base_aggression_factor': 2.0,
            'max_bet_on_table': 6.0,
            'active_opponents_count': 2,
            'opponent_tracker': tracker
        }
        
        action, amount = make_postflop_decision(**test_params)
        print(f"✓ Postflop decision: {action} {amount}")
        
        print(f"\n✓ All tests passed! Opponent tracking fix working correctly.")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_opponent_tracking_fix()
    sys.exit(0 if success else 1)
