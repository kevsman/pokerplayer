# hand_utils.py
import math # For float('inf')
import logging

# Logger for this module
logger = logging.getLogger(__name__)

SUIT_MAP_UNICODE_TO_CHAR = {
    '♥': 'h', # Hearts
    '♦': 'd', # Diamonds
    '♣': 'c', # Clubs
    '♠': 's'  # Spades
}

def normalize_card_char_suit(card_str):
    """Normalizes a single card string e.g., 'A♥' to 'Ah' or '10s' to '10s'."""
    if not isinstance(card_str, str) or len(card_str) < 2:
        logger.warning(f"Invalid card string for normalization: {card_str}")
        return card_str

    rank_part = card_str[:-1]
    suit_char = card_str[-1]

    normalized_suit = SUIT_MAP_UNICODE_TO_CHAR.get(suit_char, suit_char)
    
    return rank_part + normalized_suit

def normalize_card_list(card_list):
    """Normalizes a list of card strings."""
    if not isinstance(card_list, list):
        logger.warning(f"Cannot normalize card_list as it's not a list: {card_list}")
        return card_list # Or appropriate error handling

    normalized_cards = [normalize_card_char_suit(card) for card in card_list]
    # Avoid overly verbose logging for every call if this is frequent
    # logger.debug(f"Normalized card list from {card_list} to {normalized_cards}")
    return normalized_cards

def get_hand_strength_value(hand_evaluation_tuple):
    if not hand_evaluation_tuple or not isinstance(hand_evaluation_tuple, tuple) or len(hand_evaluation_tuple) < 1:
        return 0
    return hand_evaluation_tuple[0]

def calculate_stack_to_pot_ratio(stack_size, pot_size):
    if pot_size <= 0:
        return float('inf')
    return stack_size / pot_size

def get_preflop_hand_category(hand_evaluation_tuple, hole_cards_str):
    # Expects hole_cards_str to be already normalized, e.g., ['Ah', 'Qh']
    logger.debug(f"Enter get_preflop_hand_category with hole_cards_str: {hole_cards_str}, hand_evaluation_tuple: {hand_evaluation_tuple}")

    if not hand_evaluation_tuple or not isinstance(hand_evaluation_tuple, tuple) or len(hand_evaluation_tuple) < 3:
        logger.warning(f"Invalid hand_evaluation_tuple (1): {hand_evaluation_tuple}. Returning 'Weak'.")
        return "Weak"
    
    if not isinstance(hand_evaluation_tuple[2], tuple) or len(hand_evaluation_tuple[2]) != 2:
        logger.warning(f"Invalid hand_evaluation_tuple[2] structure: {hand_evaluation_tuple[2]}. Returning 'Weak'.")
        return "Weak"

    try:
        rank1_raw, rank2_raw = hand_evaluation_tuple[2][0], hand_evaluation_tuple[2][1]
        rank1_val, rank2_val = int(rank1_raw), int(rank2_raw)
    except (ValueError, TypeError, IndexError) as e:
        logger.error(f"Ranks in hand_evaluation_tuple[2] are invalid: {hand_evaluation_tuple[2]}. Error: {e}. Returning 'Weak'.")
        return "Weak"

    # Sort ranks: rank1_val should be the higher rank
    if rank1_val < rank2_val:
        rank1_val, rank2_val = rank2_val, rank1_val
    logger.debug(f"Normalized ranks: rank1_val={rank1_val}, rank2_val={rank2_val}")

    is_pair = (rank1_val == rank2_val)
    is_suited = False
    
    valid_hole_cards_for_suit_check = False
    if isinstance(hole_cards_str, list) and len(hole_cards_str) == 2 and \
       isinstance(hole_cards_str[0], str) and len(hole_cards_str[0]) > 1 and \
       isinstance(hole_cards_str[1], str) and len(hole_cards_str[1]) > 1:
        valid_hole_cards_for_suit_check = True
        is_suited = (hole_cards_str[0][-1] == hole_cards_str[1][-1])
    
    if not valid_hole_cards_for_suit_check:
        logger.warning(f"hole_cards_str is not in expected format for suit check: {hole_cards_str}. Assuming not suited.")
        # is_suited remains False

    logger.debug(f"Calculated is_pair: {is_pair}, is_suited: {is_suited} (from hole_cards_str: {hole_cards_str})")

    # Premium hands - AA, KK, QQ, AK suited
    if is_pair and rank1_val >= 12: # QQ, KK, AA (Q=12, K=13, A=14)
        return "Premium Pair" 
    if is_suited and rank1_val == 14 and rank2_val == 13: # AKs
        return "Premium Pair" 
    
    # Strong hands - JJ, TT, AK offsuit, AQ suited
    if is_pair and rank1_val >= 10: # TT, JJ (T=10, J=11)
        return "Strong Pair" 
    if not is_suited and rank1_val == 14 and rank2_val == 13: # AKo
        return "Strong Pair" 
    if is_suited and rank1_val == 14 and rank2_val == 12: # AQs
        return "Strong Pair" 
    if is_pair and rank1_val >= 8: # 88, 99 (8,9)
        return "Strong Pair"
    
    # Suited Ace hands (AJs down to A2s)
    if is_suited and rank1_val == 14 and rank2_val >= 2 and rank2_val <= 11: # A2s-AJs
        return "Suited Ace"
        
    # Suited Connectors / Gappers
    if is_suited and (rank1_val - rank2_val) == 1 and rank1_val >= 7: # e.g. KQs, QJs, ..., 76s
        return "Suited Connector"
    if is_suited and (rank1_val - rank2_val) == 2 and rank1_val >= 9: # e.g. KJs, QTs, ..., 97s
        return "Suited Connector" # Or "Suited Gapper"
    
    # Offsuit Broadway hands (excluding AKo, which is Strong Pair)
    if not is_suited and rank1_val >= 10 and rank2_val >= 10:
        if not (rank1_val == 14 and rank2_val == 13): # Exclude AKo
             return "Offsuit Broadway"
             
    # Medium Pairs
    if is_pair and rank1_val >= 6 and rank1_val <= 7: # 66, 77
        return "Medium Pair"
        
    # Playable Broadway (catch-all for hands with at least one broadway card not yet categorized)
    # This includes suited hands like K9s, Q8s etc. if not connectors/aces, and offsuit like A9o, K8o.
    if rank1_val >= 10: 
        return "Playable Broadway" 
    
    # Other Suited Playable hands (e.g., K8s, Q7s, 96s if not fitting above categories)
    if is_suited and rank1_val >= 9:
        return "Playable Broadway" # Or "Suited Playable"
    
    return "Weak"
