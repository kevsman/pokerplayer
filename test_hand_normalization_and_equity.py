import unittest
import logging
import sys
import os

# Add the project root directory (c:\GitRepositories\pokerplayer) to sys.path
# This allows imports like `from hand_utils import ...` if the test is run from the root
# or `from pokerplayer.hand_utils import ...` if c:\GitRepositories is in sys.path
# and pokerplayer is treated as a package.

# For the current structure where .py files are directly in c:\GitRepositories\pokerplayer
# and tests are run, we need c:\GitRepositories\pokerplayer to be the CWD or in sys.path
# for direct imports like `import hand_utils` or `from hand_utils import ...`

# If we want `from pokerplayer.config import ...` to work, then the directory
# *containing* 'pokerplayer' (i.e., c:\GitRepositories) must be in sys.path.

# Let's ensure c:\GitRepositories is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__)) # c:\GitRepositories\pokerplayer
parent_dir = os.path.dirname(current_dir) # c:\GitRepositories
sys.path.insert(0, parent_dir) # Add c:\GitRepositories to sys.path

# Now imports like `from pokerplayer.config import ...` should work.
from pokerplayer.hand_utils import normalize_card_char_suit, normalize_card_list, get_preflop_hand_category
from pokerplayer.equity_calculator import EquityCalculator
from pokerplayer.hand_evaluator import HandEvaluator
from pokerplayer.decision_engine import DecisionEngine
# The error suggested 'config' (lowercase) exists in pokerplayer.config module
from pokerplayer.config import config as config_module_instance # aliasing to avoid confusion

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestHandNormalizationAndEquity(unittest.TestCase):

    def setUp(self):
        self.hand_evaluator = HandEvaluator()
        # Assuming config_module_instance is the loaded config dictionary or object
        self.equity_calculator = EquityCalculator(self.hand_evaluator, config_module_instance)

    def test_normalize_card_char_suit(self):
        logger.info("Testing normalize_card_char_suit...")
        self.assertEqual(normalize_card_char_suit('A♥'), 'Ah')
        self.assertEqual(normalize_card_char_suit('K♦'), 'Kd')
        self.assertEqual(normalize_card_char_suit('Q♣'), 'Qc')
        self.assertEqual(normalize_card_char_suit('J♠'), 'Js')
        self.assertEqual(normalize_card_char_suit('10s'), '10s') # Already normalized
        self.assertEqual(normalize_card_char_suit('2c'), '2c')
        self.assertEqual(normalize_card_char_suit('Th'), 'Th') # Alternative Ten
        logger.info("normalize_card_char_suit tests passed.")

    def test_normalize_card_list(self):
        logger.info("Testing normalize_card_list...")
        self.assertEqual(normalize_card_list(['A♥', 'K♦']), ['Ah', 'Kd'])
        self.assertEqual(normalize_card_list(['Qc', 'J♠']), ['Qc', 'Js']) # Mix of normalized and non
        self.assertEqual(normalize_card_list(['10s', '9h']), ['10s', '9h']) # Already normalized
        self.assertEqual(normalize_card_list([]), [])
        logger.info("normalize_card_list tests passed.")

    def test_get_preflop_hand_category_aq_suited(self):
        logger.info("Testing get_preflop_hand_category with AQ suited...")
        # hand_evaluation_tuple format: (strength, hand_name_str, (rank1_val, rank2_val), kicker_ranks_tuple)
        # For AQ suited, ranks are Ace (14) and Queen (12)
        # The hand_evaluation_tuple for preflop doesn't use the full strength/name yet,
        # it primarily uses the ranks from tuple[2]
        
        # Test with Unicode suits, assuming normalization happens before this function
        # However, get_preflop_hand_category itself expects normalized cards for its is_suited check
        hole_cards_aq_suited_unicode = ['A♥', 'Q♥']
        normalized_aq_suited = normalize_card_list(hole_cards_aq_suited_unicode) # ['Ah', 'Qh']
        
        # hand_evaluation_tuple for preflop: (category_rank, "High Card", (rank_card1, rank_card2), (kicker1, kicker2, ...))
        # For preflop, the hand_evaluator.evaluate_hand(hole_cards, []) would give something like:
        # (0, "High Card", (14, 12), (14, 12)) if A=14, Q=12.
        # The critical part for get_preflop_hand_category is hand_evaluation_tuple[2]
        hand_eval_tuple_aq = (0, "High Card", (14, 12), (14,12)) # Ranks for A, Q

        category = get_preflop_hand_category(hand_eval_tuple_aq, normalized_aq_suited)
        logger.debug(f"AQ suited ({normalized_aq_suited}) categorized as: {category}")
        self.assertIn(category, ["Strong Pair", "Suited Ace"], 
                      f"AQ suited was miscategorized as {category}. Expected 'Strong Pair' or 'Suited Ace'.")

        # Test with already normalized input
        hole_cards_aq_suited_normalized = ['As', 'Qs']
        category_normalized = get_preflop_hand_category(hand_eval_tuple_aq, hole_cards_aq_suited_normalized)
        logger.debug(f"AQ suited ({hole_cards_aq_suited_normalized}) categorized as: {category_normalized}")
        self.assertIn(category_normalized, ["Strong Pair", "Suited Ace"],
                      f"AQ suited (normalized) was miscategorized as {category_normalized}. Expected 'Strong Pair' or 'Suited Ace'.")
        logger.info("get_preflop_hand_category AQ suited tests passed.")

    def test_calculate_equity_aq_suited(self):
        logger.info("Testing calculate_equity_monte_carlo with AQ suited...")
        # Ensure hole_cards are normalized before passing to equity calculator
        hole_cards_player1_aq_suited = normalize_card_list(['A♥', 'Q♥']) # ['Ah', 'Qh']
        community_cards_empty = []
        opponent_range_random = ["random"] # Assuming "random" is a supported range string
        num_simulations = 1000 # Reduced for faster test, increase for accuracy if needed

        win_prob, tie_prob, equity = self.equity_calculator.calculate_equity_monte_carlo(
            [hole_cards_player1_aq_suited], 
            community_cards_empty, 
            opponent_range_random, 
            num_simulations
        )

        logger.info(f"AQ suited equity preflop vs random: WinP={win_prob:.3f}, TieP={tie_prob:.3f}, Equity={equity:.3f} (Sims: {num_simulations})")
        
        self.assertGreater(win_prob, 0.0, "Win probability for AQ suited preflop should be greater than 0.")
        self.assertLess(win_prob, 1.0, "Win probability for AQ suited preflop should be less than 1.")
        # AQ suited vs random is roughly 65-66% win. Let's check for a plausible range.
        self.assertGreater(win_prob, 0.5, "AQ suited preflop vs random should have a win probability > 50%.") 
        self.assertLess(win_prob, 0.8, "AQ suited preflop vs random should have a win probability < 80%.")

        logger.info("calculate_equity_monte_carlo AQ suited test passed.")

if __name__ == '__main__':
    unittest.main()
