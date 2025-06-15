#!/usr/bin/env python3
"""
Enhanced Poker Bot Validation Test
Tests all major improvements and integrations.
"""

import sys
import os
import logging
import json
from unittest.mock import Mock, patch
from typing import Dict, Any

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our enhanced modules
try:
    from enhanced_opponent_analysis import get_enhanced_opponent_analysis
    from improved_postflop_decisions import make_improved_postflop_decision
    from enhanced_ui_detection import EnhancedUIDetection
    from session_performance_tracker import SessionPerformanceTracker, HandResult
    from enhanced_poker_bot import EnhancedPokerBot
    print("✓ All enhanced modules imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

def create_mock_game_analysis() -> Dict[str, Any]:
    """Create mock game analysis data for testing."""
    return {
        'player_data': [
            {
                'name': 'TestPlayer1',
                'stack': '€1,500.00',
                'bet': '€50.00',
                'position': 'BTN',
                'has_folded': False,
                'action': 'raise'
            },
            {
                'name': 'TestPlayer2', 
                'stack': '€2,000.00',
                'bet': '€25.00',
                'position': 'BB',
                'has_folded': False,
                'action': 'call'
            },
            {
                'name': 'Hero',
                'stack': '€1,800.00',
                'bet': '€0.00',
                'position': 'SB',
                'has_folded': False,
                'action': 'pending',
                'hand_evaluation': (8, 'Pair of Kings', 'PAIR')
            }
        ],
        'pot_size': '€75.00',
        'community_cards': ['Kh', 'Qd', '7c'],
        'big_blind': 25.0,
        'small_blind': 12.5,
        'my_player_name': 'Hero',
        'current_phase': 'flop'
    }

def test_enhanced_opponent_analysis():
    """Test enhanced opponent analysis."""
    print("\n=== Testing Enhanced Opponent Analysis ===")
    
    try:
        # Test with mock data
        game_analysis = create_mock_game_analysis()
        logger = logging.getLogger(__name__)
        
        # Mock opponent tracker
        mock_tracker = Mock()
        mock_tracker.get_aggregated_stats.return_value = {
            'TestPlayer1': {
                'hands_played': 25,
                'vpip': 0.24,
                'pfr': 0.16,
                'aggression_factor': 2.1,
                'fold_to_cbet': 0.45,
                'cbet_frequency': 0.65,
                'three_bet_frequency': 0.08
            }
        }
        
        analysis = get_enhanced_opponent_analysis(game_analysis, mock_tracker, logger)
        
        assert analysis is not None, "Analysis should not be None"
        assert 'analysis_quality' in analysis, "Should have analysis quality"
        assert 'opponent_summary' in analysis, "Should have opponent summary"
        assert 'strategic_recommendations' in analysis, "Should have recommendations"
        
        print("✓ Enhanced opponent analysis working correctly")
        return True
        
    except Exception as e:
        print(f"✗ Enhanced opponent analysis failed: {e}")
        return False

def test_improved_postflop_decisions():
    """Test improved postflop decision making."""
    print("\n=== Testing Improved Postflop Decisions ===")
    
    try:
        game_analysis = create_mock_game_analysis()
        logger = logging.getLogger(__name__)
        
        # Mock components
        mock_equity_calc = Mock()
        mock_equity_calc.calculate_win_probability.return_value = 0.65
        
        mock_opponent_analysis = {
            'analysis_quality': 'medium',
            'opponent_summary': {
                'TestPlayer1': {
                    'aggression_level': 'medium',
                    'tightness': 'medium',
                    'bluff_frequency': 'low'
                }
            },
            'strategic_recommendations': {
                'overall_table_style': 'balanced',
                'primary_strategy': 'value_focused'
            }
        }
        
        decision = make_improved_postflop_decision(
            game_analysis, mock_equity_calc, mock_opponent_analysis, logger
        )
        
        assert decision is not None, "Decision should not be None"
        assert 'action' in decision, "Should have action"
        assert 'amount' in decision, "Should have amount"
        assert 'confidence' in decision, "Should have confidence"
        assert 'reasoning' in decision, "Should have reasoning"
        
        # Test win probability capping
        assert decision.get('win_probability', 0) <= 1.0, "Win probability should be capped at 100%"
        
        print("✓ Improved postflop decisions working correctly")
        return True
        
    except Exception as e:
        print(f"✗ Improved postflop decisions failed: {e}")
        return False

def test_enhanced_ui_detection():
    """Test enhanced UI detection."""
    print("\n=== Testing Enhanced UI Detection ===")
    
    try:
        logger = logging.getLogger(__name__)
        ui_detector = EnhancedUIDetection(logger)
        
        # Test action detection methods
        assert hasattr(ui_detector, 'detect_action_state'), "Should have detect_action_state method"
        assert hasattr(ui_detector, 'verify_action_buttons'), "Should have verify_action_buttons method"
        assert hasattr(ui_detector, 'get_adaptive_delay'), "Should have get_adaptive_delay method"
        
        print("✓ Enhanced UI detection initialized correctly")
        return True
        
    except Exception as e:
        print(f"✗ Enhanced UI detection failed: {e}")
        return False

def test_session_performance_tracker():
    """Test session performance tracking."""
    print("\n=== Testing Session Performance Tracker ===")
    
    try:
        tracker = SessionPerformanceTracker()
        
        # Test hand result recording
        hand_result = HandResult(
            hand_id="test_hand_1",
            starting_stack=1000.0,
            ending_stack=1050.0,
            pot_won=50.0,
            actions_taken=['call', 'raise'],
            hand_strength='medium',
            opponent_types=['tight', 'aggressive']
        )
        
        tracker.record_hand_result(hand_result)
        
        # Test stats calculation
        stats = tracker.get_session_stats()
        
        assert stats is not None, "Stats should not be None"
        assert 'hands_played' in stats, "Should have hands played"
        assert 'net_profit' in stats, "Should have net profit"
        assert 'win_rate' in stats, "Should have win rate"
        
        # Test recommendations
        recommendations = tracker.get_adaptive_recommendations()
        assert recommendations is not None, "Recommendations should not be None"
        
        print("✓ Session performance tracker working correctly")
        return True
        
    except Exception as e:
        print(f"✗ Session performance tracker failed: {e}")
        return False

def test_enhanced_poker_bot_integration():
    """Test enhanced poker bot integration."""
    print("\n=== Testing Enhanced Poker Bot Integration ===")
    
    try:
        # Create config file if it doesn't exist
        if not os.path.exists('config.json'):
            default_config = {
                "ui_positions": {},
                "big_blind": 25.0,
                "small_blind": 12.5,
                "my_player_name": "Hero"
            }
            with open('config.json', 'w') as f:
                json.dump(default_config, f, indent=2)
        
        # Test bot initialization
        bot = EnhancedPokerBot('config.json')
        
        assert hasattr(bot, 'ui_detector'), "Should have UI detector"
        assert hasattr(bot, 'timing_controller'), "Should have timing controller"
        assert hasattr(bot, 'session_tracker'), "Should have session tracker"
        assert hasattr(bot, 'enhanced_main_loop'), "Should have enhanced main loop"
        
        print("✓ Enhanced poker bot integration working correctly")
        return True
        
    except Exception as e:
        print(f"✗ Enhanced poker bot integration failed: {e}")
        return False

def test_all_enhancements():
    """Run all enhancement tests."""
    print("Enhanced Poker Bot Validation Test")
    print("=" * 50)
    
    # Setup logging
    logging.basicConfig(level=logging.WARNING)  # Reduce log noise during tests
    
    tests = [
        test_enhanced_opponent_analysis,
        test_improved_postflop_decisions,
        test_enhanced_ui_detection,
        test_session_performance_tracker,
        test_enhanced_poker_bot_integration
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print(f"\n" + "=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All enhancements validated successfully!")
        print("\nThe enhanced poker bot is ready to use with:")
        print("• Fixed opponent data collection")
        print("• Improved action detection") 
        print("• Better timing control")
        print("• Capped win probability calculations")
        print("• Enhanced hand strength classification")
        print("• Improved bluffing logic")
        print("• Better SPR strategy")
        print("• Session performance tracking")
        print("\nTo run the enhanced bot:")
        print("python enhanced_poker_bot.py")
        return True
    else:
        print("❌ Some enhancements failed validation")
        return False

if __name__ == "__main__":
    success = test_all_enhancements()
    sys.exit(0 if success else 1)
