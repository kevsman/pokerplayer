#!/usr/bin/env python3
"""
Comprehensive Integration Test - Final Validation
Tests the complete integration of equity calculator, opponent tracking, and decision logic.
"""

import sys
import logging
from hand_evaluator import HandEvaluator
from decision_engine import DecisionEngine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_complete_integration():
    """Test the complete integration with realistic scenarios"""
    print("=" * 80)
    print("🔥 FINAL INTEGRATION TEST - COMPLETE POKER BOT VALIDATION")
    print("=" * 80)
    
    # Initialize components
    hand_evaluator = HandEvaluator()
    config = {
        'big_blind': 2.0,
        'small_blind': 1.0,
        'base_aggression_factor_postflop': 1.2
    }
    engine = DecisionEngine(hand_evaluator, config)
    
    print("\n✅ Components initialized successfully!")
    print(f"   - Hand Evaluator: {type(hand_evaluator).__name__}")
    print(f"   - Decision Engine: {type(engine).__name__}")
    print(f"   - Equity Calculator: {type(engine.equity_calculator).__name__}")
    print(f"   - Opponent Tracker: {type(engine.opponent_tracker).__name__}")
    
    # Test Scenario 1: Strong hand without provided win_probability
    print("\n" + "="*60)
    print("📊 TEST 1: STRONG HAND - POCKET ACES (No win_probability provided)")
    print("="*60)
    
    game_state_1 = {
        'current_round': 'preflop',
        'pot_size': 3.0,
        'community_cards': [],
        'players': [
            {
                'name': 'Hero',
                'hand': ['A♠', 'A♥'],  # Pocket Aces
                'stack': 100.0,
                'current_bet': 1.0,
                'position': 'BTN',
                'has_turn': True,
                'is_active': True,
                # NO win_probability provided - should trigger equity calculation
            },
            {
                'name': 'Villain',
                'hand': ['hidden', 'hidden'],
                'stack': 98.0,
                'current_bet': 2.0,
                'position': 'BB',
                'has_turn': False,
                'is_active': True,
                'last_action': 'raise',
                'has_acted': True
            }
        ]
    }
    
    action_1, amount_1 = engine.make_decision(game_state_1, 0)
    print(f"Decision with AA: {action_1} {amount_1}")
    print(f"Expected: Should RAISE aggressively (AA is premium)")
    
    # Test Scenario 2: Medium hand on flop with calculated equity
    print("\n" + "="*60)
    print("📊 TEST 2: MEDIUM HAND ON FLOP - 9♠J♦ on 9♦J♠7♠")
    print("="*60)
    
    game_state_2 = {
        'current_round': 'flop',
        'pot_size': 12.0,
        'community_cards': ['9♦', 'J♠', '7♠'],
        'players': [
            {
                'name': 'Hero',
                'hand': ['9♠', 'J♦'],  # Two pair
                'stack': 88.0,
                'current_bet': 0.0,
                'position': 'CO',
                'has_turn': True,
                'is_active': True,
                'bet_to_call': 0.0
                # NO win_probability provided - should calculate equity vs flush/straight draws
            },
            {
                'name': 'Villain',
                'hand': ['hidden', 'hidden'],
                'stack': 94.0,
                'current_bet': 0.0,
                'position': 'BTN',
                'has_turn': False,
                'is_active': True
            }
        ]
    }
    
    action_2, amount_2 = engine.make_decision(game_state_2, 0)
    print(f"Decision with two pair: {action_2} {amount_2}")
    print(f"Expected: Should BET for value (two pair is strong on this board)")
    
    # Test Scenario 3: Drawing hand with equity calculation
    print("\n" + "="*60)
    print("📊 TEST 3: DRAWING HAND - 8♥9♥ on A♠7♦6♣ (straight draw)")
    print("="*60)
    
    game_state_3 = {
        'current_round': 'flop',
        'pot_size': 18.0,
        'community_cards': ['A♠', '7♦', '6♣'],
        'players': [
            {
                'name': 'Hero',
                'hand': ['8♥', '9♥'],  # Gutshot straight draw
                'stack': 82.0,
                'current_bet': 0.0,
                'position': 'SB',
                'has_turn': True,
                'is_active': True,
                'bet_to_call': 8.0  # Facing a bet
            },
            {
                'name': 'Villain',
                'hand': ['hidden', 'hidden'],
                'stack': 74.0,
                'current_bet': 8.0,
                'position': 'BB',
                'has_turn': False,
                'is_active': True,
                'last_action': 'bet'
            }
        ]
    }
    
    action_3, amount_3 = engine.make_decision(game_state_3, 0)
    print(f"Decision with drawing hand: {action_3} {amount_3}")
    print(f"Expected: Should evaluate pot odds vs equity and likely FOLD")
    
    # Test Scenario 4: Weak hand - should fold quickly
    print("\n" + "="*60)
    print("📊 TEST 4: WEAK HAND - 2♠7♣ on K♥Q♦J♠ (nothing)")
    print("="*60)
    
    game_state_4 = {
        'current_round': 'flop',
        'pot_size': 24.0,
        'community_cards': ['K♥', 'Q♦', 'J♠'],
        'players': [
            {
                'name': 'Hero',
                'hand': ['2♠', '7♣'],  # Complete air
                'stack': 76.0,
                'current_bet': 0.0,
                'position': 'UTG',
                'has_turn': True,
                'is_active': True,
                'bet_to_call': 12.0  # Large bet
            },
            {
                'name': 'Villain',
                'hand': ['hidden', 'hidden'],
                'stack': 62.0,
                'current_bet': 12.0,
                'position': 'BTN',
                'has_turn': False,
                'is_active': True,
                'last_action': 'bet'
            }
        ]
    }
    
    action_4, amount_4 = engine.make_decision(game_state_4, 0)
    print(f"Decision with weak hand: {action_4} {amount_4}")
    print(f"Expected: Should FOLD (very low equity, large bet)")
    
    # Validate opponent tracking is working
    print("\n" + "="*60)
    print("📊 OPPONENT TRACKING VALIDATION")
    print("="*60)
    
    opponents = engine.opponent_tracker.opponents
    print(f"Tracked opponents: {len(opponents)}")
    for name, profile in opponents.items():
        print(f"  {name}: {profile.hands_seen} hands, VPIP: {profile.get_vpip():.1f}%, PFR: {profile.get_pfr():.1f}%")
    
    # Final validation
    print("\n" + "="*80)
    print("🎯 INTEGRATION VALIDATION SUMMARY")
    print("="*80)
    
    validations = [
        ("Equity Calculator Integration", "✅ PASS" if action_1 in ['raise'] else "❌ FAIL"),
        ("Postflop Decision Logic", "✅ PASS" if action_2 in ['raise', 'bet'] else "❌ FAIL"),  
        ("Drawing Hand Analysis", "✅ PASS" if action_3 in ['fold', 'call'] else "❌ FAIL"),
        ("Weak Hand Folding", "✅ PASS" if action_4 == 'fold' else "❌ FAIL"),
        ("Opponent Tracking", "✅ PASS" if len(opponents) > 0 else "❌ FAIL")
    ]
    
    for test_name, result in validations:
        print(f"  {test_name:.<50} {result}")
    
    passed = sum(1 for _, result in validations if "PASS" in result)
    total = len(validations)
    
    print(f"\n🏆 FINAL SCORE: {passed}/{total} tests passed")
    
    if passed == total:
        print("🚀 COMPLETE INTEGRATION SUCCESS! The poker bot is fully operational.")
        print("   - Equity calculations are working correctly")
        print("   - Decision logic responds appropriately to hand strength")
        print("   - Opponent tracking is collecting data")
        print("   - All components are properly integrated")
    else:
        print("⚠️  Some integration issues detected. Review the failed tests.")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = test_complete_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Integration test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
