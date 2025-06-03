#!/usr/bin/env python3
"""
Debug script to test equity calculator with a simple scenario
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from equity_calculator import EquityCalculator
import logging

# Set up logging to see debug output
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')

def test_equity_calculation():
    print("Testing equity calculator with simple pocket aces vs random...")
    
    equity_calc = EquityCalculator()
    
    # Test with pocket aces - should have very high win rate
    hero_cards = ["A♠", "A♥"]  # Pocket aces
    community_cards = []  # Pre-flop
    opponent_range = []  # Random opponent
    num_simulations = 100  # Small number for debugging
    
    print(f"Hero cards: {hero_cards}")
    print(f"Community cards: {community_cards}")
    print(f"Running {num_simulations} simulations...")
    
    win_prob, tie_prob, equity = equity_calc.calculate_equity_monte_carlo(
        [hero_cards],  # hole_cards_str_list expects list of hands
        community_cards,
        opponent_range,
        num_simulations
    )
    
    print(f"\nResults:")
    print(f"Win probability: {win_prob:.4f} ({win_prob*100:.2f}%)")
    print(f"Tie probability: {tie_prob:.4f} ({tie_prob*100:.2f}%)")
    print(f"Equity: {equity:.4f} ({equity*100:.2f}%)")
    
    # Test a simple post-flop scenario
    print("\n" + "="*50)
    print("Testing post-flop scenario...")
    
    hero_cards2 = ["A♠", "K♠"]  # Ace-King suited
    community_cards2 = ["A♥", "K♦", "2♣"]  # Two pair on the flop
    
    print(f"Hero cards: {hero_cards2}")
    print(f"Community cards: {community_cards2}")
    
    win_prob2, tie_prob2, equity2 = equity_calc.calculate_equity_monte_carlo(
        [hero_cards2],
        community_cards2,
        [],
        num_simulations
    )
    
    print(f"\nResults:")
    print(f"Win probability: {win_prob2:.4f} ({win_prob2*100:.2f}%)")
    print(f"Tie probability: {tie_prob2:.4f} ({tie_prob2*100:.2f}%)")
    print(f"Equity: {equity2:.4f} ({equity2*100:.2f}%)")

if __name__ == "__main__":
    test_equity_calculation()
