# fixed_opponent_integration.py
"""
Fixed opponent tracker integration that addresses the "tracked=0" issue
and provides meaningful opponent analysis for decision making.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

class FixedOpponentIntegration:
    """Provides working opponent analysis integration."""
    
    def __init__(self):
        self.default_player_stats = {
            'vpip': 25.0,
            'pfr': 18.0,
            'aggression_factor': 1.5,
            'fold_to_cbet': 0.6,
            'cbet_frequency': 0.7,
            'hands_seen': 0
        }
    
    def get_enhanced_opponent_analysis(
        self, 
        opponent_tracker=None, 
        active_opponents_count: int = 1
    ) -> Dict[str, Any]:
        """
        Get enhanced opponent analysis that actually works.
        Fixes the "tracked=0" issue by providing meaningful fallbacks.
        """
        
        if not opponent_tracker:
            return self._get_default_analysis(active_opponents_count, "no_tracker")
        
        # Check if opponent tracker has data
        if not hasattr(opponent_tracker, 'opponents') or not opponent_tracker.opponents:
            return self._get_default_analysis(active_opponents_count, "no_opponents_data")
        
        # Count opponents with meaningful data
        tracked_opponents = []
        for name, profile in opponent_tracker.opponents.items():
            if hasattr(profile, 'hands_seen') and profile.hands_seen > 0:
                tracked_opponents.append((name, profile))
        
        if not tracked_opponents:
            return self._get_default_analysis(active_opponents_count, "no_meaningful_data")
        
        # Analyze tracked opponents
        return self._analyze_tracked_opponents(tracked_opponents, active_opponents_count)
    
    def _get_default_analysis(self, opponent_count: int, reason: str) -> Dict[str, Any]:
        """Provide default analysis when no opponent data is available."""
        
        # Estimate table type based on typical online poker stats
        table_type = 'standard'
        avg_vpip = 25.0
        avg_pfr = 18.0
        
        # Adjust defaults based on opponent count (multiway = usually looser)
        if opponent_count >= 4:
            table_type = 'loose'
            avg_vpip = 32.0
            avg_pfr = 22.0
        elif opponent_count <= 1:
            table_type = 'tight'
            avg_vpip = 20.0
            avg_pfr = 15.0
        
        fold_equity_estimates = {
            'tight': 0.65,
            'standard': 0.50,
            'loose': 0.35
        }
        
        return {
            'tracked_count': 0,
            'table_type': table_type,
            'avg_vpip': avg_vpip,
            'avg_pfr': avg_pfr,
            'avg_aggression': avg_pfr / avg_vpip if avg_vpip > 0 else 0.7,
            'fold_equity_estimate': fold_equity_estimates[table_type],
            'calling_frequency': 1.0 - fold_equity_estimates[table_type],
            'reasoning': reason,
            'opponent_types': self._estimate_opponent_types(opponent_count, table_type)
        }
    
    def _analyze_tracked_opponents(
        self, 
        tracked_opponents: List[Tuple[str, Any]], 
        active_count: int
    ) -> Dict[str, Any]:
        """Analyze opponents with actual tracking data."""
        
        total_vpip = 0
        total_pfr = 0
        total_hands = 0
        opponent_types = {}
        
        for name, profile in tracked_opponents:
            # Get VPIP safely
            vpip = self._safe_get_stat(profile, 'get_vpip', self.default_player_stats['vpip'])
            pfr = self._safe_get_stat(profile, 'get_pfr', self.default_player_stats['pfr'])
            hands = getattr(profile, 'hands_seen', 1)
            
            # Weight by hands seen (more reliable opponents count more)
            weight = min(hands, 50) / 50.0  # Cap at 50 hands for weight calculation
            
            total_vpip += vpip * weight
            total_pfr += pfr * weight
            total_hands += weight
            
            # Classify opponent type
            opponent_types[name] = self._classify_opponent_type(vpip, pfr, profile)
        
        # Calculate averages
        avg_vpip = total_vpip / max(total_hands, 1)
        avg_pfr = total_pfr / max(total_hands, 1)
        avg_aggression = avg_pfr / max(avg_vpip, 1)
        
        # Determine table type
        table_type = self._determine_table_type(avg_vpip, avg_pfr, len(tracked_opponents))
        
        # Calculate fold equity
        fold_equity = self._calculate_fold_equity(opponent_types, avg_vpip, table_type)
        
        return {
            'tracked_count': len(tracked_opponents),
            'table_type': table_type,
            'avg_vpip': avg_vpip,
            'avg_pfr': avg_pfr,
            'avg_aggression': avg_aggression,
            'fold_equity_estimate': fold_equity,
            'calling_frequency': 1.0 - fold_equity,
            'reasoning': 'analyzed_tracked_opponents',
            'opponent_types': opponent_types,
            'active_opponents': active_count
        }
    
    def _safe_get_stat(self, profile, method_name: str, default: float) -> float:
        """Safely get stat from profile object."""
        try:
            if hasattr(profile, method_name):
                result = getattr(profile, method_name)()
                return result if isinstance(result, (int, float)) and 0 <= result <= 100 else default
            else:
                # Try direct attribute access
                attr_map = {
                    'get_vpip': 'vpip',
                    'get_pfr': 'pfr'
                }
                attr_name = attr_map.get(method_name)
                if attr_name and hasattr(profile, attr_name):
                    result = getattr(profile, attr_name)
                    if isinstance(result, (int, float)):
                        # Convert percentage to decimal if needed
                        return result if result <= 1.0 else result / 100.0
                    
        except Exception as e:
            logger.debug(f"Error getting stat {method_name}: {e}")
        
        return default
    
    def _classify_opponent_type(self, vpip: float, pfr: float, profile) -> str:
        """Classify opponent playing style."""
        
        # Convert to percentages if needed
        vpip_pct = vpip if vpip > 1 else vpip * 100
        pfr_pct = pfr if pfr > 1 else pfr * 100
        
        # Get aggression factor
        aggression = pfr_pct / max(vpip_pct, 1)
        
        # Check for additional stats
        fold_to_cbet = self._safe_get_stat(profile, 'get_fold_to_cbet', 0.6)
        
        # Classify based on VPIP/PFR
        if vpip_pct < 15:  # Very tight
            if aggression > 0.7:
                return 'tight_aggressive'  # TAG/Nit
            else:
                return 'tight_passive'     # Rock
        elif vpip_pct < 25:  # Tight
            if aggression > 0.6:
                return 'tight_aggressive'  # TAG
            else:
                return 'tight_passive'     # Weak tight
        elif vpip_pct < 35:  # Loose
            if aggression > 0.5:
                return 'loose_aggressive'  # LAG
            else:
                return 'loose_passive'     # Calling station
        else:  # Very loose
            if aggression > 0.4:
                return 'very_loose_aggressive'  # Maniac
            else:
                return 'very_loose_passive'     # Fish
    
    def _determine_table_type(self, avg_vpip: float, avg_pfr: float, tracked_count: int) -> str:
        """Determine overall table type."""
        
        # Convert to percentage if needed
        vpip_pct = avg_vpip if avg_vpip > 1 else avg_vpip * 100
        
        if tracked_count < 2:
            return 'unknown'
        
        if vpip_pct < 18:
            return 'tight'
        elif vpip_pct > 32:
            return 'loose'
        else:
            return 'standard'
    
    def _calculate_fold_equity(
        self, 
        opponent_types: Dict[str, str], 
        avg_vpip: float, 
        table_type: str
    ) -> float:
        """Calculate expected fold equity against opponents."""
        
        # Base fold equity by table type
        base_fold_equity = {
            'tight': 0.65,
            'standard': 0.50,
            'loose': 0.35,
            'unknown': 0.50
        }
        
        fold_equity = base_fold_equity.get(table_type, 0.50)
        
        # Adjust based on specific opponent types
        if opponent_types:
            type_adjustments = {
                'tight_aggressive': 0.60,
                'tight_passive': 0.70,
                'loose_aggressive': 0.45,
                'loose_passive': 0.30,
                'very_loose_aggressive': 0.40,
                'very_loose_passive': 0.25
            }
            
            type_fold_equities = [type_adjustments.get(opp_type, 0.50) 
                                for opp_type in opponent_types.values()]
            
            if type_fold_equities:
                fold_equity = sum(type_fold_equities) / len(type_fold_equities)
        
        return max(0.20, min(0.80, fold_equity))  # Keep in reasonable range
    
    def _estimate_opponent_types(self, opponent_count: int, table_type: str) -> Dict[str, str]:
        """Estimate opponent types when no tracking data available."""
        
        type_distributions = {
            'tight': ['tight_aggressive', 'tight_passive', 'tight_aggressive'],
            'standard': ['tight_aggressive', 'loose_passive', 'loose_aggressive'],
            'loose': ['loose_passive', 'loose_aggressive', 'very_loose_passive']
        }
        
        base_types = type_distributions.get(table_type, type_distributions['standard'])
        
        # Create estimated opponent types
        opponent_types = {}
        for i in range(min(opponent_count, 6)):  # Max 6 opponents
            opponent_types[f'Opponent_{i+1}'] = base_types[i % len(base_types)]
        
        return opponent_types
    
    def get_exploitative_adjustments(self, analysis: Dict[str, Any]) -> Dict[str, str]:
        """Get exploitative adjustments based on opponent analysis."""
        
        adjustments = {}
        
        # Table type adjustments
        table_type = analysis.get('table_type', 'standard')
        fold_equity = analysis.get('fold_equity_estimate', 0.5)
        
        if table_type == 'tight' or fold_equity > 0.6:
            adjustments['bluffing'] = 'increase_frequency'
            adjustments['value_betting'] = 'bet_smaller'
            adjustments['stealing'] = 'steal_more'
        elif table_type == 'loose' or fold_equity < 0.4:
            adjustments['bluffing'] = 'decrease_frequency'
            adjustments['value_betting'] = 'bet_larger'
            adjustments['stealing'] = 'steal_less'
        
        # Specific opponent type adjustments
        opponent_types = analysis.get('opponent_types', {})
        if opponent_types:
            tight_count = sum(1 for t in opponent_types.values() if 'tight' in t)
            loose_count = sum(1 for t in opponent_types.values() if 'loose' in t)
            
            if tight_count > loose_count:
                adjustments['overall'] = 'exploit_tight_players'
            elif loose_count > tight_count:
                adjustments['overall'] = 'exploit_loose_players'
        
        return adjustments

# Create global instance
opponent_integration = FixedOpponentIntegration()

def get_fixed_opponent_analysis(opponent_tracker=None, active_opponents_count: int = 1) -> Dict[str, Any]:
    """Get fixed opponent analysis that actually works."""
    return opponent_integration.get_enhanced_opponent_analysis(opponent_tracker, active_opponents_count)

def get_opponent_exploitative_adjustments(analysis: Dict[str, Any]) -> Dict[str, str]:
    """Get exploitative adjustments based on analysis."""
    return opponent_integration.get_exploitative_adjustments(analysis)
