\
# filepath: h:\\Programming\\pokerplayer\\postflop\\utils.py
import logging

logger = logging.getLogger(__name__)

# Enhanced drawing hand detection function
def is_drawing_hand(win_probability, hand_rank, street):
    """
    Detect if this is likely a drawing hand based on equity and hand strength.
    Drawing hands typically have:
    - Moderate equity (25-50%) but low made hand strength
    - Are not on the river (no draws possible)
    """
    if street == 'river':
        return False  # No draws on river
    
    # High card or weak pair with reasonable equity = likely draw
    # This includes flush draws, straight draws, overcards, etc.
    return (hand_rank <= 2 and 0.25 <= win_probability <= 0.50)
