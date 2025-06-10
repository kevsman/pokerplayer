# enhanced_spr_strategy.py
"""
Enhanced Stack-to-Pot Ratio (SPR) strategy system that provides
clear guidelines for different SPR scenarios and hand strengths.
"""

import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)

class EnhancedSPRStrategy:
    """Enhanced SPR-based strategy recommendations."""
    
    def __init__(self):
        # SPR thresholds and corresponding strategies
        self.spr_categories = {
            'very_low': (0, 1),      # 0-1 SPR: All-in or fold
            'low': (1, 3),           # 1-3 SPR: Commit or fold
            'medium': (3, 6),        # 3-6 SPR: Standard play
            'high': (6, 12),         # 6-12 SPR: Pot control focus
            'very_high': (12, 25),   # 12-25 SPR: Extreme pot control
            'massive': (25, float('inf'))  # 25+ SPR: Play for implied odds
        }
        
        # Hand strength recommendations by SPR category
        self.spr_strategies = {
            'very_low': {
                'very_strong': 'push_all_in',
                'strong': 'push_all_in',
                'medium': 'call_if_committed_fold_otherwise',
                'weak_made': 'fold_to_aggression',
                'weak': 'fold'
            },
            'low': {
                'very_strong': 'commit_and_build_pot',
                'strong': 'commit_and_build_pot',
                'medium': 'play_carefully_fold_to_big_bets',
                'weak_made': 'fold_to_aggression',
                'weak': 'fold_or_small_bluff'
            },
            'medium': {
                'very_strong': 'value_bet_build_pot',
                'strong': 'value_bet_standard',
                'medium': 'thin_value_or_pot_control',
                'weak_made': 'pot_control_check_call',
                'weak': 'bluff_with_equity_fold_without'
            },
            'high': {
                'very_strong': 'extract_value_carefully',
                'strong': 'pot_control_value_bet',
                'medium': 'pot_control_check_behind',
                'weak_made': 'check_fold',
                'weak': 'check_fold_or_small_bluff'
            },
            'very_high': {
                'very_strong': 'small_value_bets',
                'strong': 'pot_control_small_bets',
                'medium': 'check_behind_pot_control',
                'weak_made': 'check_fold',
                'weak': 'check_fold'
            },
            'massive': {
                'very_strong': 'implied_odds_play',
                'strong': 'check_call_implied_odds',
                'medium': 'check_fold_no_value',
                'weak_made': 'check_fold',
                'weak': 'fold_or_bluff_with_nuts_potential'
            }
        }
        
        # Betting size adjustments by SPR
        self.spr_bet_size_adjustments = {
            'very_low': 1.0,    # Standard sizing (going all-in anyway)
            'low': 1.1,         # Slightly larger to commit
            'medium': 1.0,      # Standard sizing
            'high': 0.8,        # Smaller for pot control
            'very_high': 0.6,   # Much smaller
            'massive': 0.4      # Very small
        }
    
    def get_spr_strategy(
        self,
        spr: float,
        hand_strength: str,
        street: str = 'flop',
        position: str = 'BB',
        opponent_count: int = 1,
        board_texture: str = 'moderate'
    ) -> Dict[str, str]:
        """
        Get comprehensive SPR-based strategy recommendation.
        
        Returns:
            Dictionary with strategy recommendations
        """
        
        # Categorize SPR
        spr_category = self._categorize_spr(spr)
        
        # Get base strategy
        base_strategy = self.spr_strategies[spr_category].get(
            hand_strength, 
            self.spr_strategies[spr_category]['weak']
        )
        
        # Get detailed recommendations
        strategy = {
            'spr': spr,
            'spr_category': spr_category,
            'base_strategy': base_strategy,
            'betting_action': self._get_betting_action(base_strategy),
            'sizing_adjustment': self.spr_bet_size_adjustments[spr_category],
            'reasoning': self._get_strategy_reasoning(spr_category, hand_strength, base_strategy)
        }
        
        # Add specific adjustments
        strategy.update(self._get_specific_adjustments(
            spr_category, hand_strength, street, position, opponent_count, board_texture
        ))
        
        logger.debug(f"SPR strategy: SPR={spr:.1f} ({spr_category}), "
                    f"hand={hand_strength}, action={strategy['betting_action']}")
        
        return strategy
    
    def _categorize_spr(self, spr: float) -> str:
        """Categorize SPR into strategic ranges."""
        for category, (min_spr, max_spr) in self.spr_categories.items():
            if min_spr <= spr < max_spr:
                return category
        return 'massive'
    
    def _get_betting_action(self, base_strategy: str) -> str:
        """Convert strategy to specific betting action."""
        action_mapping = {
            'push_all_in': 'bet_all_in',
            'commit_and_build_pot': 'bet_large',
            'value_bet_build_pot': 'bet_value',
            'value_bet_standard': 'bet_value',
            'thin_value_or_pot_control': 'bet_small_or_check',
            'pot_control_value_bet': 'bet_small',
            'pot_control_check_call': 'check_call',
            'extract_value_carefully': 'bet_small',
            'pot_control_small_bets': 'bet_very_small',
            'small_value_bets': 'bet_very_small',
            'pot_control_check_behind': 'check',
            'check_behind_pot_control': 'check',
            'implied_odds_play': 'check_call',
            'check_call_implied_odds': 'check_call',
            'play_carefully_fold_to_big_bets': 'check_call_small',
            'call_if_committed_fold_otherwise': 'check_call_committed',
            'check_fold_no_value': 'check_fold',
            'check_fold': 'check_fold',
            'fold_to_aggression': 'fold_to_bets',
            'fold': 'fold',
            'bluff_with_equity_fold_without': 'selective_bluff',
            'fold_or_small_bluff': 'fold_or_bluff',
            'check_fold_or_small_bluff': 'check_fold_or_bluff',
            'fold_or_bluff_with_nuts_potential': 'fold_or_nut_bluff'
        }
        
        return action_mapping.get(base_strategy, 'check')
    
    def _get_strategy_reasoning(self, spr_category: str, hand_strength: str, base_strategy: str) -> str:
        """Get human-readable reasoning for the strategy."""
        
        reasoning_templates = {
            'very_low': "Very low SPR ({}) - must commit or fold with {}",
            'low': "Low SPR ({}) - looking to commit with {} hands",
            'medium': "Medium SPR ({}) - standard play with {}",
            'high': "High SPR ({}) - pot control focus with {}",
            'very_high': "Very high SPR ({}) - extreme pot control with {}",
            'massive': "Massive SPR ({}) - implied odds play with {}"
        }
        
        template = reasoning_templates.get(spr_category, "SPR {} strategy with {}")
        return template.format(spr_category, hand_strength)
    
    def _get_specific_adjustments(
        self,
        spr_category: str,
        hand_strength: str,
        street: str,
        position: str,
        opponent_count: int,
        board_texture: str
    ) -> Dict[str, str]:
        """Get specific adjustments for the situation."""
        
        adjustments = {}
        
        # Multiway adjustments
        if opponent_count > 1:
            if spr_category in ['very_low', 'low']:
                adjustments['multiway'] = 'even_more_selective'
            else:
                adjustments['multiway'] = 'check_more_pot_control'
        
        # Position adjustments
        if position in ['BTN', 'CO']:  # Late position
            if spr_category == 'high' and hand_strength in ['medium', 'weak_made']:
                adjustments['position'] = 'check_behind_for_pot_control'
        elif position in ['UTG', 'MP']:  # Early position
            if spr_category == 'medium' and hand_strength == 'medium':
                adjustments['position'] = 'check_more_often'
        
        # Board texture adjustments
        if board_texture in ['very_wet', 'wet']:
            if spr_category in ['high', 'very_high'] and hand_strength in ['medium', 'weak_made']:
                adjustments['board'] = 'even_more_pot_control_wet_board'
        elif board_texture in ['very_dry', 'dry']:
            if spr_category == 'medium' and hand_strength == 'strong':
                adjustments['board'] = 'can_bet_larger_dry_board'
        
        # Street-specific adjustments
        if street == 'river':
            if spr_category in ['high', 'very_high']:
                adjustments['street'] = 'check_most_marginal_hands'
        elif street == 'flop':
            if spr_category == 'low' and hand_strength in ['strong', 'very_strong']:
                adjustments['street'] = 'build_pot_early'
        
        return adjustments
    
    def should_commit_stack(
        self,
        spr: float,
        hand_strength: str,
        pot_commitment_ratio: float,
        street: str = 'flop'
    ) -> Tuple[bool, str]:
        """Determine if we should commit our stack."""
        
        spr_category = self._categorize_spr(spr)
        
        # Very low SPR - almost always commit with any reasonable hand
        if spr_category == 'very_low':
            if hand_strength in ['very_strong', 'strong', 'medium']:
                return True, f"Very low SPR ({spr:.1f}) - commit with {hand_strength}"
            elif pot_commitment_ratio > 0.4:
                return True, f"Already pot committed ({pot_commitment_ratio:.1%})"
            else:
                return False, "Weak hand at very low SPR"
        
        # Low SPR - commit with strong hands
        elif spr_category == 'low':
            if hand_strength in ['very_strong', 'strong']:
                return True, f"Low SPR ({spr:.1f}) - commit with {hand_strength}"
            elif hand_strength == 'medium' and pot_commitment_ratio > 0.3:
                return True, f"Medium hand with commitment ({pot_commitment_ratio:.1%})"
            else:
                return False, f"Not strong enough for low SPR commitment"
        
        # Medium+ SPR - only commit with very strong hands
        else:
            if hand_strength == 'very_strong':
                return True, f"Very strong hand - can commit at any SPR"
            elif hand_strength == 'strong' and spr <= 6:
                return True, f"Strong hand at reasonable SPR ({spr:.1f})"
            elif pot_commitment_ratio > 0.6:
                return True, f"Already heavily committed ({pot_commitment_ratio:.1%})"
            else:
                return False, f"SPR too high ({spr:.1f}) for stack commitment"
    
    def get_protection_needs(
        self,
        spr: float,
        hand_strength: str,
        board_texture: str,
        opponent_count: int
    ) -> Tuple[str, str]:
        """Determine protection needs based on SPR and situation."""
        
        spr_category = self._categorize_spr(spr)
        
        # Low SPR - less protection needed (fewer cards to come relatively)
        if spr_category in ['very_low', 'low']:
            if hand_strength in ['very_strong', 'strong']:
                return 'high', "Strong hand at low SPR - build pot aggressively"
            else:
                return 'low', "Weak hand at low SPR - check/fold"
        
        # Medium SPR - standard protection needs
        elif spr_category == 'medium':
            if board_texture in ['very_wet', 'wet'] and opponent_count > 1:
                return 'high', "Wet board multiway - need protection"
            elif hand_strength in ['very_strong', 'strong']:
                return 'medium', "Strong hand - balanced approach"
            else:
                return 'low', "Weak hand - pot control"
        
        # High SPR - protection less important, pot control key
        else:
            if hand_strength == 'very_strong' and board_texture in ['very_wet', 'wet']:
                return 'medium', "Very strong hand on wet board - some protection"
            else:
                return 'low', "High SPR - pot control over protection"

# Create global instance
spr_strategy = EnhancedSPRStrategy()

def get_spr_strategy_recommendation(
    spr: float,
    hand_strength: str,
    street: str = 'flop',
    position: str = 'BB',
    opponent_count: int = 1,
    board_texture: str = 'moderate'
) -> Dict[str, str]:
    """Get SPR-based strategy recommendation."""
    return spr_strategy.get_spr_strategy(
        spr, hand_strength, street, position, opponent_count, board_texture
    )

def should_commit_stack_spr(
    spr: float,
    hand_strength: str,
    pot_commitment_ratio: float,
    street: str = 'flop'
) -> Tuple[bool, str]:
    """Determine if stack commitment is appropriate based on SPR."""
    return spr_strategy.should_commit_stack(spr, hand_strength, pot_commitment_ratio, street)

def get_protection_needs_spr(
    spr: float,
    hand_strength: str,
    board_texture: str,
    opponent_count: int
) -> Tuple[str, str]:
    """Get protection needs based on SPR analysis."""
    return spr_strategy.get_protection_needs(spr, hand_strength, board_texture, opponent_count)
