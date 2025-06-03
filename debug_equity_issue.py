#!/usr/bin/env python3

import logging
import sys
import traceback

print("Starting debug script...")

try:
    from equity_calculator import EquityCalculator
    from hand_evaluator import HandEvaluator
    print("Imports successful")
except Exception as e:
    print(f"Import error: {e}")
    traceback.print_exc()
    sys.exit(1)

# Set up logging to see detailed debug information
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')

def test_equity_calculator():
    print("=" * 60)
    print("DEBUGGING EQUITY CALCULATOR ISSUE")
    print("=" * 60)
    
    equity_calc = EquityCalculator()
    hand_eval = HandEvaluator()
      # Test 1: Strong hand (pocket Queens QQ)
    print("\n--- TEST 1: Pocket Queens (QQ) ---")
    hole_cards = [['Qs', 'Qh']]  # Strong pair
    community_cards = []  # Pre-flop
    
    win_prob, tie_prob, equity = equity_calc.calculate_equity_monte_carlo(
        hole_cards, community_cards, None, 100
    )
    print(f"QQ Results: Win={win_prob*100:.2f}%, Tie={tie_prob*100:.2f}%, Equity={equity*100:.2f}%")
    
    # Test 2: Medium hand
    print("\n--- TEST 2: Ace-King (AK) ---")
    hole_cards = [['As', 'Kh']]
    community_cards = []  # Pre-flop
    
    win_prob, tie_prob, equity = equity_calc.calculate_equity_monte_carlo(
        hole_cards, community_cards, None, 100
    )
    print(f"AK Results: Win={win_prob*100:.2f}%, Tie={tie_prob*100:.2f}%, Equity={equity*100:.2f}%")
    
    # Test 3: Weak hand
    print("\n--- TEST 3: 2-7 offsuit (worst hand) ---")
    hole_cards = [['2s', '7c']]
    community_cards = []  # Pre-flop
    
    win_prob, tie_prob, equity = equity_calc.calculate_equity_monte_carlo(
        hole_cards, community_cards, None, 100
    )
    print(f"27o Results: Win={win_prob*100:.2f}%, Tie={tie_prob*100:.2f}%, Equity={equity*100:.2f}%")
    
    # Test 4: Test hand evaluator directly
    print("\n--- TEST 4: Hand Evaluator Direct Test ---")    player_cards = [hand_eval._convert_card_to_value('Qs'), hand_eval._convert_card_to_value('Qh')]
    opponent_cards = [hand_eval._convert_card_to_value('7s'), hand_eval._convert_card_to_value('2c')]
    board = []
    
    player_eval = hand_eval.evaluate_hand(player_cards, board)
    opponent_eval = hand_eval.evaluate_hand(opponent_cards, board)
    
    print(f"Player (QQ) eval: {player_eval}")
    print(f"Opponent (72) eval: {opponent_eval}")
    
    comparison = equity_calc._compare_hands(player_eval, opponent_eval)
    print(f"Comparison result (should be > 0): {comparison}")
    
    # Test 5: Test a single simulation manually
    print("\n--- TEST 5: Manual Simulation ---")
    print("Testing if the simulation logic works correctly...")
    
    # Simulate what happens in one iteration
    deck = equity_calc._generate_deck()
    known_cards = ['Q♠', 'Q♥']
    available_deck = [c for c in deck if c not in known_cards]
    
    # Deal opponent cards manually
    opponent_cards_str = hand_eval.deal_random_cards(available_deck, 2)
    print(f"Opponent dealt: {opponent_cards_str}")
    
    # Deal board cards
    board_cards_str = hand_eval.deal_random_cards(available_deck, 5)
    print(f"Board dealt: {board_cards_str}")
    
    # Convert to objects and evaluate
    player_cards_obj = [hand_eval._convert_card_to_value(c) for c in ['Q♠', 'Q♥']]
    opponent_cards_obj = [hand_eval._convert_card_to_value(c) for c in opponent_cards_str]
    board_cards_obj = [hand_eval._convert_card_to_value(c) for c in board_cards_str]
    
    player_eval_manual = hand_eval.evaluate_hand(player_cards_obj, board_cards_obj)
    opponent_eval_manual = hand_eval.evaluate_hand(opponent_cards_obj, board_cards_obj)
    
    print(f"Player hand eval: {player_eval_manual}")
    print(f"Opponent hand eval: {opponent_eval_manual}")
    
    comparison_manual = equity_calc._compare_hands(player_eval_manual, opponent_eval_manual)
    print(f"Manual comparison result: {comparison_manual}")
    
    if comparison_manual > 0:
        print("✅ Player wins this hand")
    elif comparison_manual == 0:
        print("🤝 Tie")
    else:
        print("❌ Player loses this hand")

if __name__ == "__main__":
    try:
        test_equity_calculator()
    except Exception as e:
        print(f"Error in main: {e}")
        traceback.print_exc()
