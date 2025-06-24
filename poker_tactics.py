
import logging

logger = logging.getLogger(__name__)

def has_blocker_effects(my_hand, board, target_ranks, target_suits=None):
    """
    Assess if holding certain cards (blockers) reduces the likelihood of an opponent having a strong hand.
    """
    hand_cards = my_hand + board
    blocker_count = 0
    for rank in target_ranks:
        if any(card.startswith(rank) for card in hand_cards):
            blocker_count += 1
    
    if target_suits:
        for suit in target_suits:
            if any(card.endswith(suit) for card in my_hand):
                blocker_count += 1 # Simplified logic
    
    return blocker_count > 0

def should_merge_or_polarize_range(opponent_type, board_texture):
    """
    Decide whether to bet with a merged range or a polarized range.
    """
    if opponent_type == 'weak_passive' or board_texture == 'dry':
        return 'merge'
    if opponent_type == 'strong_aggressive' or board_texture == 'draw_heavy':
        return 'polarize'
    return 'merge' # Default

def should_overbet_or_underbet(street, hand_strength, board_texture, nut_advantage):
    """
    Determine optimal bet sizing beyond standard sizes.
    """
    if street in ['turn', 'river'] and hand_strength > 8 and nut_advantage and board_texture != 'draw_heavy':
        return 'overbet'
    if hand_strength < 4 and board_texture == 'dry':
        return 'underbet'
    return None

def adjust_for_multiway_pot(active_opponents_count, hand_strength):
    """
    Adjust strategy in pots with multiple players.
    """
    if active_opponents_count > 2:
        if hand_strength < 5: # Less than a strong pair
            return 'fold'
        if hand_strength < 7: # Less than two pair
            return 'check_call'
    return 'standard'

def should_double_barrel_bluff(board_runout, previous_action, opponent_type):
    """
    Decide whether to continue bluffing on the turn.
    """
    # Simple logic: double barrel if an overcard comes and opponent is not a calling station
    if previous_action == 'bet' and opponent_type != 'calling_station':
        # In a real scenario, board_runout would be analyzed for scare cards
        return True
    return False

def should_delay_cbet(street, previous_action, board_texture, opponent_type):
    """
    Decide whether to check on the flop with the intention of betting on the turn.
    """
    if street == 'flop' and previous_action == 'raise_preflop' and board_texture == 'draw_heavy' and opponent_type == 'thinking_player':
        return True
    return False

def should_river_overbluff(opponent_type, river_action_history):
    """

    Identify situations on the river where an opponent is likely to fold to a large bet.
    """
    if opponent_type == 'tight_passive' and 'check' in river_action_history:
        return True
    return False

def should_induce_bluff(opponent_type, hand_strength, street, action_history):
    """
    Check-calling with a strong hand to encourage an aggressive opponent to bluff.
    """
    if opponent_type == 'aggressive' and hand_strength > 7 and street in ['flop', 'turn']:
        if not action_history or 'check' in action_history:
            return True
    return False

def assess_board_danger(community_cards):
    """
    Evaluate how coordinated the board is.
    Returns a dictionary with boolean flags for flush and straight draws.
    """
    suits = [c[1] for c in community_cards]
    ranks = sorted([int(c[0].replace('T', '10').replace('J', '11').replace('Q', '12').replace('K', '13').replace('A', '14')) for c in community_cards])
    
    flush_draw = any(suits.count(s) >= 3 for s in set(suits))
    
    straight_draw = False
    if len(ranks) >= 3:
        unique_ranks = sorted(list(set(ranks)))
        for i in range(len(unique_ranks) - 2):
            if unique_ranks[i+2] - unique_ranks[i] <= 4:
                straight_draw = True
                break
    
    return {'flush_draw': flush_draw, 'straight_draw': straight_draw}

def should_limp_reraise(position, hand_category, big_blind, my_stack):
    """
    Decide to limp with a strong hand with the intention of re-raising if someone else raises.
    This is a deceptive play that can build a big pot.
    """
    # Good from early to middle position with premium hands
    if position in ['UTG', 'MP'] and hand_category in ['Premium Pair', 'Strong Pair']:
        # Ensure we have enough stack to make it work
        if my_stack > 50 * big_blind:
            return True
    return False
