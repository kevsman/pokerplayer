#!/usr/bin/env python3
"""
Simple test to debug the issue
"""

try:
    print("Starting test...")
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    print("Imports successful...")
    
    from decision_engine import DecisionEngine
    from hand_evaluator import HandEvaluator
    
    print("DecisionEngine imported...")
    
    hand_evaluator = HandEvaluator()
    decision_engine = DecisionEngine(big_blind=0.02, small_blind=0.01)
    
    print("Objects created successfully!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    
print("Test complete!")
