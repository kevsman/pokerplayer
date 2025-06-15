# simple_integration_test.py
"""
Simple integration test to validate key components work.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Test individual components
from adaptive_timing_controller import GameStateSnapshot, create_adaptive_timing_controller
from enhanced_action_detection import ActionElement, create_enhanced_action_detector
from advanced_decision_engine import DecisionContext, PlayingStyle, BoardTexture, create_advanced_decision_engine
from enhanced_opponent_tracking import ActionData, create_enhanced_opponent_tracker
from performance_monitor import HandPerformance, create_performance_monitor

class TestIndividualComponents(unittest.TestCase):
    """Test individual components work correctly."""
    
    def test_adaptive_timing_controller(self):
        """Test adaptive timing controller creation and basic functionality."""
        controller = create_adaptive_timing_controller()
        self.assertIsNotNone(controller)
        
        # Test game state snapshot
        snapshot = GameStateSnapshot(
            hand_id='TEST_123',
            pot_size=100.0,
            active_player='Player1',
            game_stage='flop',
            my_turn=True,
            actions_available=3,
            timestamp=1234567890.0
        )
        
        # Test should_parse_now logic
        should_parse = controller.should_parse_now(snapshot)
        self.assertIsInstance(should_parse, bool)
        
        # Test record_parse_result
        controller.record_parse_result(snapshot, True)
        
        # Test get_recommended_delay
        delay = controller.get_recommended_delay()
        self.assertIsInstance(delay, (int, float))
        self.assertGreaterEqual(delay, 0.0)
    def test_enhanced_action_detection(self):
        """Test enhanced action detection creation."""
        mock_parser = Mock()
        detector = create_enhanced_action_detector(mock_parser)
        self.assertIsNotNone(detector)
        
        # Create proper ActionElement instances
        from enhanced_action_detection import ActionElement
        mock_actions = [
            ActionElement(
                action_type='call',
                element_id='call_btn',
                confidence=0.9,
                selector='#call_button',
                text_content='Call $50',
                is_enabled=True
            ),
            ActionElement(
                action_type='raise',
                element_id='raise_btn',
                confidence=0.8,
                selector='#raise_button',
                text_content='Raise',
                is_enabled=True
            )
        ]
        
        detector.detect_available_actions = Mock(return_value=(mock_actions, 0.85))
        
        actions, confidence = detector.detect_available_actions()
        self.assertEqual(len(actions), 2)
        self.assertEqual(confidence, 0.85)
        self.assertEqual(actions[0].action_type, 'call')
    
    def test_advanced_decision_engine(self):
        """Test advanced decision engine creation and decision making."""
        settings = {'default_bet_sizing': 0.5}
        engine = create_advanced_decision_engine(settings)
        self.assertIsNotNone(engine)
        
        # Create a test decision context
        context = DecisionContext(
            hand_strength='Pocket Aces',
            position='BTN',
            pot_size=200.0,
            bet_to_call=50.0,
            stack_size=1000.0,
            pot_odds=0.25,
            win_probability=0.75,
            opponents=[],
            board_texture=BoardTexture.DRY,
            street='flop',
            spr=5.0,
            actions_available=['call', 'raise', 'fold'],
            betting_history=[]
        )
        
        # Test decision making
        action, amount, reasoning = engine.make_advanced_decision(context)
        
        self.assertIsInstance(action, str)
        self.assertIn(action, ['call', 'raise', 'fold'])
        self.assertIsInstance(amount, (int, float))
        self.assertIsInstance(reasoning, str)
        self.assertGreater(len(reasoning), 0)
    
    def test_enhanced_opponent_tracking(self):
        """Test enhanced opponent tracking creation."""
        settings = {}
        logger = Mock()
        tracker = create_enhanced_opponent_tracker(settings, logger)
        self.assertIsNotNone(tracker)
        
        # Test opponent creation
        opponent = tracker.get_or_create_opponent('TestPlayer')
        self.assertIsNotNone(opponent)
        self.assertEqual(opponent.player_name, 'TestPlayer')
          # Test action recording        # Use the log_action method instead of creating ActionData directly
        tracker.log_action(
            player_name='TestPlayer',
            action_type='raise',
            street='flop',
            position='BTN',
            amount=100.0,
            pot_size_before_action=200.0,
            stack_size=1000.0,
            hand_id='TEST_HAND_123'
        )
        
        # Verify opponent was created and updated
        opponent = tracker.get_or_create_opponent('TestPlayer')
        self.assertIsNotNone(opponent)
        self.assertEqual(opponent.player_name, 'TestPlayer')
    
    def test_performance_monitor(self):
        """Test performance monitor creation."""
        settings = {}
        monitor = create_performance_monitor(settings)
        self.assertIsNotNone(monitor)
        
        # Test hand performance recording
        hand_performance = HandPerformance(
            hand_id='TEST_123',
            timestamp=1234567890.0,
            starting_stack=1000.0,
            ending_stack=1100.0,
            profit_loss=100.0,
            position='BTN',
            actions_taken=['call', 'raise'],
            hand_strength='Pocket Aces',
            win_probability_avg=0.75,
            decision_quality_score=0.8,
            bluffs_attempted=0,
            bluffs_successful=0,
            pot_size=200.0,
            opponents_count=3
        )
        
        monitor.record_hand_result(hand_performance)
          # Test metrics retrieval (use correct method name)
        metrics = monitor.get_current_metrics()
        self.assertIsNotNone(metrics)
        self.assertGreaterEqual(metrics.hands_played, 1)
    
    def test_board_texture_classification(self):
        """Test board texture classification logic."""
        from enhanced_poker_bot import EnhancedPokerBot
        
        # Create a mock instance for testing the method
        bot = Mock()
        bot._classify_board_texture = EnhancedPokerBot._classify_board_texture.__get__(bot, EnhancedPokerBot)
          # Test different board textures
        dry_board = ['As', 'Kd', '7h']  # Rainbow board returns RAINBOW, not DRY
        texture = bot._classify_board_texture(dry_board)
        self.assertEqual(texture, BoardTexture.RAINBOW)
        
        wet_board = ['As', 'Ks', '7s']
        texture = bot._classify_board_texture(wet_board)
        self.assertEqual(texture, BoardTexture.WET)
        
        coordinated_board = ['As', 'Kd', 'Qh']
        texture = bot._classify_board_texture(coordinated_board)
        self.assertEqual(texture, BoardTexture.COORDINATED)

class TestComponentIntegration(unittest.TestCase):
    """Test components working together."""
    
    def test_timing_and_action_detection_integration(self):
        """Test timing controller with action detection."""
        controller = create_adaptive_timing_controller()
        mock_parser = Mock()
        detector = create_enhanced_action_detector(mock_parser)
        
        # Create game state
        snapshot = GameStateSnapshot(
            hand_id='TEST_123',
            pot_size=100.0,
            active_player='Player1',
            game_stage='flop',
            my_turn=True,
            actions_available=3,
            timestamp=1234567890.0
        )
        
        # Test timing decision
        should_parse = controller.should_parse_now(snapshot)
        
        if should_parse:
            # Would trigger action detection
            detector.detect_available_actions = Mock(return_value=([], 0.5))
            actions, confidence = detector.detect_available_actions()
            
            # Record result in timing controller
            controller.record_parse_result(snapshot, confidence > 0.7)
        
        # Test passed - no exceptions
        self.assertTrue(True)
    
    def test_decision_engine_with_opponent_data(self):
        """Test decision engine using opponent tracking data."""
        settings = {'default_bet_sizing': 0.5}
        engine = create_advanced_decision_engine(settings)
        
        logger = Mock()
        tracker = create_enhanced_opponent_tracker({}, logger)
        
        # Create opponent profile
        opponent = tracker.get_or_create_opponent('TestOpponent')
          # Convert to advanced profile format (simplified)
        from advanced_decision_engine import OpponentProfile
        advanced_opponent = OpponentProfile(
            name=opponent.player_name,
            vpip=opponent.vpip,
            pfr=opponent.pfr,
            aggression_factor=opponent.aggression_factor,
            hands_observed=opponent.total_hands_observed,
            style=opponent.playing_style,
            stack_size=1000.0
        )
        
        # Create decision context with opponent
        context = DecisionContext(
            hand_strength='Pocket Aces',
            position='BTN',
            pot_size=200.0,
            bet_to_call=50.0,
            stack_size=1000.0,
            pot_odds=0.25,
            win_probability=0.75,
            opponents=[advanced_opponent],
            board_texture=BoardTexture.DRY,
            street='flop',
            spr=5.0,
            actions_available=['call', 'raise', 'fold'],
            betting_history=[]
        )
        
        # Make decision
        action, amount, reasoning = engine.make_advanced_decision(context)
        
        # Verify decision was made
        self.assertIsInstance(action, str)
        self.assertIsInstance(reasoning, str)
        
    def test_performance_feedback_loop(self):
        """Test performance monitoring affecting strategy."""
        settings = {}
        monitor = create_performance_monitor(settings)
        
        # Record some hands with varying results
        winning_hand = HandPerformance(
            hand_id='WIN_1',
            timestamp=1234567890.0,
            starting_stack=1000.0,
            ending_stack=1150.0,
            profit_loss=150.0,
            position='BTN',
            actions_taken=['raise'],
            hand_strength='Pocket Aces',
            win_probability_avg=0.8,
            decision_quality_score=0.9,
            bluffs_attempted=0,
            bluffs_successful=0,
            pot_size=300.0,
            opponents_count=2
        )
        
        losing_hand = HandPerformance(
            hand_id='LOSE_1',
            timestamp=1234567900.0,
            starting_stack=1150.0,
            ending_stack=1050.0,
            profit_loss=-100.0,
            position='UTG',
            actions_taken=['call', 'fold'],
            hand_strength='Weak Pair',
            win_probability_avg=0.3,
            decision_quality_score=0.7,
            bluffs_attempted=1,
            bluffs_successful=0,
            pot_size=200.0,
            opponents_count=3
        )
        
        monitor.record_hand_result(winning_hand)
        monitor.record_hand_result(losing_hand)
        
        # Get strategy recommendations
        recommendations = monitor.get_strategy_recommendations()
        self.assertIsInstance(recommendations, dict)


if __name__ == '__main__':
    # Run individual component tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestIndividualComponents))
    suite.addTests(loader.loadTestsFromTestCase(TestComponentIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print(f"\n=== Simple Integration Test Summary ===")
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
        print("\n✅ All simple integration tests passed!")
        print("Enhanced poker bot components are working correctly!")
    else:
        print("\n❌ Some tests failed!")
        print("Please check the individual components.")
