#!/usr/bin/env python3

"""
Test floating point comparison issues
"""

def test_floating_point_issues():
    """Test various ways that 0.00 might not equal 0"""
    
    print("=== Testing Floating Point Comparison Issues ===")
    
    # Different ways to represent zero
    test_values = [
        0,
        0.0,
        0.00,
        float('0'),
        float('0.0'),
        float('0.00'),
        float(0),
        round(0.000001, 2),
        round(-0.000001, 2),
        0.0000000001,
        -0.0000000001
    ]
    
    print("Testing values:")
    for i, val in enumerate(test_values):
        print(f"  {i}: {val} (type: {type(val)})")
        print(f"     == 0: {val == 0}")
        print(f"     == 0.0: {val == 0.0}")
        print(f"     abs(val) < 1e-10: {abs(val) < 1e-10}")
        print()
    
    # Test string parsing
    print("Testing string parsing:")
    string_values = ['0', '0.0', '0.00', ' 0.00 ', '€0.00', '$0.00']
    
    for s in string_values:
        try:
            # Simulate the parse_monetary_value function
            cleaned = s.replace('€', '').replace('$', '').strip()
            parsed = float(cleaned)
            print(f"  '{s}' → {parsed} (type: {type(parsed)})")
            print(f"    == 0: {parsed == 0}")
            print(f"    == 0.0: {parsed == 0.0}")
        except Exception as e:
            print(f"  '{s}' → ERROR: {e}")
        print()

def test_calculation_scenario():
    """Test the specific calculation scenario from the bot"""
    
    print("=== Testing Bot Calculation Scenario ===")
    
    # Scenario: BB has posted blind, no one has raised
    max_bet_on_table = 0.02  # BB amount
    my_current_bet = 0.02    # BB has already posted
    
    print(f"max_bet_on_table: {max_bet_on_table}")
    print(f"my_current_bet: {my_current_bet}")
    
    # Calculate bet_to_call
    bet_to_call_calculated = max(0.0, max_bet_on_table - my_current_bet)
    print(f"bet_to_call_calculated: {bet_to_call_calculated}")
    print(f"bet_to_call_calculated == 0: {bet_to_call_calculated == 0}")
    print(f"bet_to_call_calculated == 0.0: {bet_to_call_calculated == 0.0}")
    
    # Test if UI provides '0.00'
    ui_bet_to_call_str = '0.00'
    ui_bet_to_call = float(ui_bet_to_call_str)
    print(f"ui_bet_to_call: {ui_bet_to_call}")
    print(f"ui_bet_to_call == 0: {ui_bet_to_call == 0}")
    
    # Final bet_to_call logic (from decision_engine.py)
    final_bet_to_call = bet_to_call_calculated
    if ui_bet_to_call > 0:
        final_bet_to_call = ui_bet_to_call
    
    print(f"final_bet_to_call: {final_bet_to_call}")
    print(f"final_bet_to_call == 0: {final_bet_to_call == 0}")
    
    # can_check calculation
    can_check = final_bet_to_call == 0
    print(f"can_check: {can_check}")
    
    return can_check

if __name__ == '__main__':
    test_floating_point_issues()
    print("\n" + "="*50 + "\n")
    result = test_calculation_scenario()
    
    if result:
        print("✅ can_check should be True")
    else:
        print("❌ can_check is False - this could be the bug!")
