# enhanced_drawing_analysis.py
"""
Enhanced drawing hand analysis that provides better decision making
for draws and semi-bluffs. Addresses the late drawing analysis issue.
"""

import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

class EnhancedDrawingAnalysis:
    """Enhanced analysis for drawing hands and semi-bluffs."""
    
    def __init__(self):
        # Minimum equity requirements by street
        self.min_equity_requirements = {
            'flop': {
                'drawing': 0.25,      # Need 25%+ to continue on flop
                'semi_bluff': 0.35,   # Need 35%+ to semi-bluff
                'call_large_bet': 0.40  # Need 40%+ for large bets
            },
            'turn': {
                'drawing': 0.30,      # Higher requirement on turn
                'semi_bluff': 0.40,
                'call_large_bet': 0.45
            },
            'river': {
                'drawing': 0.45,      # Must have made hand on river
                'semi_bluff': 0.45,   # No bluffs without showdown value
                'call_large_bet': 0.50
            }
        }
        
        # Outs estimation (simplified)
        self.draw_types = {
            'flush_draw': 9,
            'open_straight': 8,
            'gutshot': 4,
            'two_overcards': 6,
            'combo_draw': 12  # Flush + straight draw
        }
    
    def analyze_drawing_hand(
        self,
        hand: List[str],
        community_cards: List[str],
        win_probability: float,
        pot_size: float,
        bet_to_call: float,
        my_stack: float,
        opponent_stack: float,
        street: str,
        position: str = 'BB',
        opponent_count: int = 1
    ) -> Dict[str, any]:
        """
        Comprehensive drawing hand analysis.
        
        Returns detailed analysis including:
        - Whether to call/bet/fold
        - Reasoning
        - Implied odds consideration
        - Semi-bluff potential
        """
        
        logger.debug(f"Drawing analysis: street={street}, win_prob={win_probability:.1%}, "
                    f"pot={pot_size:.2f}, bet={bet_to_call:.2f}")
        
        # Calculate basic pot odds
        pot_odds = bet_to_call / (pot_size + bet_to_call) if (pot_size + bet_to_call) > 0 else 0
        
        # Estimate draw type and outs
        draw_info = self._estimate_draw_strength(hand, community_cards, win_probability, street)
        
        # Calculate implied odds
        implied_odds = self._calculate_implied_odds(
            pot_size, bet_to_call, my_stack, opponent_stack, 
            draw_info['outs'], street, position
        )
        
        # Get equity requirements
        equity_reqs = self.min_equity_requirements.get(street, self.min_equity_requirements['flop'])
        
        # Main decision logic
        decision = self._make_drawing_decision(
            win_probability=win_probability,
            pot_odds=pot_odds,
            implied_odds=implied_odds,
            equity_requirements=equity_reqs,
            draw_info=draw_info,
            bet_to_call=bet_to_call,
            pot_size=pot_size,
            street=street,
            opponent_count=opponent_count
        )
        
        return {
            'should_call': decision['action'] == 'call',
            'should_bet': decision['action'] == 'bet',
            'should_fold': decision['action'] == 'fold',
            'reasoning': decision['reasoning'],
            'outs': draw_info['outs'],
            'draw_type': draw_info['type'],
            'pot_odds': pot_odds,
            'implied_odds': implied_odds,
            'equity_needed': pot_odds,
            'equity_have': win_probability,
            'semi_bluff_potential': draw_info['semi_bluff_potential']
        }
    
    def _estimate_draw_strength(
        self, 
        hand: List[str], 
        community_cards: List[str], 
        win_probability: float,
        street: str
    ) -> Dict[str, any]:
        """Estimate the type and strength of draw."""
        
        # Basic estimation based on win probability and street
        if street == 'flop':
            if win_probability >= 0.45:
                return {
                    'type': 'combo_draw',
                    'outs': 12,
                    'strength': 'very_strong',
                    'semi_bluff_potential': 'high'
                }
            elif win_probability >= 0.35:
                return {
                    'type': 'flush_draw',
                    'outs': 9,
                    'strength': 'strong',
                    'semi_bluff_potential': 'medium'
                }
            elif win_probability >= 0.25:
                return {
                    'type': 'open_straight',
                    'outs': 8,
                    'strength': 'medium',
                    'semi_bluff_potential': 'medium'
                }
            elif win_probability >= 0.20:
                return {
                    'type': 'gutshot',
                    'outs': 4,
                    'strength': 'weak',
                    'semi_bluff_potential': 'low'
                }
        
        elif street == 'turn':
            # Adjust outs estimate for turn
            if win_probability >= 0.40:
                return {
                    'type': 'strong_draw',
                    'outs': 9,
                    'strength': 'strong',
                    'semi_bluff_potential': 'high'
                }
            elif win_probability >= 0.25:
                return {
                    'type': 'medium_draw',
                    'outs': 6,
                    'strength': 'medium',
                    'semi_bluff_potential': 'medium'
                }
        
        # Default weak draw
        return {
            'type': 'weak_draw',
            'outs': 3,
            'strength': 'weak',
            'semi_bluff_potential': 'low'
        }
    
    def _calculate_implied_odds(
        self,
        pot_size: float,
        bet_to_call: float,
        my_stack: float,
        opponent_stack: float,
        outs: int,
        street: str,
        position: str
    ) -> float:
        """Calculate implied odds for drawing hands."""
        
        # Estimate additional money we can win if we hit
        if street == 'flop':
            # Two streets left - more implied odds potential
            potential_additional = min(opponent_stack, my_stack) * 0.3
        elif street == 'turn':
            # One street left - less implied odds
            potential_additional = min(opponent_stack, my_stack) * 0.15
        else:
            # River - no implied odds
            potential_additional = 0
        
        # Adjust for position (better position = better implied odds)
        if position in ['BTN', 'CO']:
            potential_additional *= 1.2
        elif position in ['UTG', 'MP']:
            potential_additional *= 0.8
        
        # Adjust for outs (more outs = better implied odds due to disguise)
        if outs >= 9:
            potential_additional *= 1.1
        elif outs <= 4:
            potential_additional *= 0.8
        
        # Calculate total potential pot
        total_potential_pot = pot_size + bet_to_call + potential_additional
        
        # Implied odds = bet to call / total potential pot
        implied_odds = bet_to_call / total_potential_pot if total_potential_pot > 0 else 1.0
        
        return implied_odds
    
    def _make_drawing_decision(
        self,
        win_probability: float,
        pot_odds: float,
        implied_odds: float,
        equity_requirements: Dict[str, float],
        draw_info: Dict[str, any],
        bet_to_call: float,
        pot_size: float,
        street: str,
        opponent_count: int
    ) -> Dict[str, str]:
        """Make the final decision for drawing hands."""
        
        # Check minimum equity requirement
        min_equity = equity_requirements['drawing']
        if win_probability < min_equity:
            return {
                'action': 'fold',
                'reasoning': f'Insufficient equity: {win_probability:.1%} < {min_equity:.1%} required'
            }
        
        # Check if we have proper odds (using implied odds)
        if win_probability > implied_odds:
            # We have good implied odds
            if draw_info['strength'] in ['very_strong', 'strong']:
                return {
                    'action': 'call',
                    'reasoning': f'Good implied odds: {win_probability:.1%} > {implied_odds:.1%}, strong draw'
                }
            elif draw_info['strength'] == 'medium' and opponent_count <= 2:
                return {
                    'action': 'call',
                    'reasoning': f'Good implied odds with medium draw heads-up/3-way'
                }
        
        # Check direct pot odds
        if win_probability > pot_odds:
            return {
                'action': 'call',
                'reasoning': f'Good direct pot odds: {win_probability:.1%} > {pot_odds:.1%}'
            }
        
        # Check for semi-bluff potential (when bet_to_call is 0, meaning we can bet)
        if bet_to_call == 0 and draw_info['semi_bluff_potential'] in ['high', 'medium']:
            semi_bluff_equity = equity_requirements['semi_bluff']
            if win_probability >= semi_bluff_equity and opponent_count <= 2:
                return {
                    'action': 'bet',
                    'reasoning': f'Semi-bluff opportunity: {win_probability:.1%} equity with {draw_info["type"]}'
                }
        
        # Check for large bet situations
        bet_size_ratio = bet_to_call / pot_size if pot_size > 0 else 1
        if bet_size_ratio > 0.6:  # Large bet
            large_bet_equity = equity_requirements['call_large_bet']
            if win_probability < large_bet_equity:
                return {
                    'action': 'fold',
                    'reasoning': f'Large bet, insufficient equity: {win_probability:.1%} < {large_bet_equity:.1%}'
                }
        
        # Multiway considerations
        if opponent_count >= 3:
            # Need better equity in multiway pots
            multiway_requirement = min_equity * 1.2
            if win_probability < multiway_requirement:
                return {
                    'action': 'fold',
                    'reasoning': f'Multiway pot, need {multiway_requirement:.1%}+, have {win_probability:.1%}'
                }
        
        # Default to fold if none of the above conditions met
        return {
            'action': 'fold',
            'reasoning': f'No profitable continuation: pot_odds={pot_odds:.1%}, implied_odds={implied_odds:.1%}, equity={win_probability:.1%}'
        }
    
    def should_semi_bluff(
        self,
        win_probability: float,
        pot_size: float,
        my_stack: float,
        street: str,
        position: str,
        board_texture: str,
        opponent_analysis: Dict[str, any]
    ) -> Tuple[bool, str, float]:
        """
        Determine if we should semi-bluff with a drawing hand.
        
        Returns:
            (should_semi_bluff, reasoning, bet_size_fraction)
        """
        
        # Don't semi-bluff on river (no more cards)
        if street == 'river':
            return False, "No semi-bluffs on river", 0
        
        # Need minimum equity for semi-bluff
        min_equity = self.min_equity_requirements[street]['semi_bluff']
        if win_probability < min_equity:
            return False, f"Insufficient equity for semi-bluff: {win_probability:.1%}", 0
        
        # Get fold equity estimate
        fold_equity = opponent_analysis.get('fold_equity_estimate', 0.5)
        
        # Calculate total equity (win probability + fold equity)
        # Simplified: assume fold equity and showdown equity are independent
        total_equity = win_probability + (fold_equity * (1 - win_probability))
        
        # Need total equity > 50% for profitable semi-bluff
        if total_equity < 0.5:
            return False, f"Insufficient total equity: {total_equity:.1%}", 0
        
        # Position considerations
        if position in ['UTG', 'MP'] and opponent_analysis.get('tracked_count', 0) == 0:
            # Early position vs unknown opponents - be more cautious
            if total_equity < 0.55:
                return False, "Early position vs unknowns, need higher equity", 0
        
        # Board texture considerations
        bet_size_fraction = 0.6  # Default semi-bluff size
        
        if board_texture in ['very_wet', 'wet']:
            # Larger semi-bluffs on wet boards
            bet_size_fraction = 0.75
            reasoning = f"Semi-bluff on wet board: {total_equity:.1%} total equity"
        elif board_texture in ['very_dry', 'dry']:
            # Smaller semi-bluffs on dry boards
            bet_size_fraction = 0.45
            reasoning = f"Small semi-bluff on dry board: {total_equity:.1%} total equity"
        else:
            reasoning = f"Standard semi-bluff: {total_equity:.1%} total equity"
        
        return True, reasoning, bet_size_fraction

# Global instance
drawing_analyzer = EnhancedDrawingAnalysis()

def analyze_drawing_hand_enhanced(
    hand: List[str],
    community_cards: List[str],
    win_probability: float,
    pot_size: float,
    bet_to_call: float,
    my_stack: float,
    opponent_stack: float,
    street: str,
    position: str = 'BB',
    opponent_count: int = 1
) -> Dict[str, any]:
    """Enhanced drawing hand analysis function."""
    return drawing_analyzer.analyze_drawing_hand(
        hand, community_cards, win_probability, pot_size, bet_to_call,
        my_stack, opponent_stack, street, position, opponent_count
    )

def should_semi_bluff_enhanced(
    win_probability: float,
    pot_size: float,
    my_stack: float,
    street: str,
    position: str,
    board_texture: str,
    opponent_analysis: Dict[str, any]
) -> Tuple[bool, str, float]:
    """Enhanced semi-bluff analysis function."""
    return drawing_analyzer.should_semi_bluff(
        win_probability, pot_size, my_stack, street, position, board_texture, opponent_analysis
    )
