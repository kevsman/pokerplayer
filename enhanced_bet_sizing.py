# enhanced_bet_sizing.py
"""
Enhanced bet sizing system with consistent logic based on hand strength, board texture, 
position, and opponent tendencies. Addresses the wildly varying bet sizes identified in logs.
"""

import logging
from typing import Dict, Tuple, Optional, Any

logger = logging.getLogger(__name__)

class EnhancedBetSizing:
    """Provides consistent and strategic bet sizing."""
    
    def __init__(self):
        # Base bet sizing by hand strength (as fraction of pot)
        self.base_sizing = {
            'very_strong': {
                'value': 0.75,    # Large value bets
                'protection': 0.85,  # Even larger for protection
                'thin_value': 0.60   # Smaller for thin value
            },
            'strong': {
                'value': 0.65,
                'protection': 0.75,
                'thin_value': 0.50
            },
            'medium': {
                'value': 0.50,
                'protection': 0.60,
                'thin_value': 0.40
            },
            'weak_made': {
                'value': 0.35,
                'protection': 0.45,
                'thin_value': 0.30
            },
            'bluff': {
                'small': 0.33,     # Small bluffs
                'standard': 0.60,  # Standard bluffs
                'large': 0.90      # Large bluffs/semi-bluffs
            }
        }
        
        # Position adjustments
        self.position_adjustments = {
            'UTG': 0.90,    # Smaller from early position
            'MP': 0.95,     # Slightly smaller from middle
            'CO': 1.0,      # Standard from cutoff
            'BTN': 1.05,    # Slightly larger from button
            'SB': 0.85,     # Smaller from small blind
            'BB': 0.90      # Smaller from big blind
        }
        
        # Board texture adjustments
        self.board_texture_adjustments = {
            'very_dry': {
                'value': 0.85,      # Smaller on dry boards
                'bluff': 0.70       # Smaller bluffs on dry boards
            },
            'dry': {
                'value': 0.90,
                'bluff': 0.80
            },
            'moderate': {
                'value': 1.0,
                'bluff': 1.0
            },
            'wet': {
                'value': 1.10,      # Larger for protection
                'bluff': 1.15       # Larger bluffs on wet boards
            },
            'very_wet': {
                'value': 1.20,
                'bluff': 1.25
            }
        }
        
        # SPR-based adjustments
        self.spr_adjustments = {
            'low': (0, 2),      # SPR 0-2: commit or fold strategy
            'medium': (2, 6),   # SPR 2-6: standard play
            'high': (6, 15),    # SPR 6-15: pot control
            'very_high': (15, float('inf'))  # SPR 15+: extreme pot control
        }
    
    def get_optimal_bet_size(
        self,
        hand_strength: str,
        pot_size: float,
        my_stack: float,
        street: str,
        position: str = 'BB',
        board_texture: str = 'moderate',
        spr: float = 5.0,
        opponent_count: int = 1,
        opponent_tendencies: Optional[Dict] = None,
        bet_purpose: str = 'value'  # 'value', 'protection', 'bluff', 'thin_value'
    ) -> Tuple[float, str]:
        """
        Calculate optimal bet size based on multiple factors.
        
        Returns:
            Tuple of (bet_amount, reasoning)
        """
        
        # Get base sizing
        if bet_purpose == 'bluff':
            base_fraction = self._get_bluff_sizing(board_texture, opponent_tendencies)
            base_category = 'bluff'
        else:
            base_fraction = self._get_value_sizing(hand_strength, bet_purpose)
            base_category = hand_strength
        
        # Apply adjustments
        final_fraction = base_fraction
        adjustments = []
        
        # Position adjustment
        pos_adj = self.position_adjustments.get(position, 1.0)
        final_fraction *= pos_adj
        if pos_adj != 1.0:
            adjustments.append(f"position({position}): {pos_adj:.2f}")
        
        # Board texture adjustment
        texture_adj = self._get_board_texture_adjustment(board_texture, bet_purpose)
        final_fraction *= texture_adj
        if texture_adj != 1.0:
            adjustments.append(f"board({board_texture}): {texture_adj:.2f}")
        
        # SPR adjustment
        spr_adj = self._get_spr_adjustment(spr, hand_strength)
        final_fraction *= spr_adj
        if spr_adj != 1.0:
            adjustments.append(f"SPR({spr:.1f}): {spr_adj:.2f}")
        
        # Opponent count adjustment (multiway)
        if opponent_count > 1:
            multiway_adj = max(0.6, 1.0 - (opponent_count - 1) * 0.15)
            final_fraction *= multiway_adj
            adjustments.append(f"multiway({opponent_count}): {multiway_adj:.2f}")
        
        # Opponent tendency adjustments
        if opponent_tendencies:
            opp_adj = self._get_opponent_adjustment(opponent_tendencies, bet_purpose)
            final_fraction *= opp_adj
            if opp_adj != 1.0:
                adjustments.append(f"opponent: {opp_adj:.2f}")
        
        # Stack size considerations
        stack_adj = self._get_stack_adjustment(final_fraction * pot_size, my_stack)
        final_fraction *= stack_adj
        if stack_adj != 1.0:
            adjustments.append(f"stack: {stack_adj:.2f}")
        
        # Calculate final bet amount
        bet_amount = min(final_fraction * pot_size, my_stack)
        bet_amount = max(bet_amount, 0.01)  # Minimum bet
        
        # Generate reasoning
        reasoning = f"{bet_purpose} bet: {base_fraction:.2f} base"
        if adjustments:
            reasoning += f" * {' * '.join(adjustments)} = {final_fraction:.2f}"
        reasoning += f" of pot = {bet_amount:.2f}"
        
        logger.debug(f"Bet sizing: {reasoning}")
        
        return round(bet_amount, 2), reasoning
    
    def _get_value_sizing(self, hand_strength: str, bet_purpose: str) -> float:
        """Get base value bet sizing."""
        sizing_map = self.base_sizing.get(hand_strength, self.base_sizing['weak_made'])
        return sizing_map.get(bet_purpose, sizing_map.get('value', 0.50))
    
    def _get_bluff_sizing(self, board_texture: str, opponent_tendencies: Optional[Dict]) -> float:
        """Get bluff sizing based on board and opponents."""
        bluff_sizes = self.base_sizing['bluff']
        
        # Default to standard bluff
        base_size = bluff_sizes['standard']
        
        # Adjust for board texture
        if board_texture in ['very_wet', 'wet']:
            base_size = bluff_sizes['large']  # Larger bluffs on wet boards
        elif board_texture in ['very_dry', 'dry']:
            base_size = bluff_sizes['small']  # Smaller bluffs on dry boards
        
        # Adjust for opponent tendencies
        if opponent_tendencies:
            if opponent_tendencies.get('fold_frequency', 0.5) > 0.6:
                base_size = bluff_sizes['small']  # Smaller vs folders
            elif opponent_tendencies.get('fold_frequency', 0.5) < 0.4:
                base_size = bluff_sizes['large']  # Larger vs callers
        
        return base_size
    
    def _get_board_texture_adjustment(self, board_texture: str, bet_purpose: str) -> float:
        """Get board texture adjustment."""
        adjustments = self.board_texture_adjustments.get(board_texture, 
                                                        self.board_texture_adjustments['moderate'])
        
        if bet_purpose == 'bluff':
            return adjustments.get('bluff', 1.0)
        else:
            return adjustments.get('value', 1.0)
    
    def _get_spr_adjustment(self, spr: float, hand_strength: str) -> float:
        """Get SPR-based adjustment."""
        if spr <= 2:
            # Low SPR: commit or fold
            if hand_strength in ['very_strong', 'strong']:
                return 1.3  # Larger bets to build pot
            else:
                return 0.8  # Smaller bets with weaker hands
        elif spr <= 6:
            # Medium SPR: standard play
            return 1.0
        elif spr <= 15:
            # High SPR: pot control
            if hand_strength in ['very_strong', 'strong']:
                return 0.9  # Slightly smaller to control pot
            else:
                return 0.8  # Much smaller with medium hands
        else:
            # Very high SPR: extreme pot control
            if hand_strength == 'very_strong':
                return 0.8
            elif hand_strength == 'strong':
                return 0.7
            else:
                return 0.6  # Very small bets
    
    def _get_opponent_adjustment(self, opponent_tendencies: Dict, bet_purpose: str) -> float:
        """Get opponent-based adjustment."""
        if bet_purpose == 'bluff':
            # For bluffs, adjust based on fold frequency
            fold_freq = opponent_tendencies.get('fold_frequency', 0.5)
            if fold_freq > 0.6:
                return 0.8  # Smaller bluffs vs folders
            elif fold_freq < 0.4:
                return 1.2  # Larger bluffs vs stations
        else:
            # For value bets, adjust based on calling frequency
            call_freq = opponent_tendencies.get('calling_frequency', 0.5)
            if call_freq > 0.6:
                return 1.1  # Larger value bets vs callers
            elif call_freq < 0.4:
                return 0.9  # Smaller value bets vs folders
        
        return 1.0
    
    def _get_stack_adjustment(self, proposed_bet: float, stack_size: float) -> float:
        """Adjust for stack size considerations."""
        if proposed_bet > stack_size:
            return 1.0  # Will be capped anyway
        
        # If bet is large portion of stack, consider going all-in
        bet_to_stack_ratio = proposed_bet / stack_size
        
        if bet_to_stack_ratio > 0.6:
            return 1.15  # Go bigger when committing large portion
        elif bet_to_stack_ratio > 0.4:
            return 1.05  # Slightly bigger
        
        return 1.0
    
    def should_check_instead(
        self,
        hand_strength: str,
        win_probability: float,
        pot_size: float,
        opponent_count: int,
        position: str,
        street: str
    ) -> Tuple[bool, str]:
        """Determine if checking is better than betting."""
        
        # Always check very weak hands
        if hand_strength == 'weak' and win_probability < 0.25:
            return True, "Very weak hand, no value to extract"
        
        # Check weak made hands in multiway pots
        if hand_strength == 'weak_made' and opponent_count >= 3:
            return True, "Weak made hand in multiway pot"
        
        # Check medium hands against many opponents
        if hand_strength == 'medium' and opponent_count >= 4:
            return True, "Medium hand against too many opponents"
        
        # Check for pot control in position
        if position == 'BTN' and hand_strength == 'medium' and street == 'turn':
            if win_probability < 0.55:
                return True, "Pot control with medium hand in position"
        
        # Check behind on river with marginal hands
        if street == 'river' and hand_strength in ['weak_made', 'medium'] and win_probability < 0.50:
            return True, "Marginal hand on river, check for showdown value"
        
        return False, "Betting is preferred"

# Create global instance
bet_sizer = EnhancedBetSizing()

def get_enhanced_bet_size(
    hand_strength: str,
    pot_size: float,
    my_stack: float,
    street: str,
    position: str = 'BB',
    board_texture: str = 'moderate',
    spr: float = 5.0,
    opponent_count: int = 1,
    opponent_tendencies: Optional[Dict] = None,
    bet_purpose: str = 'value'
) -> Tuple[float, str]:
    """Enhanced bet sizing function."""
    return bet_sizer.get_optimal_bet_size(
        hand_strength, pot_size, my_stack, street, position,
        board_texture, spr, opponent_count, opponent_tendencies, bet_purpose
    )

def should_check_instead_of_bet(
    hand_strength: str,
    win_probability: float,
    pot_size: float,
    opponent_count: int,
    position: str,
    street: str
) -> Tuple[bool, str]:
    """Check if checking is better than betting."""
    return bet_sizer.should_check_instead(
        hand_strength, win_probability, pot_size, opponent_count, position, street
    )
