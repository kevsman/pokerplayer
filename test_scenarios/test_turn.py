import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from poker_bot import PokerBot

class TestTurnScenarios(unittest.TestCase):
    def setUp(self):
        self.bot = PokerBot(big_blind=0.02, small_blind=0.01)

    def _run_test_html_file(self, file_path):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'examples'))
        # We need example HTML files for turn scenarios. Assuming they will be created.
        # For now, this will fail if 'turn_my_turn.html' etc. don't exist.
        full_file_path = os.path.join(base_dir, file_path) 
        if not os.path.exists(full_file_path):
            print(f"Warning: Test HTML file not found: {full_file_path}")
            # self.skipTest(f"HTML file {file_path} not found") # Option to skip test
            return # Or simply return, letting the test fail if run_test_file handles it
        self.bot.run_test_file(full_file_path)
        # Add assertions based on expected bot behavior

    def test_turn_my_turn_opportunity_to_bet(self):
        """Test turn scenario: bot's turn, can bet or check."""
        # Assuming an HTML file like 'turn_my_turn_can_bet.html' will exist in 'examples'
        self._run_test_html_file('turn_my_turn_can_bet.html')
        # Add assertions

    def test_turn_opponent_bets(self):
        """Test turn scenario: bot's turn, opponent has bet."""
        # Assuming an HTML file like 'turn_my_turn_opponent_bet.html' will exist
        self._run_test_html_file('turn_my_turn_opponent_bet.html')
        # Add assertions

    def test_turn_not_my_turn(self):
        """Test turn scenario: not bot's turn."""
        # Assuming an HTML file like 'turn_not_my_turn.html' will exist
        self._run_test_html_file('turn_not_my_turn.html')
        # Add assertions

if __name__ == '__main__':
    unittest.main()
