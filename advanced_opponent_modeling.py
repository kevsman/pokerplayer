# advanced_opponent_modeling.py
"""
Advanced opponent modeling system for enhanced exploitative play.
This builds upon the existing opponent tracker with sophisticated analysis.
"""

import logging
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)

class OpponentProfile:
    """Enhanced opponent profile with detailed statistics."""
    
    def __init__(self, player_name: str):
        self.name = player_name
        self.hands_observed = 0
        
        # Basic stats
        self.vpip = 0.0  # Voluntarily put money in pot
        self.pfr = 0.0   # Preflop raise frequency
        self.aggression_factor = 0.0
        self.fold_to_3bet = 0.0
        
        # Advanced stats
        self.cbet_frequency = 0.0  # Continuation bet frequency
        self.fold_to_cbet = 0.0    # Fold to continuation bet
        self.turn_aggression = 0.0  # Turn betting frequency
        self.river_aggression = 0.0 # River betting frequency
        
        # Position-based stats
        self.position_stats = defaultdict(lambda: {
            'vpip': 0.0, 'pfr': 0.0, 'hands': 0
        })
        
        # Bet sizing patterns
        self.bet_sizes = {
            'flop': [], 'turn': [], 'river': []
        }
        
        # Showdown tendencies
        self.showdown_strength = []  # Hand strengths at showdown
        self.bluff_frequency = 0.0
        
    def update_preflop_action(self, position: str, action: str, amount: float = 0):
        """Update preflop statistics."""
        self.hands_observed += 1
        pos_stats = self.position_stats[position]
        pos_stats['hands'] += 1
        
        if action in ['call', 'raise', 'bet']:
            # VPIP
            pos_stats['vpip'] = ((pos_stats['vpip'] * (pos_stats['hands'] - 1)) + 1) / pos_stats['hands']
            self.vpip = sum(stats['vpip'] * stats['hands'] for stats in self.position_stats.values()) / self.hands_observed
            
            if action in ['raise', 'bet']:
                # PFR
                pos_stats['pfr'] = ((pos_stats['pfr'] * (pos_stats['hands'] - 1)) + 1) / pos_stats['hands']
                self.pfr = sum(stats['pfr'] * stats['hands'] for stats in self.position_stats.values()) / self.hands_observed
    
    def update_postflop_action(self, street: str, action: str, amount: float, pot_size: float):
        """Update postflop statistics."""
        if action in ['bet', 'raise']:
            bet_ratio = amount / pot_size if pot_size > 0 else 0
            self.bet_sizes[street].append(bet_ratio)
            
            # Update street-specific aggression
            if street == 'flop':
                self.cbet_frequency = self._update_frequency(self.cbet_frequency, True)
            elif street == 'turn':
                self.turn_aggression = self._update_frequency(self.turn_aggression, True)
            elif street == 'river':
                self.river_aggression = self._update_frequency(self.river_aggression, True)
    
    def update_fold_to_bet(self, street: str, bet_type: str = 'standard'):
        """Update folding statistics."""
        if street == 'flop' and bet_type == 'cbet':
            self.fold_to_cbet = self._update_frequency(self.fold_to_cbet, True)
    
    def _update_frequency(self, current_freq: float, occurred: bool) -> float:
        """Update frequency statistics with exponential decay."""
        alpha = 0.1  # Learning rate
        return current_freq * (1 - alpha) + (1.0 if occurred else 0.0) * alpha
    
    def get_betting_tendency(self, street: str) -> str:
        """Get opponent's betting tendency for a street."""
        if street == 'flop':
            freq = self.cbet_frequency
        elif street == 'turn':
            freq = self.turn_aggression
        else:
            freq = self.river_aggression
            
        if freq > 0.7:
            return 'very_aggressive'
        elif freq > 0.5:
            return 'aggressive'
        elif freq > 0.3:
            return 'moderate'
        else:
            return 'passive'
    
    def get_average_bet_size(self, street: str) -> float:
        """Get opponent's average bet size for a street."""
        sizes = self.bet_sizes.get(street, [])
        return statistics.mean(sizes) if sizes else 0.5  # Default 50% pot
    
    def is_tight_player(self) -> bool:
        """Determine if opponent is tight."""
        return self.vpip < 0.15  # Less than 15% VPIP
    
    def is_aggressive_player(self) -> bool:
        """Determine if opponent is aggressive."""
        return self.pfr > 0.12 and self.aggression_factor > 1.5
    
    def get_exploitative_adjustments(self) -> Dict[str, str]:
        """Get recommended adjustments against this opponent."""
        adjustments = {}
        
        if self.is_tight_player():
            adjustments['preflop'] = 'steal_more_vs_tight'
            adjustments['postflop'] = 'bluff_more_vs_tight'
        
        if self.fold_to_cbet > 0.6:
            adjustments['flop'] = 'cbet_more_vs_folder'
        
        if self.cbet_frequency > 0.8:
            adjustments['flop_defense'] = 'call_down_vs_cbetter'
        
        return adjustments


class AdvancedOpponentAnalyzer:
    """Advanced analysis of opponent behavior patterns."""
    
    def __init__(self):
        self.profiles: Dict[str, OpponentProfile] = {}
        self.global_pool_stats = {
            'avg_vpip': 0.22,  # Typical online poker stats
            'avg_pfr': 0.18,
            'avg_aggression': 1.8
        }
        
        # New attributes for quick profiling
        self.default_table_type = 'balanced'  # Default assumption
        self.quick_profiling_enabled = True   # New flag to enable quick profiling
        self.min_hands_for_accurate_profile = 5  # Reduced from typical 10+ for faster profiling
        self.exploit_level = 0.8  # How aggressively to exploit (0-1 scale)

    def get_or_create_profile(self, player_name: str) -> OpponentProfile:
        """Get existing profile or create new one."""
        if player_name not in self.profiles:
            self.profiles[player_name] = OpponentProfile(player_name)
        return self.profiles[player_name]
    
    def update_opponent_profile(self, player_name: str, stats_data: Dict) -> None:
        """Update or create opponent profile with statistics from existing tracker."""
        profile = self.get_or_create_profile(player_name)
        
        # Update basic stats if available
        if 'vpip' in stats_data:
            profile.vpip = stats_data['vpip'] / 100.0 if stats_data['vpip'] > 1.0 else stats_data['vpip']
        if 'pfr' in stats_data:
            profile.pfr = stats_data['pfr'] / 100.0 if stats_data['pfr'] > 1.0 else stats_data['pfr']
        if 'hands_seen' in stats_data:
            profile.hands_observed = max(profile.hands_observed, stats_data['hands_seen'])
        
        # Calculate derived stats
        if profile.vpip > 0 and profile.pfr > 0:
            profile.aggression_factor = profile.pfr / profile.vpip
    
    def analyze_betting_pattern(self, player_name: str, action_sequence: List[Tuple[str, str, float]]) -> Dict:
        """Analyze a sequence of betting actions."""
        profile = self.get_or_create_profile(player_name)
        
        pattern_analysis = {
            'consistency': self._analyze_consistency(action_sequence),
            'aggression_level': self._analyze_aggression(action_sequence),
            'sizing_tells': self._analyze_sizing_tells(profile, action_sequence),
            'street_tendencies': self._analyze_street_tendencies(action_sequence)
        }
        
        return pattern_analysis
    
    def _analyze_consistency(self, actions: List[Tuple[str, str, float]]) -> str:
        """Analyze consistency of betting patterns."""
        bet_actions = [action for street, action, amount in actions if action in ['bet', 'raise']]
        
        if len(bet_actions) >= 3:
            return 'consistent_aggressor'
        elif len(bet_actions) == 0:
            return 'consistent_passive'
        else:
            return 'mixed_strategy'
    
    def _analyze_aggression(self, actions: List[Tuple[str, str, float]]) -> str:
        """Analyze level of aggression."""
        aggressive_actions = sum(1 for _, action, _ in actions if action in ['bet', 'raise'])
        total_actions = len(actions)
        
        if total_actions == 0:
            return 'unknown'
        
        aggression_ratio = aggressive_actions / total_actions
        
        if aggression_ratio > 0.7:
            return 'very_aggressive'
        elif aggression_ratio > 0.4:
            return 'aggressive'
        elif aggression_ratio > 0.2:
            return 'moderate'
        else:
            return 'passive'
    
    def _analyze_sizing_tells(self, profile: OpponentProfile, actions: List[Tuple[str, str, float]]) -> Dict:
        """Analyze betting size patterns for tells."""
        size_analysis = {}
        
        for street, action, amount in actions:
            if action in ['bet', 'raise'] and amount > 0:
                avg_size = profile.get_average_bet_size(street)
                
                if amount > avg_size * 1.5:
                    size_analysis[street] = 'overbet_pattern'
                elif amount < avg_size * 0.7:                    size_analysis[street] = 'small_bet_pattern'
                else:
                    size_analysis[street] = 'standard_sizing'
        
        return size_analysis
    
    def _analyze_street_tendencies(self, actions: List[Tuple[str, str, float]]) -> Dict:
        """Analyze tendencies by street."""
        street_analysis = {}
        
        streets = ['flop', 'turn', 'river']
        for street in streets:
            street_actions = [action for s, action, _ in actions if s == street]
            if street_actions:
                aggressive = sum(1 for a in street_actions if a in ['bet', 'raise'])
                tendency = 'aggressive' if aggressive > 0 else 'passive'
                street_analysis[street] = tendency
        
        return street_analysis
    
    def get_exploitative_strategy(self, player_name: str, current_situation: Dict) -> Dict[str, str]:
        """Get exploitative strategy recommendations."""
        if player_name not in self.profiles or player_name == "Unknown":
            return {
                'recommended_action': 'balanced_default',
                'reasoning': 'insufficient_opponent_data',
                'strategy': 'balanced_default',
                'sizing_adjustment': 'standard_sizing',
                'bluff_frequency': 'standard_bluffing'
            }
        
        profile = self.profiles[player_name]
        adjustments = profile.get_exploitative_adjustments()
        
        # Situational adjustments
        situation = current_situation.get('situation', 'unknown')
        street = current_situation.get('street', 'flop')
        position = current_situation.get('position', 'unknown')
        
        # Generate exploitative recommendations
        recommended_action = 'balanced_default'
        reasoning = 'standard_play'
        
        if profile.is_tight_player() and situation == 'facing_bet':
            recommended_action = 'bluff_more'
            reasoning = 'tight_opponent_folds_often'
        elif profile.is_aggressive_player() and situation == 'checked_to':
            recommended_action = 'bet_thin_value'
            reasoning = 'aggressive_opponent_calls_light'
        elif profile.fold_to_cbet > 0.65:
            recommended_action = 'cbet_more'
            reasoning = 'opponent_folds_to_cbets_frequently'
        
        strategy = {
            'recommended_action': recommended_action,
            'reasoning': reasoning,
            'primary': adjustments.get(street, 'balanced'),
            'secondary': adjustments.get('postflop', 'standard'),
            'sizing_adjustment': self._get_sizing_adjustment(profile, street),
            'bluff_frequency': self._get_bluff_frequency_adjustment(profile)
        }
        
        return strategy
    
    def _get_sizing_adjustment(self, profile: OpponentProfile, street: str) -> str:
        """Get recommended sizing adjustment."""
        if profile.fold_to_cbet > 0.6:
            return 'smaller_sizes_vs_folder'
        elif profile.cbet_frequency > 0.8:
            return 'larger_sizes_for_value'
        else:
            return 'standard_sizing'
    
    def _get_bluff_frequency_adjustment(self, profile: OpponentProfile) -> str:
        """Get bluff frequency adjustment."""
        if profile.fold_to_cbet > 0.6:
            return 'bluff_more'
        elif profile.fold_to_cbet < 0.3:
            return 'bluff_less'
        else:
            return 'standard_bluffing'
    
    def analyze_opponent(self, opponent_id, tracked_data=None, history=None, position=None, hand_strength=None):
        """
        Analyze opponent and get exploitative adjustments.
        Returns a dict with opponent profile and adjustment recommendations.
        """
        # Quick profiling if we have limited data but quick profiling is enabled
        if tracked_data and self.quick_profiling_enabled:
            # Use even minimal data to make faster assessments
            if tracked_data.get('hands_seen', 0) >= 3:  # Reduced threshold for quicker profiling
                return self._perform_quick_profiling(tracked_data, position, hand_strength)
        
        # Default profile for unknown opponents based on table type
        return self._get_default_profile(position, hand_strength)
    
    def _perform_quick_profiling(self, data, position=None, hand_strength=None):
        """
        More aggressive quick profiling to make faster assessments of opponents.
        Even with minimal data, make exploitative adjustments more quickly.
        """
        # Extract key stats
        vpip = data.get('vpip', 25.0)
        pfr = data.get('pfr', 15.0)
        aggression = data.get('aggression_factor', 1.0)
        
        # Quick classifications with lower thresholds
        is_tight = vpip < 20.0
        is_loose = vpip > 30.0
        is_passive = aggression < 1.0
        is_aggressive = aggression > 2.0
        
        # Fast profile determination
        if is_tight and is_aggressive:
            player_type = 'tag'  # Tight-aggressive
            fold_equity = 65.0   # High fold equity against tight players
        elif is_loose and is_aggressive:
            player_type = 'lag'  # Loose-aggressive
            fold_equity = 40.0   # Lower fold equity against loose players
        elif is_loose and is_passive:
            player_type = 'calling_station'
            fold_equity = 30.0   # Very low fold equity against calling stations
        elif is_tight and is_passive:
            player_type = 'nit'  # Very tight player
            fold_equity = 75.0   # Very high fold equity against tight players
        else:
            player_type = 'balanced'
            fold_equity = 50.0   # Average fold equity
        
        # Exploitative recommendations tailored to opponent type and our hand
        adjustments = {}
        
        # Against tight-aggressive players
        if player_type == 'tag':
            adjustments['value_bet_size'] = 0.8  # Slightly smaller value bets
            adjustments['bluff_frequency'] = 1.2  # More bluffs
            adjustments['call_threshold'] = 0.9   # Tighter calling vs their aggression
        
        # Against loose-aggressive players
        elif player_type == 'lag':
            adjustments['value_bet_size'] = 1.2   # Larger value bets
            adjustments['bluff_frequency'] = 0.6  # Fewer bluffs
            adjustments['call_threshold'] = 0.8   # Wider calling range
        
        # Against calling stations
        elif player_type == 'calling_station':
            adjustments['value_bet_size'] = 1.3   # Much larger value bets
            adjustments['bluff_frequency'] = 0.2   # Almost never bluff
            adjustments['call_threshold'] = 0.5   # Much tighter calling
        
        # Against nitty players
        elif player_type == 'nit':
            adjustments['value_bet_size'] = 0.6   # Smaller value bets
            adjustments['bluff_frequency'] = 1.5   # Much more bluffing
            adjustments['call_threshold'] = 1.1    # Much wider calling
        
        return {
            'player_type': player_type,
            'fold_equity': fold_equity,
            'adjustments': adjustments,
            'confidence': min(0.7, data.get('hands_seen', 0) / 10)  # Limited confidence with quick profiling
        }
    
    def _get_default_profile(self, position=None, hand_strength=None):
        """
        Get default opponent profile based on table position and hand strength.
        This is a fallback for unknown opponents.
        """
        # Default to balanced profile
        default_profile = {
            'vpip': 0.25,
            'pfr': 0.15,
            'aggression_factor': 1.0,
            'fold_to_3bet': 0.5,
            'cbet_frequency': 0.6,
            'fold_to_cbet': 0.4,
            'turn_aggression': 0.5,
            'river_aggression': 0.5,
            'hands_seen': 10
        }
        
        # Adjust based on position (early, middle, late, blind)
        if position in ['UTG', 'EP']:
            default_profile['vpip'] -= 0.05
            default_profile['pfr'] -= 0.05
        elif position in ['BTN', 'LP']:
            default_profile['vpip'] += 0.05
            default_profile['pfr'] += 0.05
        
        # Further adjust based on hand strength (for initial hand ranges)
        if hand_strength:
            if hand_strength == 'strong':
                default_profile['vpip'] -= 0.05
                default_profile['pfr'] -= 0.05
            elif hand_strength == 'weak':
                default_profile['vpip'] += 0.1
                default_profile['pfr'] += 0.1
        
        return default_profile
    
def integrate_with_existing_tracker(opponent_tracker, active_opponents_count: int) -> Dict:
    """Integration function with existing opponent tracker."""
    try:
        # Initialize advanced analyzer
        analyzer = AdvancedOpponentAnalyzer()
        
        # Get opponent data from existing tracker
        if hasattr(opponent_tracker, 'tracked_opponents'):
            for opponent_name, data in opponent_tracker.tracked_opponents.items():
                profile = analyzer.get_or_create_profile(opponent_name)
                  # Update profile with tracked data
                if 'actions' in data:
                    for action_data in data['actions']:
                        # Process historical actions
                        pass
        
        return {
            'analyzer': analyzer,
            'profiles_count': len(analyzer.profiles),
            'status': 'enhanced_analysis_active',
            'tracked_count': len(analyzer.profiles),
            'avg_vpip': 0.22
        }
        
    except Exception as e:
        logger.warning(f"Advanced opponent modeling failed: {e}")
        return {
            'analyzer': None,
            'profiles_count': 0,
            'status': 'fallback_to_basic_tracking'
        }


if __name__ == "__main__":
    # Example usage
    analyzer = AdvancedOpponentAnalyzer()
    
    # Create test profile
    profile = analyzer.get_or_create_profile("TestPlayer")
    profile.update_preflop_action("BTN", "raise", 3.0)
    profile.update_postflop_action("flop", "bet", 0.6, 1.0)
    
    print(f"Player tendency: {profile.get_betting_tendency('flop')}")
    print(f"Exploitative adjustments: {profile.get_exploitative_adjustments()}")
