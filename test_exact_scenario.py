#!/usr/bin/env python3

"""
Test the exact scenario from the bot logs to reproduce the bug
"""

def parse_monetary_value(value_str_or_float):
    """Simulate the parse_monetary_value function"""
    if isinstance(value_str_or_float, (int, float)):
        return float(value_str_or_float)
    if value_str_or_float is None or str(value_str_or_float).strip() == "" or str(value_str_or_float).strip().upper() == "N/A":
        return 0.0
    try:
        return float(str(value_str_or_float).replace('$', '').replace(',', '').replace('€', ''))
    except ValueError:
        return 0.0

def test_exact_scenario():
    """Test the exact scenario from the logs"""
    
    print("=== Testing Exact Scenario from Logs ===")
    print("Log entry: 'My turn. Hand: ['7♠', '3♥'], Rank: 73 offsuit, Stack: €0.78, Bet to call: 0.00'")
    print("Log entry: 'Pot: €0.07, Community Cards: []'")
    print("Result: 'Decision: fold Amount: 0.00' ❌")
    print()
    
    # Simulate the game state that would produce this log
    # The challenge is we need to reverse-engineer what the game state looked like
    
    # Hypothesis 1: BB posted €0.02, no one raised, should be able to check
    print("=== HYPOTHESIS 1: Normal BB scenario ===")
    
    # BB scenario
    all_players_h1 = [
        None, None, None,
        {   # BB (our bot)
            'name': 'warriorwonder25',
            'position': 'BB',
            'current_bet': 0.02,  # Posted BB
            'bet_to_call': '0.00',  # UI shows 0.00
            'stack': 0.78,
        },
        None, None
    ]
    
    # Simulate decision engine calculation
    max_bet_on_table = 0.0
    for p in all_players_h1:
        if p:
            current_bet = parse_monetary_value(p.get('current_bet', 0.0))
            print(f"Player {p['name']}: current_bet = {current_bet}")
            if current_bet > max_bet_on_table:
                max_bet_on_table = current_bet
    
    my_player = all_players_h1[3]
    my_current_bet = parse_monetary_value(my_player.get('current_bet', 0.0))
    bet_to_call_calculated = max(0.0, max_bet_on_table - my_current_bet)
    
    bet_to_call_str = my_player.get('bet_to_call')
    parsed_ui_bet_to_call = parse_monetary_value(bet_to_call_str)
    
    final_bet_to_call = bet_to_call_calculated
    if parsed_ui_bet_to_call > 0:
        final_bet_to_call = parsed_ui_bet_to_call
    
    can_check = final_bet_to_call == 0
    
    print(f"max_bet_on_table: {max_bet_on_table}")
    print(f"my_current_bet: {my_current_bet}")
    print(f"bet_to_call_calculated: {bet_to_call_calculated}")
    print(f"parsed_ui_bet_to_call: {parsed_ui_bet_to_call}")
    print(f"final_bet_to_call: {final_bet_to_call}")
    print(f"can_check: {can_check}")
    
    if can_check:
        print("✅ H1: can_check is True - this should work")
    else:
        print("❌ H1: can_check is False - this could be the bug")
    
    print()
    
    # Hypothesis 2: There's someone else who raised but the UI still shows 0.00
    print("=== HYPOTHESIS 2: Someone raised but UI shows 0.00 ===")
    
    all_players_h2 = [
        None, 
        {   # Another player who raised
            'name': 'Player1',
            'position': 'UTG',
            'current_bet': 0.05,  # Raised to 5 cents
        },
        None,
        {   # BB (our bot)
            'name': 'warriorwonder25',
            'position': 'BB',
            'current_bet': 0.02,  # Posted BB
            'bet_to_call': '0.00',  # UI incorrectly shows 0.00?
            'stack': 0.78,
        },
        None, None
    ]
    
    # Recalculate
    max_bet_on_table = 0.0
    for p in all_players_h2:
        if p:
            current_bet = parse_monetary_value(p.get('current_bet', 0.0))
            print(f"Player {p['name']}: current_bet = {current_bet}")
            if current_bet > max_bet_on_table:
                max_bet_on_table = current_bet
    
    my_player = all_players_h2[3]
    my_current_bet = parse_monetary_value(my_player.get('current_bet', 0.0))
    bet_to_call_calculated = max(0.0, max_bet_on_table - my_current_bet)
    
    bet_to_call_str = my_player.get('bet_to_call')
    parsed_ui_bet_to_call = parse_monetary_value(bet_to_call_str)
    
    final_bet_to_call = bet_to_call_calculated
    if parsed_ui_bet_to_call > 0:
        final_bet_to_call = parsed_ui_bet_to_call
    
    can_check = final_bet_to_call == 0
    
    print(f"max_bet_on_table: {max_bet_on_table}")
    print(f"my_current_bet: {my_current_bet}")
    print(f"bet_to_call_calculated: {bet_to_call_calculated}")
    print(f"parsed_ui_bet_to_call: {parsed_ui_bet_to_call}")
    print(f"final_bet_to_call: {final_bet_to_call}")
    print(f"can_check: {can_check}")
    
    if can_check:
        print("❌ H2: can_check is True - but we expect it to be False in this scenario")
    else:
        print("✅ H2: can_check is False - this would explain the bug!")
    
    return can_check

if __name__ == '__main__':
    result = test_exact_scenario()
    print(f"\nFinal analysis:")
    print("The bug is likely caused by one of these scenarios:")
    print("1. UI shows 'Bet to call: 0.00' but someone actually raised")
    print("2. Floating point precision issues")
    print("3. Incorrect game state parsing")
    print("4. The actual decision logic has a bug in an earlier return path")
