# enhanced_board_analysis.py
"""
Enhanced board texture analysis for more sophisticated postflop decisions.
Analyzes board wetness, draw potential, and strategic implications.
"""

import logging
from typing import List, Dict, Tuple, Optional
from collections import Counter
import itertools

logger = logging.getLogger(__name__)

class BoardTexture:
    """Comprehensive board texture analysis."""
    
    def __init__(self, community_cards: List[str]):
        self.cards = community_cards
        self.num_cards = len(community_cards)
        self.suits = [card[-1] for card in community_cards if len(card) >= 2]
        self.ranks = [card[:-1] for card in community_cards if len(card) >= 2]
        # Convert face cards to numbers for analysis
        self.rank_values = []
        for rank in self.ranks:
            if rank == 'A':
                self.rank_values.append(14)
            elif rank == 'K':
                self.rank_values.append(13)
            elif rank == 'Q':
                self.rank_values.append(12)
            elif rank == 'J':
                self.rank_values.append(11)
            elif rank == 'T':
                self.rank_values.append(10)
            else:
                try:
                    self.rank_values.append(int(rank))
                except ValueError:
                    # Skip invalid ranks
                    continue
    
    def get_texture_type(self) -> str:
        """Get overall board texture classification."""
        if self.num_cards < 3:
            return "preflop"
        
        wetness_score = self._calculate_wetness_score()
        
        if wetness_score >= 8:
            return "very_wet"
        elif wetness_score >= 6:
            return "wet"
        elif wetness_score >= 4:
            return "semi_wet"
        elif wetness_score >= 2:
            return "dry"
        else:
            return "very_dry"
    
    def _calculate_wetness_score(self) -> int:
        """Calculate board wetness score (0-10 scale)."""
        score = 0
        
        # Flush draws
        if self._has_flush_draw():
            score += 3
        elif self._has_backdoor_flush_draw():
            score += 1
        
        # Straight draws
        straight_info = self._analyze_straight_draws()
        if straight_info['open_ended']:
            score += 3
        elif straight_info['gutshot']:
            score += 2
        elif straight_info['backdoor_straight']:
            score += 1
        
        # Pairs on board
        if self._has_pair():
            score += 1
        
        # High cards
        high_cards = sum(1 for rank in self.rank_values if rank >= 10)
        score += min(high_cards, 2)  # Max 2 points for high cards
        
        # Connected ranks
        if self._has_connected_ranks():
            score += 1
        
        return min(score, 10)  # Cap at 10
    
    def _has_flush_draw(self) -> bool:
        """Check for flush draw (3+ of same suit)."""
        if self.num_cards < 3 or not self.suits:
            return False
        suit_counts = Counter(self.suits)
        if not suit_counts:
            return False
        return max(suit_counts.values()) >= 3
    
    def _has_backdoor_flush_draw(self) -> bool:
        """Check for backdoor flush draw (2 of same suit on flop)."""
        if self.num_cards != 3 or not self.suits:
            return False
        suit_counts = Counter(self.suits)
        if not suit_counts:
            return False
        return max(suit_counts.values()) >= 2
    
    def _analyze_straight_draws(self) -> Dict[str, bool]:
        """Analyze potential straight draws."""
        if self.num_cards < 3:
            return {'open_ended': False, 'gutshot': False, 'backdoor_straight': False}
        
        sorted_ranks = sorted(set(self.rank_values))
        
        # Check for open-ended straight draw
        open_ended = self._has_open_ended_draw(sorted_ranks)
        
        # Check for gutshot
        gutshot = self._has_gutshot_draw(sorted_ranks)
        
        # Check for backdoor straight
        backdoor = self._has_backdoor_straight_draw(sorted_ranks)
        
        return {
            'open_ended': open_ended,
            'gutshot': gutshot,
            'backdoor_straight': backdoor
        }
    
    def _has_open_ended_draw(self, ranks: List[int]) -> bool:
        """Check for open-ended straight draw."""
        if len(ranks) < 3:
            return False
        
        # Check all possible 4-card sequences that could be completed
        for i in range(len(ranks) - 2):
            if ranks[i+2] - ranks[i] <= 4:  # Within straight range
                return True
        return False
    
    def _has_gutshot_draw(self, ranks: List[int]) -> bool:
        """Check for gutshot straight draw."""
        if len(ranks) < 3:
            return False
        
        # Look for ranks with gaps that could be filled
        for combo in itertools.combinations(ranks, min(3, len(ranks))):
            sorted_combo = sorted(combo)
            if len(sorted_combo) >= 3:
                span = sorted_combo[-1] - sorted_combo[0]
                if span == 4 and len(sorted_combo) == 3:
                    return True
        return False
    
    def _has_backdoor_straight_draw(self, ranks: List[int]) -> bool:
        """Check for backdoor straight draw (need 2 cards)."""
        if self.num_cards != 3 or not ranks:
            return False
        
        # Check if ranks could form part of a straight with 2 more cards
        for high in range(max(ranks) + 2, 15):  # Up to Ace
            for low in range(max(1, high - 4), high - 2):
                straight_ranks = set(range(low, high + 1))
                if len(set(ranks).intersection(straight_ranks)) >= 2:
                    return True
        return False
    
    def _has_pair(self) -> bool:
        """Check if board has a pair."""
        if not self.rank_values:
            return False
        rank_counts = Counter(self.rank_values)
        if not rank_counts:
            return False
        return max(rank_counts.values()) >= 2
    
    def _has_connected_ranks(self) -> bool:
        """Check for connected ranks (consecutive)."""
        if len(self.rank_values) < 2:
            return False
        
        sorted_ranks = sorted(self.rank_values)
        for i in range(len(sorted_ranks) - 1):
            if sorted_ranks[i+1] - sorted_ranks[i] == 1:
                return True
        return False
    
    def get_betting_implications(self) -> Dict[str, str]:
        """Get strategic implications for betting."""
        texture = self.get_texture_type()
        implications = {}
        
        if texture in ["very_wet", "wet"]:
            implications['protection'] = 'high_priority'
            implications['bluffing'] = 'many_semibluffs_available'
            implications['value_betting'] = 'bet_for_protection'
            implications['sizing'] = 'larger_sizes_for_protection'
        
        elif texture in ["dry", "very_dry"]:
            implications['protection'] = 'low_priority'
            implications['bluffing'] = 'pure_bluffs_needed'
            implications['value_betting'] = 'thin_value_possible'
            implications['sizing'] = 'smaller_sizes_extract_value'
        
        else:  # semi_wet
            implications['protection'] = 'moderate_priority'
            implications['bluffing'] = 'balanced_approach'
            implications['value_betting'] = 'standard_value'
            implications['sizing'] = 'standard_sizing'
        
        # Specific board features
        if self._has_flush_draw():
            implications['flush_draw'] = 'charge_draws'
        
        if self._analyze_straight_draws()['open_ended']:
            implications['straight_draw'] = 'charge_draws'
        
        if self._has_pair():
            implications['paired_board'] = 'value_bet_carefully'
        
        return implications
    
    def get_hand_strength_adjustments(self, hand_strength: str) -> Dict[str, float]:
        """Get hand strength adjustments based on board texture."""
        texture = self.get_texture_type()
        adjustments = {'equity_multiplier': 1.0, 'protection_urgency': 0.5}
        
        if texture in ["very_wet", "wet"]:
            # Strong hands need protection, weak hands lose value
            if hand_strength in ['very_strong', 'strong']:
                adjustments['equity_multiplier'] = 1.1
                adjustments['protection_urgency'] = 0.8
            elif hand_strength in ['weak_made', 'very_weak']:
                adjustments['equity_multiplier'] = 0.9
                adjustments['protection_urgency'] = 0.2
        
        elif texture in ["dry", "very_dry"]:
            # More time to realize equity, thin value more viable
            if hand_strength in ['medium', 'weak_made']:
                adjustments['equity_multiplier'] = 1.05
                adjustments['protection_urgency'] = 0.3
        
        return adjustments


class EnhancedBoardAnalyzer:
    """Main class for enhanced board analysis integration."""
    
    def __init__(self):
        self.texture_cache = {}
    
    def analyze_board(self, community_cards: List[str]) -> Dict:
        """Comprehensive board analysis."""
        try:
            # Create cache key
            cache_key = tuple(sorted(community_cards))
            
            if cache_key in self.texture_cache:
                return self.texture_cache[cache_key]
            
            # Analyze board texture
            texture = BoardTexture(community_cards)
            
            analysis = {
                'texture_type': texture.get_texture_type(),
                'wetness_score': texture._calculate_wetness_score(),
                'flush_draws': texture._has_flush_draw(),
                'has_flush_draw': texture._has_flush_draw(),
                'straight_draws': texture._analyze_straight_draws(),
                'pairs_on_board': texture._has_pair(),
                'has_pair': texture._has_pair(),
                'betting_implications': texture.get_betting_implications(),
                'num_cards': len(community_cards)
            }
            
            # Cache result
            self.texture_cache[cache_key] = analysis
            
            return analysis
            
        except Exception as e:
            logger.warning(f"Board analysis failed: {e}")
            return {
                'texture_type': 'unknown',
                'wetness_score': 5,
                'has_flush_draw': False,
                'straight_draws': {'open_ended': False, 'gutshot': False, 'backdoor_straight': False},
                'has_pair': False,
                'betting_implications': {'status': 'analysis_failed'},
                'num_cards': len(community_cards) if community_cards else 0
            }
    
    def get_bet_sizing_recommendation(self, board_analysis: Dict, hand_strength: str, pot_size: float) -> Dict:
        """Get bet sizing recommendation based on board texture."""
        implications = board_analysis.get('betting_implications', {})
        texture_type = board_analysis.get('texture_type', 'unknown')
        
        # Base sizing by hand strength
        base_sizes = {
            'very_strong': 0.75,
            'strong': 0.65,
            'medium': 0.50,
            'weak_made': 0.35
        }
        
        base_size = base_sizes.get(hand_strength, 0.50)
        
        # Adjust for board texture
        if texture_type in ['very_wet', 'wet']:
            if hand_strength in ['very_strong', 'strong']:
                adjusted_size = base_size * 1.2
                reasoning = 'protection_betting_wet_board'
            else:
                adjusted_size = base_size * 0.8
                reasoning = 'cautious_weak_hand_wet_board'
        
        elif texture_type in ['dry', 'very_dry']:
            if hand_strength == 'medium':
                adjusted_size = base_size * 0.8
                reasoning = 'thin_value_dry_board'
            else:
                adjusted_size = base_size
                reasoning = 'standard_sizing_dry_board'
        
        else:
            adjusted_size = base_size
            reasoning = 'standard_sizing'
        
        return {
            'size_fraction': adjusted_size,
            'bet_amount': pot_size * adjusted_size,
            'reasoning': reasoning,
            'board_texture': texture_type
        }
    
    def should_bet_for_protection(self, board_analysis: Dict, hand_strength: str, opponents_count: int) -> bool:
        """Determine if betting for protection is recommended."""
        if hand_strength not in ['very_strong', 'strong', 'medium']:
            return False
        
        wetness_score = board_analysis.get('wetness_score', 5)
        has_draws = (board_analysis.get('has_flush_draw', False) or 
                    board_analysis.get('straight_draws', {}).get('open_ended', False))
        
        # Strong hands on wet boards vs multiple opponents need protection
        if hand_strength in ['very_strong', 'strong'] and wetness_score >= 6:
            return True
        
        # Medium hands need protection on very wet boards vs few opponents
        if hand_strength == 'medium' and wetness_score >= 8 and opponents_count <= 2:
            return True
        
        return False


def integrate_board_analysis_with_postflop(community_cards: List[str], hand_strength: str, 
                                         pot_size: float, opponents_count: int) -> Dict:
    """Integration function for postflop decision logic."""
    try:
        analyzer = EnhancedBoardAnalyzer()
        board_analysis = analyzer.analyze_board(community_cards)
        
        # Get sizing recommendation
        sizing_rec = analyzer.get_bet_sizing_recommendation(board_analysis, hand_strength, pot_size)
        
        # Check protection needs
        needs_protection = analyzer.should_bet_for_protection(board_analysis, hand_strength, opponents_count)
        
        return {
            'board_analysis': board_analysis,
            'sizing_recommendation': sizing_rec,
            'needs_protection': needs_protection,
            'status': 'enhanced_board_analysis_active'
        }
        
    except Exception as e:
        logger.warning(f"Enhanced board analysis failed: {e}")
        return {
            'board_analysis': {'texture_type': 'unknown'},
            'sizing_recommendation': {'size_fraction': 0.5, 'reasoning': 'fallback_sizing'},
            'needs_protection': False,
            'status': 'fallback_to_basic_analysis'
        }


if __name__ == "__main__":
    # Example usage
    analyzer = EnhancedBoardAnalyzer()
    
    # Test wet board
    wet_board = ['A♠', 'K♠', '7♠']
    analysis = analyzer.analyze_board(wet_board)
    print(f"Wet board analysis: {analysis['texture_type']}")
    print(f"Betting implications: {analysis['betting_implications']}")
    
    # Test dry board
    dry_board = ['A♦', '7♣', '2♠']
    analysis = analyzer.analyze_board(dry_board)
    print(f"Dry board analysis: {analysis['texture_type']}")
    print(f"Betting implications: {analysis['betting_implications']}")
