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

RANK_TO_VALUE = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14, '10': 10}

def _get_rank_value(card_str):
    """Helper to get numerical rank from a card string like 'Ah' or 'Td'."""
    if not card_str or len(card_str) < 2: # Ensure card string has at least rank and suit
        return 0
    
    # Extract rank part (e.g., '10' from '10h', 'A' from 'Ah')
    # Assumes card_str is normalized, e.g., "3s", "Th", "10d"
    rank_part = card_str[:-1] # Gets '3' from '3s', '10' from '10s'
    
    return RANK_TO_VALUE.get(rank_part.upper(), 0)


def get_preflop_hand_category(hole_cards, position): # Renamed parameters for clarity
    logger.debug(f"Enter get_preflop_hand_category with hole_cards: {hole_cards}, position: {position}")

    if not isinstance(hole_cards, list) or len(hole_cards) != 2:
        logger.error(f"Invalid hole_cards (expected list of 2 cards): {hole_cards}. Returning 'Weak'.")
        return "Weak"
    
    # Ensure cards in hole_cards are strings before trying to get rank/suit
    if not all(isinstance(c, str) and len(c) >= 2 for c in hole_cards):
        logger.error(f"Elements in hole_cards are not valid card strings: {hole_cards}. Returning 'Weak'.")
        return "Weak"

    # Normalize card strings before processing
    cards_to_process = normalize_card_list(hole_cards)
    
    logger.debug(f"Cards being processed for rank extraction (normalized): {cards_to_process}")

    try:
        rank1_val = _get_rank_value(cards_to_process[0])
        rank2_val = _get_rank_value(cards_to_process[1])
        if rank1_val == 0 or rank2_val == 0: 
            logger.error(f"Failed to get valid rank values from cards: {cards_to_process}. Ranks: {rank1_val}, {rank2_val}. Returning 'Weak'.")
            return "Weak"
    except Exception as e:
        logger.error(f"Error extracting ranks from cards_to_process: {cards_to_process}. Error: {e}. Returning 'Weak'.")
        return "Weak"

    if rank1_val < rank2_val:
        rank1_val, rank2_val = rank2_val, rank1_val
    logger.debug(f"Normalized ranks: rank1_val={rank1_val}, rank2_val={rank2_val}")

    is_pair = (rank1_val == rank2_val)
    # Suit check directly from hole_cards
    is_suited = (cards_to_process[0][-1].lower() == cards_to_process[1][-1].lower())

    logger.debug(f"Calculated is_pair: {is_pair}, is_suited: {is_suited} (from hole_cards: {cards_to_process})")    # Premium hands - AA, KK, QQ, AKs, AKo
    if is_pair and rank1_val >= 12: # QQ, KK, AA (Q=12, K=13, A=14)
        return "Premium Pair" 
    if rank1_val == 14 and rank2_val == 13: # AKs, AKo
        return "Premium Pair" 
    
    # Strong hands - JJ, TT, AQs, AQo, 99
    if is_pair and rank1_val >= 10: # TT, JJ (T=10, J=11)
        return "Strong Pair" 
    if rank1_val == 14 and rank2_val == 12: # AQs, AQo
        return "Strong Pair" 
    if is_pair and rank1_val == 9: # 99
        return "Strong Pair"
      # Medium-Strong hands - 88, 77
    if is_pair and rank1_val >= 7 and rank1_val <= 8: # 77, 88
        return "Medium Pair"
        
    # Suited Ace hands (AJs down to A2s) - excluding AKs, AQs which are in higher categories
    if is_suited and rank1_val == 14 and rank2_val >= 2 and rank2_val <= 11: # A2s-AJs
        return "Suited Ace"
    
    # Offsuit Ace hands (AJo down to A5o) - excluding AKo, AQo which are in higher categories  
    if not is_suited and rank1_val == 14 and rank2_val >= 5 and rank2_val <= 11: # A5o-AJo
        return "Offsuit Ace"
          # Broadway suited hands (KQs, KJs, QJs, JTs)
    if is_suited and rank1_val >= 10 and rank2_val >= 10 and rank1_val != 14: # Exclude suited aces
        return "Suited Broadway"
        
    # Suited Connectors and One-gap suited hands
    if is_suited and (rank1_val - rank2_val) == 1 and rank1_val >= 6: # Connected: 65s, 76s, 87s, 98s, T9s
        return "Suited Connector"
    if is_suited and (rank1_val - rank2_val) == 2 and rank1_val >= 8: # One-gap: 86s, 97s, T8s, J9s, Q9s 
        return "Suited Connector"        
    # Offsuit Broadway hands (KQo, KJo, QJo, JTo) - excluding AKo, AQo which are in higher categories
    if not is_suited and rank1_val >= 10 and rank2_val >= 10 and rank1_val != 14:
        return "Offsuit Broadway"
             
    # Small Pairs (66, 55, 44, 33, 22) 
    if is_pair and rank1_val >= 2 and rank1_val <= 6: # 22, 33, 44, 55, 66
        return "Small Pair"
        
    # Other suited playable hands (not already categorized)
    if is_suited:
        # King-x suited (excluding broadway and connectors already categorized)
        if rank1_val == 13 and rank2_val <= 9 and rank2_val >= 5: # K9s down to K5s
            return "Suited Playable" 
        # Queen-x suited (excluding broadway and connectors already categorized)
        elif rank1_val == 12 and rank2_val <= 8 and rank2_val >= 5: # Q8s down to Q5s
            return "Suited Playable" 
        # Jack-x suited (excluding broadway and connectors already categorized)
        elif rank1_val == 11 and rank2_val <= 7 and rank2_val >= 5: # J7s down to J5s
            return "Suited Playable" 
        # Ten-x suited (excluding broadway and connectors already categorized)
        elif rank1_val == 10 and rank2_val <= 6 and rank2_val >= 5: # T6s, T5s
            return "Suited Playable"
    
    # Offsuit playable hands (not already categorized)
    if not is_suited:
        # King-x offsuit (excluding broadway already categorized)
        if rank1_val == 13 and rank2_val <= 9 and rank2_val >= 7: # K9o down to K7o
            return "Offsuit Playable" 
        # Queen-x offsuit (excluding broadway already categorized)
        elif rank1_val == 12 and rank2_val <= 9 and rank2_val >= 6: # Q9o down to Q6o
            return "Offsuit Playable" 
        # Jack-x offsuit (excluding broadway already categorized)
        elif rank1_val == 11 and rank2_val <= 8 and rank2_val >= 6: # J8o down to J6o
            return "Offsuit Playable" 
        # Ten-x offsuit
        elif rank1_val == 10 and rank2_val <= 7 and rank2_val >= 6: # T7o, T6o
            return "Offsuit Playable"
    
    return "Weak"
