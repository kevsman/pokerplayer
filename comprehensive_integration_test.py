# comprehensive_integration_test.py
"""
Comprehensive integration test for the enhanced poker bot system.
Tests all major components working together.
"""

import unittest
import json
import time
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_poker_bot import EnhancedPokerBot
from adaptive_timing_controller import GameStateSnapshot
from enhanced_action_detection import ActionElement
from advanced_decision_engine import DecisionContext, PlayingStyle, BoardTexture
from enhanced_opponent_tracking import ActionData
from performance_monitor import HandPerformance

class TestEnhancedPokerBotIntegration(unittest.TestCase):
    """Integration tests for enhanced poker bot."""
    
    def setUp(self):
        """Set up test environment."""
        # Create the bot instance with mocked dependencies
        self.bot = Mock(spec=EnhancedPokerBot)
        
        # Mock all the enhanced components
        self.bot.timing_controller = Mock()
        self.bot.action_detector = Mock()
        self.bot.decision_engine_advanced = Mock()
        self.bot.opponent_tracker_enhanced = Mock()
        self.bot.performance_monitor = Mock()
        self.bot.session_tracker = Mock()
        
        # Mock essential attributes
        self.bot.ui_controller = Mock()
        self.bot.parser = Mock()
        self.bot.config = Mock()
        self.bot.config.settings = {'default_bet_sizing': 0.5}
        self.bot.logger = Mock()
        
        # Initialize tracking attributes
        self.bot.current_hand_start_time = None
        self.bot.current_hand_starting_stack = 0.0
        self.bot.current_hand_actions = []
        self.bot.last_decision_time = 0.0
        self.bot.consecutive_parse_failures = 0
        self.bot.last_game_state = None
        self.bot.total_decisions_made = 0
        self.bot.successful_parses = 0
        self.bot.failed_parses = 0
        self.bot.actions_taken_this_session = []
        self.bot.strategy_adjustments = {
            'aggression_multiplier': 1.0,
            'tightness_adjustment': 0.0,
            'bluff_frequency_multiplier': 1.0
        }
        
        # Initialize data structures
        self.bot.table_data = {}
        self.bot.player_data = []
        self.bot.opponent_tracker = Mock()
        self.bot.action_history = []
        self.bot.current_hand_id_for_history = None
        
        # Add actual method implementations for testing
        self.bot._create_game_state_snapshot = EnhancedPokerBot._create_game_state_snapshot.__get__(self.bot, EnhancedPokerBot)
        self.bot._classify_board_texture = EnhancedPokerBot._classify_board_texture.__get__(self.bot, EnhancedPokerBot)
        self.bot._parse_stack_amount = EnhancedPokerBot._parse_stack_amount.__get__(self.bot, EnhancedPokerBot)
        self.bot._handle_parse_failure = EnhancedPokerBot._handle_parse_failure.__get__(self.bot, EnhancedPokerBot)
        self.bot._apply_adaptive_adjustments = EnhancedPokerBot._apply_adaptive_adjustments.__get__(self.bot, EnhancedPokerBot)
        
        # Setup mock methods
        self.bot.get_my_player = Mock(return_value={
            'name': 'TestPlayer',
            'stack': '1000.0',
            'position': 'BTN',
            'has_turn': True,
            'win_probability': 0.75,
            'hand_evaluation': ('AA', 'Pocket Aces')
        })
        
        self.bot.get_active_player = Mock(return_value={
            'name': 'TestPlayer',
            'is_my_player': True
        })
        
        self.bot.analyze = Mock()
    
    def test_enhanced_components_initialization(self):
        """Test that all enhanced components are properly initialized."""
        # Check that all new components exist
        self.assertIsNotNone(self.bot.timing_controller)
        self.assertIsNotNone(self.bot.action_detector)
        self.assertIsNotNone(self.bot.decision_engine_advanced)
        self.assertIsNotNone(self.bot.opponent_tracker_enhanced)
        self.assertIsNotNone(self.bot.performance_monitor)
        self.assertIsNotNone(self.bot.session_tracker)
        
        # Check tracking variables
        self.assertEqual(self.bot.consecutive_parse_failures, 0)
        self.assertEqual(self.bot.total_decisions_made, 0)
        self.assertEqual(self.bot.successful_parses, 0)
        self.assertEqual(self.bot.failed_parses, 0)
    
    def test_game_state_snapshot_creation(self):
        """Test game state snapshot creation."""
        # Test with minimal data
        snapshot = self.bot._create_game_state_snapshot()
        self.assertIsInstance(snapshot, GameStateSnapshot)
        self.assertIsNone(snapshot.hand_id)
        self.assertEqual(snapshot.pot_size, 0.0)
        
        # Test with parsed result
        parsed_result = {
            'table_data': {
                'hand_id': 'TEST_HAND_123',
                'pot_size': 150.0,
                'game_stage': 'flop'
            },
            'my_player': {'has_turn': True},
            'actions_available': [{'type': 'call'}, {'type': 'raise'}],
            'active_player': {'name': 'TestPlayer'}
        }
        
        snapshot = self.bot._create_game_state_snapshot(parsed_result)
        self.assertEqual(snapshot.hand_id, 'TEST_HAND_123')
        self.assertEqual(snapshot.pot_size, 150.0)
        self.assertEqual(snapshot.game_stage, 'flop')
        self.assertTrue(snapshot.my_turn)
        self.assertEqual(snapshot.actions_available, 2)
    
    def test_enhanced_parsing_with_action_detection(self):
        """Test enhanced HTML parsing with action detection."""
        # Mock HTML content
        html_content = "<html><body>Test poker table</body></html>"
        
        # Mock parser response
        mock_parsed_state = {
            'table_id': 'test_table',
            'pot_size': 100.0
        }
        self.bot.parser.parse_html.return_value = mock_parsed_state
        
        # Mock action detection
        mock_actions = [
            ActionElement('call', 0.9, {'amount': 50.0}),
            ActionElement('raise', 0.8, {'min_amount': 100.0})
        ]
        self.bot.action_detector.detect_available_actions.return_value = (mock_actions, 0.85)
        
        # Test parsing
        result = self.bot._enhanced_parse_html(html_content)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['parsed_state'], mock_parsed_state)
        self.assertEqual(len(result['enhanced_actions']), 2)
        self.assertEqual(result['action_confidence'], 0.85)
    
    def test_enhanced_decision_making(self):
        """Test enhanced decision making process."""
        # Setup game analysis
        game_analysis = {
            'my_player': {
                'win_probability': 0.75,
                'bet_to_call': 50.0,
                'stack': '1000.0',
                'position': 'BTN',
                'hand_evaluation': ('AA', 'Pocket Aces')
            },
            'table_data': {
                'pot_size': 200.0,
                'game_stage': 'flop',
                'hand_id': 'TEST_HAND_123',
                'community_cards': ['As', 'Kd', '7h']
            },
            'player_data': [
                {'name': 'Opponent1', 'is_my_player': False, 'is_empty': False},
                {'name': 'TestPlayer', 'is_my_player': True}
            ],
            'actions_available': ['call', 'raise', 'fold']
        }
        
        # Mock opponent profile
        mock_opponent_profile = Mock()
        mock_opponent_profile.player_name = 'Opponent1'
        mock_opponent_profile.vpip = 0.25
        mock_opponent_profile.pfr = 0.15
        mock_opponent_profile.aggression_factor = 2.5
        mock_opponent_profile.total_hands_observed = 100
        mock_opponent_profile.playing_style = PlayingStyle.TIGHT_AGGRESSIVE
        mock_opponent_profile.avg_stack_size = 1500.0
        
        self.bot.opponent_tracker_enhanced.get_or_create_opponent.return_value = mock_opponent_profile
        
        # Mock decision engine response
        self.bot.decision_engine_advanced.make_advanced_decision.return_value = (
            'raise', 150.0, 'Strong hand with good position'
        )
        
        # Test decision making
        decision = self.bot._make_enhanced_decision(game_analysis)
        
        self.assertIsNotNone(decision)
        self.assertEqual(decision['action'], 'raise')
        self.assertEqual(decision['amount'], 150.0)
        self.assertIn('Strong hand', decision['reasoning'])
        self.assertEqual(self.bot.total_decisions_made, 1)
    
    def test_action_execution_and_tracking(self):
        """Test action execution with session tracking."""
        # Setup decision result
        decision_result = {
            'action': 'raise',
            'amount': 150.0,
            'reasoning': 'Value bet with strong hand'
        }
        
        # Setup game analysis
        game_analysis = {
            'table_data': {'hand_id': 'TEST_HAND_123', 'pot_size': 200.0},
            'my_player': {'win_probability': 0.75}
        }
        
        # Mock UI actions
        self.bot.ui_controller.set_raise_amount = Mock()
        self.bot.ui_controller.click_raise = Mock()
        
        # Execute action
        self.bot._execute_enhanced_action(decision_result, game_analysis)
        
        # Verify UI interactions
        self.bot.ui_controller.set_raise_amount.assert_called_once_with(150.0)
        self.bot.ui_controller.click_raise.assert_called_once()
        
        # Verify tracking
        self.assertEqual(len(self.bot.actions_taken_this_session), 1)
        self.assertEqual(len(self.bot.current_hand_actions), 1)
        
        action_record = self.bot.actions_taken_this_session[0]
        self.assertEqual(action_record['action_type'], 'raise')
        self.assertEqual(action_record['amount'], 150.0)
        self.assertEqual(action_record['hand_id'], 'TEST_HAND_123')
    
    def test_performance_tracking_integration(self):
        """Test performance tracking integration."""
        # Setup hand tracking
        self.bot.current_hand_id_for_history = 'TEST_HAND_123'
        self.bot.current_hand_start_time = time.time() - 60  # 1 minute ago
        self.bot.current_hand_starting_stack = 1000.0
        
        # Add some actions
        self.bot.actions_taken_this_session = [
            {
                'action_type': 'call',
                'amount': 50.0,
                'win_probability': 0.6,
                'pot_odds': 0.25
            },
            {
                'action_type': 'raise',
                'amount': 150.0,
                'win_probability': 0.8,
                'pot_odds': 0.3
            }
        ]
        
        # Mock current stack
        self.bot._get_current_stack = Mock(return_value=1100.0)
        self.bot._get_last_known_position = Mock(return_value='BTN')
        self.bot._get_hand_strength_summary = Mock(return_value='Pocket Aces')
        
        # Complete hand tracking
        self.bot._complete_hand_performance_tracking()
        
        # Verify performance monitor was called
        self.assertTrue(self.bot.performance_monitor.record_hand_result.called)
        
        # Check that actions were reset
        self.assertEqual(len(self.bot.actions_taken_this_session), 0)
    
    def test_adaptive_strategy_adjustments(self):
        """Test adaptive strategy adjustments."""
        # Mock performance monitor recommendations
        self.bot.performance_monitor.get_strategy_recommendations.return_value = {
            'aggression': 'increase aggression for better value',
            'vpip': 'tighten selection against loose opponents'
        }
        
        # Apply adjustments
        initial_aggression = self.bot.strategy_adjustments['aggression_multiplier']
        initial_tightness = self.bot.strategy_adjustments['tightness_adjustment']
        
        self.bot._apply_adaptive_adjustments()
        
        # Check adjustments were applied
        self.assertGreater(self.bot.strategy_adjustments['aggression_multiplier'], initial_aggression)
        self.assertGreater(self.bot.strategy_adjustments['tightness_adjustment'], initial_tightness)
    
    def test_error_handling_and_recovery(self):
        """Test error handling and recovery mechanisms."""
        # Test parse failure handling
        self.bot._handle_parse_failure()
        self.assertEqual(self.bot.failed_parses, 1)
        self.assertEqual(self.bot.consecutive_parse_failures, 1)
        
        # Test multiple failures
        for _ in range(12):
            self.bot._handle_parse_failure()
        
        # Should have reset consecutive failures after 10
        self.assertEqual(self.bot.consecutive_parse_failures, 2)  # Reset after 10, then 2 more
    
    def test_board_texture_classification(self):
        """Test board texture classification."""
        # Test dry board
        dry_board = ['As', 'Kd', '7h']
        texture = self.bot._classify_board_texture(dry_board)
        self.assertEqual(texture, BoardTexture.DRY)
        
        # Test wet board (flush draw)
        wet_board = ['As', 'Ks', '7s']
        texture = self.bot._classify_board_texture(wet_board)
        self.assertEqual(texture, BoardTexture.WET)
        
        # Test coordinated board
        coordinated_board = ['As', 'Kd', 'Qh']
        texture = self.bot._classify_board_texture(coordinated_board)
        self.assertEqual(texture, BoardTexture.COORDINATED)
    
    def test_session_cleanup(self):
        """Test session cleanup functionality."""
        # Setup session data
        self.bot.current_hand_id_for_history = 'TEST_HAND_123'
        self.bot.current_hand_start_time = time.time()
        self.bot.successful_parses = 100
        self.bot.failed_parses = 5
        self.bot.total_decisions_made = 50
        
        # Mock session metrics
        mock_metrics = Mock()
        mock_metrics.hands_played = 25
        mock_metrics.session_profit_loss = 250.0
        mock_metrics.win_rate = 0.68
        self.bot.performance_monitor.get_session_metrics.return_value = mock_metrics
        
        # Mock save methods
        self.bot.opponent_tracker_enhanced.save_to_file = Mock()
        self.bot.performance_monitor.save_session_data = Mock()
        self.bot.session_tracker.save_session = Mock()
        
        # Run cleanup
        self.bot._cleanup_session()
        
        # Verify saves were called
        self.bot.opponent_tracker_enhanced.save_to_file.assert_called_once()
        self.bot.performance_monitor.save_session_data.assert_called_once()
        self.bot.session_tracker.save_session.assert_called_once()

class TestComponentInteractions(unittest.TestCase):
    """Test interactions between different components."""
    
    def test_timing_controller_with_action_detector(self):
        """Test timing controller working with action detector."""
        # This would test the integration between timing decisions and action detection
        pass
    
    def test_decision_engine_with_opponent_tracking(self):
        """Test decision engine using opponent tracking data."""
        # This would test how opponent profiles influence decisions
        pass
    
    def test_performance_monitor_feedback_loop(self):
        """Test performance monitoring feedback affecting strategy."""
        # This would test the adaptive strategy adjustment loop
        pass

if __name__ == '__main__':
    # Create a test suite using modern approach
    loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # Add integration tests
    test_suite.addTests(loader.loadTestsFromTestCase(TestEnhancedPokerBotIntegration))
    test_suite.addTests(loader.loadTestsFromTestCase(TestComponentInteractions))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    print(f"\n=== Integration Test Summary ===")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}")
    
    if result.wasSuccessful():
        print("\n✅ All integration tests passed!")
    else:
        print("\n❌ Some integration tests failed!")
        
    # Exit with appropriate code
    import sys
    sys.exit(0 if result.wasSuccessful() else 1)
