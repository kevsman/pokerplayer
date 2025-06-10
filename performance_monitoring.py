# performance_monitoring.py
"""
Performance monitoring system for tracking poker bot improvements.
Collects metrics, analyzes performance trends, and provides actionable insights.
"""

import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque
import statistics

logger = logging.getLogger(__name__)

class PerformanceMetrics:
    """Tracks detailed performance metrics."""
    
    def __init__(self, data_file: str = "performance_data.json"):
        self.data_file = data_file
        self.session_data = {
            'session_id': datetime.now().isoformat(),
            'start_time': datetime.now().isoformat(),
            'hands_played': 0,
            'total_winnings': 0.0,
            'decisions': [],
            'improvements_active': []
        }
        
        # Load historical data
        self.historical_data = self._load_historical_data()
        
        # Real-time tracking
        self.recent_results = deque(maxlen=100)  # Last 100 hands
        self.decision_quality_scores = deque(maxlen=50)
        
    def _load_historical_data(self) -> List[Dict]:
        """Load historical performance data."""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.warning(f"Could not load historical data: {e}")
            return []
    
    def record_hand_result(self, hand_id: str, result: Dict):
        """Record the result of a poker hand."""
        hand_data = {
            'hand_id': hand_id,
            'timestamp': datetime.now().isoformat(),
            'result': result.get('winnings', 0.0),
            'position': result.get('position'),
            'hand_strength': result.get('hand_strength'),
            'action_taken': result.get('action_taken'),
            'pot_size': result.get('pot_size', 0.0),
            'opponents_count': result.get('opponents_count', 0),
            'improvements_used': result.get('improvements_used', [])
        }
        
        self.session_data['hands_played'] += 1
        self.session_data['total_winnings'] += hand_data['result']
        self.session_data['decisions'].append(hand_data)
        
        # Update real-time tracking
        self.recent_results.append(hand_data['result'])
        
        # Calculate decision quality score
        quality_score = self._calculate_decision_quality(hand_data)
        self.decision_quality_scores.append(quality_score)
    
    def _calculate_decision_quality(self, hand_data: Dict) -> float:
        """Calculate a quality score for the decision (0-1 scale)."""
        # Simplified decision quality based on multiple factors
        score = 0.5  # Start neutral
        
        # Position-based adjustments
        if hand_data.get('position') in ['BTN', 'CO']:
            score += 0.1  # Bonus for good position
        elif hand_data.get('position') in ['UTG', 'UTG+1']:
            score -= 0.1  # Penalty for early position
        
        # Result-based adjustment (careful not to overweight short-term results)
        if hand_data['result'] > 0:
            score += 0.2
        elif hand_data['result'] < 0:
            score -= 0.1  # Smaller penalty for losses (variance)
        
        # Hand strength vs action consistency
        hand_strength = hand_data.get('hand_strength')
        action = hand_data.get('action_taken')
        
        if hand_strength in ['very_strong', 'strong'] and action in ['bet', 'raise']:
            score += 0.2
        elif hand_strength in ['very_weak'] and action == 'fold':
            score += 0.1
        elif hand_strength in ['very_strong'] and action == 'fold':
            score -= 0.3  # Major penalty for folding strong hands
        
        return max(0.0, min(1.0, score))  # Clamp to 0-1
    
    def get_session_summary(self) -> Dict:
        """Get current session performance summary."""
        if not self.session_data['decisions']:
            return {'status': 'no_data'}
        
        # Calculate key metrics
        win_rate = sum(1 for d in self.session_data['decisions'] if d['result'] > 0) / len(self.session_data['decisions'])
        avg_decision_quality = statistics.mean(self.decision_quality_scores) if self.decision_quality_scores else 0.5
        
        # Recent performance (last 20 hands)
        recent_hands = self.session_data['decisions'][-20:] if len(self.session_data['decisions']) >= 20 else self.session_data['decisions']
        recent_winnings = sum(d['result'] for d in recent_hands)
        
        return {
            'hands_played': self.session_data['hands_played'],
            'total_winnings': round(self.session_data['total_winnings'], 2),
            'win_rate': round(win_rate * 100, 1),
            'avg_decision_quality': round(avg_decision_quality, 3),
            'recent_trend': 'positive' if recent_winnings > 0 else 'negative',
            'recent_winnings': round(recent_winnings, 2),
            'session_duration': self._get_session_duration(),
            'improvements_impact': self._analyze_improvements_impact()
        }
    
    def _get_session_duration(self) -> str:
        """Get session duration in readable format."""
        start = datetime.fromisoformat(self.session_data['start_time'])
        duration = datetime.now() - start
        
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def _analyze_improvements_impact(self) -> Dict:
        """Analyze the impact of postflop improvements."""
        if not self.session_data['decisions']:
            return {'status': 'insufficient_data'}
        
        # Compare hands with vs without improvements
        improved_hands = [d for d in self.session_data['decisions'] if d.get('improvements_used')]
        baseline_hands = [d for d in self.session_data['decisions'] if not d.get('improvements_used')]
        
        if not improved_hands or not baseline_hands:
            return {'status': 'insufficient_comparison_data'}
        
        improved_avg = statistics.mean(d['result'] for d in improved_hands)
        baseline_avg = statistics.mean(d['result'] for d in baseline_hands)
        
        improvement_delta = improved_avg - baseline_avg
        
        return {
            'improved_hands_count': len(improved_hands),
            'baseline_hands_count': len(baseline_hands),
            'improved_avg_result': round(improved_avg, 3),
            'baseline_avg_result': round(baseline_avg, 3),
            'improvement_delta': round(improvement_delta, 3),
            'improvement_percentage': round((improvement_delta / abs(baseline_avg)) * 100, 1) if baseline_avg != 0 else 0
        }
    
    def save_session_data(self):
        """Save current session to historical data."""
        try:
            self.session_data['end_time'] = datetime.now().isoformat()
            self.historical_data.append(self.session_data.copy())
            
            # Keep only last 100 sessions
            if len(self.historical_data) > 100:
                self.historical_data = self.historical_data[-100:]
            
            with open(self.data_file, 'w') as f:
                json.dump(self.historical_data, f, indent=2)
                
            logger.info(f"Session data saved: {self.session_data['hands_played']} hands, {self.session_data['total_winnings']:.2f} winnings")
            
        except Exception as e:
            logger.error(f"Failed to save session data: {e}")
    
    def get_long_term_trends(self, days: int = 7) -> Dict:
        """Get performance trends over specified period."""
        if not self.historical_data:
            return {'status': 'no_historical_data'}
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        recent_sessions = [
            s for s in self.historical_data 
            if datetime.fromisoformat(s['start_time']) > cutoff_date
        ]
        
        if not recent_sessions:
            return {'status': 'insufficient_recent_data'}
        
        total_hands = sum(s['hands_played'] for s in recent_sessions)
        total_winnings = sum(s['total_winnings'] for s in recent_sessions)
        
        # Calculate daily averages
        daily_winnings = [s['total_winnings'] for s in recent_sessions]
        daily_hands = [s['hands_played'] for s in recent_sessions]
        
        return {
            'period_days': days,
            'total_sessions': len(recent_sessions),
            'total_hands': total_hands,
            'total_winnings': round(total_winnings, 2),
            'avg_daily_winnings': round(statistics.mean(daily_winnings), 2),
            'avg_daily_hands': round(statistics.mean(daily_hands), 1),            'winnings_per_hand': round(total_winnings / total_hands, 4) if total_hands > 0 else 0,
            'consistency_score': round(1 - (statistics.stdev(daily_winnings) / abs(statistics.mean(daily_winnings))), 3) if len(daily_winnings) > 1 and statistics.mean(daily_winnings) != 0 else 0
        }
    
    def check_performance_alerts(self) -> List[Dict]:
        """Check for performance alerts using the PerformanceAlerts system."""
        alerts_system = PerformanceAlerts(self)
        return alerts_system.check_alerts()


class PerformanceAlerts:
    """System for detecting performance issues and opportunities."""
    
    def __init__(self, metrics: PerformanceMetrics):
        self.metrics = metrics
        self.alert_thresholds = {
            'losing_streak': 10,  # Alert after 10 losing hands
            'low_decision_quality': 0.3,  # Alert if quality drops below 30%
            'significant_loss': -50.0,  # Alert for large losses
            'improvement_failure': 0.1  # Alert if improvements aren't helping
        }
    
    def check_alerts(self) -> List[Dict]:
        """Check for performance alerts."""
        alerts = []
        
        # Check for losing streak
        if len(self.metrics.recent_results) >= 10:
            recent_losses = sum(1 for r in list(self.metrics.recent_results)[-10:] if r < 0)
            if recent_losses >= 8:
                alerts.append({
                    'type': 'losing_streak',
                    'severity': 'warning',
                    'message': f'Lost {recent_losses} of last 10 hands',
                    'recommendation': 'Consider taking a break or reviewing strategy'
                })
        
        # Check decision quality
        if self.metrics.decision_quality_scores:
            recent_quality = statistics.mean(list(self.metrics.decision_quality_scores)[-20:])
            if recent_quality < self.alert_thresholds['low_decision_quality']:
                alerts.append({
                    'type': 'low_decision_quality',
                    'severity': 'warning',
                    'message': f'Decision quality dropped to {recent_quality:.2f}',
                    'recommendation': 'Review recent decisions and strategy'
                })
        
        # Check for significant losses
        session_summary = self.metrics.get_session_summary()
        if session_summary.get('total_winnings', 0) < self.alert_thresholds['significant_loss']:
            alerts.append({
                'type': 'significant_loss',
                'severity': 'critical',
                'message': f'Session loss: {session_summary.get("total_winnings", 0):.2f}',
                'recommendation': 'Consider stopping session and reviewing strategy'
            })
        
        return alerts


class PerformanceReporter:
    """Generates performance reports and insights."""
    
    def __init__(self, metrics: PerformanceMetrics):
        self.metrics = metrics
    
    def generate_session_report(self) -> str:
        """Generate a comprehensive session report."""
        summary = self.metrics.get_session_summary()
        alerts = PerformanceAlerts(self.metrics).check_alerts()
        
        report = f"""
=== POKER BOT PERFORMANCE REPORT ===
Session Duration: {summary.get('session_duration', 'Unknown')}
Hands Played: {summary.get('hands_played', 0)}
Total Winnings: ${summary.get('total_winnings', 0):.2f}
Win Rate: {summary.get('win_rate', 0):.1f}%
Decision Quality: {summary.get('avg_decision_quality', 0):.3f}/1.000

Recent Trend: {summary.get('recent_trend', 'Unknown')}
Recent Winnings (last 20 hands): ${summary.get('recent_winnings', 0):.2f}

=== IMPROVEMENTS IMPACT ==="""
        
        impact = summary.get('improvements_impact', {})
        if impact.get('status') == 'insufficient_data':
            report += "\nInsufficient data to analyze improvements impact"
        else:
            report += f"""
Improved Hands: {impact.get('improved_hands_count', 0)}
Baseline Hands: {impact.get('baseline_hands_count', 0)}
Improvement Delta: ${impact.get('improvement_delta', 0):.3f}
Improvement Percentage: {impact.get('improvement_percentage', 0):.1f}%"""
        
        if alerts:
            report += "\n\n=== ALERTS ==="
            for alert in alerts:
                report += f"\n⚠️  {alert['type'].upper()}: {alert['message']}"
                report += f"\n   Recommendation: {alert['recommendation']}"
        
        return report
    
    def generate_trend_report(self, days: int = 7) -> str:
        """Generate a trend analysis report."""
        trends = self.metrics.get_long_term_trends(days)
        
        if trends.get('status') == 'no_historical_data':
            return "No historical data available for trend analysis"
        
        report = f"""
=== {days}-DAY PERFORMANCE TRENDS ===
Total Sessions: {trends.get('total_sessions', 0)}
Total Hands: {trends.get('total_hands', 0)}
Total Winnings: ${trends.get('total_winnings', 0):.2f}

Daily Averages:
- Winnings: ${trends.get('avg_daily_winnings', 0):.2f}
- Hands: {trends.get('avg_daily_hands', 0):.1f}

Winnings per Hand: ${trends.get('winnings_per_hand', 0):.4f}
Consistency Score: {trends.get('consistency_score', 0):.3f}/1.000
"""
        
        return report


def integrate_performance_monitoring(hand_result: Dict = None, improvements_used: List[str] = None) -> Dict:
    """Integration function for performance monitoring."""
    try:
        # Initialize metrics (in practice, this would be a singleton)
        metrics = PerformanceMetrics()
        
        # If called without arguments, just return current status
        if hand_result is None:
            summary = metrics.get_session_summary()
            return {
                'monitoring_active': True,
                'current_session': summary,
                'status': 'performance_monitoring_active'
            }
        
        # Add improvements info to result
        hand_result['improvements_used'] = improvements_used or []
        
        # Record the hand
        hand_id = f"hand_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        metrics.record_hand_result(hand_id, hand_result)
        
        # Generate quick summary
        summary = metrics.get_session_summary()
        
        return {
            'monitoring_active': True,
            'session_summary': summary,
            'status': 'performance_tracked'
        }
        
    except Exception as e:
        logger.warning(f"Performance monitoring failed: {e}")
        return {
            'monitoring_active': False,
            'status': 'monitoring_failed'
        }


if __name__ == "__main__":
    # Example usage
    metrics = PerformanceMetrics()
    
    # Simulate some hands
    test_results = [
        {'winnings': 5.0, 'position': 'BTN', 'hand_strength': 'strong', 'action_taken': 'bet'},
        {'winnings': -2.0, 'position': 'UTG', 'hand_strength': 'weak', 'action_taken': 'fold'},
        {'winnings': 10.0, 'position': 'CO', 'hand_strength': 'very_strong', 'action_taken': 'raise'}
    ]
    
    for i, result in enumerate(test_results):
        metrics.record_hand_result(f"test_hand_{i}", result)
    
    # Generate reports
    reporter = PerformanceReporter(metrics)
    print(reporter.generate_session_report())
