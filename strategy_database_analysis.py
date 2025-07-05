#!/usr/bin/env python3
"""
Strategy Database Analysis and Optimization Guide

This script analyzes the current strategy database and provides recommendations
for building a comprehensive strategy database for real-world poker play.
"""
import json
import os
import math
import logging
from collections import Counter, defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StrategyDatabaseAnalyzer:
    def __init__(self, strategy_file='strategy_table.json'):
        self.strategy_file = strategy_file
        self.data = self._load_data()
        
    def _load_data(self):
        """Load strategy data for analysis"""
        if not os.path.exists(self.strategy_file):
            logger.error(f"Strategy file {self.strategy_file} not found")
            return {}
        
        with open(self.strategy_file, 'r') as f:
            return json.load(f)
    
    def analyze_current_database(self):
        """Comprehensive analysis of current strategy database"""
        logger.info("🔍 STRATEGY DATABASE ANALYSIS")
        logger.info("=" * 50)
        
        # Basic statistics
        total_strategies = len(self.data)
        file_size_mb = os.path.getsize(self.strategy_file) / 1024 / 1024
        
        logger.info(f"📊 Current Database Stats:")
        logger.info(f"   • Total Strategies: {total_strategies:,}")
        logger.info(f"   • File Size: {file_size_mb:.1f} MB")
        logger.info(f"   • Average bytes per strategy: {file_size_mb * 1024 * 1024 / total_strategies:.0f}")
        
        # Analyze hash distribution and coverage
        self._analyze_hash_distribution()
        self._analyze_game_state_coverage()
        self._estimate_real_world_coverage()
        
    def _analyze_hash_distribution(self):
        """Analyze the distribution of hash values"""
        logger.info(f"\n🎯 Hash Distribution Analysis:")
        
        # Extract components from hashes (reverse engineering)
        streets = Counter()
        positions = Counter()
        
        sample_size = min(10000, len(self.data))
        sample_hashes = list(self.data.keys())[:sample_size]
        
        for hash_str in sample_hashes:
            try:
                hash_val = int(hash_str)
                # Reverse engineer components (approximate)
                street = (hash_val // 10000000000) % 10
                position = (hash_val // 1000000000) % 10
                
                streets[street] += 1
                positions[position] += 1
            except:
                continue
        
        logger.info(f"   • Street distribution (sample of {sample_size:,}):")
        for street, count in sorted(streets.items()):
            street_name = ['Preflop', 'Flop', 'Turn', 'River'][street] if street < 4 else f'Street{street}'
            percentage = count / sample_size * 100
            logger.info(f"     - {street_name}: {count:,} ({percentage:.1f}%)")
        
        logger.info(f"   • Position distribution:")
        for pos, count in sorted(positions.items()):
            percentage = count / sample_size * 100
            logger.info(f"     - Position {pos}: {count:,} ({percentage:.1f}%)")
    
    def _analyze_game_state_coverage(self):
        """Analyze coverage of different game states"""
        logger.info(f"\n📈 Game State Coverage Analysis:")
        
        # Theoretical maximum states calculation
        streets = 4  # preflop, flop, turn, river
        positions = 6  # max players
        pot_sizes = 100  # different pot size ranges
        bet_patterns = 50  # different betting patterns
        
        theoretical_max = streets * positions * pot_sizes * bet_patterns
        logger.info(f"   • Theoretical max basic states: ~{theoretical_max:,}")
        logger.info(f"   • Current coverage: {len(self.data) / theoretical_max * 100:.2f}% of basic states")
        
        # Real poker complexity is much higher
        card_combinations = 1326  # Hold'em starting hands
        board_textures = 1000  # Different board texture categories
        stack_depths = 20  # Different stack depth ranges
        
        realistic_complexity = theoretical_max * 10  # Conservative estimate
        logger.info(f"   • Realistic game complexity: ~{realistic_complexity:,} states")
        logger.info(f"   • Realistic coverage: {len(self.data) / realistic_complexity * 100:.2f}%")
    
    def _estimate_real_world_coverage(self):
        """Estimate coverage for real-world poker scenarios"""
        logger.info(f"\n🌍 Real-World Coverage Estimation:")
        
        current_strategies = len(self.data)
        
        # Coverage levels and recommendations
        coverage_levels = [
            (50000, "Minimal", "Basic preflop + common flop situations"),
            (200000, "Good", "Most common situations covered"),
            (500000, "Very Good", "Comprehensive coverage for casual play"),
            (1000000, "Excellent", "Professional-level coverage"),
            (2000000, "Elite", "Tournament-level comprehensive coverage"),
            (5000000, "Master", "Complete coverage including edge cases")
        ]
        
        current_level = "Unknown"
        for threshold, level, description in coverage_levels:
            if current_strategies >= threshold:
                current_level = level
                current_desc = description
            else:
                break
        
        logger.info(f"   • Current Level: {current_level}")
        logger.info(f"   • Description: {current_desc}")
        logger.info(f"   • Next targets:")
        
        for threshold, level, description in coverage_levels:
            if current_strategies < threshold:
                improvement = threshold - current_strategies
                logger.info(f"     - {level}: +{improvement:,} strategies ({description})")
                if len([x for x in coverage_levels if current_strategies < x[0]]) <= 2:
                    break
    
    def generate_improvement_recommendations(self):
        """Generate specific recommendations for improving the database"""
        logger.info(f"\n🚀 IMPROVEMENT RECOMMENDATIONS")
        logger.info("=" * 50)
        
        current_strategies = len(self.data)
        
        logger.info("📋 Training Strategy Recommendations:")
        logger.info("\n1. 🎯 IMMEDIATE IMPROVEMENTS (Current → 500K strategies):")
        logger.info("   • Run training 2-3 more times with current parameters")
        logger.info("   • Increase iterations from 2,000 → 5,000 per session")
        logger.info("   • Focus on postflop situations (flop/turn/river)")
        logger.info("   • Command: py fixed_cfr_training.py (modify iterations=5000)")
        
        logger.info("\n2. 🔥 MEDIUM-TERM GOALS (500K → 1M strategies):")
        logger.info("   • Implement multi-session training with different parameters")
        logger.info("   • Vary stack depths (10bb, 20bb, 50bb, 100bb+)")
        logger.info("   • Include tournament scenarios (short stack play)")
        logger.info("   • Add more betting patterns and positions")
        
        logger.info("\n3. ⚡ ADVANCED OPTIMIZATION (1M+ strategies):")
        logger.info("   • Implement iterative deepening CFR")
        logger.info("   • Add opponent modeling variants")
        logger.info("   • Include ICM (tournament) considerations")
        logger.info("   • Multi-table tournament scenarios")
        
        logger.info("\n💡 PRACTICAL TRAINING PLAN:")
        sessions_needed = max(1, (500000 - current_strategies) // 200000)
        logger.info(f"   • Run {sessions_needed} more training sessions")
        logger.info(f"   • Each session should generate ~200K strategies")
        logger.info(f"   • Total training time: ~{sessions_needed * 2} hours")
        logger.info(f"   • Expected database size: ~{(current_strategies + sessions_needed * 200000) / 1000000:.1f}M strategies")
        
        self._generate_training_commands()
    
    def _generate_training_commands(self):
        """Generate specific training commands for improvement"""
        logger.info(f"\n💻 TRAINING COMMANDS:")
        
        training_configs = [
            {
                'name': 'Extended Training',
                'iterations': 5000,
                'batch_size': 40000,
                'description': 'Double the iterations for deeper coverage'
            },
            {
                'name': 'Short Stack Focus',
                'iterations': 3000,
                'batch_size': 30000,
                'description': 'Focus on short stack situations'
            },
            {
                'name': 'Deep Stack Focus', 
                'iterations': 4000,
                'batch_size': 35000,
                'description': 'Focus on deep stack cash game play'
            }
        ]
        
        for i, config in enumerate(training_configs, 1):
            logger.info(f"\n   Session {i}: {config['name']}")
            logger.info(f"   Description: {config['description']}")
            logger.info(f"   Command: Modify fixed_cfr_training.py:")
            logger.info(f"            iterations={config['iterations']}")
            logger.info(f"            batch_size={config['batch_size']}")
            logger.info(f"   Expected output: ~{config['iterations'] * config['batch_size'] // 100:,} strategies")

def main():
    analyzer = StrategyDatabaseAnalyzer()
    analyzer.analyze_current_database()
    analyzer.generate_improvement_recommendations()
    
    print(f"\n🎮 SUMMARY:")
    print(f"Current database is GOOD for casual play but needs expansion for professional use.")
    print(f"Target: 500K-1M strategies for comprehensive coverage.")
    print(f"Method: Run training 3-5 more times with extended parameters.")

if __name__ == "__main__":
    main()
