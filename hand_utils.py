# hand_utils.py
import math # For float('inf')

def get_hand_strength_value(hand_evaluation_tuple):
    if not hand_evaluation_tuple or not isinstance(hand_evaluation_tuple, tuple) or len(hand_evaluation_tuple) < 1:
        return 0
    return hand_evaluation_tuple[0]

def calculate_stack_to_pot_ratio(stack_size, pot_size):
    if pot_size <= 0:
        return float('inf')
    return stack_size / pot_size

def get_preflop_hand_category(hand_evaluation_tuple, hole_cards_str):
    if not hand_evaluation_tuple or len(hand_evaluation_tuple) < 3:
        return "Weak"
    if len(hand_evaluation_tuple[2]) != 2:
        return "Weak"

    rank1_val, rank2_val = hand_evaluation_tuple[2][0], hand_evaluation_tuple[2][1]
    is_pair = (rank1_val == rank2_val)
    is_suited = False
    if len(hole_cards_str) == 2 and len(hole_cards_str[0]) > 1 and len(hole_cards_str[1]) > 1:
        is_suited = (hole_cards_str[0][-1] == hole_cards_str[1][-1])

    # Premium hands - AA, KK, QQ, AK suited
    if is_pair and rank1_val >= 12: return "Premium Pair"  # QQ+
    if is_suited and rank1_val == 14 and rank2_val == 13: return "Premium Pair"  # AKs
    
    # Strong hands - JJ, TT, AK offsuit, AQ suited, suited aces A5+
    if is_pair and rank1_val >= 10: return "Strong Pair"  # JJ, TT
    if not is_suited and rank1_val == 14 and rank2_val == 13: return "Strong Pair"  # AKo
    if is_suited and rank1_val == 14 and rank2_val >= 12: return "Strong Pair"  # AQs+
    if is_pair and rank1_val >= 8: return "Strong Pair"  # Moved 99, 88 to strong
    
    # Suited hands with good potential
    if is_suited and rank1_val == 14 and rank2_val >= 4: return "Suited Ace"  # A4s+ (was A5+)
    if is_suited and abs(rank1_val - rank2_val) == 1 and (rank1_val >= 7 or rank2_val >= 7): return "Suited Connector"  # 78s+
    if is_suited and abs(rank1_val - rank2_val) == 2 and (rank1_val >= 9 or rank2_val >= 9): return "Suited Connector"  # T8s, 97s etc
    
    # Broadway hands and medium pairs
    if not is_suited and rank1_val >= 10 and rank2_val >= 10: return "Offsuit Broadway"
    if is_pair and rank1_val >= 6: return "Medium Pair"  # 77, 66 now medium
    if rank1_val >= 10 or rank2_val >= 10: return "Playable Broadway"
    
    # Add more suited hands as playable
    if is_suited and (rank1_val >= 9 or rank2_val >= 9): return "Playable Broadway"  # Any suited with 9+
    
    return "Weak"
