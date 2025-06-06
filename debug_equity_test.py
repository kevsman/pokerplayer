#!/usr/bin/env python3
"""
Debug version to identify where the hanging occurs
"""

def debug_equity_test():
    print("Step 1: Starting debug test")
    
    try:
        print("Step 2: Importing EquityCalculator")
        from equity_calculator import EquityCalculator
        print("Step 3: Import successful")
        
        print("Step 4: Creating calculator instance")
        calc = EquityCalculator()
        print("Step 5: Calculator created")
        
        print("Step 6: About to call calculate_win_probability")
        hole_cards = ['A♠', 'A♥']
        community_cards = []
        print(f"Step 7: Parameters - hole_cards: {hole_cards}, community_cards: {community_cards}")
        
        # Let's call the monte carlo method directly with fewer simulations
        print("Step 8: Calling calculate_equity_monte_carlo directly with 5 simulations")
        win_prob, tie_prob, equity = calc.calculate_equity_monte_carlo(
            [hole_cards], community_cards, None, 5
        )
        print(f"Step 9: Direct call successful - win: {win_prob}, tie: {tie_prob}, equity: {equity}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_equity_test()
