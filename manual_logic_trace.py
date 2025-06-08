#!/usr/bin/env python3

"""
Simple test to check the BB folding logic - manual trace
"""

def test_bb_check_logic():
    """Manually trace through the logic to understand the issue"""
    
    print("=== Manual Logic Trace for BB Check Issue ===")
    
    # Values from the problematic log entry
    position = "BB"
    bet_to_call = 0.00  # From log: "Bet to call: 0.00"
    can_check = (bet_to_call == 0)  # Should be True
    is_bb = (position == "BB")  # Should be True
    hand_category = "Weak"  # 73o is definitely weak
    
    print(f"Input values:")
    print(f"  position: {position}")
    print(f"  bet_to_call: {bet_to_call}")
    print(f"  can_check: {can_check}")
    print(f"  is_bb: {is_bb}")
    print(f"  hand_category: {hand_category}")
    print()
    
    # Trace through the preflop decision logic
    print("Tracing through preflop_decision_logic.py:")
    print()
    
    if hand_category == "Weak":
        print("1. hand_category == 'Weak' ✓")
        
        # First check: Special BB check case
        if can_check and is_bb and bet_to_call == 0:
            print("2. can_check and is_bb and bet_to_call == 0 ✓")
            print("   → Should return CHECK here!")
            return "check"
        else:
            print("2. can_check and is_bb and bet_to_call == 0 ✗")
            print(f"   → can_check={can_check}, is_bb={is_bb}, bet_to_call={bet_to_call}")
        
        # Continue with other logic...
        print("3. Checking for BTN stealing... (not BB, so skip)")
        print("4. Checking for CO play... (not CO, so skip)")
        
        # Check for facing a bet
        if bet_to_call > 0:
            print("5. bet_to_call > 0 ✗ (bet_to_call = 0.00)")
        else:
            print("5. bet_to_call > 0 ✗, checking if bet_to_call == 0...")
            
            if bet_to_call == 0:
                print("6. bet_to_call == 0 ✓")
                
                # BTN steal logic (not applicable for BB)
                print("7. BTN steal logic... (not BTN, so skip)")
                
                # The critical check
                if not can_check:
                    print("8. not can_check ✗ (can_check is True)")
                    print("   → This should NOT execute - the bug might be here")
                    return "fold"  # This is where the bug would occur
                else:
                    print("8. not can_check ✗ (can_check is True, so this doesn't execute)")
        
        # Final check/fold logic
        print("9. Reaching final check/fold logic...")
        if bet_to_call == 0 and can_check:
            print("10. bet_to_call == 0 and can_check ✓")
            print("    → Should return CHECK!")
            return "check"
        else:
            print("10. bet_to_call == 0 and can_check ✗")
            print(f"    → bet_to_call={bet_to_call}, can_check={can_check}")
            if can_check:
                return "check"
            else:
                return "fold"
    
    return "unknown"

if __name__ == '__main__':
    result = test_bb_check_logic()
    print(f"\nFinal result: {result}")
    
    if result == "check":
        print("✅ Logic should result in CHECK")
    elif result == "fold":
        print("❌ Logic incorrectly results in FOLD")
    else:
        print("? Unexpected result")
