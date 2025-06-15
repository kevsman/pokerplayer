# enhanced_opponent_tracking.py
"""
Enhanced opponent tracking with advanced statistical analysis and pattern recognition.
"""

import logging
import time
import json
from collections import defaultdict, deque
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import statistics

logger = logging.getLogger(__name__)

class PlayingStyle(Enum):
    TIGHT_PASSIVE = "tight_passive"
    TIGHT_AGGRESSIVE = "tight_aggressive"
    LOOSE_PASSIVE = "loose_passive"
    LOOSE_AGGRESSIVE = "loose_aggressive"
    MANIAC = "maniac"
    ROCK = "rock"
    UNKNOWN = "unknown"

@dataclass
class ActionData:
    """Single action data point."""
    action_type: str
    amount: float
    street: str
    position: str
    pot_size_before: float
    stack_size: float
    timestamp: float
    hand_id: str
    was_aggressor: bool = False
    facing_bet: bool = False
    decision_time: float = 0.0

@dataclass
class HandData:
    """Complete hand data for an opponent."""
    hand_id: str
    position: str
    starting_stack: float
    ending_stack: float
    actions: List[ActionData]
    went_to_showdown: bool = False
    won_hand: bool = False
    shown_cards: List[str] = None
    hand_strength: str = ""

class EnhancedOpponentProfile:
    """Enhanced opponent profile with comprehensive statistics."""
    
    def __init__(self, player_name: str):
        self.player_name = player_name
        self.created_time = time.time()
        self.last_updated = time.time()
        
        # Hand and action tracking
        self.hands_data = deque(maxlen=200)  # Store detailed hand data
        self.recent_actions = deque(maxlen=50)  # Recent actions for pattern analysis
        self.session_hands = 0
        self.total_hands_observed = 0
        
        # Core statistics
        self.vpip = 0.0  # Voluntarily Put $ In Pot
        self.pfr = 0.0   # Pre-Flop Raise
        self.three_bet = 0.0  # 3-bet percentage
        self.fold_to_three_bet = 0.0
        self.steal_attempt = 0.0  # Steal attempt from late position
        
        # Postflop statistics
        self.cbet_flop = 0.0  # Continuation bet on flop
        self.cbet_turn = 0.0  # Continuation bet on turn
        self.fold_to_cbet_flop = 0.0
        self.fold_to_cbet_turn = 0.0
        self.double_barrel = 0.0  # Bet flop and turn
        self.triple_barrel = 0.0  # Bet flop, turn, and river
        
        # Showdown statistics
        self.wtsd = 0.0  # Went To ShowDown
        self.w_sd = 0.0  # Won at ShowDown
        self.showdown_hands = []
        
        # Aggression statistics
        self.aggression_factor = 0.0  # (Bets + Raises) / Calls
        self.aggression_frequency = 0.0  # (Bets + Raises) / (Bets + Raises + Calls)
        
        # Betting patterns
        self.avg_bet_size = defaultdict(float)  # By street
        self.bet_size_variance = defaultdict(float)
        self.pot_size_betting = defaultdict(list)  # Bet sizes relative to pot
          # Position-based statistics
        self.position_stats = defaultdict(lambda: defaultdict(float))
          # Street-based statistics
        self.street_stats = {
            'preflop': {
                'aggressive_actions': 0,
                'passive_actions': 0,
                'total_actions': 0
            },
            'flop': {
                'aggressive_actions': 0,
                'passive_actions': 0,
                'total_actions': 0
            },
            'turn': {
                'aggressive_actions': 0,
                'passive_actions': 0,
                'total_actions': 0
            },
            'river': {
                'aggressive_actions': 0,
                'passive_actions': 0,
                'total_actions': 0
            }        }
        
        # Timing patterns
        self.decision_times = deque(maxlen=30)
        self.avg_decision_time = 0.0
        self.quick_decisions = 0  # Decisions under 2 seconds
        self.slow_decisions = 0   # Decisions over 10 seconds
        
        # Advanced patterns
        self.bluff_frequency = 0.0
        self.value_bet_frequency = 0.0
        self.check_raise_frequency = 0.0
        self.donk_bet_frequency = 0.0  # Leading into preflop aggressor
        
        # Stack management
        self.stack_sizes = deque(maxlen=20)
        self.avg_stack_size = 0.0
        self.all_in_frequency = 0.0
        
        # Playing style
        self.playing_style = PlayingStyle.UNKNOWN
        self.style_confidence = 0.0
        self.style_history = deque(maxlen=10)  # Track style changes
        
        # Tendencies by situation
        self.situational_stats = {
            'short_stack': defaultdict(float),  # M < 10
            'medium_stack': defaultdict(float), # 10 <= M <= 20
            'deep_stack': defaultdict(float),   # M > 20
            'heads_up': defaultdict(float),
            'multiway': defaultdict(float)
        }
        
        # Session tracking
        self.session_profit = 0.0
        self.session_start_stack = 0.0
        self.hands_this_session = 0
        
    def add_action(self, action_data: ActionData):
        """Add a new action to the profile."""
        self.recent_actions.append(action_data)
        self.last_updated = time.time()
        
        # Update decision timing
        if action_data.decision_time > 0:
            self.decision_times.append(action_data.decision_time)
            self._update_timing_stats()
            
        # Update stack tracking
        if action_data.stack_size > 0:
            self.stack_sizes.append(action_data.stack_size)
            self._update_stack_stats()
            
        # Update betting patterns
        if action_data.action_type in ['bet', 'raise'] and action_data.amount > 0:
            self._update_betting_patterns(action_data)
            
        # Update position statistics
        self._update_position_stats(action_data)
        
        # Update street-specific statistics
        self._update_street_stats(action_data)
        
        logger.debug(f"Added action for {self.player_name}: {action_data.action_type} on {action_data.street}")
        
    def add_hand_data(self, hand_data: HandData):
        """Add complete hand data."""
        self.hands_data.append(hand_data)
        self.total_hands_observed += 1
        self.hands_this_session += 1
        
        # Update profit tracking
        profit = hand_data.ending_stack - hand_data.starting_stack
        self.session_profit += profit
        
        # Update showdown statistics
        if hand_data.went_to_showdown:
            self.showdown_hands.append(hand_data)
            self._update_showdown_stats()
            
        # Recalculate all statistics
        self._recalculate_statistics()
        
        logger.debug(f"Added hand data for {self.player_name}: {hand_data.hand_id}")
        
    def _update_timing_stats(self):
        """Update timing-related statistics."""
        if self.decision_times:
            self.avg_decision_time = statistics.mean(self.decision_times)
            
            # Count quick and slow decisions
            quick_count = sum(1 for t in self.decision_times if t < 2.0)
            slow_count = sum(1 for t in self.decision_times if t > 10.0)
            
            total_decisions = len(self.decision_times)
            self.quick_decisions = quick_count / total_decisions if total_decisions > 0 else 0
            self.slow_decisions = slow_count / total_decisions if total_decisions > 0 else 0
            
    def _update_stack_stats(self):
        """Update stack-related statistics."""
        if self.stack_sizes:
            self.avg_stack_size = statistics.mean(self.stack_sizes)
            
    def _update_betting_patterns(self, action_data: ActionData):
        """Update betting pattern analysis."""
        street = action_data.street
        bet_amount = action_data.amount
        pot_size = action_data.pot_size_before
        
        # Update average bet size
        if street in self.avg_bet_size:
            # Running average
            count = len([a for a in self.recent_actions if a.street == street and a.action_type in ['bet', 'raise']])
            self.avg_bet_size[street] = ((self.avg_bet_size[street] * (count - 1)) + bet_amount) / count
        else:
            self.avg_bet_size[street] = bet_amount
            
        # Track bet size relative to pot
        if pot_size > 0:
            bet_ratio = bet_amount / pot_size
            self.pot_size_betting[street].append(bet_ratio)
            if len(self.pot_size_betting[street]) > 20:
                self.pot_size_betting[street].pop(0)
                
    def _update_position_stats(self, action_data: ActionData):
        """Update position-based statistics."""
        position = action_data.position
        action_type = action_data.action_type
        
        # Count total actions from this position
        self.position_stats[position]['total_actions'] += 1
        
        # Count specific action types
        self.position_stats[position][action_type] += 1
        
        # Special cases
        if action_data.street == 'preflop':
            if action_type in ['call', 'raise']:
                self.position_stats[position]['vpip_actions'] += 1
            if action_type == 'raise':
                self.position_stats[position]['pfr_actions'] += 1
                
    def _update_street_stats(self, action_data: ActionData):
        """Update street-specific statistics."""
        street = action_data.street
        action_type = action_data.action_type
        
        # Track aggression by street
        if action_type in ['bet', 'raise']:
            self.street_stats[street]['aggressive_actions'] += 1
        elif action_type in ['call', 'check', 'fold']:
            self.street_stats[street]['passive_actions'] += 1
            
        self.street_stats[street]['total_actions'] += 1
        
    def _update_showdown_stats(self):
        """Update showdown-related statistics."""
        if not self.showdown_hands:
            return
            
        total_showdowns = len(self.showdown_hands)
        won_showdowns = sum(1 for hand in self.showdown_hands if hand.won_hand)
        
        self.w_sd = won_showdowns / total_showdowns if total_showdowns > 0 else 0
        
        # WTSD calculation (hands that went to showdown / hands played)
        if self.total_hands_observed > 0:
            self.wtsd = total_showdowns / self.total_hands_observed
            
    def _recalculate_statistics(self):
        """Recalculate all derived statistics."""
        if not self.hands_data:
            return
            
        # Calculate VPIP and PFR
        preflop_hands = [h for h in self.hands_data if any(a.street == 'preflop' for a in h.actions)]
        
        if preflop_hands:
            vpip_hands = sum(1 for hand in preflop_hands 
                           if any(a.action_type in ['call', 'raise'] for a in hand.actions if a.street == 'preflop'))
            pfr_hands = sum(1 for hand in preflop_hands 
                          if any(a.action_type == 'raise' for a in hand.actions if a.street == 'preflop'))
            
            self.vpip = vpip_hands / len(preflop_hands)
            self.pfr = pfr_hands / len(preflop_hands)
            
        # Calculate aggression factor
        all_actions = [a for hand in self.hands_data for a in hand.actions]
        aggressive_actions = sum(1 for a in all_actions if a.action_type in ['bet', 'raise'])
        passive_actions = sum(1 for a in all_actions if a.action_type == 'call')
        
        if passive_actions > 0:
            self.aggression_factor = aggressive_actions / passive_actions
        else:
            self.aggression_factor = aggressive_actions  # No calls = very aggressive
            
        # Calculate aggression frequency
        total_non_fold = aggressive_actions + passive_actions
        if total_non_fold > 0:
            self.aggression_frequency = aggressive_actions / total_non_fold
            
        # Update playing style
        self._classify_playing_style()
        
    def _classify_playing_style(self):
        """Classify the opponent's playing style."""
        if self.total_hands_observed < 10:
            self.playing_style = PlayingStyle.UNKNOWN
            self.style_confidence = 0.0
            return
            
        # Define thresholds
        tight_vpip_threshold = 0.20
        loose_vpip_threshold = 0.35
        aggressive_af_threshold = 1.5
        very_aggressive_af_threshold = 3.0
        
        is_tight = self.vpip < tight_vpip_threshold
        is_loose = self.vpip > loose_vpip_threshold
        is_aggressive = self.aggression_factor > aggressive_af_threshold
        is_very_aggressive = self.aggression_factor > very_aggressive_af_threshold
        
        # Classify style
        if is_very_aggressive and is_loose:
            new_style = PlayingStyle.MANIAC
        elif is_tight and self.vpip < 0.10 and self.aggression_factor < 0.5:
            new_style = PlayingStyle.ROCK
        elif is_tight and is_aggressive:
            new_style = PlayingStyle.TIGHT_AGGRESSIVE
        elif is_tight and not is_aggressive:
            new_style = PlayingStyle.TIGHT_PASSIVE
        elif is_loose and is_aggressive:
            new_style = PlayingStyle.LOOSE_AGGRESSIVE
        elif is_loose and not is_aggressive:
            new_style = PlayingStyle.LOOSE_PASSIVE
        else:
            new_style = PlayingStyle.UNKNOWN
            
        # Update style with confidence
        if new_style != self.playing_style:
            self.style_history.append(new_style)
            self.playing_style = new_style
            
        # Calculate confidence based on sample size and consistency
        sample_confidence = min(1.0, self.total_hands_observed / 50.0)
        
        if len(self.style_history) >= 3:
            recent_styles = list(self.style_history)[-3:]
            consistency = sum(1 for s in recent_styles if s == new_style) / len(recent_styles)
        else:
            consistency = 0.5
            
        self.style_confidence = sample_confidence * consistency
        
    def get_exploitative_recommendations(self) -> Dict[str, str]:
        """Get recommendations for exploiting this opponent."""
        recommendations = {}
        
        if self.style_confidence < 0.3:
            recommendations['general'] = "Insufficient data - play standard strategy"
            return recommendations
            
        style = self.playing_style
        
        if style == PlayingStyle.TIGHT_PASSIVE:
            recommendations.update({
                'preflop': "Steal blinds frequently, avoid bluffing postflop",
                'postflop': "Value bet thinly, rarely bluff",
                'general': "Apply pressure, they fold too much"
            })
        elif style == PlayingStyle.TIGHT_AGGRESSIVE:
            recommendations.update({
                'preflop': "Respect their raises, 3-bet light occasionally",
                'postflop': "Don't bluff catch, value bet strong hands",
                'general': "Play straightforward, avoid fancy plays"
            })
        elif style == PlayingStyle.LOOSE_PASSIVE:
            recommendations.update({
                'preflop': "Value bet wider range, avoid bluffs",
                'postflop': "Bet for value frequently, check weak hands",
                'general': "Extract maximum value, they call too much"
            })
        elif style == PlayingStyle.LOOSE_AGGRESSIVE:
            recommendations.update({
                'preflop': "Tighten up, let them bluff into you",
                'postflop': "Call down lighter, check-call more",
                'general': "Trap them with strong hands"
            })
        elif style == PlayingStyle.MANIAC:
            recommendations.update({
                'preflop': "Play very tight, only premium hands",
                'postflop': "Let them hang themselves, rarely fold strong hands",
                'general': "Wait for big hands and get paid"
            })
        elif style == PlayingStyle.ROCK:
            recommendations.update({
                'preflop': "Steal constantly, fold to any aggression",
                'postflop': "Bluff frequently, they rarely have anything",
                'general': "Maximum aggression - they're too tight"
            })
            
        return recommendations
        
    def get_statistical_summary(self) -> Dict:
        """Get comprehensive statistical summary."""
        return {
            'basic_stats': {
                'hands_observed': self.total_hands_observed,
                'vpip': f"{self.vpip:.1%}",
                'pfr': f"{self.pfr:.1%}",
                'aggression_factor': f"{self.aggression_factor:.2f}",
                'wtsd': f"{self.wtsd:.1%}",
                'w_sd': f"{self.w_sd:.1%}"
            },
            'playing_style': {
                'style': self.playing_style.value,
                'confidence': f"{self.style_confidence:.1%}"
            },
            'betting_patterns': {
                'avg_bet_size': dict(self.avg_bet_size),
                'avg_decision_time': f"{self.avg_decision_time:.1f}s",
                'quick_decisions': f"{self.quick_decisions:.1%}"
            },
            'profitability': {
                'session_profit': self.session_profit,
                'hands_this_session': self.hands_this_session,
                'avg_stack_size': self.avg_stack_size
            }
        }
        
    def save_to_file(self, filename: str):
        """Save profile data to file."""
        try:
            data = {
                'player_name': self.player_name,
                'basic_stats': self.get_statistical_summary(),
                'created_time': self.created_time,
                'last_updated': self.last_updated
            }
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving opponent profile: {e}")

class EnhancedOpponentTracker:
    """Enhanced opponent tracker managing multiple opponent profiles."""
    
    def __init__(self, config: Dict = None, logger_instance: logging.Logger = None):
        self.config = config or {}
        self.logger = logger_instance or logging.getLogger(__name__)
        
        self.opponents = {}  # player_name -> EnhancedOpponentProfile
        self.session_start_time = time.time()
        self.hands_this_session = 0
        
        # Configuration
        self.min_hands_for_stats = self.config.get('min_hands_for_stats', 20)
        self.max_opponents_tracked = self.config.get('max_opponents_tracked', 50)
        
        # Table dynamics
        self.table_style = PlayingStyle.UNKNOWN
        self.table_aggression = 0.0
        self.average_vpip = 0.0
        
        self.logger.info("Enhanced opponent tracker initialized")
        
    def get_or_create_opponent(self, player_name: str) -> EnhancedOpponentProfile:
        """Get existing opponent profile or create new one."""
        if player_name not in self.opponents:
            if len(self.opponents) >= self.max_opponents_tracked:
                # Remove oldest opponent
                oldest_name = min(self.opponents.keys(), 
                                key=lambda name: self.opponents[name].last_updated)
                del self.opponents[oldest_name]
                self.logger.info(f"Removed oldest opponent profile: {oldest_name}")
                
            self.opponents[player_name] = EnhancedOpponentProfile(player_name)
            self.logger.info(f"Created new opponent profile: {player_name}")
            
        return self.opponents[player_name]
        
    def log_action(self, player_name: str, action_type: str, street: str, 
                  position: str = "unknown", amount: float = 0.0, 
                  pot_size_before_action: float = 0.0, stack_size: float = 0.0,
                  hand_id: str = "", decision_time: float = 0.0):
        """Log an action for an opponent."""
        
        opponent = self.get_or_create_opponent(player_name)
        
        action_data = ActionData(
            action_type=action_type,
            amount=amount,
            street=street,
            position=position,
            pot_size_before=pot_size_before_action,
            stack_size=stack_size,
            timestamp=time.time(),
            hand_id=hand_id,
            decision_time=decision_time
        )
        
        opponent.add_action(action_data)
        self._update_table_dynamics()
        
        self.logger.debug(f"Logged action for {player_name}: {action_type} on {street}")
        
    def get_opponent_analysis(self, player_name: str) -> Dict:
        """Get comprehensive analysis for an opponent."""
        if player_name not in self.opponents:
            return {
                'available': False,
                'reason': 'No data available',
                'recommendations': {'general': 'Play standard strategy'}
            }
            
        opponent = self.opponents[player_name]
        
        if opponent.total_hands_observed < self.min_hands_for_stats:
            return {
                'available': True,
                'insufficient_data': True,
                'hands_observed': opponent.total_hands_observed,
                'min_required': self.min_hands_for_stats,
                'preliminary_style': opponent.playing_style.value,
                'recommendations': {'general': 'Gathering data - play standard strategy'}
            }
            
        return {
            'available': True,
            'sufficient_data': True,
            'profile': opponent.get_statistical_summary(),
            'recommendations': opponent.get_exploitative_recommendations(),
            'reliability': opponent.style_confidence
        }
        
    def get_table_dynamics(self) -> Dict:
        """Analyze overall table dynamics."""
        if not self.opponents:
            return {
                'table_style': 'unknown',
                'aggression_level': 'medium',
                'average_vpip': 0.25,
                'recommendations': 'Insufficient data'
            }
            
        # Calculate table averages
        valid_opponents = [opp for opp in self.opponents.values() 
                          if opp.total_hands_observed >= 5]
        
        if not valid_opponents:
            return {
                'table_style': 'unknown',
                'aggression_level': 'medium',
                'average_vpip': 0.25,
                'recommendations': 'Gathering table data'
            }
            
        avg_vpip = statistics.mean([opp.vpip for opp in valid_opponents])
        avg_aggression = statistics.mean([opp.aggression_factor for opp in valid_opponents])
        
        # Classify table
        if avg_vpip < 0.20:
            table_style = 'tight'
        elif avg_vpip > 0.35:
            table_style = 'loose'
        else:
            table_style = 'normal'
            
        if avg_aggression < 1.0:
            aggression_level = 'passive'
        elif avg_aggression > 2.0:
            aggression_level = 'aggressive'
        else:
            aggression_level = 'normal'
            
        # Generate recommendations
        recommendations = self._get_table_recommendations(table_style, aggression_level)
        
        return {
            'table_style': table_style,
            'aggression_level': aggression_level,
            'average_vpip': avg_vpip,
            'average_aggression': avg_aggression,
            'active_opponents': len(valid_opponents),
            'recommendations': recommendations
        }
        
    def _update_table_dynamics(self):
        """Update overall table dynamics."""
        valid_opponents = [opp for opp in self.opponents.values() 
                          if opp.total_hands_observed >= 5]
        
        if valid_opponents:
            self.average_vpip = statistics.mean([opp.vpip for opp in valid_opponents])
            self.table_aggression = statistics.mean([opp.aggression_factor for opp in valid_opponents])
            
    def _get_table_recommendations(self, table_style: str, aggression_level: str) -> str:
        """Get strategic recommendations based on table dynamics."""
        if table_style == 'tight' and aggression_level == 'passive':
            return "Loosen up preflop, steal blinds frequently, bluff more postflop"
        elif table_style == 'tight' and aggression_level == 'aggressive':
            return "Play premium hands, avoid bluffs, let them do the betting"
        elif table_style == 'loose' and aggression_level == 'passive':
            return "Value bet wider, avoid bluffs, extract maximum value"
        elif table_style == 'loose' and aggression_level == 'aggressive':
            return "Tighten up significantly, call down lighter with strong hands"
        else:
            return "Play balanced strategy, adapt to individual opponents"
            
    def save_session_data(self, filename: str = None):
        """Save session data for all opponents."""
        if not filename:
            timestamp = int(time.time())
            filename = f"opponent_data_{timestamp}.json"
            
        try:
            session_data = {
                'session_start': self.session_start_time,
                'session_end': time.time(),
                'hands_played': self.hands_this_session,
                'table_dynamics': self.get_table_dynamics(),
                'opponents': {
                    name: profile.get_statistical_summary() 
                    for name, profile in self.opponents.items()
                }
            }
            
            with open(filename, 'w') as f:
                json.dump(session_data, f, indent=2)
                
            self.logger.info(f"Saved session data to {filename}")
            
        except Exception as e:
            self.logger.error(f"Error saving session data: {e}")

def create_enhanced_opponent_tracker(config: Dict = None, logger_instance: logging.Logger = None) -> EnhancedOpponentTracker:
    """Factory function to create enhanced opponent tracker."""
    return EnhancedOpponentTracker(config, logger_instance)
