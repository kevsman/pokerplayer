# opponent_tracking.py
# Enhanced opponent modeling and tracking for poker bot

import logging
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class OpponentProfile:
    """
    Track and analyze opponent tendencies for better decision making.
    """
    
    def __init__(self, player_name: str, max_hands_tracked: int = 100):
        self.player_name = player_name
        self.max_hands_tracked = max_hands_tracked
        
        # Basic stats
        self.hands_played = 0
        self.hands_seen = 0
        self.preflop_raises = 0
        self.preflop_calls = 0
        self.preflop_folds = 0
        
        # Positional stats
        self.position_stats = defaultdict(lambda: {'hands': 0, 'raises': 0, 'calls': 0, 'folds': 0})
        
        # Postflop aggression
        self.postflop_bets = 0
        self.postflop_raises = 0
        self.postflop_calls = 0
        self.postflop_checks = 0
        self.postflop_folds = 0
        
        # Recent hand history (for tracking patterns)
        self.recent_actions = deque(maxlen=max_hands_tracked)
        
        # Bet sizing patterns
        self.bet_sizes = {
            'preflop_open': [],
            'preflop_3bet': [],
            'flop_bet': [],
            'turn_bet': [],
            'river_bet': []
        }
        
    def update_preflop_action(self, action: str, position: str, bet_size: float = 0, pot_size: float = 0):
        """Update preflop statistics for this opponent."""
        self.hands_seen += 1
        
        if action in ['raise', 'call']:
            self.hands_played += 1
            
        if action == 'raise':
            self.preflop_raises += 1
            self.position_stats[position]['raises'] += 1
            if bet_size > 0 and pot_size > 0:
                self.bet_sizes['preflop_open'].append(bet_size / pot_size)
        elif action == 'call':
            self.preflop_calls += 1
            self.position_stats[position]['calls'] += 1
        elif action == 'fold':
            self.preflop_folds += 1
            self.position_stats[position]['folds'] += 1
            
        self.position_stats[position]['hands'] += 1
        self.recent_actions.append({
            'street': 'preflop',
            'action': action,            'position': position,
            'bet_size_ratio': bet_size / pot_size if pot_size > 0 else 0
        })
        
    def update_postflop_action(self, action: str, street: str, bet_size: float = 0, pot_size: float = 0, position: str = 'unknown'):
        """Update postflop statistics for this opponent."""
        if action == 'bet':
            self.postflop_bets += 1
            if bet_size > 0 and pot_size > 0:
                self.bet_sizes[f'{street}_bet'].append(bet_size / pot_size)
        elif action == 'raise':
            self.postflop_raises += 1
        elif action == 'call':
            self.postflop_calls += 1
        elif action == 'check':
            self.postflop_checks += 1
        elif action == 'fold':
            self.postflop_folds += 1
            
        self.recent_actions.append({
            'street': street,
            'action': action,
            'position': position,
            'bet_size_ratio': bet_size / pot_size if pot_size > 0 else 0
        })
        
    def get_vpip(self) -> float:
        """Voluntarily Put money In Pot - percentage of hands played."""
        if self.hands_seen == 0:
            return 0.0
        return (self.hands_played / self.hands_seen) * 100
        
    def get_pfr(self) -> float:
        """Preflop Raise percentage."""
        if self.hands_seen == 0:
            return 0.0
        return (self.preflop_raises / self.hands_seen) * 100
        
    def get_aggression_factor(self) -> float:
        """Postflop aggression factor: (bets + raises) / calls."""
        total_aggressive = self.postflop_bets + self.postflop_raises
        total_passive = self.postflop_calls
        
        if total_passive == 0:
            return float('inf') if total_aggressive > 0 else 0.0
        return total_aggressive / total_passive
        
    def get_position_tendencies(self, position: str) -> Dict[str, float]:
        """Get playing tendencies for specific position."""
        stats = self.position_stats[position]
        total_hands = stats['hands']
        
        if total_hands == 0:
            return {'vpip': 0.0, 'pfr': 0.0, 'fold_rate': 0.0}
            
        vpip = ((stats['raises'] + stats['calls']) / total_hands) * 100
        pfr = (stats['raises'] / total_hands) * 100
        fold_rate = (stats['folds'] / total_hands) * 100
        
        return {
            'vpip': vpip,
            'pfr': pfr,
            'fold_rate': fold_rate
        }
        
    def get_average_bet_size(self, bet_type: str) -> float:
        """Get average bet size ratio for specific bet type."""
        sizes = self.bet_sizes.get(bet_type, [])
        if not sizes:
            return 0.0
        return sum(sizes) / len(sizes)
        
    def classify_player_type(self) -> str:
        """Classify opponent based on VPIP/PFR statistics."""
        vpip = self.get_vpip()
        pfr = self.get_pfr()
        
        if vpip < 15:
            if pfr < 10:
                return "tight_passive"
            else:
                return "tight_aggressive"
        elif vpip < 25:
            if pfr < 15:
                return "loose_passive"
            else:
                return "loose_aggressive"
        else:
            if pfr < 20:
                return "very_loose_passive"
            else:
                return "very_loose_aggressive"
                
    def get_fold_equity_estimate(self, position: str, bet_size_ratio: float) -> float:
        """Estimate fold equity against this opponent."""
        player_type = self.classify_player_type()
        position_stats = self.get_position_tendencies(position)
        
        # Base fold equity based on player type
        base_fold_equity = {
            "tight_passive": 0.7,
            "tight_aggressive": 0.6,
            "loose_passive": 0.4,
            "loose_aggressive": 0.5,
            "very_loose_passive": 0.3,
            "very_loose_aggressive": 0.4
        }.get(player_type, 0.5)
        
        # Adjust for bet size
        if bet_size_ratio > 1.0:  # Overbet
            base_fold_equity += 0.15
        elif bet_size_ratio > 0.75:  # Large bet
            base_fold_equity += 0.1
        elif bet_size_ratio < 0.5:  # Small bet
            base_fold_equity -= 0.1
            
        # Adjust for position-specific fold rate
        if position_stats['fold_rate'] > 0:
            fold_adjustment = (position_stats['fold_rate'] - 50) / 100  # Normalize around 50%
            base_fold_equity += fold_adjustment * 0.2
            
        return max(0.1, min(0.9, base_fold_equity))
        
    def should_value_bet_thin(self, position: str) -> bool:
        """Determine if we can value bet thinly against this opponent."""
        player_type = self.classify_player_type()
        
        # Can value bet thinner against loose passive players
        if "loose_passive" in player_type:
            return True
        elif "tight" in player_type:
            return False
        else:
            return position in ['CO', 'BTN']  # Only in position against unknown types
            
    def __str__(self) -> str:
        """String representation of opponent profile."""
        return (f"OpponentProfile({self.player_name}): "
                f"VPIP={self.get_vpip():.1f}%, PFR={self.get_pfr():.1f}%, "
                f"Type={self.classify_player_type()}, "
                f"Hands={self.hands_seen}")


class OpponentTracker:
    """
    Manages multiple opponent profiles and provides analysis.
    """
    
    def __init__(self, config=None, logger=None): # Added config and logger
        self.opponents: Dict[str, OpponentProfile] = {}
        self.config = config # Store config
        self.logger = logger if logger else logging.getLogger(__name__) # Store logger

    def get_or_create_profile(self, player_name: str) -> OpponentProfile:
        """Get existing profile or create new one."""
        if player_name not in self.opponents:
            self.opponents[player_name] = OpponentProfile(player_name)
        return self.opponents[player_name]
        
    def log_action(self, player_name: str, action: str, street: str, 
                             position: str = 'unknown', bet_size: float = 0, pot_size: float = 0, hand_id: Optional[str] = None): # Renamed and added hand_id
        """Update opponent statistics based on their action."""
        profile = self.get_or_create_profile(player_name)
        
        # Log the raw action with hand_id for more detailed future analysis if needed
        # For now, we'll pass it to the existing update methods which don't use hand_id yet
        if self.logger:
            self.logger.debug(f"Logging action for {player_name}: Hand ID {hand_id}, {street}, {action}, Pos: {position}, Size: {bet_size}, Pot: {pot_size}")

        if street == 'preflop':
            profile.update_preflop_action(action, position, bet_size, pot_size)
        else:
            profile.update_postflop_action(action, street, bet_size, pot_size, position)
            
    def get_table_dynamics(self) -> Dict[str, float]:
        """Analyze overall table dynamics."""
        if not self.opponents:
            return {'avg_vpip': 25.0, 'avg_pfr': 15.0, 'table_type': 'unknown'}
            
        vpips = [profile.get_vpip() for profile in self.opponents.values() if profile.hands_seen > 5]
        pfrs = [profile.get_pfr() for profile in self.opponents.values() if profile.hands_seen > 5]
        
        if not vpips:
            return {'avg_vpip': 25.0, 'avg_pfr': 15.0, 'table_type': 'unknown'}
            
        avg_vpip = sum(vpips) / len(vpips)
        avg_pfr = sum(pfrs) / len(pfrs)
        
        # Classify table type
        if avg_vpip < 20:
            table_type = 'tight'
        elif avg_vpip > 30:
            table_type = 'loose'
        else:
            table_type = 'normal'
            
        return {
            'avg_vpip': avg_vpip,
            'avg_pfr': avg_pfr,
            'table_type': table_type,
            'sample_size': len(vpips)
        }
        
    def get_opponent_recommendation(self, player_name: str, situation: str) -> str:
        """Get playing recommendation against specific opponent."""
        if player_name not in self.opponents:
            return "play_standard"
            
        profile = self.opponents[player_name]
        player_type = profile.classify_player_type()
        
        recommendations = {
            "tight_passive": "value_bet_thin",
            "tight_aggressive": "play_straightforward", 
            "loose_passive": "value_bet_wide",
            "loose_aggressive": "play_tighter",
            "very_loose_passive": "value_bet_very_wide",
            "very_loose_aggressive": "play_much_tighter"
        }
        
        return recommendations.get(player_type, "play_standard")
