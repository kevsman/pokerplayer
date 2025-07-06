#!/usr/bin/env python3
"""
Debug the hand strength estimator
"""
import sys
sys.path.append('.')

def parse_card(card):
    if len(card) >= 2:
        if card.startswith('10'):
            return '10', card[-1]
        else:
            return card[:-1], card[-1]
    return card[0], card[1] if len(card) > 1 else ''

def debug_hand_strength():
    hole_cards = ['4♦', 'K♠']
    community_cards = ['8♠', '3♠', '7♦', '4♥', '4♣']
    stage = 'river'
    
    print(f"Debugging hand strength calculation:")
    print(f"Hole cards: {hole_cards}")
    print(f"Community cards: {community_cards}")
    print(f"Stage: {stage}")
    
    # Parse all cards
    all_cards = hole_cards + community_cards
    ranks = []
    
    rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, 
                   '9': 9, '10': 10, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
    
    for card in all_cards:
        rank, suit = parse_card(card)
        rank_val = rank_values.get(rank, 2)
        ranks.append(rank_val)
        print(f"Card {card}: rank='{rank}', suit='{suit}', value={rank_val}")
    
    print(f"All rank values: {ranks}")
    
    # Count frequencies
    from collections import Counter
    rank_counts = Counter(ranks)
    print(f"Rank counts: {rank_counts}")
    
    sorted_counts = sorted(rank_counts.values(), reverse=True)
    print(f"Sorted counts: {sorted_counts}")
    
    # Check for trips
    if sorted_counts[0] == 3:
        print("🎯 TRIPS DETECTED!")
        
        hole_rank1 = rank_values.get(parse_card(hole_cards[0])[0], 2)
        hole_rank2 = rank_values.get(parse_card(hole_cards[1])[0], 2)
        print(f"Hole card ranks: {hole_rank1}, {hole_rank2}")
        
        for rank_val, count in rank_counts.items():
            if count == 3:
                print(f"Trip rank: {rank_val}")
                if rank_val == hole_rank1 or rank_val == hole_rank2:
                    print(f"✅ We have trips with our hole card! Strength = 0.85")
                    return 0.85
                else:
                    print(f"⚠️ Set trips (not our card)")
                    return 0.45
    else:
        print("❌ No trips detected")
        
    return 0.30  # fallback

if __name__ == "__main__":
    debug_hand_strength()
