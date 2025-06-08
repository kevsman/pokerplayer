# advanced_position_strategy.py
"""
Advanced position-based strategy module for cash game poker.
Implements sophisticated positional awareness for all streets and situations.
"""

import logging

logger = logging.getLogger(__name__)

class AdvancedPositionStrategy:
    """
    Advanced position-based strategy implementation for cash games.
    Handles position-specific adjustments for betting, calling, and bluffing.
    """
    
    def __init__(self):
        # Position rankings for relative strength
        self.position_power = {
            'UTG': 1, 'UTG+1': 2, 'MP': 3, 'MP+1': 4, 'LJ': 5,
            'HJ': 6, 'CO': 7, 'BTN': 8, 'SB': 2, 'BB': 3  # Blinds act last preflop but first postflop
        }
        
        # Position categories
        self.early_positions = ['UTG', 'UTG+1', 'MP']
        self.middle_positions = ['MP+1', 'LJ', 'HJ']
        self.late_positions = ['CO', 'BTN']
        self.blind_positions = ['SB', 'BB']

    def get_positional_betting_strategy(self, position, street, hand_strength, board_texture,
                                      active_opponents, stack_depth_bb):
        """
        Get comprehensive positional betting strategy.
        
        Args:
            position: Player position
            street: Current street
            hand_strength: Hand strength classification
            board_texture: Board texture analysis
            active_opponents: Number of active opponents
            stack_depth_bb: Stack depth in big blinds
            
        Returns:
            dict: Positional betting strategy recommendations
        """
        try:
            position_category = self._get_position_category(position)
            
            # Base strategy by position category
            if position_category == 'late':
                strategy = self._get_late_position_strategy(
                    position, street, hand_strength, board_texture, active_opponents, stack_depth_bb
                )
            elif position_category == 'middle':
                strategy = self._get_middle_position_strategy(
                    position, street, hand_strength, board_texture, active_opponents, stack_depth_bb
                )
            elif position_category == 'early':
                strategy = self._get_early_position_strategy(
                    position, street, hand_strength, board_texture, active_opponents, stack_depth_bb
                )
            else:  # blind positions
                strategy = self._get_blind_position_strategy(
                    position, street, hand_strength, board_texture, active_opponents, stack_depth_bb
                )
            
            # Add universal adjustments
            strategy = self._apply_universal_adjustments(strategy, street, active_opponents, stack_depth_bb)
            
            return strategy
            
        except Exception as e:
            logger.warning(f"Error in positional betting strategy: {e}")
            return self._get_default_strategy()

    def _get_position_category(self, position):
        """Categorize position into early, middle, late, or blind."""
        if position in self.late_positions:
            return 'late'
        elif position in self.middle_positions:
            return 'middle'
        elif position in self.early_positions:
            return 'early'
        else:
            return 'blind'

    def _get_late_position_strategy(self, position, street, hand_strength, board_texture,
                                  active_opponents, stack_depth_bb):
        """Strategy for late position (CO, BTN)."""
        strategy = {
            'aggression_multiplier': 1.2,
            'bluff_frequency': 0.35,
            'value_bet_sizing': 0.70,
            'thin_value_threshold': 0.52,
            'steal_frequency': 0.45,
            'position_advantage': 'high'
        }
        
        if position == 'BTN':  # Button gets extra aggression
            strategy['aggression_multiplier'] = 1.25
            strategy['bluff_frequency'] = 0.40
            strategy['steal_frequency'] = 0.50
            strategy['barrel_frequency'] = 0.65  # Continue betting on multiple streets
        
        # Street-specific adjustments
        if street == 'flop':
            strategy['c_bet_frequency'] = 0.75
            strategy['check_behind_frequency'] = 0.25
        elif street == 'turn':
            strategy['double_barrel_frequency'] = 0.45
            strategy['give_up_frequency'] = 0.30
        elif street == 'river':
            strategy['value_bet_frequency'] = 0.65
            strategy['river_bluff_frequency'] = 0.35
            strategy['thin_value_threshold'] = 0.50  # Can bet very thin on river
        
        # Board texture adjustments
        if board_texture:
            if board_texture.get('dry', False):
                strategy['bluff_frequency'] *= 1.15
                strategy['c_bet_frequency'] = min(0.85, strategy.get('c_bet_frequency', 0.75) * 1.1)
            elif board_texture.get('wet', False):
                strategy['value_bet_sizing'] *= 1.1  # Bet bigger for protection
                strategy['bluff_frequency'] *= 0.9
        
        return strategy

    def _get_middle_position_strategy(self, position, street, hand_strength, board_texture,
                                    active_opponents, stack_depth_bb):
        """Strategy for middle position (MP+1, LJ, HJ)."""
        strategy = {
            'aggression_multiplier': 1.0,
            'bluff_frequency': 0.25,
            'value_bet_sizing': 0.65,
            'thin_value_threshold': 0.58,
            'steal_frequency': 0.25,
            'position_advantage': 'medium'
        }
        
        # HJ gets slightly more aggression than earlier middle positions
        if position == 'HJ':
            strategy['aggression_multiplier'] = 1.05
            strategy['bluff_frequency'] = 0.28
            strategy['steal_frequency'] = 0.30
        
        # Street-specific adjustments
        if street == 'flop':
            strategy['c_bet_frequency'] = 0.65
        elif street == 'turn':
            strategy['double_barrel_frequency'] = 0.35
        elif street == 'river':
            strategy['value_bet_frequency'] = 0.55
            strategy['river_bluff_frequency'] = 0.25
        
        # Multiway adjustments (middle position often faces multiway pots)
        if active_opponents > 2:
            strategy['aggression_multiplier'] *= 0.85
            strategy['bluff_frequency'] *= 0.8
            strategy['thin_value_threshold'] += 0.05
        
        return strategy

    def _get_early_position_strategy(self, position, street, hand_strength, board_texture,
                                   active_opponents, stack_depth_bb):
        """Strategy for early position (UTG, UTG+1, MP)."""
        strategy = {
            'aggression_multiplier': 0.85,
            'bluff_frequency': 0.18,
            'value_bet_sizing': 0.60,
            'thin_value_threshold': 0.62,
            'steal_frequency': 0.10,
            'position_advantage': 'low'
        }
        
        # UTG is most constrained
        if position == 'UTG':
            strategy['aggression_multiplier'] = 0.80
            strategy['bluff_frequency'] = 0.15
            strategy['steal_frequency'] = 0.05
        
        # Street-specific adjustments
        if street == 'flop':
            strategy['c_bet_frequency'] = 0.55
            strategy['check_call_frequency'] = 0.35
        elif street == 'turn':
            strategy['double_barrel_frequency'] = 0.25
            strategy['check_fold_frequency'] = 0.40
        elif street == 'river':
            strategy['value_bet_frequency'] = 0.45
            strategy['river_bluff_frequency'] = 0.15
        
        # Early position needs stronger hands for aggression
        if hand_strength in ['medium', 'weak_made']:
            strategy['aggression_multiplier'] *= 0.9
            strategy['thin_value_threshold'] += 0.03
        
        return strategy

    def _get_blind_position_strategy(self, position, street, hand_strength, board_texture,
                                   active_opponents, stack_depth_bb):
        """Strategy for blind positions (SB, BB)."""
        if street == 'preflop':
            # Preflop: blinds act last
            strategy = {
                'aggression_multiplier': 0.95,
                'bluff_frequency': 0.20,
                'defend_frequency': 0.40,
                'squeeze_frequency': 0.15,
                'position_advantage': 'medium_preflop'
            }
            if position == 'BB':
                strategy['defend_frequency'] = 0.45  # BB defends wider
        else:
            # Postflop: blinds act first (out of position)
            strategy = {
                'aggression_multiplier': 0.75,
                'bluff_frequency': 0.15,
                'value_bet_sizing': 0.55,
                'thin_value_threshold': 0.65,
                'check_call_frequency': 0.45,
                'position_advantage': 'low_postflop'
            }
        
        # Street-specific postflop adjustments
        if street in ['flop', 'turn', 'river']:
            if street == 'flop':
                strategy['donk_bet_frequency'] = 0.15  # Occasional donk bets
                strategy['check_raise_frequency'] = 0.20
            elif street == 'turn':
                strategy['check_raise_frequency'] = 0.15
                strategy['give_up_frequency'] = 0.50
            elif street == 'river':
                strategy['check_raise_frequency'] = 0.10
                strategy['river_bluff_frequency'] = 0.10
        
        return strategy

    def _apply_universal_adjustments(self, strategy, street, active_opponents, stack_depth_bb):
        """Apply adjustments that affect all positions."""
        
        # Stack depth adjustments
        if stack_depth_bb > 150:  # Deep stacks
            strategy['aggression_multiplier'] *= 1.05
            strategy['bluff_frequency'] = min(0.5, strategy['bluff_frequency'] * 1.1)
        elif stack_depth_bb < 50:  # Short stacks
            strategy['aggression_multiplier'] *= 1.15
            strategy['bluff_frequency'] *= 0.8
            strategy['value_bet_sizing'] = min(1.0, strategy.get('value_bet_sizing', 0.65) * 1.2)
        
        # Multiway adjustments
        if active_opponents > 2:
            strategy['aggression_multiplier'] *= 0.85
            strategy['bluff_frequency'] *= 0.75
            if 'thin_value_threshold' in strategy:
                strategy['thin_value_threshold'] += 0.05
        
        # Late street adjustments
        if street == 'river':
            # River is more polarized
            strategy['bluff_frequency'] = min(0.4, strategy.get('bluff_frequency', 0.25) * 1.2)
            strategy['value_bet_sizing'] = min(0.9, strategy.get('value_bet_sizing', 0.65) * 1.1)
        
        return strategy

    def get_position_based_calling_strategy(self, position, street, hand_strength, bet_size,
                                          pot_size, opponent_position=None):
        """
        Get position-based calling strategy against bets.
        
        Args:
            position: Our position
            street: Current street
            hand_strength: Our hand strength
            bet_size: Size of bet we're facing
            pot_size: Current pot size
            opponent_position: Position of betting opponent
            
        Returns:
            dict: Calling strategy recommendations
        """
        try:
            bet_to_pot_ratio = bet_size / pot_size if pot_size > 0 else 1.0
            position_category = self._get_position_category(position)
            
            # Base calling thresholds by position
            base_thresholds = {
                'late': 0.45,    # Can call wider in position
                'middle': 0.50,  # Standard calling threshold
                'early': 0.55,   # Need stronger hands out of position
                'blind': 0.52    # Slightly wider due to pot odds from blinds
            }
            
            calling_threshold = base_thresholds.get(position_category, 0.50)
            
            # Adjust for bet sizing
            if bet_to_pot_ratio > 1.0:  # Large bet/overbet
                calling_threshold += 0.08
            elif bet_to_pot_ratio < 0.4:  # Small bet
                calling_threshold -= 0.05
            elif bet_to_pot_ratio < 0.6:  # Medium bet
                calling_threshold -= 0.02
            
            # Position vs position adjustments
            if opponent_position:
                opponent_category = self._get_position_category(opponent_position)
                
                # Calling wider against early position (likely stronger range)
                if opponent_category == 'early':
                    calling_threshold += 0.03
                # Calling tighter against late position (wider range)
                elif opponent_category == 'late':
                    calling_threshold -= 0.02
            
            # Street adjustments
            if street == 'river':
                # River calls need to be more precise
                calling_threshold += 0.03
            elif street == 'flop':
                # Can call wider on flop with implied odds
                calling_threshold -= 0.02
            
            # Hand strength category adjustments
            if hand_strength in ['strong', 'very_strong']:
                calling_threshold -= 0.05  # More likely to call with strong hands
            elif hand_strength in ['weak_made', 'drawing']:
                calling_threshold += 0.03  # Need better odds with weak hands
            
            return {
                'calling_threshold': calling_threshold,
                'pot_odds_adjustment': max(0.0, calling_threshold - 0.45),
                'position_advantage': self.position_power.get(position, 5),
                'reasoning': f'pos_{position}_vs_{opponent_position}_street_{street}_bet_{bet_to_pot_ratio:.2f}'
            }
            
        except Exception as e:
            logger.warning(f"Error in position-based calling strategy: {e}")
            return {
                'calling_threshold': 0.50,
                'pot_odds_adjustment': 0.0,
                'position_advantage': 5,
                'reasoning': 'fallback_calling_strategy'
            }

    def get_steal_attempt_strategy(self, position, stack_depth_bb, opponents_left,
                                 fold_equity_estimate=None):
        """
        Get strategy for steal attempts from various positions.
        
        Args:
            position: Our position
            stack_depth_bb: Stack depth in big blinds
            opponents_left: Number of opponents left to act
            fold_equity_estimate: Estimated fold equity
            
        Returns:
            dict: Steal attempt strategy
        """
        try:
            position_category = self._get_position_category(position)
            
            # Base steal frequencies by position
            base_steal_frequencies = {
                'BTN': 0.50,
                'CO': 0.40,
                'HJ': 0.25,
                'LJ': 0.15,
                'MP+1': 0.10,
                'MP': 0.05,
                'UTG+1': 0.02,
                'UTG': 0.01,
                'SB': 0.35,  # SB vs BB only
                'BB': 0.05   # Rare BB steals
            }
            
            steal_frequency = base_steal_frequencies.get(position, 0.10)
            
            # Adjust for number of opponents
            if opponents_left == 1:  # Only one opponent (e.g., SB vs BB)
                steal_frequency *= 1.3
            elif opponents_left == 2:  # Two opponents
                steal_frequency *= 1.0
            else:  # More opponents
                steal_frequency *= max(0.3, 1.0 - (opponents_left - 2) * 0.2)
            
            # Stack depth adjustments
            if stack_depth_bb > 100:  # Deep stacks
                steal_frequency *= 1.1  # More stealing with deep stacks
            elif stack_depth_bb < 30:  # Short stacks
                steal_frequency *= 0.7  # Less stealing, more push/fold
            
            # Fold equity adjustments
            if fold_equity_estimate:
                if fold_equity_estimate > 0.6:
                    steal_frequency *= 1.2
                elif fold_equity_estimate < 0.4:
                    steal_frequency *= 0.8
            
            # Sizing for steals
            if position == 'SB':
                steal_sizing = 3.0  # 3x BB from SB
            elif position in ['BTN', 'CO']:
                steal_sizing = 2.5  # 2.5x BB from late position
            else:
                steal_sizing = 3.0  # 3x BB from other positions
            
            return {
                'steal_frequency': min(0.8, steal_frequency),
                'steal_sizing_bb': steal_sizing,
                'hand_range_expansion': steal_frequency * 2,  # Wider range with higher frequency
                'reasoning': f'steal_{position}_opps_{opponents_left}_stacks_{stack_depth_bb:.0f}bb'
            }
            
        except Exception as e:
            logger.warning(f"Error in steal attempt strategy: {e}")
            return {
                'steal_frequency': 0.20,
                'steal_sizing_bb': 2.5,
                'hand_range_expansion': 0.40,
                'reasoning': 'fallback_steal_strategy'
            }

    def _get_default_strategy(self):
        """Fallback strategy when errors occur."""
        return {
            'aggression_multiplier': 1.0,
            'bluff_frequency': 0.25,
            'value_bet_sizing': 0.65,
            'thin_value_threshold': 0.55,
            'steal_frequency': 0.25,
            'position_advantage': 'medium',
            'reasoning': 'default_fallback_strategy'
        }

# Global instance
advanced_position_strategy = AdvancedPositionStrategy()

def get_position_strategy(position, street, hand_strength, board_texture=None,
                         active_opponents=1, stack_depth_bb=100):
    """
    Convenience function to get position-based strategy.
    
    Args:
        position: Player position
        street: Current street
        hand_strength: Hand strength classification
        board_texture: Board texture analysis (optional)
        active_opponents: Number of active opponents
        stack_depth_bb: Stack depth in big blinds
        
    Returns:
        dict: Position-based strategy recommendations
    """
    return advanced_position_strategy.get_positional_betting_strategy(
        position, street, hand_strength, board_texture, active_opponents, stack_depth_bb
    )
