#!/usr/bin/env python3
"""
Simple equity test for KK.
"""
from gpu_accelerated_equity import GPUEquityCalculator

# Test KK equity
calc = GPUEquityCalculator(use_gpu=True)

hole_cards = ['K♠', 'K♥']
board = ['8♠', '5♥', '4♥']

print("Testing KK equity...")

# Test against different numbers of opponents
for opponents in [1, 2, 5]:
    try:
        win, tie, lose = calc.calculate_equity_monte_carlo(
            [hole_cards], board, None, 
            num_simulations=1000, num_opponents=opponents
        )
        total = win + tie + lose
        print(f"vs {opponents} opponents: win={win:.3f}, tie={tie:.3f}, lose={lose:.3f}, total={total:.3f}")
    except Exception as e:
        print(f"Error with {opponents} opponents: {e}")

print("Done.")
