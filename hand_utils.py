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

    logger.debug(f"Calculated is_pair: {is_pair}, is_suited: {is_suited} (from hole_cards: {cards_to_process})")

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
        
    # Playable Broadway suited (KQs specifically)
    if is_suited and rank1_val == 13 and rank2_val == 12: # KQs
        return "Playable Broadway"
          # Suited Connectors / Gappers
    if is_suited and (rank1_val - rank2_val) == 1 and rank1_val >= 6: # e.g. 76s, 87s, 98s, ..., QJs (excluding KQs which is Playable Broadway)
        return "Suited Connector"
    if is_suited and (rank1_val - rank2_val) == 2 and rank1_val >= 8: # e.g. 86s, 97s, T8s, ..., QTs
        return "Suited Connector" # Or "Suited Gapper"
    
    # Offsuit Broadway hands (excluding AKo, which is Strong Pair)
    if not is_suited and rank1_val >= 10 and rank2_val >= 10:
        if not (rank1_val == 14 and rank2_val == 13): # Exclude AKo
             return "Offsuit Broadway"
             
    # Medium Pairs
    if is_pair and rank1_val >= 6 and rank1_val <= 7: # 66, 77
        return "Medium Pair"
        
    # Suited Playable hands (e.g. K9s, Q8s, J7s, T7s etc. that are not connectors/Aces)
    # These are hands with a high card and a decent suited kicker, not strong enough to be "Suited Ace"
    # and not connected enough to be "Suited Connector".
    if is_suited:
        # Axs is "Suited Ace"
        # Kxs (KQs, KJs are connectors)
        if rank1_val == 13 and rank2_val <= 11 and not (rank1_val - rank2_val <= 2): # KTs down to K2s, excluding connectors
            if rank2_val >= 5: return "Suited Playable" # K5s+ (K2s-K4s are weak)
        # Qxs (QJs, QTs are connectors)
        elif rank1_val == 12 and rank2_val <= 10 and not (rank1_val - rank2_val <= 2): # Q9s down to Q2s
            if rank2_val >= 5: return "Suited Playable" # Q5s+
        # Jxs (JTs, J9s are connectors/gappers)
        elif rank1_val == 11 and rank2_val <= 9 and not (rank1_val - rank2_val <= 2): # J8s down to J2s
            if rank2_val >= 4: return "Suited Playable" # J4s+
        # Txs (T9s, T8s are connectors/gappers)
        elif rank1_val == 10 and rank2_val <= 8 and not (rank1_val - rank2_val <= 2): # T7s down to T2s
            if rank2_val >= 4: return "Suited Playable" # T4s+ (T3s should be weak by falling through)
        # 9xs (98s, 97s are connectors/gappers)
        elif rank1_val == 9 and rank2_val <= 7 and not (rank1_val - rank2_val <= 2): # 96s down to 92s
            if rank2_val >= 4: return "Suited Playable" # 94s+
              # Offsuit Playable hands (e.g. A9o, KTo, QTo, JTo, T9o that are not "Offsuit Broadway")
    # These are hands with a high card and a decent offsuit kicker.
    if not is_suited:
        # Axs (AKo, AQo are "Strong Pair")
        if rank1_val == 14 and rank2_val <= 11: # AJo, ATo, A9o...A2o
            if rank2_val >= 5: return "Offsuit Playable" # A5o+ (widened for late position)
        # Kxs (KQo, KJo, KTo are "Offsuit Broadway")
        elif rank1_val == 13 and rank2_val <= 9: # K9o...K2o
            if rank2_val >= 7: return "Offsuit Playable" # K7o+
        # Qxs (QJo, QTo are "Offsuit Broadway")
        elif rank1_val == 12 and rank2_val <= 9: # Q9o...Q2o (QTo is Offsuit Broadway)
            if rank2_val >= 6: return "Offsuit Playable" # Q6o+
        # Jxs (JTo is "Offsuit Broadway")
        elif rank1_val == 11 and rank2_val <= 8: # J9o...J2o
            if rank2_val >= 6: return "Offsuit Playable" # J6o+
        # Txs
        elif rank1_val == 10 and rank2_val <= 7: # T9o is often played, T8o, T7o
            if rank2_val >= 6: return "Offsuit Playable" # T6o+

    # Small Pairs (22-55)
    if is_pair and rank1_val <= 5:
        return "Small Pair"
    
    return "Weak"
