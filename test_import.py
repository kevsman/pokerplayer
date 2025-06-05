#!/usr/bin/env python3

import sys
import os

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing imports...")

try:
    from preflop_decision_logic import adjust_for_implied_odds
    print("✓ Successfully imported adjust_for_implied_odds")
    
    # Test the function
    result = adjust_for_implied_odds("Suited Connector", "CO", 2.0, 2.0, 0.02)
    print(f"✓ Function call successful: {result}")
    
except Exception as e:
    print(f"✗ Import error: {e}")
    import traceback
    traceback.print_exc()

print("Done.")
