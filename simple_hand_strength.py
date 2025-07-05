#!/usr/bin/env python3
"""
Create a simple, reliable equity calculator for emergency fallback.
"""

def simple_hand_strength_estimate(hole_cards, community_cards, stage):
    """
    Simple hand strength estimate without complex equity calculations.
    This is a fallback for when the main equity calculator is broken.
    """
    if not hole_cards or len(hole_cards) != 2:
        return 0.3
    
    # Extract ranks and suits
    def parse_card(card):
        if len(card) >= 2:
            if card.startswith('10'):
                return '10', card[-1]
            else:
                return card[:-1], card[-1]
        return card[0], card[1] if len(card) > 1 else ''
    
    rank1, suit1 = parse_card(hole_cards[0])
    rank2, suit2 = parse_card(hole_cards[1])
    
    # Normalize ranks
    rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, 
                   '9': 9, '10': 10, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
    
    val1 = rank_values.get(rank1, 2)
    val2 = rank_values.get(rank2, 2)
    
    # Pocket pairs
    if val1 == val2:
        if val1 >= 13:  # AA, KK
            return 0.85 if stage == 'preflop' else 0.75
        elif val1 >= 11:  # QQ, JJ  
            return 0.80 if stage == 'preflop' else 0.70
        elif val1 >= 8:   # TT, 99, 88
            return 0.70 if stage == 'preflop' else 0.60
        else:
            return 0.55 if stage == 'preflop' else 0.45
    
    # High cards
    max_val = max(val1, val2)
    min_val = min(val1, val2)
    
    if max_val == 14:  # Ace
        if min_val >= 13:  # AK
            return 0.70 if stage == 'preflop' else 0.55
        elif min_val >= 11:  # AQ, AJ
            return 0.60 if stage == 'preflop' else 0.45
        else:  # Ax
            return 0.50 if stage == 'preflop' else 0.35
    elif max_val >= 13:  # King high
        if min_val >= 12:  # KQ
            return 0.55 if stage == 'preflop' else 0.40
        else:
            return 0.45 if stage == 'preflop' else 0.30
    else:
        # Low cards
        return 0.35 if stage == 'preflop' else 0.25

# Test with KK
kk_strength = simple_hand_strength_estimate(['K♠', 'K♥'], ['8♠', '5♥', '4♥'], 'flop')
print(f"KK on 8-5-4 flop estimated strength: {kk_strength:.3f}")

# Test with other hands
test_hands = [
    (['A♠', 'A♥'], 'preflop', 'AA preflop'),
    (['7♦', '2♣'], 'preflop', '72o preflop'),
    (['8♦', '8♣'], 'flop', '88 on flop'),
]

for cards, stage, desc in test_hands:
    strength = simple_hand_strength_estimate(cards, [], stage)
    print(f"{desc}: {strength:.3f}")
