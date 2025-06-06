# A/B Testing Framework for Poker Bot Strategy Validation

import logging
import json
import time
import statistics
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class StrategyTest:
    """Represents a single A/B test for strategy comparison."""
    
    def __init__(self, test_name: str, strategy_a_name: str, strategy_b_name: str):
        self.test_name = test_name
        self.strategy_a_name = strategy_a_name
        self.strategy_b_name = strategy_b_name
        self.strategy_a_results = []
        self.strategy_b_results = []
        self.start_time = datetime.now()
        
    def add_result(self, strategy: str, result: Dict[str, Any]):
        """Add a game result for the specified strategy."""
        result['timestamp'] = datetime.now().isoformat()
        
        if strategy == 'A':
            self.strategy_a_results.append(result)
        elif strategy == 'B':
            self.strategy_b_results.append(result)
        else:
            logger.warning(f"Unknown strategy: {strategy}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Calculate statistics for both strategies."""
        def calc_stats(results: List[Dict]) -> Dict:
            if not results:
                return {'count': 0, 'mean_profit': 0, 'win_rate': 0, 'std_dev': 0}
            
            profits = [r.get('profit', 0) for r in results]
            wins = [r.get('won', False) for r in results]
            
            return {
                'count': len(results),
                'mean_profit': statistics.mean(profits) if profits else 0,
                'win_rate': sum(wins) / len(wins) if wins else 0,
                'std_dev': statistics.stdev(profits) if len(profits) > 1 else 0,
                'total_profit': sum(profits)
            }
        
        stats_a = calc_stats(self.strategy_a_results)
        stats_b = calc_stats(self.strategy_b_results)
        
        # Calculate statistical significance (simplified t-test)
        if stats_a['count'] > 10 and stats_b['count'] > 10:
            profit_diff = stats_a['mean_profit'] - stats_b['mean_profit']
            pooled_std = ((stats_a['std_dev'] ** 2) + (stats_b['std_dev'] ** 2)) ** 0.5
            
            if pooled_std > 0:
                t_statistic = profit_diff / (pooled_std * ((1/stats_a['count']) + (1/stats_b['count'])) ** 0.5)
                significant = abs(t_statistic) > 2.0  # Rough significance threshold
            else:
                significant = False
        else:
            significant = False
        
        return {
            'strategy_a': stats_a,
            'strategy_b': stats_b,
            'statistical_significance': significant,
            'recommendation': self._get_recommendation(stats_a, stats_b, significant)
        }
    
    def _get_recommendation(self, stats_a: Dict, stats_b: Dict, significant: bool) -> str:
        """Generate recommendation based on test results."""
        if not significant:
            return "Insufficient data or no significant difference"
        
        if stats_a['mean_profit'] > stats_b['mean_profit']:
            improvement = ((stats_a['mean_profit'] - stats_b['mean_profit']) / abs(stats_b['mean_profit'])) * 100
            return f"Strategy A ({self.strategy_a_name}) is superior by {improvement:.1f}%"
        else:
            improvement = ((stats_b['mean_profit'] - stats_a['mean_profit']) / abs(stats_a['mean_profit'])) * 100
            return f"Strategy B ({self.strategy_b_name}) is superior by {improvement:.1f}%"

class StrategyTester:
    """Main class for managing A/B tests of poker strategies."""
    
    def __init__(self, results_file: str = "strategy_test_results.json"):
        self.results_file = results_file
        self.active_tests: Dict[str, StrategyTest] = {}
        self.completed_tests: List[StrategyTest] = []
        
    def create_test(self, test_name: str, strategy_a_name: str, strategy_b_name: str) -> StrategyTest:
        """Create a new A/B test."""
        test = StrategyTest(test_name, strategy_a_name, strategy_b_name)
        self.active_tests[test_name] = test
        logger.info(f"Created new strategy test: {test_name} ({strategy_a_name} vs {strategy_b_name})")
        return test
    
    def record_game_result(self, test_name: str, strategy: str, game_result: Dict[str, Any]):
        """Record the result of a game for a specific test and strategy."""
        if test_name in self.active_tests:
            self.active_tests[test_name].add_result(strategy, game_result)
            logger.debug(f"Recorded result for {test_name}, strategy {strategy}")
        else:
            logger.warning(f"Test {test_name} not found")
    
    def analyze_test(self, test_name: str) -> Dict[str, Any]:
        """Analyze the results of a specific test."""
        if test_name not in self.active_tests:
            logger.error(f"Test {test_name} not found")
            return {}
        
        test = self.active_tests[test_name]
        stats = test.get_statistics()
        
        logger.info(f"Analysis for {test_name}:")
        logger.info(f"  Strategy A ({test.strategy_a_name}): {stats['strategy_a']['count']} games, "
                   f"${stats['strategy_a']['mean_profit']:.2f} avg profit")
        logger.info(f"  Strategy B ({test.strategy_b_name}): {stats['strategy_b']['count']} games, "
                   f"${stats['strategy_b']['mean_profit']:.2f} avg profit")
        logger.info(f"  Recommendation: {stats['recommendation']}")
        
        return stats
    
    def complete_test(self, test_name: str):
        """Mark a test as completed and move it to completed tests."""
        if test_name in self.active_tests:
            test = self.active_tests.pop(test_name)
            self.completed_tests.append(test)
            self.save_results()
            logger.info(f"Completed test: {test_name}")
    
    def save_results(self):
        """Save test results to file."""
        try:
            results = {
                'active_tests': {name: self._serialize_test(test) for name, test in self.active_tests.items()},
                'completed_tests': [self._serialize_test(test) for test in self.completed_tests],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.results_file, 'w') as f:
                json.dump(results, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save test results: {e}")
    
    def _serialize_test(self, test: StrategyTest) -> Dict:
        """Convert test object to serializable dictionary."""
        return {
            'test_name': test.test_name,
            'strategy_a_name': test.strategy_a_name,
            'strategy_b_name': test.strategy_b_name,
            'strategy_a_results': test.strategy_a_results,
            'strategy_b_results': test.strategy_b_results,
            'start_time': test.start_time.isoformat(),
            'statistics': test.get_statistics()
        }
    
    def get_all_test_summaries(self) -> Dict[str, Any]:
        """Get summary of all tests (active and completed)."""
        summaries = {}
        
        for name, test in self.active_tests.items():
            stats = test.get_statistics()
            summaries[name] = {
                'status': 'active',
                'games_a': stats['strategy_a']['count'],
                'games_b': stats['strategy_b']['count'],
                'profit_diff': stats['strategy_a']['mean_profit'] - stats['strategy_b']['mean_profit'],
                'recommendation': stats['recommendation']
            }
        
        for test in self.completed_tests:
            stats = test.get_statistics()
            summaries[test.test_name] = {
                'status': 'completed',
                'games_a': stats['strategy_a']['count'],
                'games_b': stats['strategy_b']['count'],
                'profit_diff': stats['strategy_a']['mean_profit'] - stats['strategy_b']['mean_profit'],
                'recommendation': stats['recommendation']
            }
        
        return summaries

# Example usage and testing scenarios
def create_sample_tests():
    """Create sample A/B tests for common strategy comparisons."""
    tester = StrategyTester()
    
    # Test 1: Preflop range tightness
    tester.create_test(
        "preflop_range_comparison",
        "tight_ranges",
        "loose_ranges"
    )
    
    # Test 2: Bet sizing strategy
    tester.create_test(
        "bet_sizing_comparison", 
        "conservative_sizing",
        "aggressive_sizing"
    )
    
    # Test 3: Opponent modeling impact
    tester.create_test(
        "opponent_modeling_impact",
        "without_opponent_tracking",
        "with_opponent_tracking"
    )
    
    return tester

if __name__ == "__main__":
    # Example of how to use the testing framework
    tester = create_sample_tests()
    
    # Simulate some test results
    test_result = {
        'profit': 25.50,
        'won': True,
        'hands_played': 150,
        'vpip': 0.22,
        'pfr': 0.18
    }
    
    tester.record_game_result("preflop_range_comparison", "A", test_result)
    analysis = tester.analyze_test("preflop_range_comparison")
    print(f"Test analysis: {analysis}")
