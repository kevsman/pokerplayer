#!/usr/bin/env python3

from hand_evaluator import HandEvaluator

def test_simple():
    print("=== Simple Hand Evaluator Test ===")
    
    evaluator = HandEvaluator()
    
    # Test 1: Card conversion
    print("\n1. Testing card conversion:")
    cards = ['Qs', 'Qh', 'As', 'Kh', '2s', '7c']
    for card in cards:
        result = evaluator._convert_card_to_value(card)
        print(f"  {card} -> {result}")
    
    # Test 2: Pre-flop evaluation
    print("\n2. Testing pre-flop hands:")
    
    # Pocket Queens
    print("  Testing QQ:")
    result = evaluator.calculate_best_hand(['Qs', 'Qh'], [])
    print(f"    calculate_best_hand: {result}")
    
    eval_result = evaluator.evaluate_hand(['Qs', 'Qh'], [])
    print(f"    evaluate_hand: {eval_result}")
    
    # AK suited
    print("  Testing AK:")
    result = evaluator.calculate_best_hand(['As', 'Kh'], [])
    print(f"    calculate_best_hand: {result}")
    
    eval_result = evaluator.evaluate_hand(['As', 'Kh'], [])
    print(f"    evaluate_hand: {eval_result}")
    
    # 27 offsuit  
    print("  Testing 27:")
    result = evaluator.calculate_best_hand(['2s', '7c'], [])
    print(f"    calculate_best_hand: {result}")
    
    eval_result = evaluator.evaluate_hand(['2s', '7c'], [])
    print(f"    evaluate_hand: {eval_result}")

if __name__ == "__main__":
    test_simple()
