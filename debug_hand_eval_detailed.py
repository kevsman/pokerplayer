#!/usr/bin/env python3

from hand_evaluator import HandEvaluator

def test_hand_evaluation():
    evaluator = HandEvaluator()
    
    print("=== Testing Hand Evaluator ===")
    
    # Test card conversion
    print("\n1. Testing card conversion:")
    test_cards = ['Q♠', 'Q♥', 'A♠', 'K♥', '2♠', '7♣']
    for card in test_cards:
        result = evaluator._convert_card_to_value(card)
        print(f"Card '{card}' -> {result}")
    
    # Test pre-flop evaluation
    print("\n2. Testing pre-flop hands:")
    hole_cards_list = [
        ['Q♠', 'Q♥'],  # Pocket Queens
        ['A♠', 'K♥'],  # AK
        ['2♠', '7♣']   # 27o
    ]
    
    for hole_cards in hole_cards_list:
        print(f"\nHole cards: {hole_cards}")
        result = evaluator.calculate_best_hand(hole_cards, [])
        print(f"Result: {result}")
        
        # Also test evaluate_hand method
        eval_result = evaluator.evaluate_hand(hole_cards, [])
        print(f"Evaluate result: {eval_result}")
    
    # Test with community cards
    print("\n3. Testing with community cards:")
    hole_cards = ['Q♠', 'Q♥']
    community_cards = ['A♠', 'K♥', '2♣']
    result = evaluator.calculate_best_hand(hole_cards, community_cards)
    print(f"QQ with flop A-K-2: {result}")

if __name__ == "__main__":
    test_hand_evaluation()
