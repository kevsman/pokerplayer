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
        logger.error(f"Invalid hole_cards (expected list of 2 cards): {hole_cards}. Returning 'Trash'.")
        return "Trash"
    
    # Ensure cards in hole_cards are strings before trying to get rank/suit
    if not all(isinstance(c, str) and len(c) >= 2 for c in hole_cards):
        logger.error(f"Elements in hole_cards are not valid card strings: {hole_cards}. Returning 'Trash'.")
        return "Trash"

    # Normalize card strings before processing
    cards_to_process = normalize_card_list(hole_cards)
    
    logger.debug(f"Cards being processed for rank extraction (normalized): {cards_to_process}")

    try:
        rank1_val = _get_rank_value(cards_to_process[0])
        rank2_val = _get_rank_value(cards_to_process[1])
        if rank1_val == 0 or rank2_val == 0: 
            logger.error(f"Failed to get valid rank values from cards: {cards_to_process}. Ranks: {rank1_val}, {rank2_val}. Returning 'Trash'.")
            return "Trash"
    except Exception as e:
        logger.error(f"Error extracting ranks from cards_to_process: {cards_to_process}. Error: {e}. Returning 'Trash'.")
        return "Trash"

    if rank1_val < rank2_val:
        rank1_val, rank2_val = rank2_val, rank1_val
    logger.debug(f"Normalized ranks: rank1_val={rank1_val}, rank2_val={rank2_val}")

    is_pair = (rank1_val == rank2_val)
    # Suit check directly from hole_cards
    is_suited = (cards_to_process[0][-1].lower() == cards_to_process[1][-1].lower())
    gap = rank1_val - rank2_val

    logger.debug(f"Calculated is_pair: {is_pair}, is_suited: {is_suited} (from hole_cards: {cards_to_process})")

    # 1. Premium Hands: AA, KK, QQ, AKs, AKo
    if is_pair and rank1_val >= 12: # AA, KK, QQ
        return "Premium"
    if rank1_val == 14 and rank2_val == 13: # AKs, AKo
        return "Premium"

    # 2. Strong Hands: JJ, TT, AQs, AQo, KQs
    if is_pair and rank1_val >= 10: # JJ, TT
        return "Strong"
    if rank1_val == 14 and rank2_val == 12: # AQs, AQo
        return "Strong"
    if is_suited and rank1_val == 13 and rank2_val == 12: # KQs
        return "Strong"

    # 3. Medium Pairs: 99, 88, 77
    if is_pair and rank1_val >= 7: # 99, 88, 77
        return "Medium Pair"

    # 4. Small Pairs: 66-22
    if is_pair and rank1_val < 7: # 66, 55, 44, 33, 22
        return "Small Pair"

    # 5. Suited Aces: AJs-A2s
    if is_suited and rank1_val == 14:
        return "Suited Ace"

    # 6. Suited Broadway: KJs, KTs, QJs, QTs, JTs
    if is_suited and rank1_val >= 11 and rank2_val >= 10:
        return "Suited Broadway"

    # 7. Offsuit Broadway: KQo, KJo, KTo, QJo, QTo, JTo
    if not is_suited and rank1_val >= 10 and rank2_val >= 10:
        return "Offsuit Broadway"

    # 8. Suited Connectors: T9s, 98s, 87s, 76s, 65s, 54s
    if is_suited and gap == 1 and rank1_val < 11:
        return "Suited Connector"

    # 9. Suited Gappers: K9s, Q9s, J9s, T8s, 97s, 86s, 75s, 64s
    if is_suited and gap >= 2 and rank1_val >= 9 and rank2_val >= 4:
        return "Suited Gapper"

    # 10. Offsuit Aces: AJo-A2o
    if not is_suited and rank1_val == 14:
        return "Offsuit Ace"

    # 11. Offsuit Kings: K9o-K2o
    if not is_suited and rank1_val == 13:
        return "Offsuit King"

    # All other hands are considered Trash
    return "Trash"
