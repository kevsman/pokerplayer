import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from poker_bot import PokerBot

class TestFlopScenarios(unittest.TestCase):
    def setUp(self):
        self.bot = PokerBot(big_blind=0.02, small_blind=0.01)

    def _run_test_html_file(self, file_path):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'examples'))
        full_file_path = os.path.join(base_dir, file_path)
        self.bot.run_test_file(full_file_path)
        # Add assertions based on expected bot behavior

    def test_flop_my_turn_check_possible(self):
        """Test flop scenario: bot's turn, checking is possible."""
        self._run_test_html_file('flop_my_turn_check.html')
        # Example assertion (actual assertion depends on bot logic and log output):
        # self.assertIn("Decision: CHECK", log_output_or_bot_state)

    def test_flop_my_turn_raised_to_bot(self):
        """Test flop scenario: bot's turn, opponent raised."""
        self._run_test_html_file('flop_my_turn_raised.html')

    def test_flop_not_my_turn(self):
        """Test flop scenario: not bot's turn."""
        self._run_test_html_file('flop_not_my_turn.html')

if __name__ == '__main__':
    unittest.main()
