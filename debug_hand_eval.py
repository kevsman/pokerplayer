#!/usr/bin/env python3
"""
Debug script to understand hand evaluation tuples
"""

from hand_evaluator import HandEvaluator

def debug_hand_evaluation():
    hand_evaluator = HandEvaluator()
    
    # Test some hands
    test_hands = [
        ['A♠', 'A♣'],  # Pocket Aces
        ['8♥', '8♠'],  # Pocket 8s  
        ['A♥', '4♥'],  # A4 suited
        ['9♦', 'K♣'],  # K9 offsuit
    ]
    
    for cards in test_hands:
        hand_eval = hand_evaluator.evaluate_hand(cards, [])
        print(f"Cards: {cards}")
        print(f"  Hand evaluation: {hand_eval}")
        print(f"  Type: {type(hand_eval)}")
        if hand_eval:
            print(f"  hand_eval[0]: {hand_eval[0]}")
            print(f"  hand_eval[1]: {hand_eval[1]}")
            if len(hand_eval) > 2:
                print(f"  hand_eval[2]: {hand_eval[2]}")
        print()

if __name__ == "__main__":
    debug_hand_evaluation()
