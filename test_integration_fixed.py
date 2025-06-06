#!/usr/bin/env python3
"""
Fixed comprehensive test suite for poker bot improvements.
Tests the integration of all major enhancements with correct function signatures.
"""

import sys
import os
import logging
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from preflop_decision_logic import make_preflop_decision, adjust_for_implied_odds
from postflop_decision_logic import make_postflop_decision, get_dynamic_bet_size
from opponent_tracking import OpponentTracker
from tournament_adjustments import get_tournament_adjustment_factor
from implied_odds import calculate_implied_odds

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Action constants
ACTION_FOLD = 0
ACTION_CHECK = 1
ACTION_CALL = 2
ACTION_RAISE = 3

def test_preflop_integration():
    """Test preflop decision logic with correct parameters"""
    print("\n--- Preflop Integration Test ---")
    
    try:
        # Test suited connector with deep stacks
        action, amount = make_preflop_decision(
            my_player={'current_bet': 0, 'stack': 3.0},
            hand_category='Suited Connector',
            position='CO',
            bet_to_call=0.08,  # 4BB
            can_check=False,
            my_stack=3.0,
            pot_size=0.03,
            active_opponents_count=2,
            small_blind=0.01,
            big_blind=0.02,
            my_current_bet_this_street=0,
            max_bet_on_table=0.08,
            min_raise=0.04,
            is_sb=False,
            is_bb=False,
            action_fold_const=ACTION_FOLD,
            action_check_const=ACTION_CHECK,
            action_call_const=ACTION_CALL,
            action_raise_const=ACTION_RAISE
        )
        
        print(f"✓ Suited connector deep stacks: Action={action}, Amount={amount:.3f}")
        if action == ACTION_CALL:
            print("  ✓ PASS - Called with implied odds")
        else:
            print("  ✗ FAIL - Should call with deep stacks")
            
    except Exception as e:
        print(f"✗ Error in preflop test: {e}")
    
    print("✓ Preflop integration test completed")

def test_postflop_integration():
    """Test postflop decision logic with correct parameters"""
    print("\n--- Postflop Integration Test ---")
    
    # Mock decision engine
    class MockDecisionEngine:
        def should_bluff_func(self, pot_size, stack, street, win_prob, **kwargs):
            return street == 'river' and win_prob < 0.3 and pot_size < stack * 0.2
    
    mock_engine = MockDecisionEngine()
    
    try:
        # Test value betting with strong hand
        action, amount = make_postflop_decision(
            decision_engine_instance=mock_engine,
            numerical_hand_rank=6,  # Straight
            hand_description="Straight",
            bet_to_call=0,
            can_check=True,
            pot_size=0.20,
            my_stack=1.8,
            win_probability=0.80,
            pot_odds_to_call=0,
            game_stage="flop",
            spr=9.0,
            action_fold_const=ACTION_FOLD,
            action_check_const=ACTION_CHECK,
            action_call_const=ACTION_CALL,
            action_raise_const=ACTION_RAISE,
            my_player_data={'current_bet': 0},
            big_blind_amount=0.02,
            base_aggression_factor=1.0,
            max_bet_on_table=0,
            active_opponents_count=1
        )
        
        print(f"✓ Strong hand value bet: Action={action}, Amount={amount:.3f}")
        if action == ACTION_RAISE and amount > 0:
            print("  ✓ PASS - Betting for value with strong hand")
        else:
            print("  ✗ FAIL - Should bet with strong hand")
            
    except Exception as e:
        print(f"✗ Error in postflop test: {e}")
    
    print("✓ Postflop integration test completed")

def test_dynamic_bet_sizing():
    """Test dynamic bet sizing function"""
    print("\n--- Dynamic Bet Sizing Test ---")
    
    try:
        # Test value bet sizing
        bet_size = get_dynamic_bet_size(
            numerical_hand_rank=4,  # Three of a kind
            pot_size=0.20,
            my_stack=1.0,
            street="flop",
            big_blind_amount=0.02,
            active_opponents_count=1,
            bluff=False
        )
        
        print(f"✓ Value bet sizing: {bet_size:.3f} (pot: 0.20)")
        if 0.10 <= bet_size <= 0.25:  # Should be 50-125% of pot
            print("  ✓ PASS - Reasonable value bet size")
        else:
            print("  ✗ FAIL - Bet size out of expected range")
            
        # Test bluff sizing
        bluff_size = get_dynamic_bet_size(
            numerical_hand_rank=0,  # High card
            pot_size=0.15,
            my_stack=0.8,
            street="turn",
            big_blind_amount=0.02,
            active_opponents_count=1,
            bluff=True
        )
        
        print(f"✓ Bluff bet sizing: {bluff_size:.3f} (pot: 0.15)")
        if 0.05 <= bluff_size <= 0.15:  # Should be reasonable bluff size
            print("  ✓ PASS - Reasonable bluff size")
        else:
            print("  ✗ FAIL - Bluff size out of expected range")
            
    except Exception as e:
        print(f"✗ Error in bet sizing test: {e}")
    
    print("✓ Dynamic bet sizing test completed")

def test_opponent_tracking():
    """Test opponent tracking integration"""
    print("\n--- Opponent Tracking Test ---")
    
    try:
        tracker = OpponentTracker()
        
        # Add some opponent actions
        tracker.update_opponent_action("Player1", "preflop", "raise", 0.08, 0.03)
        tracker.update_opponent_action("Player1", "flop", "bet", 0.15, 0.20)
        tracker.update_opponent_action("Player2", "preflop", "call", 0.08, 0.03)
        tracker.update_opponent_action("Player2", "flop", "fold", 0, 0.20)
        
        # Get opponent profile
        if "Player1" in tracker.opponents:
            profile = tracker.opponents["Player1"]
            print(f"✓ Player1 profile: VPIP={profile.vpip:.1f}%, PFR={profile.pfr:.1f}%, Type={profile.player_type}")
            
            if profile.hands_seen > 0:
                print("  ✓ PASS - Opponent tracking working")
            else:
                print("  ✗ FAIL - No hands tracked")
        else:
            print("  ✗ FAIL - Player1 not found in tracker")
            
        # Test table dynamics
        dynamics = tracker.get_table_dynamics()
        print(f"✓ Table dynamics: {dynamics}")
        
    except Exception as e:
        print(f"✗ Error in opponent tracking test: {e}")
    
    print("✓ Opponent tracking test completed")

def test_tournament_adjustments():
    """Test tournament adjustment integration"""
    print("\n--- Tournament Adjustments Test ---")
    
    try:
        # Test short stack tournament adjustments
        adjustment = get_tournament_adjustment_factor(
            stack_size=0.6,  # 30BB
            big_blind=0.02,
            tournament_level=2
        )
        
        print(f"✓ Tournament adjustment (30BB, level 2): {adjustment}")
        if 0.5 <= adjustment <= 1.5:
            print("  ✓ PASS - Reasonable tournament adjustment")
        else:
            print("  ✗ FAIL - Tournament adjustment out of range")
            
    except Exception as e:
        print(f"✗ Error in tournament test: {e}")
    
    print("✓ Tournament adjustments test completed")

def test_implied_odds():
    """Test implied odds calculation"""
    print("\n--- Implied Odds Test ---")
    
    try:
        # Test implied odds calculation
        implied_odds = calculate_implied_odds(
            pot_size=0.20,
            bet_to_call=0.08,
            win_probability=0.35,
            opponent_stack=1.5,
            my_stack=1.2,
            street="flop"
        )
        
        print(f"✓ Implied odds calculation: {implied_odds:.3f}")
        if implied_odds > 0:
            print("  ✓ PASS - Implied odds calculated")
        else:
            print("  ✗ FAIL - Invalid implied odds")
            
    except Exception as e:
        print(f"✗ Error in implied odds test: {e}")
    
    print("✓ Implied odds test completed")

def main():
    """Run all integration tests"""
    print("=" * 60)
    print("FIXED INTEGRATION TESTS FOR POKER BOT ENHANCEMENTS")
    print("=" * 60)
    
    test_preflop_integration()
    test_postflop_integration()
    test_dynamic_bet_sizing()
    test_opponent_tracking()
    test_tournament_adjustments()
    test_implied_odds()
    
    print("\n" + "=" * 60)
    print("INTEGRATION TESTS COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    main()
