#!/usr/bin/env python3

"""
Test script to verify the aggressive changes for A9 suited calling behavior
"""

from decision_engine import DecisionEngine
from hand_evaluator import HandEvaluator

def test_a9_suited_calling():
    """Test that A9 suited calls in favorable pot odds situations"""
    
    # Create a test scenario similar to what we saw in the original issue
    # Pot odds: 21.1% (better than our new 25% threshold)
    # Win probability: ~20.8%
    
    print("Testing A9 suited calling behavior...")
    
    decision_engine = DecisionEngine()
    hand_evaluator = HandEvaluator()
    
    # Test hole cards: A9 suited (clubs)
    hole_cards = [('A', 'C'), ('9', 'C')]
    
    # Mock game state for favorable calling situation
    game_state = {
        'pot_size': 100,
        'bet_to_call': 25,  # This gives pot odds of 25/(100+25) = 20%, which is better than 25%
        'my_stack': 500,
        'active_opponents_count': 2,
        'position': 'Late',  # Good position
        'my_bet_this_round': 0,
        'can_check': False,
        'limpers': 0,
        'big_blind': 10
    }
    
    # Calculate some values
    pot_odds = game_state['bet_to_call'] / (game_state['pot_size'] + game_state['bet_to_call'])
    print(f"Pot odds: {pot_odds:.3f} ({pot_odds*100:.1f}%)")
    
    # Mock community cards (empty for preflop)
    community_cards = []
    
    # Call the preflop decision method
    try:
        action, amount = decision_engine.decide_preflop(
            hole_cards, 
            game_state['pot_size'],
            game_state['bet_to_call'],
            game_state['my_stack'],
            game_state['active_opponents_count'],
            game_state['position'],
            game_state['my_bet_this_round'],
            game_state['can_check'],
            game_state['limpers'],
            game_state['big_blind']
        )
        
        print(f"Decision: {action}, Amount: {amount}")
        
        if action == "call":
            print("✅ SUCCESS: Bot correctly calls A9 suited in favorable situation!")
            return True
        else:
            print(f"❌ ISSUE: Bot chose {action} instead of calling")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: Exception occurred: {e}")
        return False

def test_aggression_factor():
    """Test that the aggression factor was increased"""
    
    print("\nTesting aggression factor...")
    
    decision_engine = DecisionEngine()
    
    print(f"Base aggression factor: {decision_engine.base_aggression_factor}")
    
    if decision_engine.base_aggression_factor >= 1.3:
        print("✅ SUCCESS: Aggression factor increased to 1.3 or higher")
        return True
    else:
        print(f"❌ ISSUE: Aggression factor is {decision_engine.base_aggression_factor}, expected 1.3+")
        return False

def test_suited_ace_category():
    """Test that A9 suited is correctly categorized"""
    
    print("\nTesting A9 suited categorization...")
    
    decision_engine = DecisionEngine()
    
    # Test A9 suited
    hole_cards = [('A', 'C'), ('9', 'C')]
    category = decision_engine.categorize_preflop_hand(hole_cards)
    
    print(f"A9 suited categorized as: {category}")
    
    if category == "Suited Ace":
        print("✅ SUCCESS: A9 suited correctly categorized as 'Suited Ace'")
        return True
    else:
        print(f"❌ ISSUE: A9 suited categorized as '{category}', expected 'Suited Ace'")
        return False

if __name__ == "__main__":
    print("Running aggressive behavior tests...\n")
    
    results = []
    results.append(test_aggression_factor())
    results.append(test_suited_ace_category())
    results.append(test_a9_suited_calling())
    
    print(f"\n{'='*50}")
    print(f"Test Results: {sum(results)}/{len(results)} passed")
    
    if all(results):
        print("🎉 All tests passed! The bot should now be more aggressive with suited hands.")
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
