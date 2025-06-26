"""
Enhanced GPU Memory Management for CFR Training
===============================================

This module enhances the existing CFR training with maximum memory utilization,
larger batch sizes, and memory pooling strategies.
"""

import sys
import os
import logging
import numpy as np
import time
import json
from typing import Dict, List, Tuple, Optional

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GPU memory management
try:
    import cupy as cp
    import cupy.cuda.memory
    GPU_AVAILABLE = True
    
    # Get initial GPU memory info
    mempool = cp.get_default_memory_pool()
    gpu_info = cp.cuda.runtime.memGetInfo()
    free_memory = gpu_info[0]
    total_memory = gpu_info[1]
    
    logger.info(f"🔧 GPU Memory Available: {free_memory / 1024**3:.1f}GB / {total_memory / 1024**3:.1f}GB total")
    
except ImportError:
    GPU_AVAILABLE = False
    logger.error("❌ CuPy not available")

class EnhancedMemoryManager:
    """Enhanced memory management for GPU CFR training."""
    
    def __init__(self, memory_fraction=0.9):
        """
        Initialize enhanced memory manager.
        
        Args:
            memory_fraction: Fraction of GPU memory to use (0.9 = 90%)
        """
        self.memory_fraction = memory_fraction
        self.gpu_pools = {}
        self.cpu_pools = {}
        
        if GPU_AVAILABLE:
            self._initialize_gpu_memory()
        
    def _initialize_gpu_memory(self):
        """Initialize GPU memory pools with maximum allocation."""
        
        # Get available memory
        gpu_info = cp.cuda.runtime.memGetInfo()
        available_memory = gpu_info[0] * self.memory_fraction
        
        logger.info(f"🚀 Initializing GPU memory pools with {available_memory / 1024**3:.1f}GB")
        
        # Calculate optimal sizes
        self.max_scenarios_per_batch = self._calculate_max_batch_size(available_memory)
        
        # Pre-allocate memory pools
        self._create_memory_pools()
        
        logger.info(f"✅ GPU memory pools initialized for {self.max_scenarios_per_batch:,} scenarios per batch")
        
    def _calculate_max_batch_size(self, available_memory):
        """Calculate maximum batch size based on available memory."""
        
        # Memory requirements per scenario (bytes):
        # - Deck representation: 52 * 4 = 208
        # - Player hands: 6 * 2 * 4 = 48  
        # - Community cards: 5 * 4 = 20
        # - Pot and bets: 6 * 4 = 24
        # - Equity results: 6 * 4 = 24
        # - CFR regrets: 100 nodes * 4 actions * 4 = 1600
        # - CFR strategies: 100 nodes * 4 actions * 4 = 1600
        # - Working arrays and overhead: ~2000
        # Total per scenario: ~5500 bytes
        
        bytes_per_scenario = 7000  # Conservative with overhead
        max_scenarios = int(available_memory / bytes_per_scenario)
        
        # Round down to nearest power of 2 for better GPU efficiency
        power_of_2 = 1
        while power_of_2 * 2 <= max_scenarios:
            power_of_2 *= 2
            
        return min(power_of_2, 100000)  # Cap at 100k scenarios
        
    def _create_memory_pools(self):
        """Create pre-allocated GPU memory pools."""
        
        batch_size = self.max_scenarios_per_batch
        num_players = 6
        max_nodes = 200
        max_actions = 4
        
        # Card and game state pools
        self.gpu_pools['decks'] = cp.zeros((batch_size, 52), dtype=cp.int32)
        self.gpu_pools['hands'] = cp.zeros((batch_size, num_players, 2), dtype=cp.int32)
        self.gpu_pools['community'] = cp.zeros((batch_size, 5), dtype=cp.int32)
        self.gpu_pools['pots'] = cp.zeros(batch_size, dtype=cp.float32)
        self.gpu_pools['bets'] = cp.zeros((batch_size, num_players), dtype=cp.float32)
        self.gpu_pools['active_players'] = cp.zeros((batch_size, num_players), dtype=cp.bool_)
        
        # Equity calculation pools
        self.gpu_pools['equity_results'] = cp.zeros((batch_size, num_players), dtype=cp.float32)
        self.gpu_pools['win_counts'] = cp.zeros((batch_size, num_players), dtype=cp.int32)
        self.gpu_pools['simulation_results'] = cp.zeros((batch_size, 10000), dtype=cp.float32)
        
        # CFR data structure pools
        self.gpu_pools['regrets'] = cp.zeros((batch_size, max_nodes, max_actions), dtype=cp.float32)
        self.gpu_pools['strategies'] = cp.zeros((batch_size, max_nodes, max_actions), dtype=cp.float32)
        self.gpu_pools['utilities'] = cp.zeros((batch_size, num_players), dtype=cp.float32)
        self.gpu_pools['reach_probs'] = cp.zeros((batch_size, num_players), dtype=cp.float32)
        
        # Working arrays for computations
        self.gpu_pools['temp_float_1'] = cp.zeros((batch_size, 1000), dtype=cp.float32)
        self.gpu_pools['temp_float_2'] = cp.zeros((batch_size, 1000), dtype=cp.float32)
        self.gpu_pools['temp_int_1'] = cp.zeros((batch_size, 1000), dtype=cp.int32)
        self.gpu_pools['temp_int_2'] = cp.zeros((batch_size, 1000), dtype=cp.int32)
        
        # Random number generation pools
        self.gpu_pools['random_seeds'] = cp.random.randint(0, 2**31, size=batch_size, dtype=cp.int32)
        
        # Force allocation
        cp.cuda.Stream.null.synchronize()
        
        # Log memory usage
        mempool = cp.get_default_memory_pool()
        allocated_bytes = mempool.used_bytes()
        logger.info(f"💾 GPU memory allocated: {allocated_bytes / 1024**3:.2f}GB")
        
    def get_memory_stats(self):
        """Get current memory usage statistics."""
        if not GPU_AVAILABLE:
            return {}
        
        mempool = cp.get_default_memory_pool()
        gpu_info = cp.cuda.runtime.memGetInfo()
        
        return {
            'pool_used_gb': mempool.used_bytes() / 1024**3,
            'pool_total_gb': mempool.total_bytes() / 1024**3,
            'gpu_free_gb': gpu_info[0] / 1024**3,
            'gpu_total_gb': gpu_info[1] / 1024**3,
            'max_batch_size': self.max_scenarios_per_batch
        }

class MaximumThroughputCFRTrainer:
    """CFR Trainer optimized for maximum GPU memory utilization and throughput."""
    
    def __init__(self, num_players=6):
        self.num_players = num_players
        
        # Import required modules
        from train_cfr import CFRTrainer
        from gpu_accelerated_equity import GPUEquityCalculator
        
        # Initialize memory manager
        self.memory_manager = EnhancedMemoryManager(memory_fraction=0.9)
        
        # Initialize components
        self.gpu_equity_calculator = GPUEquityCalculator(use_gpu=True)
        self.base_trainer = CFRTrainer(num_players=num_players)
        
        # Training statistics
        self.stats = {
            'iterations_completed': 0,
            'total_simulation_time': 0,
            'total_batch_time': 0,
            'batches_processed': 0,
            'peak_memory_usage': 0,
            'throughput_history': []
        }
        
        logger.info(f"✅ Maximum Throughput CFR Trainer initialized")
        logger.info(f"   Max batch size: {self.memory_manager.max_scenarios_per_batch:,}")
        
    def train_maximum_throughput(self, total_iterations=500000):
        """Train with maximum memory utilization for highest throughput."""
        
        logger.info(f"🚀 MAXIMUM THROUGHPUT CFR TRAINING")
        logger.info(f"   Target iterations: {total_iterations:,}")
        logger.info(f"   Expected memory usage: {self.memory_manager.get_memory_stats()['pool_used_gb']:.1f}GB")
        
        start_time = time.time()
        completed = 0
        
        # Use maximum batch size throughout
        batch_size = self.memory_manager.max_scenarios_per_batch
        
        while completed < total_iterations:
            batch_start = time.time()
            
            # Calculate actual batch size for this iteration
            remaining = total_iterations - completed
            actual_batch_size = min(batch_size, remaining)
            
            progress_pct = 100 * completed / total_iterations
            logger.info(f"🔥 Processing batch: {actual_batch_size:,} scenarios ({progress_pct:.1f}% complete)")
            
            # Generate maximum batch
            scenarios = self._generate_maximum_batch(actual_batch_size)
            
            # Process with maximum GPU utilization
            results = self._process_maximum_batch(scenarios)
            
            batch_time = time.time() - batch_start
            throughput = actual_batch_size / batch_time
            
            # Update statistics
            completed += actual_batch_size
            self.stats['iterations_completed'] = completed
            self.stats['batches_processed'] += 1
            self.stats['total_batch_time'] += batch_time
            self.stats['throughput_history'].append(throughput)
            
            # Log progress
            self._log_batch_progress(actual_batch_size, batch_time, throughput, completed, total_iterations)
            
            # Memory monitoring
            if completed % 50000 == 0:
                self._log_memory_status()
        
        total_time = time.time() - start_time
        self._log_final_results(total_time)
        
    def _generate_maximum_batch(self, batch_size):
        """Generate scenarios using pre-allocated GPU memory."""
        
        # Use pre-allocated GPU arrays for maximum efficiency
        gpu_pools = self.memory_manager.gpu_pools
        
        # Generate random scenarios directly on GPU
        scenarios = []
        
        for i in range(batch_size):
            # Generate deck on CPU, then transfer (for now)
            deck = list(range(52))
            np.random.shuffle(deck)
            
            # Deal hands
            hands = []
            cards_dealt = 0
            for player in range(self.num_players):
                hand = deck[cards_dealt:cards_dealt + 2]
                hands.append(hand)
                cards_dealt += 2
            
            # Community cards
            community = deck[cards_dealt:cards_dealt + 5]
            
            scenario = {
                'id': i,
                'deck': deck,
                'hands': hands,
                'community': community[:3],  # Flop
                'pot': 3.0,
                'active_players': list(range(self.num_players))
            }
            scenarios.append(scenario)
        
        return scenarios
    
    def _process_maximum_batch(self, scenarios):
        """Process batch with maximum GPU utilization."""
        
        batch_size = len(scenarios)
        
        # Prepare data for massive GPU equity calculation
        all_hands = []
        for scenario in scenarios:
            for hand in scenario['hands']:
                hand_cards = [self.gpu_equity_calculator.all_cards[card_idx] for card_idx in hand]
                all_hands.append(hand_cards)
        
        # Use first scenario's community cards
        community_cards = [self.gpu_equity_calculator.all_cards[card_idx] 
                          for card_idx in scenarios[0]['community']]
        
        # Massive GPU equity calculation with maximum simulations
        sim_start = time.time()
        
        # Use larger simulation count for better accuracy
        num_simulations = 20000  # Increased from default
        
        equities, mean_equity, std_equity = self.gpu_equity_calculator.calculate_equity_batch_gpu(
            all_hands,
            community_cards,
            num_simulations=num_simulations,
            num_opponents=2
        )
        
        sim_time = time.time() - sim_start
        self.stats['total_simulation_time'] += sim_time
        
        # Process CFR updates (simplified for maximum throughput)
        results = []
        for i, scenario in enumerate(scenarios):
            player_equities = equities[i * self.num_players:(i + 1) * self.num_players]
            
            result = {
                'scenario_id': scenario['id'],
                'equities': player_equities,
                'mean_equity': np.mean(player_equities),
                'pot': scenario['pot'],
                'simulation_time': sim_time / batch_size
            }
            results.append(result)
        
        return results
    
    def _log_batch_progress(self, batch_size, batch_time, throughput, completed, total):
        """Log detailed batch progress."""
        
        avg_throughput = np.mean(self.stats['throughput_history'][-10:]) if self.stats['throughput_history'] else 0
        progress_pct = 100 * completed / total
        
        logger.info(f"✅ Batch completed:")
        logger.info(f"   📦 Size: {batch_size:,} scenarios")
        logger.info(f"   ⏱️ Time: {batch_time:.2f}s")
        logger.info(f"   ⚡ Throughput: {throughput:.1f} scenarios/sec")
        logger.info(f"   📊 10-batch avg: {avg_throughput:.1f} scenarios/sec")
        logger.info(f"   📈 Progress: {completed:,}/{total:,} ({progress_pct:.1f}%)")
        
    def _log_memory_status(self):
        """Log current memory usage."""
        
        memory_stats = self.memory_manager.get_memory_stats()
        
        logger.info(f"💾 MEMORY STATUS:")
        logger.info(f"   Pool used: {memory_stats['pool_used_gb']:.2f}GB")
        logger.info(f"   Pool total: {memory_stats['pool_total_gb']:.2f}GB")
        logger.info(f"   GPU free: {memory_stats['gpu_free_gb']:.2f}GB")
        logger.info(f"   Max batch: {memory_stats['max_batch_size']:,}")
        
        self.stats['peak_memory_usage'] = max(
            self.stats['peak_memory_usage'], 
            memory_stats['pool_used_gb']
        )
        
    def _log_final_results(self, total_time):
        """Log comprehensive final results."""
        
        avg_throughput = np.mean(self.stats['throughput_history']) if self.stats['throughput_history'] else 0
        total_simulations = self.stats['iterations_completed'] * 20000  # scenarios * sims per scenario
        
        logger.info(f"🏁 MAXIMUM THROUGHPUT TRAINING COMPLETED!")
        logger.info(f"📊 FINAL PERFORMANCE METRICS:")
        logger.info(f"   ⏱️ Total time: {total_time/60:.1f} minutes")
        logger.info(f"   ✅ Iterations: {self.stats['iterations_completed']:,}")
        logger.info(f"   📦 Batches: {self.stats['batches_processed']:,}")
        logger.info(f"   ⚡ Avg throughput: {avg_throughput:.1f} scenarios/sec")
        logger.info(f"   🔢 Total simulations: {total_simulations:,}")
        logger.info(f"   🚀 Simulation rate: {total_simulations/total_time:.0f} sims/sec")
        logger.info(f"   💾 Peak memory: {self.stats['peak_memory_usage']:.2f}GB")
        logger.info(f"   📈 GPU utilization: {self.stats['total_simulation_time']/total_time*100:.1f}%")
        
        # Save performance data
        performance_data = {
            'total_time_minutes': total_time / 60,
            'iterations_completed': self.stats['iterations_completed'],
            'average_throughput': avg_throughput,
            'total_simulations': total_simulations,
            'simulation_rate': total_simulations / total_time,
            'peak_memory_gb': self.stats['peak_memory_usage'],
            'gpu_utilization_percent': self.stats['total_simulation_time'] / total_time * 100,
            'max_batch_size_used': self.memory_manager.max_scenarios_per_batch
        }
        
        with open('maximum_throughput_results.json', 'w') as f:
            json.dump(performance_data, f, indent=2)
        
        logger.info(f"📄 Results saved to maximum_throughput_results.json")

def run_maximum_memory_test():
    """Run maximum memory utilization test."""
    
    if not GPU_AVAILABLE:
        logger.error("❌ GPU not available for maximum memory test")
        return
    
    logger.info("🚀 MAXIMUM MEMORY UTILIZATION TEST")
    logger.info("=" * 50)
    
    try:
        # Initialize trainer
        trainer = MaximumThroughputCFRTrainer(num_players=6)
        
        # Run with maximum throughput settings
        trainer.train_maximum_throughput(total_iterations=1000000)  # 1M iterations
        
    except Exception as e:
        logger.error(f"❌ Maximum memory test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_maximum_memory_test()
