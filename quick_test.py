#!/usr/bin/env python3
"""
Quick test to verify basic functionality.
"""

print("Starting test...")

try:
    from enhanced_postflop_improvements import classify_hand_strength_enhanced
    print("Import successful")
    
    result = classify_hand_strength_enhanced(
        numerical_hand_rank=2,  # one pair
        win_probability=0.42,
        hand_description="pair of nines"
    )
    print(f"Classification result: {result}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("Test complete")
