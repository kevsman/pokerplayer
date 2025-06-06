#!/usr/bin/env python3
"""
Minimal test to isolate the equity calculator hanging issue
"""

import sys
import time
from equity_calculator import EquityCalculator

def test_minimal_equity():
    print("Starting minimal equity test...")
    start_time = time.time()
    
    calc = EquityCalculator()
    
    # Test 1: Very simple case with just 10 simulations
    print("Test 1: Pocket Aces vs random (10 sims)")
    try:
        hole_cards = ['A♠', 'A♥']
        community_cards = []
        
        print(f"Calling calculate_win_probability with {hole_cards}, {community_cards}")
        win_prob = calc.calculate_win_probability(hole_cards, community_cards, 1)
        print(f"Result: {win_prob:.3f}")
        
    except Exception as e:
        print(f"Error in test 1: {e}")
        import traceback
        traceback.print_exc()
    
    elapsed = time.time() - start_time
    print(f"Test completed in {elapsed:.2f} seconds")

if __name__ == "__main__":
    # Add a timeout mechanism
    import signal
    
    def timeout_handler(signum, frame):
        print("Test timed out after 30 seconds!")
        sys.exit(1)
    
    # Set 30 second timeout (Windows may not support this)
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)
    except AttributeError:
        print("Timeout not supported on this platform")
    
    test_minimal_equity()
