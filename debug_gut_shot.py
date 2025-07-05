#!/usr/bin/env python3
"""
Debug the specific gut shot scenario to understand why it's raising so much.
"""
from gpu_accelerated_equity import GPUEquityCalculator

# Test the specific problematic scenario
equity_calculator = GPUEquityCalculator(use_gpu=True)

hole_cards = ['J♦', 'T♣']
board = ['A♠', '9♥', '7♦', '2♠', 'K♦']

print("🔍 Debugging Gut Shot Scenario")
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

# Check if this hand actually has any outs
from hand_evaluator import HandEvaluator
hand_evaluator = HandEvaluator()

all_cards = hole_cards + board
print(f"All cards: {all_cards}")

# Evaluate the current hand
try:
    hand_rank = hand_evaluator.evaluate_hand(hole_cards, board)
    print(f"Hand rank: {hand_rank}")
except Exception as e:
    print(f"Error evaluating hand: {e}")

# Check what this hand actually is
print("\nHand analysis:")
print("- Jack high (no pair)")
print("- No flush potential")
print("- No straight potential")
print("- Essentially a bluff with 0% equity")
