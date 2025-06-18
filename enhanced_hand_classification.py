# enhanced_hand_classification.py
"""
Enhanced hand strength classification system with consistent and accurate categorization.
Addresses the inconsistent hand strength classification issues identified in the logs.
"""

import logging
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)

class EnhancedHandClassifier:
    """Provides consistent and accurate hand strength classification."""
    
    def __init__(self):
        # Define hand rank thresholds more precisely
        self.hand_rank_thresholds = {
            # Royal Flush = 10, Straight Flush = 9
            'very_strong': [10, 9, 8],  # Royal Flush, Straight Flush, Four of a Kind
            # Full House = 7, Flush = 6, Straight = 5
            'strong': [7, 6, 5],  # Full House, Flush, Straight
            # Three of a Kind = 4, Two Pair = 3
            'medium': [4, 3],  # Three of a Kind, Two Pair
            # One Pair = 2
            'weak_made': [2],  # One Pair
            # High Card = 1
            'weak': [1]  # High Card / Drawing hands
        }
          # Win probability thresholds for each street
        # Lowered thresholds to reduce fold frequency and allow more calls and raises
        self.win_prob_thresholds = {
            'flop': {
                'very_strong': 0.80, # Was 0.85
                'strong': 0.65, # Was 0.70
                'medium': 0.45, # Was 0.55
                'weak_made': 0.30, # Was 0.35
                'weak': 0.0
            },
            'turn': {
                'very_strong': 0.85, # Was 0.90
                'strong': 0.70, # Was 0.75
                'medium': 0.50, # Was 0.60
                'weak_made': 0.35, # Was 0.40
                'weak': 0.0
            },
            'river': {
                'very_strong': 0.90, # Was 0.95
                'strong': 0.75, # Was 0.80
                'medium': 0.55, # Was 0.65
                'weak_made': 0.40, # Was 0.45
                'weak': 0.0
            }
        }
    
    def classify_hand_strength(
        self, 
        numerical_hand_rank: int, 
        win_probability: float, 
        street: str = 'flop',
        board_texture: str = 'unknown'
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Classify hand strength consistently based on multiple factors.
        
        Returns:
            Tuple of (classification, details)
        """
        # Get thresholds for current street
        prob_thresholds = self.win_prob_thresholds.get(street, self.win_prob_thresholds['flop'])
        
        # Primary classification based on hand rank
        primary_classification = self._classify_by_rank(numerical_hand_rank)
        
        # Secondary check based on win probability
        prob_classification = self._classify_by_probability(win_probability, prob_thresholds)
        
        # Resolve conflicts between rank and probability
        final_classification = self._resolve_classification_conflict(
            primary_classification, 
            prob_classification, 
            numerical_hand_rank, 
            win_probability,
            street
        )
        
        # Board texture adjustments
        adjusted_classification = self._adjust_for_board_texture(
            final_classification, 
            board_texture, 
            numerical_hand_rank
        )
        
        # Generate detailed analysis
        details = {
            'numerical_rank': numerical_hand_rank,
            'win_probability': win_probability,
            'street': street,
            'board_texture': board_texture,
            'rank_classification': primary_classification,
            'probability_classification': prob_classification,
            'final_classification': adjusted_classification,
            'is_very_strong': adjusted_classification == 'very_strong',
            'is_strong': adjusted_classification == 'strong',
            'is_medium': adjusted_classification == 'medium',
            'is_weak_made': adjusted_classification == 'weak_made',
            'is_weak': adjusted_classification == 'weak'
        }
        
        logger.debug(f"Hand classification: rank={numerical_hand_rank}, win_prob={win_probability:.1%}, "
                    f"street={street}, final={adjusted_classification}")
        
        return adjusted_classification, details
    
    def _classify_by_rank(self, numerical_hand_rank: int) -> str:
        """Classify based on numerical hand rank."""
        for classification, ranks in self.hand_rank_thresholds.items():
            if numerical_hand_rank in ranks:
                return classification
        return 'weak'
    
    def _classify_by_probability(self, win_probability: float, thresholds: Dict[str, float]) -> str:
        """Classify based on win probability."""
        if win_probability >= thresholds['very_strong']:
            return 'very_strong'
        elif win_probability >= thresholds['strong']:
            return 'strong'
        elif win_probability >= thresholds['medium']:
            return 'medium'
        elif win_probability >= thresholds['weak_made']:
            return 'weak_made'
        else:
            return 'weak'
    
    def _resolve_classification_conflict(
        self, 
        rank_class: str, 
        prob_class: str, 
        rank: int, 
        win_prob: float,
        street: str
    ) -> str:
        """Resolve conflicts between rank-based and probability-based classifications."""
        
        # If classifications match, use them
        if rank_class == prob_class:
            return rank_class
        
        # Special handling for one pair (rank=2)
        if rank == 2:  # One pair
            if win_prob >= 0.60:
                return 'medium'  # Strong pair (overpair, top pair good kicker)
            elif win_prob >= 0.45:
                return 'weak_made'  # Decent pair
            else:
                return 'weak'  # Weak pair
        
        # For drawing hands (rank=1), rely more on probability
        if rank == 1:
            if win_prob >= 0.45:
                return 'medium'  # Strong draw
            elif win_prob >= 0.30:
                return 'weak_made'  # Decent draw
            else:
                return 'weak'  # Weak draw
        
        # For made hands (rank >= 3), be more conservative on later streets
        if rank >= 3:
            if street == 'river':
                # On river, trust the rank more than probability
                return rank_class
            else:
                # On flop/turn, consider probability for protection needs
                if abs(self._get_classification_strength(rank_class) - 
                       self._get_classification_strength(prob_class)) <= 1:
                    # If classifications are close (e.g. strong vs very_strong, or medium vs strong)
                    # lean towards the probability-based one if it's stronger, otherwise rank.
                    # This helps to correctly upgrade strong draws or slightly weaker made hands with high potential.
                    if self._get_classification_strength(prob_class) > self._get_classification_strength(rank_class):
                        return prob_class
                    return rank_class
                else:
                    # If classifications differ significantly, take the stronger one
                    return max(rank_class, prob_class, 
                             key=self._get_classification_strength)
        
        # Default: take more conservative classification (should ideally be covered by above logic)
        # For safety, if somehow not covered, prefer stronger if prob_class is much better.
        if self._get_classification_strength(prob_class) > self._get_classification_strength(rank_class) + 1:
             return prob_class
        return min(rank_class, prob_class, key=self._get_classification_strength)
    
    def _get_classification_strength(self, classification: str) -> int:
        """Get numerical strength for comparison."""
        strength_map = {
            'very_strong': 5,
            'strong': 4,
            'medium': 3,
            'weak_made': 2,
            'weak': 1
        }
        return strength_map.get(classification, 1)
    
    def _adjust_for_board_texture(
        self, 
        classification: str, 
        board_texture: str, 
        numerical_rank: int
    ) -> str:
        """Adjust classification based on board texture."""
        
        if board_texture == 'unknown':
            return classification
        
        # On very wet boards, downgrade medium hands slightly
        if board_texture in ['very_wet', 'coordinated'] and classification == 'medium':
            if numerical_rank == 2:  # One pair on wet board
                return 'weak_made'
        
        # On very dry boards, upgrade certain hands slightly
        elif board_texture in ['very_dry', 'rainbow'] and classification == 'weak_made':
            if numerical_rank == 2:  # One pair on dry board might play better
                return 'weak_made'  # Keep same, but note it plays up
        
        return classification
    
    def get_pot_commitment_threshold(self, classification: str, street: str = 'flop') -> float:
        """Get standardized pot commitment thresholds."""
        base_thresholds = {
            'very_strong': 0.15,  # Commit with 15% of stack
            'strong': 0.25,       # Commit with 25% of stack
            'medium': 0.45,       # Commit with 45% of stack
            'weak_made': 0.65,    # Commit with 65% of stack
            'weak': 0.80          # Almost never commit
        }
        
        # Adjust for street (be more willing to commit on later streets)
        street_adjustments = {
            'flop': 1.0,
            'turn': 0.85,
            'river': 0.70
        }
        
        base_threshold = base_thresholds.get(classification, 0.80)
        adjustment = street_adjustments.get(street, 1.0)
        
        return base_threshold * adjustment

# Create global instance
hand_classifier = EnhancedHandClassifier()

def classify_hand_strength_enhanced(
    numerical_hand_rank: int,
    win_probability: float,
    street: str = 'flop',
    board_texture: str = 'unknown'
) -> Tuple[str, Dict[str, Any]]:
    """Enhanced hand strength classification function."""
    return hand_classifier.classify_hand_strength(
        numerical_hand_rank, win_probability, street, board_texture
    )

def get_standardized_pot_commitment_threshold(classification: str, street: str = 'flop') -> float:
    """Get standardized pot commitment threshold."""
    return hand_classifier.get_pot_commitment_threshold(classification, street)
