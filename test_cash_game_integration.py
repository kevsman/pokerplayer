# test_cash_game_integration.py
"""
Comprehensive testing for cash game enhancements integration.
Tests the new CashGameEnhancer and AdvancedPositionStrategy modules.
"""

import unittest
import sys
from unittest.mock import Mock, MagicMock

# Test that cash game enhancement modules exist and work
def test_cash_game_modules_available():
    """Test that both new cash game modules are available and functional."""
    try:
        from cash_game_enhancements import CashGameEnhancer, apply_cash_game_enhancements
        from advanced_position_strategy import AdvancedPositionStrategy
        
        print("✅ Cash game enhancement modules imported successfully")
        return True, "Modules available"
    except ImportError as e:
        print(f"❌ Cash game modules not available: {e}")
        return False, str(e)

def test_cash_game_enhancer_functionality():
    """Test CashGameEnhancer class functionality."""
    try:
        from cash_game_enhancements import CashGameEnhancer
        
        enhancer = CashGameEnhancer()
        
        # Test position adjustments
        position_adj = enhancer.get_position_based_adjustments(
            position='BTN',
            street='flop',
            hand_strength='strong',
            active_opponents_count=1,
            stack_depth_bb=100
        )
        
        assert 'aggression_multiplier' in position_adj
        assert 'thin_value_threshold' in position_adj
        assert position_adj['aggression_multiplier'] > 1.0  # Button should be aggressive
        
        # Test stack depth strategy
        stack_strategy = enhancer.get_stack_depth_strategy(
            stack_depth_bb=150,  # Deep stack
            effective_stack_bb=150,
            pot_size=20,
            big_blind=2
        )
        
        assert 'strategy_type' in stack_strategy
        assert 'recommendations' in stack_strategy
        assert stack_strategy['strategy_type'] == 'deep_stack'
        
        # Test thin value analysis
        thin_value = enhancer.analyze_thin_value_opportunity(
            hand_strength='medium',
            win_probability=0.62,
            position='BTN',
            opponent_analysis={'calling_frequency': 0.6},
            board_texture={'texture': 'dry'},
            street='river'
        )
        
        assert 'is_thin_value_spot' in thin_value
        assert 'confidence' in thin_value
        
        # Test bet sizing optimization
        bet_sizing = enhancer.get_bet_sizing_optimization(
            hand_strength='strong',
            pot_size=100,
            street='flop',
            position='BTN',
            opponent_count=1,
            stack_depth_bb=100,
            board_texture={'texture': 'wet'},
            opponent_stats={'calling_frequency': 0.7}
        )
        
        assert 'recommended_size' in bet_sizing
        assert 'pot_fraction' in bet_sizing
        assert bet_sizing['recommended_size'] > 0
        
        print("✅ CashGameEnhancer functionality tests passed")
        return True, "All functionality tests passed"
        
    except Exception as e:
        print(f"❌ CashGameEnhancer functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)

def test_advanced_position_strategy():
    """Test AdvancedPositionStrategy class functionality."""
    try:
        from advanced_position_strategy import AdvancedPositionStrategy
        
        strategy = AdvancedPositionStrategy()
        
        # Test position classification
        position_info = strategy.get_position_strategy('BTN', 'flop', 'strong', 1, 100)
        
        assert 'position_power' in position_info
        assert 'aggression_level' in position_info
        assert 'bluff_frequency' in position_info
        
        # Test stealing strategy
        steal_analysis = strategy.analyze_steal_opportunity('CO', 100, 6, {'tight': 2, 'loose': 1})
        
        assert 'should_attempt_steal' in steal_analysis
        assert 'steal_frequency' in steal_analysis
        assert 'sizing_recommendation' in steal_analysis
        
        # Test calling strategy
        call_analysis = strategy.get_position_based_calling_strategy(
            'MP', 'BTN', 'medium', 0.55, 50, 100, 'flop'
        )
        
        assert 'calling_threshold' in call_analysis
        assert 'position_adjustment' in call_analysis
        
        print("✅ AdvancedPositionStrategy functionality tests passed")
        return True, "All position strategy tests passed"
        
    except Exception as e:
        print(f"❌ AdvancedPositionStrategy functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)

def test_cash_game_enhancements_integration():
    """Test apply_cash_game_enhancements function with realistic scenarios."""
    try:
        from cash_game_enhancements import apply_cash_game_enhancements
        
        # Scenario 1: Button thin value spot on river
        decision_context = {
            'hand_strength': 'medium',
            'win_probability': 0.58,
            'position': 'BTN',
            'street': 'river',
            'pot_size': 120,
            'stack_size': 800,
            'big_blind': 10,
            'active_opponents': 1,
            'opponent_analysis': {
                'calling_frequency': 0.65,
                'vpip': 28.0,
                'pfr': 22.0,
                'player_type': 'TAG'
            },
            'board_texture': {
                'texture': 'dry',
                'paired': False,
                'flush_possible': False,
                'straight_possible': False
            }
        }
        
        enhancements = apply_cash_game_enhancements(decision_context)
        
        assert 'position_adjustments' in enhancements
        assert 'thin_value_analysis' in enhancements
        assert 'optimized_bet_sizing' in enhancements
        assert 'river_analysis' in enhancements
        assert enhancements['overall_confidence'] > 0.5
        
        # Scenario 2: Early position with deep stacks
        decision_context_2 = {
            'hand_strength': 'strong',
            'win_probability': 0.75,
            'position': 'UTG',
            'street': 'flop',
            'pot_size': 45,
            'stack_size': 3000,  # Deep stack
            'big_blind': 10,
            'active_opponents': 3,
            'opponent_analysis': {
                'avg_vpip': 35.0,
                'avg_calling_frequency': 0.45
            },
            'board_texture': {
                'texture': 'wet',
                'flush_possible': True,
                'straight_possible': True
            }
        }
        
        enhancements_2 = apply_cash_game_enhancements(decision_context_2)
        
        assert 'stack_strategy' in enhancements_2
        assert 'exploitative_adjustments' in enhancements_2
        assert enhancements_2['stack_strategy']['strategy_type'] == 'deep_stack'
        
        print("✅ Cash game enhancements integration tests passed")
        return True, "Integration tests passed"
        
    except Exception as e:
        print(f"❌ Cash game enhancements integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)

def test_postflop_integration_readiness():
    """Test that postflop decision logic can integrate with cash game enhancements."""
    try:
        # Import required modules
        from postflop_decision_logic import make_postflop_decision
        from cash_game_enhancements import apply_cash_game_enhancements
        
        # Create mock decision engine
        mock_engine = Mock()
        mock_engine.should_bluff_func = Mock(return_value=False)
        
        # Create mock opponent tracker
        mock_opponent_tracker = Mock()
        mock_opponent_tracker.opponents = {}
        mock_opponent_tracker.get_fold_to_cbet_percent = Mock(return_value=50.0)
        
        # Test current postflop decision (without cash game enhancements)
        decision, amount = make_postflop_decision(
            decision_engine_instance=mock_engine,
            numerical_hand_rank=5,  # Strong hand
            hand_description="Two Pair",
            bet_to_call=0,
            can_check=True,
            pot_size=100,
            my_stack=800,
            win_probability=0.70,
            pot_odds_to_call=0,
            game_stage='flop',
            spr=8.0,
            action_fold_const='fold',
            action_check_const='check',
            action_call_const='call',
            action_raise_const='raise',
            my_player_data={'current_bet': 0, 'position': 'BTN'},
            big_blind_amount=10,
            base_aggression_factor=1.0,
            max_bet_on_table=0,
            active_opponents_count=1,
            opponent_tracker=mock_opponent_tracker
        )
        
        assert decision in ['check', 'raise']
        if decision == 'raise':
            assert amount > 0
        
        # Test cash game enhancement context preparation
        enhancement_context = {
            'hand_strength': 'strong',
            'win_probability': 0.70,
            'position': 'BTN',
            'street': 'flop',
            'pot_size': 100,
            'stack_size': 800,
            'big_blind': 10,
            'active_opponents': 1,
            'opponent_analysis': {
                'fold_to_cbet': 50.0,
                'calling_frequency': 0.6,
                'player_type': 'unknown'
            },
            'board_texture': {
                'texture': 'unknown',
                'paired': False
            }
        }
        
        enhancements = apply_cash_game_enhancements(enhancement_context)
        
        assert enhancements is not None
        assert 'position_adjustments' in enhancements
        
        print("✅ Postflop integration readiness tests passed")
        return True, "Integration readiness confirmed"
        
    except Exception as e:
        print(f"❌ Postflop integration readiness test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)

def run_all_cash_game_tests():
    """Run all cash game enhancement tests."""
    print("🚀 STARTING CASH GAME ENHANCEMENT TESTING")
    print("=" * 60)
    
    tests = [
        ("Module Availability", test_cash_game_modules_available),
        ("CashGameEnhancer Functionality", test_cash_game_enhancer_functionality),
        ("AdvancedPositionStrategy", test_advanced_position_strategy),
        ("Enhancements Integration", test_cash_game_enhancements_integration),
        ("Postflop Integration Readiness", test_postflop_integration_readiness)
    ]
    
    passed = 0
    total = len(tests)
    results = []
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            success, message = test_func()
            if success:
                passed += 1
                results.append(f"✅ {test_name}: PASSED")
            else:
                results.append(f"❌ {test_name}: FAILED - {message}")
        except Exception as e:
            results.append(f"❌ {test_name}: ERROR - {str(e)}")
    
    print("\n" + "=" * 60)
    print("🎯 CASH GAME ENHANCEMENT TEST RESULTS")
    print("=" * 60)
    
    for result in results:
        print(result)
    
    print(f"\n📊 OVERALL: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL CASH GAME ENHANCEMENT TESTS PASSED!")
        print("✅ Ready for integration into main postflop decision logic")
        return True
    else:
        print("⚠️  Some tests failed - check implementations before integration")
        return False

if __name__ == "__main__":
    success = run_all_cash_game_tests()
    sys.exit(0 if success else 1)
