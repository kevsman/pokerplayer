#!/usr/bin/env python3

"""
Test script to debug the exact issue with BB folding when bet_to_call = 0.00
"""

# Simulate the decision engine calculation
def test_bet_to_call_calculation():
    """Test how bet_to_call is calculated"""
    
    print("=== Testing Bet To Call Calculation ===")
    
    # Simulate BB scenario from the log
    # BB has posted the blind, no one has raised
    
    # Player data (simplified)
    all_players = [
        None,  # Empty seat
        None,  # Empty seat  
        None,  # Empty seat
        {      # BB player (our bot)
            'name': 'warriorwonder25',
            'seat': 4,
            'position': 'BB',
            'current_bet': 0.02,  # Posted BB
            'bet_to_call': '0.00',  # From UI - should be able to check
            'stack': 1.24
        },
        None,  # Empty seat
        None   # Empty seat
    ]
    
    # Simulate the calculation from decision_engine.py
    max_bet_on_table = 0.0
    for i, p_data in enumerate(all_players):
        if p_data:
            player_current_bet = float(p_data.get('current_bet', 0.0))
            print(f"Player at seat {p_data['seat']}: current_bet = {player_current_bet}")
            if player_current_bet > max_bet_on_table:
                max_bet_on_table = player_current_bet
    
    print(f"max_bet_on_table = {max_bet_on_table}")
    
    # Our player's data
    my_player = all_players[3]
    my_current_bet = float(my_player.get('current_bet', 0.0))
    print(f"my_current_bet = {my_current_bet}")
    
    # Calculate bet_to_call
    bet_to_call_calculated = max(0.0, max_bet_on_table - my_current_bet)
    print(f"bet_to_call_calculated = {bet_to_call_calculated}")
    
    # Parse UI bet_to_call
    bet_to_call_str = my_player.get('bet_to_call')
    parsed_ui_bet_to_call = float(bet_to_call_str) if bet_to_call_str else None
    print(f"parsed_ui_bet_to_call = {parsed_ui_bet_to_call}")
    
    # Determine final bet_to_call (logic from decision_engine.py)
    final_bet_to_call = bet_to_call_calculated
    if parsed_ui_bet_to_call is not None:
        if parsed_ui_bet_to_call > 0:
            final_bet_to_call = parsed_ui_bet_to_call
            print(f"Using UI bet_to_call: {final_bet_to_call}")
        else:
            print(f"UI bet_to_call is 0, using calculated: {final_bet_to_call}")
    
    print(f"final_bet_to_call = {final_bet_to_call}")
    
    # Calculate can_check
    can_check = final_bet_to_call == 0
    print(f"can_check = {can_check}")
    
    # Check for floating point issues
    print(f"final_bet_to_call type: {type(final_bet_to_call)}")
    print(f"final_bet_to_call == 0: {final_bet_to_call == 0}")
    print(f"final_bet_to_call == 0.0: {final_bet_to_call == 0.0}")
    print(f"abs(final_bet_to_call) < 1e-10: {abs(final_bet_to_call) < 1e-10}")
    
    return final_bet_to_call, can_check

def test_weak_hand_logic():
    """Test the weak hand decision logic"""
    
    print("\n=== Testing Weak Hand Logic ===")
    
    final_bet_to_call, can_check = test_bet_to_call_calculation()
    
    position = "BB"
    is_bb = True
    hand_category = "Weak"
    
    print(f"\nInputs to preflop logic:")
    print(f"  position: {position}")
    print(f"  hand_category: {hand_category}")
    print(f"  bet_to_call: {final_bet_to_call}")
    print(f"  can_check: {can_check}")
    print(f"  is_bb: {is_bb}")
    
    print(f"\nTesting decision paths:")
    
    # Test the first condition that should catch this case
    if hand_category == "Weak":
        print("1. hand_category == 'Weak' ✓")
        
        if can_check and is_bb and final_bet_to_call == 0:
            print("2. can_check and is_bb and bet_to_call == 0 ✓")
            print("   → Should return CHECK!")
            return "check"
        else:
            print("2. can_check and is_bb and bet_to_call == 0 ✗")
            print(f"   Details: can_check={can_check}, is_bb={is_bb}, bet_to_call={final_bet_to_call}")
            print(f"   Combined condition: {can_check and is_bb and final_bet_to_call == 0}")
    
    return "unknown"

if __name__ == '__main__':
    result = test_weak_hand_logic()
    print(f"\nResult: {result}")
    
    if result == "check":
        print("✅ Logic correctly returns CHECK")
    else:
        print("❌ Logic has an issue - should return CHECK but doesn't")
