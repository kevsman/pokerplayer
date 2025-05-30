import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from poker_bot import PokerBot

class TestRiverScenarios(unittest.TestCase):
    def setUp(self):
        self.bot = PokerBot(big_blind=0.02, small_blind=0.01)

    def _run_test_html_file(self, file_path):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'examples'))
        # Assuming HTML files for river scenarios will be created in 'examples'
        full_file_path = os.path.join(base_dir, file_path)
        if not os.path.exists(full_file_path):
            print(f"Warning: Test HTML file not found: {full_file_path}")
            # self.skipTest(f"HTML file {file_path} not found")
            return
        self.bot.run_test_file(full_file_path)
        # Add assertions based on expected bot behavior

    def test_river_my_turn_value_bet(self):
        """Test river scenario: bot has a strong hand, should value bet."""
        # Assuming 'river_my_turn_strong_hand.html'
        self._run_test_html_file('river_my_turn_strong_hand.html')
        # Add assertions for value bet

    def test_river_my_turn_bluff_catch(self):
        """Test river scenario: opponent bets, bot has a medium strength hand, decide to call or fold."""
        # Assuming 'river_my_turn_opponent_bets_medium_hand.html'
        self._run_test_html_file('river_my_turn_opponent_bets_medium_hand.html')
        # Add assertions for call or fold based on pot odds and perceived opponent range

    def test_river_not_my_turn(self):
        """Test river scenario: not bot's turn."""
        # Assuming 'river_not_my_turn.html'
        self._run_test_html_file('river_not_my_turn.html')
        # Add assertions (likely no action expected)

if __name__ == '__main__':
    unittest.main()
