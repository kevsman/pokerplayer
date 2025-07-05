#!/usr/bin/env python3
"""
Debug the AK missed draw scenario to see why it works correctly.
"""
from gpu_accelerated_equity import GPUEquityCalculator

# Test the working scenario from our main test
equity_calculator = GPUEquityCalculator(use_gpu=True)

hole_cards = ['A♠', 'K♠']
board = ['2♥', '7♦', 'Q♣', '3♥', '9♦']

print("🔍 Debugging AK Missed Draw Scenario (Working)")
print(f"Hand: {hole_cards}")
print(f"Board: {board}")

# Calculate equity
win_prob, tie_prob, lose_prob = equity_calculator.calculate_equity_monte_carlo(
    [hole_cards], board, None, 
    num_simulations=10000, num_opponents=1
)

print(f"Win probability: {win_prob:.6f}")
print(f"Tie probability: {tie_prob:.6f}")
print(f"Lose probability: {lose_prob:.6f}")
print(f"Total: {win_prob + tie_prob + lose_prob:.6f}")

# Check what this hand actually is
from hand_evaluator import HandEvaluator
hand_evaluator = HandEvaluator()

try:
    hand_rank = hand_evaluator.evaluate_hand(hole_cards, board)
    print(f"Hand rank: {hand_rank}")
except Exception as e:
    print(f"Error evaluating hand: {e}")

print("\nHand analysis:")
print("- Ace high (no pair)")
print("- Missed flush draw")
print("- No straight potential")
print("- Should have very low equity")
