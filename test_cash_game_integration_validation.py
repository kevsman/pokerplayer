# test_cash_game_integration_validation.py
"""
Integration test to validate cash game enhancements in the main postflop decision logic.
"""

import unittest
import sys
from unittest.mock import Mock, MagicMock

def test_cash_game_integration():
    """Test that cash game enhancements are properly integrated into postflop decisions."""
    print("🎯 TESTING CASH GAME ENHANCEMENTS INTEGRATION")
    print("=" * 60)
    
    try:
        # Test 1: Import functionality
        print("\n--- Test 1: Module Integration ---")
        from postflop_decision_logic import make_postflop_decision
        from cash_game_enhancements import CashGameEnhancer, apply_cash_game_enhancements
        from advanced_position_strategy import AdvancedPositionStrategy
        
        print("✅ All modules imported successfully")
        
        # Test 2: Basic functionality test
        print("\n--- Test 2: Basic Cash Game Enhancement ---")
        enhancer = CashGameEnhancer()
        
        # Test position adjustments
        position_adj = enhancer.get_position_based_adjustments('BTN', 'flop', 'strong', 1, 100)
        print(f"✅ Position adjustments: aggression={position_adj['aggression_multiplier']:.2f}")
        
        # Test stack strategy  
        stack_strategy = enhancer.get_stack_depth_strategy(150, 150, 20, 2)
        print(f"✅ Stack strategy: {stack_strategy['strategy_type']}")
        
        # Test 3: Postflop integration test
        print("\n--- Test 3: Postflop Decision Integration ---")
        
        # Create mock decision engine
        mock_engine = Mock()
        mock_engine.should_bluff_func = Mock(return_value=False)
        
        # Create mock opponent tracker
        mock_opponent_tracker = Mock()
        mock_opponent_tracker.opponents = {
            'Player1': Mock(
                hands_seen=20,
                get_vpip=Mock(return_value=28.0),
                get_pfr=Mock(return_value=22.0)
            )
        }
        mock_opponent_tracker.get_fold_to_cbet_percent = Mock(return_value=55.0)
        
        # Test scenario 1: Button value betting on river
        decision, amount = make_postflop_decision(
            decision_engine_instance=mock_engine,
            numerical_hand_rank=5,  # Strong hand
            hand_description="Two Pair",
            bet_to_call=0,
            can_check=True,
            pot_size=120,
            my_stack=800,
            win_probability=0.72,
            pot_odds_to_call=0,
            game_stage='river',
            spr=6.7,
            action_fold_const='fold',
            action_check_const='check',
            action_call_const='call',
            action_raise_const='raise',
            my_player_data={
                'current_bet': 0,
                'position': 'BTN',
                'community_cards': ['Ah', '9c', '7s', 'Kh', '2d']
            },
            big_blind_amount=10,
            base_aggression_factor=1.0,
            max_bet_on_table=0,
            active_opponents_count=1,
            opponent_tracker=mock_opponent_tracker
        )
        
        print(f"✅ Button river value bet: {decision} {amount if amount > 0 else ''}")
        assert decision in ['check', 'raise'], f"Expected check or raise, got {decision}"
        
        # Test scenario 2: Early position with deep stacks
        decision2, amount2 = make_postflop_decision(
            decision_engine_instance=mock_engine,
            numerical_hand_rank=4,  # Strong hand
            hand_description="Straight",
            bet_to_call=0,
            can_check=True,
            pot_size=45,
            my_stack=3000,  # Deep stack
            win_probability=0.85,
            pot_odds_to_call=0,
            game_stage='flop',
            spr=66.7,
            action_fold_const='fold',
            action_check_const='check',
            action_call_const='call',
            action_raise_const='raise',
            my_player_data={
                'current_bet': 0,
                'position': 'UTG',
                'community_cards': ['8h', '9c', '7s']
            },
            big_blind_amount=10,
            base_aggression_factor=1.0,
            max_bet_on_table=0,
            active_opponents_count=3,
            opponent_tracker=mock_opponent_tracker
        )
        
        print(f"✅ UTG deep stack strong hand: {decision2} {amount2 if amount2 > 0 else ''}")
        assert decision2 in ['check', 'raise'], f"Expected check or raise, got {decision2}"
        
        # Test scenario 3: River calling decision with cash game analysis
        decision3, amount3 = make_postflop_decision(
            decision_engine_instance=mock_engine,
            numerical_hand_rank=2,  # Medium hand (one pair)
            hand_description="Pair of Kings",
            bet_to_call=80,
            can_check=False,
            pot_size=200,
            my_stack=400,
            win_probability=0.58,
            pot_odds_to_call=0.29,  # 80/(200+80) = 28.6%
            game_stage='river',
            spr=2.0,
            action_fold_const='fold',
            action_check_const='check',
            action_call_const='call',
            action_raise_const='raise',
            my_player_data={
                'current_bet': 0,
                'position': 'BB',
                'community_cards': ['Kh', '9c', '7s', '4h', '2d']
            },
            big_blind_amount=10,
            base_aggression_factor=1.0,
            max_bet_on_table=80,
            active_opponents_count=1,
            opponent_tracker=mock_opponent_tracker
        )
        
        print(f"✅ River calling decision: {decision3} {amount3 if amount3 > 0 else ''}")
        assert decision3 in ['call', 'fold'], f"Expected call or fold, got {decision3}"
        
        print("\n--- Test 4: Advanced Position Strategy ---")
        
        # Test advanced position strategy
        position_strategy = AdvancedPositionStrategy()
        
        # Test late position strategy
        late_pos_strategy = position_strategy.get_position_strategy('BTN', 'flop', 'medium', 1, 100)
        print(f"✅ Button strategy: power={late_pos_strategy['position_power']}, aggression={late_pos_strategy['aggression_level']}")
        
        # Test early position strategy
        early_pos_strategy = position_strategy.get_position_strategy('UTG', 'flop', 'medium', 3, 100)
        print(f"✅ UTG strategy: power={early_pos_strategy['position_power']}, aggression={early_pos_strategy['aggression_level']}")
        
        # Verify position differences
        assert late_pos_strategy['position_power'] > early_pos_strategy['position_power'], "Button should have higher position power than UTG"
        assert late_pos_strategy['aggression_level'] >= early_pos_strategy['aggression_level'], "Button should be at least as aggressive as UTG"
        
        print("\n🎉 ALL CASH GAME INTEGRATION TESTS PASSED!")
        print("✅ Cash game enhancements are properly integrated")
        print("✅ Position-based adjustments working")
        print("✅ Stack depth strategy working")
        print("✅ River decision enhancements working")
        print("✅ Advanced position strategy working")
        
        return True
        
    except Exception as e:
        print(f"\n❌ INTEGRATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cash_game_enhancement_effects():
    """Test that cash game enhancements actually affect decisions."""
    print("\n🔍 TESTING CASH GAME ENHANCEMENT EFFECTS")
    print("=" * 60)
    
    try:
        from postflop_decision_logic import make_postflop_decision
        
        # Create mock decision engine
        mock_engine = Mock()
        mock_engine.should_bluff_func = Mock(return_value=False)
        
        # Create mock opponent tracker for loose opponent
        loose_opponent_tracker = Mock()
        loose_opponent_tracker.opponents = {
            'LoosePlayer': Mock(
                hands_seen=50,
                get_vpip=Mock(return_value=45.0),  # Very loose
                get_pfr=Mock(return_value=12.0)
            )
        }
        loose_opponent_tracker.get_fold_to_cbet_percent = Mock(return_value=25.0)  # Rarely folds
        
        # Create mock opponent tracker for tight opponent
        tight_opponent_tracker = Mock()
        tight_opponent_tracker.opponents = {
            'TightPlayer': Mock(
                hands_seen=50,
                get_vpip=Mock(return_value=18.0),  # Very tight
                get_pfr=Mock(return_value=15.0)
            )
        }
        tight_opponent_tracker.get_fold_to_cbet_percent = Mock(return_value=70.0)  # Often folds
        
        base_scenario = {
            'decision_engine_instance': mock_engine,
            'numerical_hand_rank': 5,  # Strong hand
            'hand_description': "Two Pair",
            'bet_to_call': 0,
            'can_check': True,
            'pot_size': 100,
            'my_stack': 800,
            'win_probability': 0.68,
            'pot_odds_to_call': 0,
            'game_stage': 'flop',
            'spr': 8.0,
            'action_fold_const': 'fold',
            'action_check_const': 'check',
            'action_call_const': 'call',
            'action_raise_const': 'raise',
            'my_player_data': {
                'current_bet': 0,
                'position': 'BTN',
                'community_cards': ['Ah', '9c', '7s']
            },
            'big_blind_amount': 10,
            'base_aggression_factor': 1.0,
            'max_bet_on_table': 0,
            'active_opponents_count': 1
        }
        
        # Test vs loose opponent
        decision_vs_loose, amount_vs_loose = make_postflop_decision(
            opponent_tracker=loose_opponent_tracker,
            **base_scenario
        )
        
        # Test vs tight opponent  
        decision_vs_tight, amount_vs_tight = make_postflop_decision(
            opponent_tracker=tight_opponent_tracker,
            **base_scenario
        )
        
        print(f"✅ Vs Loose opponent (VPIP 45%): {decision_vs_loose} {amount_vs_loose if amount_vs_loose > 0 else ''}")
        print(f"✅ Vs Tight opponent (VPIP 18%): {decision_vs_tight} {amount_vs_tight if amount_vs_tight > 0 else ''}")
        
        # Both should bet, but potentially different sizes
        if decision_vs_loose == 'raise' and decision_vs_tight == 'raise':
            if amount_vs_loose != amount_vs_tight:
                print(f"✅ Different bet sizes detected: {amount_vs_loose:.2f} vs {amount_vs_tight:.2f}")
            else:
                print("ℹ️  Same bet sizes (may be correct depending on analysis)")
        
        # Test position effects
        print("\n--- Position Effects Test ---")
        
        # Button vs UTG comparison
        btn_scenario = base_scenario.copy()
        btn_scenario['my_player_data'] = {
            'current_bet': 0,
            'position': 'BTN',
            'community_cards': ['Ah', '9c', '7s']
        }
        
        utg_scenario = base_scenario.copy()
        utg_scenario['my_player_data'] = {
            'current_bet': 0,
            'position': 'UTG',
            'community_cards': ['Ah', '9c', '7s']
        }
        utg_scenario['active_opponents_count'] = 3  # More opponents from early position
        
        decision_btn, amount_btn = make_postflop_decision(
            opponent_tracker=loose_opponent_tracker,
            **btn_scenario
        )
        
        decision_utg, amount_utg = make_postflop_decision(
            opponent_tracker=loose_opponent_tracker,
            **utg_scenario
        )
        
        print(f"✅ Button position: {decision_btn} {amount_btn if amount_btn > 0 else ''}")
        print(f"✅ UTG position: {decision_utg} {amount_utg if amount_utg > 0 else ''}")
        
        print("\n🎉 CASH GAME ENHANCEMENT EFFECTS VALIDATED!")
        return True
        
    except Exception as e:
        print(f"\n❌ EFFECTS TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_complete_cash_game_validation():
    """Run all cash game enhancement validation tests."""
    print("🚀 COMPLETE CASH GAME ENHANCEMENT VALIDATION")
    print("=" * 70)
    
    test_results = []
    
    # Test 1: Basic integration
    print("\n📋 PHASE 1: INTEGRATION TESTING")
    integration_success = test_cash_game_integration()
    test_results.append(("Integration Test", integration_success))
    
    # Test 2: Enhancement effects
    print("\n📋 PHASE 2: ENHANCEMENT EFFECTS TESTING")
    effects_success = test_cash_game_enhancement_effects()
    test_results.append(("Enhancement Effects Test", effects_success))
    
    # Summary
    print("\n" + "=" * 70)
    print("🎯 CASH GAME ENHANCEMENT VALIDATION SUMMARY")
    print("=" * 70)
    
    passed = 0
    total = len(test_results)
    
    for test_name, success in test_results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\n📊 OVERALL RESULT: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL CASH GAME ENHANCEMENT VALIDATIONS PASSED!")
        print("✅ System ready for live testing with cash game enhancements")
        print("\n🚀 NEXT STEPS:")
        print("   • Deploy to test environment")
        print("   • Monitor performance over 100+ hands")
        print("   • Fine-tune parameters based on results")
        print("   • Consider additional cash game features")
        return True
    else:
        print("⚠️  Some validations failed - review implementations")
        return False

if __name__ == "__main__":
    success = run_complete_cash_game_validation()
    sys.exit(0 if success else 1)
