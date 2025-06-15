# performance_monitor.py
"""
Real-time performance monitoring and adaptive strategy adjustments.
"""

import logging
import time
import json
import statistics
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)

class PerformanceMetric(Enum):
    WIN_RATE = "win_rate"
    PROFIT_LOSS = "profit_loss"
    VPIP = "vpip"
    PFR = "pfr"
    AGGRESSION_FACTOR = "aggression_factor"
    HANDS_PER_HOUR = "hands_per_hour"
    AVERAGE_POT_SIZE = "avg_pot_size"
    BIGGEST_WIN = "biggest_win"
    BIGGEST_LOSS = "biggest_loss"
    BLUFF_SUCCESS_RATE = "bluff_success_rate"

@dataclass
class HandPerformance:
    """Performance data for a single hand."""
    hand_id: str
    timestamp: float
    starting_stack: float
    ending_stack: float
    profit_loss: float
    position: str
    actions_taken: List[str]
    hand_strength: str
    win_probability_avg: float
    decision_quality_score: float
    bluffs_attempted: int
    bluffs_successful: int
    pot_size: float
    opponents_count: int

@dataclass
class SessionMetrics:
    """Metrics for the current session."""
    start_time: float
    hands_played: int
    total_profit: float
    win_rate: float
    vpip: float
    pfr: float
    aggression_factor: float
    avg_pot_size: float
    biggest_win: float
    biggest_loss: float
    bluff_attempts: int
    successful_bluffs: int
    hands_per_hour: float
    current_streak: int  # Positive for winning streak, negative for losing

class PerformanceMonitor:
    """Monitor and analyze bot performance in real-time."""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Performance tracking
        self.hand_history = deque(maxlen=500)  # Store recent hands
        self.session_start_time = time.time()
        self.current_session_hands = 0
        
        # Real-time metrics
        self.current_streak = 0
        self.longest_winning_streak = 0
        self.longest_losing_streak = 0
        
        # Rolling windows for trend analysis
        self.short_term_window = deque(maxlen=20)   # Last 20 hands
        self.medium_term_window = deque(maxlen=100) # Last 100 hands
        self.long_term_window = deque(maxlen=500)   # Last 500 hands
        
        # Performance targets and thresholds
        self.performance_targets = {
            'win_rate': 0.55,
            'profit_per_hour': 5.0,  # Big blinds per hour
            'vpip_target': 0.25,
            'pfr_target': 0.18,
            'aggression_target': 1.2
        }
        
        # Adaptive strategy parameters
        self.strategy_adjustments = {
            'aggression_multiplier': 1.0,
            'bluff_frequency_multiplier': 1.0,
            'tightness_adjustment': 0.0,
            'position_adjustment': 0.0
        }
        
        # Alerts and notifications
        self.performance_alerts = []
        self.last_alert_time = 0.0
        
        self.logger.info("Performance monitor initialized")
        
    def record_hand_result(self, hand_performance: HandPerformance):
        """Record the result of a completed hand."""
        self.hand_history.append(hand_performance)
        self.current_session_hands += 1
        
        # Update all rolling windows
        self.short_term_window.append(hand_performance)
        self.medium_term_window.append(hand_performance)
        self.long_term_window.append(hand_performance)
        
        # Update streak tracking
        self._update_streaks(hand_performance)
        
        # Check for performance alerts
        self._check_performance_alerts()
        
        # Update adaptive strategy
        self._update_adaptive_strategy()
        
        self.logger.debug(f"Recorded hand result: {hand_performance.hand_id}, P/L: {hand_performance.profit_loss:.2f}")
        
    def get_current_metrics(self) -> SessionMetrics:
        """Get current session metrics."""
        if not self.hand_history:
            return self._create_empty_metrics()
            
        hands = list(self.hand_history)
        session_time = time.time() - self.session_start_time
        
        # Calculate basic metrics
        total_profit = sum(h.profit_loss for h in hands)
        wins = sum(1 for h in hands if h.profit_loss > 0)
        total_hands = len(hands)
        win_rate = wins / total_hands if total_hands > 0 else 0
        
        # Calculate VPIP and PFR
        preflop_actions = [h for h in hands if any(action in ['call', 'raise'] for action in h.actions_taken)]
        vpip = len(preflop_actions) / total_hands if total_hands > 0 else 0
        
        pfr_actions = [h for h in hands if 'raise' in h.actions_taken]
        pfr = len(pfr_actions) / total_hands if total_hands > 0 else 0
        
        # Calculate aggression factor
        aggressive_actions = sum(h.actions_taken.count('raise') + h.actions_taken.count('bet') for h in hands)
        passive_actions = sum(h.actions_taken.count('call') for h in hands)
        aggression_factor = aggressive_actions / max(1, passive_actions)
        
        # Calculate other metrics
        avg_pot_size = statistics.mean([h.pot_size for h in hands]) if hands else 0
        biggest_win = max([h.profit_loss for h in hands], default=0)
        biggest_loss = min([h.profit_loss for h in hands], default=0)
        
        # Bluff statistics
        total_bluff_attempts = sum(h.bluffs_attempted for h in hands)
        successful_bluffs = sum(h.bluffs_successful for h in hands)
        
        # Hands per hour
        hours_played = session_time / 3600
        hands_per_hour = total_hands / hours_played if hours_played > 0 else 0
        
        return SessionMetrics(
            start_time=self.session_start_time,
            hands_played=total_hands,
            total_profit=total_profit,
            win_rate=win_rate,
            vpip=vpip,
            pfr=pfr,
            aggression_factor=aggression_factor,
            avg_pot_size=avg_pot_size,
            biggest_win=biggest_win,
            biggest_loss=biggest_loss,
            bluff_attempts=total_bluff_attempts,
            successful_bluffs=successful_bluffs,
            hands_per_hour=hands_per_hour,
            current_streak=self.current_streak
        )
        
    def get_performance_trends(self) -> Dict:
        """Analyze performance trends across different time windows."""
        if len(self.hand_history) < 10:
            return {'insufficient_data': True}
            
        trends = {}
        
        # Analyze each time window
        for window_name, window_data in [
            ('short_term', self.short_term_window),
            ('medium_term', self.medium_term_window),
            ('long_term', self.long_term_window)
        ]:
            if len(window_data) >= 5:
                window_profit = sum(h.profit_loss for h in window_data)
                window_win_rate = sum(1 for h in window_data if h.profit_loss > 0) / len(window_data)
                avg_decision_quality = statistics.mean([h.decision_quality_score for h in window_data])
                
                trends[window_name] = {
                    'profit': window_profit,
                    'win_rate': window_win_rate,
                    'hands': len(window_data),
                    'avg_decision_quality': avg_decision_quality
                }
                
        # Calculate trend direction
        if 'short_term' in trends and 'medium_term' in trends:
            profit_trend = 'improving' if trends['short_term']['profit'] > trends['medium_term']['profit'] / 2 else 'declining'
            wr_trend = 'improving' if trends['short_term']['win_rate'] > trends['medium_term']['win_rate'] else 'declining'
            
            trends['analysis'] = {
                'profit_trend': profit_trend,
                'win_rate_trend': wr_trend,
                'overall_trend': 'positive' if profit_trend == 'improving' and wr_trend == 'improving' else 'negative'
            }
            
        return trends
        
    def get_strategy_recommendations(self) -> Dict[str, str]:
        """Get strategy recommendations based on performance analysis."""
        metrics = self.get_current_metrics()
        trends = self.get_performance_trends()
        recommendations = {}
        
        # Check if we have enough data
        if metrics.hands_played < 20:
            recommendations['general'] = "Continue playing - gathering performance data"
            return recommendations
            
        # Analyze win rate
        if metrics.win_rate < 0.45:
            recommendations['win_rate'] = "Win rate below target - consider tightening preflop range"
        elif metrics.win_rate > 0.65:
            recommendations['win_rate'] = "Excellent win rate - consider loosening up to increase volume"
            
        # Analyze VPIP
        if metrics.vpip < 0.18:
            recommendations['vpip'] = "Playing too tight - consider expanding preflop range"
        elif metrics.vpip > 0.35:
            recommendations['vpip'] = "Playing too loose - consider tightening preflop range"
            
        # Analyze aggression
        if metrics.aggression_factor < 0.8:
            recommendations['aggression'] = "Too passive - increase betting and raising frequency"
        elif metrics.aggression_factor > 2.5:
            recommendations['aggression'] = "Too aggressive - consider calling more, betting less"
            
        # Analyze profit trend
        if trends.get('analysis', {}).get('profit_trend') == 'declining':
            recommendations['trend'] = "Declining profit trend - review recent decisions and tighten play"
            
        # Analyze streaks
        if self.current_streak < -5:
            recommendations['streak'] = "Long losing streak - take a break or tighten up significantly"
        elif self.current_streak > 10:
            recommendations['streak'] = "Hot streak - maintain current strategy"
            
        # Bluff analysis
        if metrics.bluff_attempts > 0:
            bluff_success_rate = metrics.successful_bluffs / metrics.bluff_attempts
            if bluff_success_rate < 0.3:
                recommendations['bluffing'] = "Low bluff success rate - reduce bluff frequency"
            elif bluff_success_rate > 0.7:
                recommendations['bluffing'] = "High bluff success rate - consider increasing bluff frequency"
                
        return recommendations
        
    def get_adaptive_adjustments(self) -> Dict[str, float]:
        """Get current adaptive strategy adjustments."""
        return self.strategy_adjustments.copy()
        
    def _update_streaks(self, hand_performance: HandPerformance):
        """Update winning/losing streak tracking."""
        if hand_performance.profit_loss > 0:
            if self.current_streak >= 0:
                self.current_streak += 1
            else:
                self.current_streak = 1
            self.longest_winning_streak = max(self.longest_winning_streak, self.current_streak)
        elif hand_performance.profit_loss < 0:
            if self.current_streak <= 0:
                self.current_streak -= 1
            else:
                self.current_streak = -1
            self.longest_losing_streak = min(self.longest_losing_streak, self.current_streak)
        # Break even hands don't change streak
        
    def _update_adaptive_strategy(self):
        """Update adaptive strategy parameters based on performance."""
        metrics = self.get_current_metrics()
        
        if metrics.hands_played < 30:
            return  # Not enough data
            
        # Adjust aggression based on win rate
        if metrics.win_rate < 0.4:
            self.strategy_adjustments['aggression_multiplier'] = max(0.5, self.strategy_adjustments['aggression_multiplier'] * 0.95)
        elif metrics.win_rate > 0.65:
            self.strategy_adjustments['aggression_multiplier'] = min(1.5, self.strategy_adjustments['aggression_multiplier'] * 1.02)
            
        # Adjust bluffing based on success rate
        if metrics.bluff_attempts > 5:
            bluff_success_rate = metrics.successful_bluffs / metrics.bluff_attempts
            if bluff_success_rate < 0.25:
                self.strategy_adjustments['bluff_frequency_multiplier'] = max(0.3, self.strategy_adjustments['bluff_frequency_multiplier'] * 0.9)
            elif bluff_success_rate > 0.6:
                self.strategy_adjustments['bluff_frequency_multiplier'] = min(2.0, self.strategy_adjustments['bluff_frequency_multiplier'] * 1.1)
                
        # Adjust tightness based on VPIP performance
        if metrics.vpip > 0.35 and metrics.win_rate < 0.5:
            self.strategy_adjustments['tightness_adjustment'] = min(0.1, self.strategy_adjustments['tightness_adjustment'] + 0.01)
        elif metrics.vpip < 0.15 and metrics.win_rate > 0.6:
            self.strategy_adjustments['tightness_adjustment'] = max(-0.1, self.strategy_adjustments['tightness_adjustment'] - 0.01)
            
    def _check_performance_alerts(self):
        """Check for performance issues that require immediate attention."""
        current_time = time.time()
        
        # Don't spam alerts
        if current_time - self.last_alert_time < 300:  # 5 minutes
            return
            
        metrics = self.get_current_metrics()
        new_alerts = []
        
        # Check for dangerous losing streak
        if self.current_streak <= -8:
            new_alerts.append(f"ALERT: Losing streak of {abs(self.current_streak)} hands - consider taking a break")
            
        # Check for dramatic profit loss
        if len(self.short_term_window) >= 10:
            recent_profit = sum(h.profit_loss for h in list(self.short_term_window)[-10:])
            if recent_profit < -20:  # Lost more than 20 big blinds in last 10 hands
                new_alerts.append(f"ALERT: Large recent losses ({recent_profit:.1f} BB in last 10 hands)")
                
        # Check for very low win rate
        if metrics.hands_played >= 30 and metrics.win_rate < 0.3:
            new_alerts.append(f"ALERT: Very low win rate ({metrics.win_rate:.1%}) - review strategy")
            
        # Check for extremely passive play
        if metrics.hands_played >= 20 and metrics.aggression_factor < 0.3:
            new_alerts.append("ALERT: Extremely passive play - increase aggression")
            
        if new_alerts:
            self.performance_alerts.extend(new_alerts)
            self.last_alert_time = current_time
            for alert in new_alerts:
                self.logger.warning(alert)
                
    def _create_empty_metrics(self) -> SessionMetrics:
        """Create empty metrics object."""
        return SessionMetrics(
            start_time=self.session_start_time,
            hands_played=0,
            total_profit=0.0,
            win_rate=0.0,
            vpip=0.0,
            pfr=0.0,
            aggression_factor=0.0,
            avg_pot_size=0.0,
            biggest_win=0.0,
            biggest_loss=0.0,
            bluff_attempts=0,
            successful_bluffs=0,
            hands_per_hour=0.0,
            current_streak=0
        )
        
    def generate_performance_report(self) -> str:
        """Generate a comprehensive performance report."""
        metrics = self.get_current_metrics()
        trends = self.get_performance_trends()
        recommendations = self.get_strategy_recommendations()
        
        report = []
        report.append("=== POKER BOT PERFORMANCE REPORT ===")
        report.append("")
        
        # Session overview
        session_duration = (time.time() - self.session_start_time) / 3600
        report.append(f"Session Duration: {session_duration:.1f} hours")
        report.append(f"Hands Played: {metrics.hands_played}")
        report.append("")
        
        # Financial performance
        report.append("=== FINANCIAL PERFORMANCE ===")
        report.append(f"Total Profit/Loss: {metrics.total_profit:+.2f} BB")
        report.append(f"BB/Hour: {metrics.total_profit/session_duration:+.1f}")
        report.append(f"Win Rate: {metrics.win_rate:.1%}")
        report.append(f"Biggest Win: +{metrics.biggest_win:.2f} BB")
        report.append(f"Biggest Loss: {metrics.biggest_loss:-.2f} BB")
        report.append("")
        
        # Playing statistics
        report.append("=== PLAYING STATISTICS ===")
        report.append(f"VPIP: {metrics.vpip:.1%}")
        report.append(f"PFR: {metrics.pfr:.1%}")
        report.append(f"Aggression Factor: {metrics.aggression_factor:.2f}")
        report.append(f"Average Pot Size: {metrics.avg_pot_size:.2f} BB")
        report.append(f"Hands/Hour: {metrics.hands_per_hour:.1f}")
        report.append("")
        
        # Bluffing statistics
        if metrics.bluff_attempts > 0:
            bluff_success = metrics.successful_bluffs / metrics.bluff_attempts
            report.append("=== BLUFFING STATISTICS ===")
            report.append(f"Bluff Attempts: {metrics.bluff_attempts}")
            report.append(f"Successful Bluffs: {metrics.successful_bluffs}")
            report.append(f"Bluff Success Rate: {bluff_success:.1%}")
            report.append("")
            
        # Trend analysis
        if not trends.get('insufficient_data'):
            report.append("=== TREND ANALYSIS ===")
            if 'analysis' in trends:
                report.append(f"Profit Trend: {trends['analysis']['profit_trend'].title()}")
                report.append(f"Win Rate Trend: {trends['analysis']['win_rate_trend'].title()}")
                report.append(f"Overall Trend: {trends['analysis']['overall_trend'].title()}")
            report.append("")
            
        # Current streak
        if abs(self.current_streak) >= 3:
            streak_type = "winning" if self.current_streak > 0 else "losing"
            report.append(f"=== CURRENT STREAK ===")
            report.append(f"{streak_type.title()} streak: {abs(self.current_streak)} hands")
            report.append("")
            
        # Recommendations
        if recommendations:
            report.append("=== RECOMMENDATIONS ===")
            for category, recommendation in recommendations.items():
                report.append(f"{category.title()}: {recommendation}")
            report.append("")
            
        # Alerts
        if self.performance_alerts:
            report.append("=== RECENT ALERTS ===")
            for alert in self.performance_alerts[-5:]:  # Last 5 alerts
                report.append(alert)
            report.append("")
            
        return "\n".join(report)
        
    def save_performance_data(self, filename: str = None):
        """Save performance data to file."""
        if not filename:
            timestamp = int(time.time())
            filename = f"performance_data_{timestamp}.json"
            
        try:
            data = {
                'session_metrics': asdict(self.get_current_metrics()),
                'trends': self.get_performance_trends(),
                'recommendations': self.get_strategy_recommendations(),
                'adaptive_adjustments': self.get_adaptive_adjustments(),
                'alerts': self.performance_alerts,
                'hand_count': len(self.hand_history)
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
                
            self.logger.info(f"Saved performance data to {filename}")
            
        except Exception as e:
            self.logger.error(f"Error saving performance data: {e}")

def create_performance_monitor(config: Dict = None) -> PerformanceMonitor:
    """Factory function to create performance monitor."""
    return PerformanceMonitor(config)
