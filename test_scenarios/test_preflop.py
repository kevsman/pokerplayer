import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from poker_bot import PokerBot

class TestPreFlopScenarios(unittest.TestCase):
    def setUp(self):
        """Set up for test methods."""
        self.bot = PokerBot(big_blind=0.02, small_blind=0.01)
        # Suppress logging output during tests
        # logging.disable(logging.CRITICAL)

    def tearDown(self):
        """Tear down after test methods."""
        # Re-enable logging
        # logging.disable(logging.NOTSET)
        pass

    def _run_test_html_file(self, file_path):
        """Helper function to run a test with a specific HTML file."""
        # Construct the full path to the HTML file
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'examples'))
        full_file_path = os.path.join(base_dir, file_path)
        
        print(f"Testing with HTML file: {full_file_path}") # Debug print
        
        # Mock or simulate UIController actions if necessary, or ensure they don't execute
        # For now, we rely on run_test_file which doesn't perform actual UI actions.
        self.bot.run_test_file(full_file_path)
        
        # Assertions will depend on the expected outcome for each HTML file.
        # For example, you might check:
        # - The decision made by the bot (e.g., fold, call, raise)
        # - The correctness of hand evaluation
        # - The accuracy of player and table data parsing

        # Example (needs to be adapted based on actual bot logging or return values):
        # self.assertIn("Decision: FOLD", captured_log_output) 
        # Or, if run_test_file returns the action:
        # action, amount = self.bot.run_test_file(full_file_path) 
        # self.assertEqual(action, ACTION_FOLD)

    def test_preflop_my_turn_unraised(self):
        """Test preflop scenario where it is the bot's turn and no one has raised yet."""
        # This test will call run_test_file, which logs output.
        # We need a way to capture or inspect this log output, or modify run_test_file
        # to return the decision for easier assertion.
        # For now, this test will execute and we can manually inspect logs.
        # A more robust approach would involve mocking logger or capturing stdout.
        self._run_test_html_file('preflop_my_turn.html')
        # Add assertions here based on expected behavior for 'preflop_my_turn.html'
        # e.g. self.assertEqual(self.bot.decision_engine.last_action, ACTION_CALL) # Fictional attribute

    def test_preflop_my_turn_raised(self):
        """Test preflop scenario where it is the bot's turn and there has been a raise."""
        self._run_test_html_file('preflop_my_turn_raised.html')
        # Add assertions here

    def test_preflop_not_my_turn(self):
        """Test preflop scenario where it is not the bot's turn."""
        self._run_test_html_file('preflop_not_my_turn.html')
        # Add assertions here

if __name__ == '__main__':
    unittest.main()
