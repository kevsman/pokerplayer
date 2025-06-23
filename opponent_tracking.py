# opponent_tracking.py
# Enhanced opponent modeling and tracking for poker bot

import logging
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple
from opponent_persistence import save_opponent_analysis, load_opponent_analysis, OPPONENT_ANALYSIS_FILE
import re
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class OpponentProfile:
    """
    Enhanced tracking and analysis of opponent tendencies for better decision making.
    Significantly improved to track more detailed patterns and support quicker profiling.
    """
    
    def __init__(self, player_name: str, max_hands_tracked: int = 150):  # Increased from 100
        self.player_name = player_name
        self.max_hands_tracked = max_hands_tracked
        
        # Basic stats - expanded
        self.hands_played = 0
        self.hands_seen = 0
        self.preflop_raises = 0
        self.preflop_calls = 0
        self.preflop_folds = 0
        self.vpip = 0.0  # Voluntarily Put Money In Pot
        self.pfr = 0.0   # PreFlop Raise %
        self.three_bet = 0.0  # 3-bet frequency
        self.fold_to_three_bet = 0.0  # Folding to 3-bets
        
        # Positional stats - enhanced
        self.position_stats = defaultdict(lambda: {
            'hands': 0, 
            'raises': 0, 
            'calls': 0, 
            'folds': 0,
            'vpip': 0.0,
            'pfr': 0.0,
            'steal_attempt': 0,
            'fold_to_steal': 0
        })
        
        # Postflop aggression - enhanced tracking
        self.postflop_bets = 0
        self.postflop_raises = 0
        self.postflop_calls = 0
        self.postflop_checks = 0
        self.postflop_folds = 0
        self.aggression_factor = 0.0
        self.fold_to_cbet = 0.0
        self.cbet_frequency = 0.0
        
        # Street-specific tendencies
        self.street_tendencies = {
            'flop': {'aggression': 0.0, 'fold_to_bet': 0.0, 'bet_frequency': 0.0},
            'turn': {'aggression': 0.0, 'fold_to_bet': 0.0, 'bet_frequency': 0.0},
            'river': {'aggression': 0.0, 'fold_to_bet': 0.0, 'bet_frequency': 0.0}
        }
        
        # Recent hand history (for tracking patterns)
        self.recent_actions = deque(maxlen=max_hands_tracked)
        self.showdown_hands = []  # Track actual hands shown down
        
        # Bet sizing patterns - expanded
        self.bet_sizes = {
            'preflop_open': [],
            'preflop_3bet': [],
            'preflop_4bet': [],
            'flop_bet': [],
            'flop_raise': [],
            'turn_bet': [],
            'turn_raise': [],
            'river_bet': [],
            'river_raise': []
        }
        
        # Quick profiling flags - helps with faster opponent classification
        self.is_tight = False
        self.is_loose = False
        self.is_passive = False
        self.is_aggressive = False
        self.is_calling_station = False
        self.is_maniac = False
        self.is_rock = False
        self.is_tag = False  # Tight-Aggressive
        self.is_lag = False  # Loose-Aggressive
        
    def update_preflop_action(self, action: str, position: str, bet_size: float = 0, pot_size: float = 0):
        """Update preflop statistics for this opponent."""
        self.hands_seen += 1
        
        # VPIP is true if player voluntarily puts money in pot (call, bet, raise)
        if action in ['call', 'bet', 'raise']:
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
    
    def __init__(self):
        self.opponents: Dict[str, OpponentProfile] = {}
        
    def get_or_create_profile(self, player_name: str) -> OpponentProfile:
        """Get existing profile or create new one."""
        if player_name not in self.opponents:
            self.opponents[player_name] = OpponentProfile(player_name)
        return self.opponents[player_name]
        
    def update_opponent_action(self, player_name: str, action: str, street: str, 
                             position: str = 'unknown', bet_size: float = 0, pot_size: float = 0):
        """Update opponent statistics based on their action."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[DEBUG] update_opponent_action: player={player_name}, action={action}, street={street}, position={position}, bet_size={bet_size}, pot_size={pot_size}")
        profile = self.get_or_create_profile(player_name)
        if street == 'preflop':
            profile.update_preflop_action(action, position, bet_size, pot_size)
        else:
            profile.update_postflop_action(action, street, bet_size, pot_size, position)
            
    def update_from_html(self, html_content: str, street_hint: str = None):
        """
        Parse HTML to detect opponent actions from the text displayed under the opponent name.
        The text says bet/fold/check/call/raise. This should be called frequently as the text is only visible for a short time.
        Tries to infer preflop/postflop from context, or uses street_hint if provided.
        Automatically saves profiles if a new action is detected.
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        player_areas = soup.find_all(class_=re.compile(r'player-area|table-player|player-nameplate'))
        updated = False
        
        # Determine current street from board cards if possible
        board_cards = soup.find(class_=re.compile(r'board-cards|table-board'))
        street = street_hint
        if not street:
            if board_cards and board_cards.find_all(class_=re.compile(r'card-image|card')):
                num_cards = len(board_cards.find_all(class_=re.compile(r'card-image|card')))
                if num_cards == 5:
                    street = 'river'
                elif num_cards == 4:
                    street = 'turn'
                elif num_cards >= 3:
                    street = 'flop'
                else:
                    street = 'preflop'
            else:
                street = 'preflop'

        for area in player_areas:
            name_div = area.find(class_=re.compile(r'text-block nickname|target|player-name|nickname'))
            if not name_div:
                continue
            player_name = name_div.get_text(strip=True)
            if not player_name:
                continue
            
            action_text = None
            # Expanded search for action text
            action_divs = area.find_all(class_=re.compile(r'action-text|player-action|action-indicator|status-text'))
            for div in action_divs:
                txt = div.get_text(strip=True).lower()
                # More robust action detection
                if any(action in txt for action in ['bet', 'fold', 'check', 'call', 'raise']):
                    if 'bet' in txt:
                        action_text = 'bet'
                    elif 'raise' in txt:
                        action_text = 'raise'
                    elif 'call' in txt:
                        action_text = 'call'
                    elif 'check' in txt:
                        action_text = 'check'
                    elif 'fold' in txt:
                        action_text = 'fold'
                    break # Found action

            if not action_text:
                # Fallback search in the whole player area
                area_text = area.get_text(strip=True).lower()
                if any(action in area_text for action in ['bet', 'fold', 'check', 'call', 'raise']):
                    if 'bet' in area_text:
                        action_text = 'bet'
                    elif 'raise' in area_text:
                        action_text = 'raise'
                    elif 'call' in area_text:
                        action_text = 'call'
                    elif 'check' in area_text:
                        action_text = 'check'
                    elif 'fold' in area_text:
                        action_text = 'fold'

            if action_text:
                # Only update and save if this is a new action
                profile = self.get_or_create_profile(player_name)
                if not profile.recent_actions or profile.recent_actions[-1]['action'] != action_text:
                    self.update_opponent_action(player_name, action_text, street=street)
                    updated = True

        if updated:
            self.save_all_profiles()

    def get_last_action(self, player_name: str):
        """Return the last action for a given opponent, or None."""
        profile = self.opponents.get(player_name)
        if not profile or not profile.recent_actions:
            return None
        return profile.recent_actions[-1]

    def get_opponent_action_adjustment(self, player_name: str, default_decision: str) -> str:
        """
        Suggest an adjustment to the bot's decision based on the opponent's last action.
        For example, if opponent just checked, consider betting more often.
        """
        last_action = self.get_last_action(player_name)
        if not last_action:
            return default_decision
        action = last_action['action']
        # Simple logic: if opponent checked, be more aggressive; if bet, be more cautious
        if action == 'check' and default_decision == 'check':
            return 'bet'  # Consider betting into weakness
        if action == 'bet' and default_decision == 'bet':
            return 'call'  # Don't raise into strength
        if action == 'fold':
            return default_decision  # No adjustment
        return default_decision
    
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
    
    def save_all_profiles(self, file_path=None):
        """Save all opponent profiles to disk."""
        import logging
        logger = logging.getLogger(__name__)
        if file_path is None:
            file_path = OPPONENT_ANALYSIS_FILE
        logger.info(f"[DEBUG] save_all_profiles: {len(self.opponents)} profiles to save: {list(self.opponents.keys())}")
        data = {name: vars(profile) for name, profile in self.opponents.items()}
        save_opponent_analysis(data, file_path)

    def load_all_profiles(self, file_path=None):
        """Load all opponent profiles from disk."""
        if file_path is None:
            file_path = OPPONENT_ANALYSIS_FILE
        data = load_opponent_analysis(file_path)
        for name, profile_data in data.items():
            profile = self.get_or_create_profile(name)
            for k, v in profile_data.items():
                setattr(profile, k, v)
