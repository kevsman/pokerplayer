# session_performance_tracker.py
"""
Session performance tracking and adaptive strategy system.
Tracks win rates, decision outcomes, and adjusts strategy dynamically.
"""

import logging
import time
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class HandResult:
    """Track individual hand results."""
    hand_id: str
    starting_stack: float = 0.0
    ending_stack: float = 0.0
    pot_won: float = 0.0
    actions_taken: List = None
    hand_strength: str = 'unknown'
    opponent_types: List = None
    start_time: float = None
    end_time: float = None
    position: str = 'unknown'
    profit_loss: float = None
    win_probability_estimates: List[float] = None
    final_outcome: str = 'unknown'  # 'win', 'loss', 'fold'
    showdown: bool = False
    
    def __post_init__(self):
        if self.actions_taken is None:
            self.actions_taken = []
        if self.opponent_types is None:
            self.opponent_types = []
        if self.win_probability_estimates is None:
            self.win_probability_estimates = []
        if self.start_time is None:
            self.start_time = time.time()
        if self.end_time is None:
            self.end_time = time.time()
        if self.profit_loss is None:
            self.profit_loss = self.ending_stack - self.starting_stack
    
class SessionPerformanceTracker:
    """Track session performance and provide adaptive recommendations."""
    
    def __init__(self, session_file: str = "session_performance.json"):
        self.session_file = session_file
        self.session_start_time = time.time()
        self.hands_played = []
        self.decisions_made = defaultdict(int)
        self.decision_outcomes = defaultdict(list)
        self.hourly_performance = defaultdict(list)
        self.opponent_adjustments = defaultdict(dict)
        
        # Performance metrics
        self.starting_bankroll = 0.0
        self.current_bankroll = 0.0
        self.peak_bankroll = 0.0
        self.valley_bankroll = 0.0
        
        # Recent performance tracking (for adaptive adjustments)
        self.recent_hands = deque(maxlen=50)  # Last 50 hands
        self.recent_decisions = deque(maxlen=100)  # Last 100 decisions
        
        # Load previous session data if available
        self._load_session_data()
        
        logger.info("Session performance tracker initialized")
    
    def start_new_session(self, starting_stack: float):
        """Start a new poker session."""
        self.session_start_time = time.time()
        self.starting_bankroll = starting_stack
        self.current_bankroll = starting_stack
        self.peak_bankroll = starting_stack
        self.valley_bankroll = starting_stack
        
        logger.info(f"New session started with ${starting_stack:.2f}")
    
    def record_hand_result(self, hand_result: HandResult):
        """Record the result of a completed hand."""
        self.hands_played.append(hand_result)
        self.recent_hands.append(hand_result)
        
        # Update bankroll tracking
        profit_loss = hand_result.profit_loss
        self.current_bankroll += profit_loss
        
        if self.current_bankroll > self.peak_bankroll:
            self.peak_bankroll = self.current_bankroll
        if self.current_bankroll < self.valley_bankroll:
            self.valley_bankroll = self.current_bankroll
        
        # Track hourly performance
        hour = int((time.time() - self.session_start_time) / 3600)
        self.hourly_performance[hour].append(profit_loss)
        
        logger.info(f"Hand {hand_result.hand_id} recorded: {profit_loss:+.2f} "
                   f"(Total: ${self.current_bankroll:.2f})")
          # Check for performance patterns
        self._analyze_recent_performance()
    
    def record_decision(self, decision_type: str, context: Dict, outcome: Optional[str] = None):
        """Record a decision made during play."""
        # Handle case where context is a string instead of dict
        if isinstance(context, str):
            context = {'description': context}
        elif not isinstance(context, dict):
            context = {'unknown': str(context)}
        
        decision_record = {
            'type': decision_type,
            'context': context,
            'outcome': outcome,
            'timestamp': time.time()
        }
        
        self.decisions_made[decision_type] += 1
        self.recent_decisions.append(decision_record)
        
        if outcome:
            self.decision_outcomes[decision_type].append(outcome)
        
        logger.debug(f"Decision recorded: {decision_type} -> {outcome}")
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get comprehensive session statistics."""
        session_duration = time.time() - self.session_start_time
        hands_count = len(self.hands_played)
        
        # Basic stats
        total_profit = self.current_bankroll - self.starting_bankroll
        win_rate = self._calculate_win_rate()
        hands_per_hour = (hands_count / (session_duration / 3600)) if session_duration > 0 else 0
        bb_per_hour = self._calculate_bb_per_hour()
          # Advanced stats
        vpip = self._calculate_vpip()
        pfr = self._calculate_pfr()
        aggression_factor = self._calculate_aggression_factor()
        
        return {
            'session_duration_minutes': session_duration / 60,
            'hands_played': hands_count,
            'starting_bankroll': self.starting_bankroll,
            'current_bankroll': self.current_bankroll,
            'peak_bankroll': self.peak_bankroll,
            'valley_bankroll': self.valley_bankroll,
            'total_profit': total_profit,
            'net_profit': total_profit,  # Alias for compatibility
            'roi_percentage': (total_profit / self.starting_bankroll * 100) if self.starting_bankroll > 0 else 0,
            'win_rate': win_rate,
            'hands_per_hour': hands_per_hour,
            'bb_per_hour': bb_per_hour,
            'vpip': vpip,
            'pfr': pfr,
            'aggression_factor': aggression_factor,
            'decision_breakdown': dict(self.decisions_made),
            'recent_trend': self._get_recent_trend()
        }
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Alias for get_session_statistics for backward compatibility."""
        return self.get_session_statistics()
    
    def get_adaptive_recommendations(self) -> Dict[str, Any]:
        """Get recommendations for strategy adjustments based on performance."""
        recommendations = {
            'overall_strategy': 'maintain',
            'aggression_adjustment': 0.0,
            'position_adjustments': {},
            'opponent_exploits': {},
            'risk_management': 'normal',
            'reasoning': []
        }
        
        # Analyze recent performance for recommendations
        if len(self.recent_hands) >= 10:
            recent_profit = sum(hand.profit_loss for hand in list(self.recent_hands)[-10:])
            
            if recent_profit < -5.0:  # Losing streak
                recommendations.update({
                    'overall_strategy': 'tighten_up',
                    'aggression_adjustment': -0.2,
                    'risk_management': 'conservative'
                })
                recommendations['reasoning'].append("Recent losses suggest tightening up")
            
            elif recent_profit > 5.0:  # Winning streak
                recommendations.update({
                    'overall_strategy': 'maintain_aggression',
                    'aggression_adjustment': 0.1,
                    'risk_management': 'standard'
                })
                recommendations['reasoning'].append("Recent wins suggest maintaining current strategy")
        
        # Check decision success rates
        self._analyze_decision_effectiveness(recommendations)
          # Position-specific adjustments
        self._analyze_positional_performance(recommendations)
        
        return recommendations
    
    def _calculate_win_rate(self) -> float:
        """Calculate win rate (hands won / hands played to showdown)."""
        try:
            showdown_hands = []
            for h in self.hands_played:
                # Handle case where h might be a string or invalid object
                if hasattr(h, 'showdown') and hasattr(h, 'final_outcome'):
                    if getattr(h, 'showdown', False):
                        showdown_hands.append(h)
            
            if not showdown_hands:
                return 0.0
            
            wins = 0
            for h in showdown_hands:
                if getattr(h, 'final_outcome', '') == 'win':
                    wins += 1
            
            return wins / len(showdown_hands) * 100
        except Exception as e:
            logger.debug(f"Error calculating win rate: {e}")
            return 0.0
    
    def _calculate_bb_per_hour(self) -> float:
        """Calculate big blinds per hour (assuming $0.02 big blind for micro stakes)."""
        session_duration_hours = (time.time() - self.session_start_time) / 3600
        if session_duration_hours <= 0:
            return 0.0
        
        total_profit = self.current_bankroll - self.starting_bankroll
        big_blind = 0.02  # Micro stakes assumption
        
        return (total_profit / big_blind) / session_duration_hours
    
    def _calculate_vpip(self) -> float:
        """Calculate VPIP (Voluntarily Put money In Pot)."""
        preflop_opportunities = 0
        vpip_actions = 0
        
        for hand in self.hands_played:
            # Handle both string actions and dict actions
            preflop_actions = []
            for action in hand.actions_taken:
                if isinstance(action, dict):
                    if action.get('street') == 'preflop':
                        preflop_actions.append(action)
                elif isinstance(action, str):
                    # Assume string actions are preflop for simplicity
                    preflop_actions.append({'action_type': action.upper(), 'street': 'preflop'})
            
            if preflop_actions:
                preflop_opportunities += 1
                # Check if we voluntarily put money in (call/bet/raise, not forced blind)
                voluntary_actions = [a for a in preflop_actions 
                                   if a.get('action_type') in ['CALL', 'BET', 'RAISE']]
                if voluntary_actions:
                    vpip_actions += 1
        
        return (vpip_actions / preflop_opportunities * 100) if preflop_opportunities > 0 else 0
    
    def _calculate_pfr(self) -> float:
        """Calculate PFR (Preflop Raise)."""
        preflop_opportunities = 0
        pfr_actions = 0
        
        for hand in self.hands_played:
            # Handle both string actions and dict actions
            preflop_actions = []
            for action in hand.actions_taken:
                if isinstance(action, dict):
                    if action.get('street') == 'preflop':
                        preflop_actions.append(action)
                elif isinstance(action, str):
                    # Assume string actions are preflop for simplicity
                    preflop_actions.append({'action_type': action.upper(), 'street': 'preflop'})
            
            if preflop_actions:
                preflop_opportunities += 1
                raise_actions = [a for a in preflop_actions 
                               if a.get('action_type') in ['BET', 'RAISE']]
                if raise_actions:
                    pfr_actions += 1
        
        return (pfr_actions / preflop_opportunities * 100) if preflop_opportunities > 0 else 0
    
    def _calculate_aggression_factor(self) -> float:
        """Calculate aggression factor (bets+raises)/(calls)."""
        aggressive_actions = 0
        passive_actions = 0
        
        for hand in self.hands_played:
            for action in hand.actions_taken:
                # Handle both string actions and dict actions
                if isinstance(action, dict):
                    if action.get('action_type') in ['BET', 'RAISE']:
                        aggressive_actions += 1
                    elif action.get('action_type') == 'CALL':
                        passive_actions += 1
                elif isinstance(action, str):
                    # Handle string actions
                    action_upper = action.upper()
                    if action_upper in ['BET', 'RAISE']:
                        aggressive_actions += 1
                    elif action_upper == 'CALL':
                        passive_actions += 1
        
        return aggressive_actions / max(passive_actions, 1)
    
    def _get_recent_trend(self) -> str:
        """Analyze recent performance trend."""
        if len(self.recent_hands) < 5:
            return "insufficient_data"
        
        recent_profits = [hand.profit_loss for hand in list(self.recent_hands)[-5:]]
        total_recent = sum(recent_profits)
        
        if total_recent > 2.0:
            return "strong_upward"
        elif total_recent > 0.5:
            return "upward"
        elif total_recent > -0.5:
            return "stable"
        elif total_recent > -2.0:
            return "downward"
        else:
            return "strong_downward"
    
    def _analyze_recent_performance(self):
        """Analyze recent performance for adaptive adjustments."""
        if len(self.recent_hands) < 10:
            return
        
        # Check for tilt indicators
        recent_losses = sum(1 for hand in list(self.recent_hands)[-5:] 
                          if hand.profit_loss < 0)
        
        if recent_losses >= 4:
            logger.warning("Possible tilt detected - consider taking a break")
        
        # Check for decision pattern issues
        recent_folds = sum(1 for hand in list(self.recent_hands)[-10:] 
                         if hand.final_outcome == 'fold')
        
        if recent_folds >= 8:
            logger.info("High fold rate detected - consider loosening up")
        elif recent_folds <= 2:
            logger.info("Low fold rate detected - consider tightening up")
    
    def _analyze_decision_effectiveness(self, recommendations: Dict):
        """Analyze effectiveness of different decision types."""
        if len(self.recent_decisions) < 20:
            return
        
        # Analyze bluff success rate
        bluff_decisions = [d for d in self.recent_decisions 
                         if d['type'] == 'bluff' and d.get('outcome')]
        if bluff_decisions:
            bluff_success_rate = sum(1 for d in bluff_decisions 
                                   if d['outcome'] == 'success') / len(bluff_decisions)
            
            if bluff_success_rate < 0.3:
                recommendations['reasoning'].append("Low bluff success rate - reduce bluffing")
            elif bluff_success_rate > 0.7:
                recommendations['reasoning'].append("High bluff success rate - can bluff more")
        
        # Analyze value betting effectiveness
        value_decisions = [d for d in self.recent_decisions 
                         if d['type'] == 'value_bet' and d.get('outcome')]
        if value_decisions:
            value_success_rate = sum(1 for d in value_decisions 
                                   if d['outcome'] == 'success') / len(value_decisions)
            
            if value_success_rate < 0.6:
                recommendations['reasoning'].append("Value bets not getting called - bet smaller")
    
    def _analyze_positional_performance(self, recommendations: Dict):
        """Analyze performance by position."""
        position_profits = defaultdict(list)
        
        for hand in self.hands_played:
            position_profits[hand.position].append(hand.profit_loss)
        
        for position, profits in position_profits.items():
            if len(profits) >= 5:  # Minimum sample size
                avg_profit = sum(profits) / len(profits)
                
                if avg_profit < -0.5:
                    recommendations['position_adjustments'][position] = "play_tighter"
                elif avg_profit > 0.5:
                    recommendations['position_adjustments'][position] = "can_loosen_slightly"
    
    def _load_session_data(self):
        """Load previous session data if available."""
        try:
            with open(self.session_file, 'r') as f:
                data = json.load(f)
                # Load relevant data for continuation
                logger.info("Previous session data loaded")
        except FileNotFoundError:
            logger.info("No previous session data found - starting fresh")
        except Exception as e:
            logger.warning(f"Error loading session data: {e}")
    
    def save_session_data(self):
        """Save current session data."""
        try:
            session_data = {
                'session_start_time': self.session_start_time,
                'hands_played_count': len(self.hands_played),
                'total_decisions': sum(self.decisions_made.values()),
                'final_bankroll': self.current_bankroll,
                'session_profit': self.current_bankroll - self.starting_bankroll,
                'statistics': self.get_session_statistics(),
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
                
            logger.info(f"Session data saved to {self.session_file}")
            
        except Exception as e:
            logger.error(f"Error saving session data: {e}")
    
    def generate_session_report(self) -> str:
        """Generate a comprehensive session report."""
        stats = self.get_session_statistics()
        recommendations = self.get_adaptive_recommendations()
        
        report = f"""
=== POKER SESSION REPORT ===
Session Duration: {stats['session_duration_minutes']:.1f} minutes
Hands Played: {stats['hands_played']}

=== FINANCIAL PERFORMANCE ===
Starting Bankroll: ${stats['starting_bankroll']:.2f}
Current Bankroll: ${stats['current_bankroll']:.2f}
Total Profit/Loss: ${stats['total_profit']:+.2f}
ROI: {stats['roi_percentage']:+.1f}%
BB/Hour: {stats['bb_per_hour']:+.1f}

=== PLAYING STATISTICS ===
VPIP: {stats['vpip']:.1f}%
PFR: {stats['pfr']:.1f}%
Aggression Factor: {stats['aggression_factor']:.2f}
Win Rate: {stats['win_rate']:.1f}%
Hands/Hour: {stats['hands_per_hour']:.1f}

=== RECENT TREND ===
{stats['recent_trend'].replace('_', ' ').title()}

=== RECOMMENDATIONS ===
Overall Strategy: {recommendations['overall_strategy'].replace('_', ' ').title()}
Risk Management: {recommendations['risk_management'].title()}
"""
        
        if recommendations['reasoning']:
            report += "\nKey Insights:\n"
            for reason in recommendations['reasoning']:
                report += f"• {reason}\n"
        
        return report

# Global session tracker instance
session_tracker = SessionPerformanceTracker()

def get_session_tracker() -> SessionPerformanceTracker:
    """Get the global session tracker instance."""
    return session_tracker
