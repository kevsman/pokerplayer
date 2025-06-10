#!/usr/bin/env python3
"""
Debug script to understand the import issue with classify_hand_strength_enhanced
"""

import sys
import traceback

print("Python version:", sys.version)
print("Current working directory:", sys.path[0])
print("\n" + "="*50)
print("TESTING IMPORTS")
print("="*50)

# Test 1: Try to import enhanced_hand_classification
try:
    print("\n1. Importing enhanced_hand_classification...")
    import enhanced_hand_classification
    print("   ✓ Successfully imported enhanced_hand_classification")
    
    # Check if the function exists
    if hasattr(enhanced_hand_classification, 'classify_hand_strength_enhanced'):
        print("   ✓ classify_hand_strength_enhanced function found")
        func = getattr(enhanced_hand_classification, 'classify_hand_strength_enhanced')
        print(f"   Function signature: {func.__name__}")
        print(f"   Function doc: {func.__doc__}")
    else:
        print("   ✗ classify_hand_strength_enhanced function NOT found")
        print("   Available functions:", [attr for attr in dir(enhanced_hand_classification) if not attr.startswith('_')])
        
except Exception as e:
    print(f"   ✗ Failed to import enhanced_hand_classification: {e}")
    traceback.print_exc()

# Test 2: Try the specific import that's failing
try:
    print("\n2. Testing specific import...")
    from enhanced_hand_classification import classify_hand_strength_enhanced
    print("   ✓ Successfully imported classify_hand_strength_enhanced")
    print(f"   Function type: {type(classify_hand_strength_enhanced)}")
except Exception as e:
    print(f"   ✗ Failed to import classify_hand_strength_enhanced: {e}")
    traceback.print_exc()

# Test 3: Check the postflop_decision_logic import section
try:
    print("\n3. Testing postflop_decision_logic imports...")
    
    # Simulate the import logic from postflop_decision_logic.py
    ENHANCED_MODULES_AVAILABLE = False
    
    try:
        from enhanced_hand_classification import classify_hand_strength_enhanced
        from enhanced_postflop_improvements import classify_hand_strength_enhanced as classify_improved
        ENHANCED_MODULES_AVAILABLE = True
        print("   ✓ Both enhanced modules imported successfully")
        print(f"   ENHANCED_MODULES_AVAILABLE = {ENHANCED_MODULES_AVAILABLE}")
    except ImportError as e:
        print(f"   ✗ Import failed: {e}")
        print(f"   ENHANCED_MODULES_AVAILABLE = {ENHANCED_MODULES_AVAILABLE}")
        
except Exception as e:
    print(f"   ✗ Error in test 3: {e}")
    traceback.print_exc()

# Test 4: Check for name conflicts
try:
    print("\n4. Checking for function name conflicts...")
    from enhanced_hand_classification import classify_hand_strength_enhanced as func1
    from enhanced_postflop_improvements import classify_hand_strength_enhanced as func2
    
    print(f"   enhanced_hand_classification function: {func1}")
    print(f"   enhanced_postflop_improvements function: {func2}")
    print(f"   Are they the same? {func1 is func2}")
    
except Exception as e:
    print(f"   ✗ Error checking conflicts: {e}")
    traceback.print_exc()

print("\n" + "="*50)
print("DIAGNOSIS COMPLETE")
print("="*50)
