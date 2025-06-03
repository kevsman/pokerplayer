#!/usr/bin/env python3

from equity_calculator import EquityCalculator
from hand_evaluator import HandEvaluator
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')

def test_equity():
    print("=== Testing Equity Calculator ===")
    
    equity_calc = EquityCalculator()
    
    # Test 1: Strong hand vs random
    print("\n1. Testing QQ vs random:")
    win_prob, tie_prob, equity = equity_calc.calculate_equity_monte_carlo(
        [['Qs', 'Qh']], [], None, 1000
    )
    print(f"   QQ Results: Win={win_prob*100:.2f}%, Tie={tie_prob*100:.2f}%, Equity={equity*100:.2f}%")
    
    # Test 2: Premium hand vs random
    print("\n2. Testing AK vs random:")
    win_prob, tie_prob, equity = equity_calc.calculate_equity_monte_carlo(
        [['As', 'Kh']], [], None, 1000
    )
    print(f"   AK Results: Win={win_prob*100:.2f}%, Tie={tie_prob*100:.2f}%, Equity={equity*100:.2f}%")
    
    # Test 3: Weak hand vs random
    print("\n3. Testing 27o vs random:")
    win_prob, tie_prob, equity = equity_calc.calculate_equity_monte_carlo(
        [['2s', '7c']], [], None, 1000
    )
    print(f"   27o Results: Win={win_prob*100:.2f}%, Tie={tie_prob*100:.2f}%, Equity={equity*100:.2f}%")
    
    # Test 4: Head-to-head comparison
    print("\n4. Testing QQ vs AK:")
    win_prob, tie_prob, equity = equity_calc.calculate_equity_monte_carlo(
        [['Qs', 'Qh'], ['As', 'Kh']], [], None, 1000
    )
    print(f"   QQ vs AK: Win={win_prob*100:.2f}%, Tie={tie_prob*100:.2f}%, Equity={equity*100:.2f}%")

if __name__ == "__main__":
    test_equity()
