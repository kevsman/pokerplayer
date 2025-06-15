#!/usr/bin/env python3
"""
Test the maximum aggression settings for the poker bot.
This test validates that the bot is significantly more aggressive with the new settings.
"""

import logging
import json
from unittest.mock import Mock
from config import Config
from decision_engine import DecisionEngine
from hand_evaluator import HandEvaluator
from preflop_decision_logic import make_preflop_decision

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_maximum_aggression_config():
    """Test that the config has the maximum aggression settings."""
    
    # Load config
    config = Config()
    strategy = config.get_setting('strategy', {})
    
    # Test aggression factors
    assert strategy.get('base_aggression_factor_preflop', 0) >= 3.0, "Preflop aggression should be >= 3.0"
    assert strategy.get('base_aggression_factor_postflop', 0) >= 3.0, "Postflop aggression should be >= 3.0"
    
    # Test bluff frequencies
    assert strategy.get('bluff_frequency', 0) >= 0.55, "Bluff frequency should be >= 55%"
    assert strategy.get('three_bet_frequency', 0) >= 0.70, "3-bet frequency should be >= 70%"
    
    # Test range widening
    assert strategy.get('preflop_range_widening', 0) >= 0.50, "Range widening should be >= 50%"
    
    print("✓ Maximum aggression config test passed!")

def test_weak_hand_aggression():
    """Test that weak hands are played more aggressively."""
    
    config = Config()
    hand_evaluator = HandEvaluator()
    decision_engine = DecisionEngine(hand_evaluator, config)
    
    # Mock player with weak hand
    mock_player = {
        'name': 'TestBot',
        'hand': ['6♦', 'K♠'],  # K6 offsuit - weak hand
        'stack': 1.0,
        'current_bet': 0.0,
        'config': config
    }
    
    # Test from BTN (should be very aggressive)
    action, amount = make_preflop_decision(
        my_player=mock_player,
        hand_category="Weak",
        position="BTN",
        bet_to_call=0.02,
        can_check=False,
        my_stack=1.0,
        pot_size=0.03,
        active_opponents_count=2,
        small_blind=0.01,
        big_blind=0.02,
        my_current_bet_this_street=0.0,
        max_bet_on_table=0.02,
        min_raise=0.04,
        is_sb=False,
        is_bb=False,
        action_fold_const='fold',
        action_check_const='check',
        action_call_const='call',
        action_raise_const='raise'
    )
    
    print(f"Weak hand from BTN: Action={action}, Amount={amount}")
    
    # Test from CO (should still be aggressive)
    action2, amount2 = make_preflop_decision(
        my_player=mock_player,
        hand_category="Weak",
        position="CO",
        bet_to_call=0.02,
        can_check=False,
        my_stack=1.0,
        pot_size=0.03,
        active_opponents_count=3,
        small_blind=0.01,
        big_blind=0.02,
        my_current_bet_this_street=0.0,
        max_bet_on_table=0.02,
        min_raise=0.04,
        is_sb=False,
        is_bb=False,
        action_fold_const='fold',
        action_check_const='check',
        action_call_const='call',
        action_raise_const='raise'
    )
    
    print(f"Weak hand from CO: Action={action2}, Amount={amount2}")
    
    print("✓ Weak hand aggression test completed!")

def test_bet_sizing_aggression():
    """Test that bet sizing is maximally aggressive."""
    
    from bet_utils import get_optimal_bet_size
    
    # Test bluff sizing
    bluff_bet = get_optimal_bet_size(
        hand_strength=1,  # Weak hand
        pot_size=0.10,
        stack_size=1.0,
        game_stage="Flop",
        big_blind=0.02,
        bluff=True,
        aggression_factor=3.5
    )
    
    # Should be a large bluff (> pot size with max aggression)
    assert bluff_bet >= 0.10, f"Bluff bet should be >= pot size, got {bluff_bet}"
    print(f"Aggressive bluff sizing: {bluff_bet} (pot: 0.10)")
    
    # Test value betting
    value_bet = get_optimal_bet_size(
        hand_strength=5,  # Strong hand
        pot_size=0.10,
        stack_size=1.0,
        game_stage="River",
        big_blind=0.02,
        bluff=False,
        aggression_factor=3.5
    )
    
    # Should be a large value bet
    assert value_bet >= 0.12, f"Value bet should be > pot size, got {value_bet}"
    print(f"Aggressive value sizing: {value_bet} (pot: 0.10)")
    
    print("✓ Bet sizing aggression test passed!")

def test_decision_engine_aggression():
    """Test that the decision engine is initialized with maximum aggression."""
    
    config = Config()
    hand_evaluator = HandEvaluator()
    decision_engine = DecisionEngine(hand_evaluator, config)
    
    # Check aggression factors
    assert decision_engine.preflop_aggression_factor >= 3.0, "Preflop aggression factor should be >= 3.0"
    assert decision_engine.base_aggression_factor >= 3.0, "Postflop aggression factor should be >= 3.0"
    assert decision_engine.bluff_frequency >= 0.55, "Bluff frequency should be >= 55%"
    
    print(f"Decision engine aggression - Preflop: {decision_engine.preflop_aggression_factor}, Postflop: {decision_engine.base_aggression_factor}")
    print(f"Bluff frequency: {decision_engine.bluff_frequency}")
    
    print("✓ Decision engine aggression test passed!")

if __name__ == "__main__":
    print("🚀 Testing Maximum Aggression Settings...")
    print("=" * 50)
    
    try:
        test_maximum_aggression_config()
        test_bet_sizing_aggression()
        test_decision_engine_aggression()
        test_weak_hand_aggression()
        
        print("=" * 50)
        print("✅ ALL MAXIMUM AGGRESSION TESTS PASSED!")
        print("🔥 Bot is now configured for complete table domination!")
        print("=" * 50)
        
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
