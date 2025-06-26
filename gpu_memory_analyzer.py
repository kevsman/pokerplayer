"""
GPU Memory Analysis and Optimization Tool
=========================================

This script analyzes GPU memory and determines the optimal batch sizes and 
memory allocation strategies for maximum throughput CFR training.
"""

import sys
import logging
import numpy as np
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GPU Memory Analysis
try:
    import cupy as cp
    GPU_AVAILABLE = True
    logger.info("✅ CuPy available for memory analysis")
except ImportError:
    GPU_AVAILABLE = False
    logger.error("❌ CuPy not available")
    sys.exit(1)

def analyze_gpu_memory():
    """Analyze available GPU memory and calculate optimal settings."""
    
    logger.info("🔍 ANALYZING GPU MEMORY")
    logger.info("=" * 40)
    
    # Get GPU memory info
    mempool = cp.get_default_memory_pool()
    gpu_info = cp.cuda.runtime.memGetInfo()
    
    free_memory = gpu_info[0]
    total_memory = gpu_info[1]
    used_memory = total_memory - free_memory
    
    logger.info(f"💾 GPU Memory Status:")
    logger.info(f"   Total: {total_memory / 1024**3:.2f}GB")
    logger.info(f"   Used: {used_memory / 1024**3:.2f}GB")
    logger.info(f"   Free: {free_memory / 1024**3:.2f}GB")
    logger.info(f"   Utilization: {100 * used_memory / total_memory:.1f}%")
    
    return free_memory, total_memory

def calculate_optimal_batch_sizes(available_memory):
    """Calculate optimal batch sizes for different memory utilization levels."""
    
    logger.info("🧮 CALCULATING OPTIMAL BATCH SIZES")
    logger.info("=" * 40)
    
    # Memory requirements per scenario (conservative estimate)
    bytes_per_scenario = 8000  # Includes all arrays, overhead, etc.
    
    utilization_levels = [0.5, 0.7, 0.8, 0.9, 0.95]
    
    for util in utilization_levels:
        usable_memory = available_memory * util
        max_scenarios = int(usable_memory / bytes_per_scenario)
        
        # Round to nearest power of 2 for GPU efficiency
        power_of_2 = 1
        while power_of_2 * 2 <= max_scenarios:
            power_of_2 *= 2
        
        logger.info(f"📊 {util*100:4.0f}% utilization:")
        logger.info(f"   Memory: {usable_memory / 1024**3:.2f}GB")
        logger.info(f"   Max scenarios: {max_scenarios:,}")
        logger.info(f"   Power-of-2 batch: {power_of_2:,}")
        logger.info("")

def test_memory_allocation(batch_size):
    """Test actual memory allocation with a specific batch size."""
    
    logger.info(f"🧪 TESTING MEMORY ALLOCATION: {batch_size:,} scenarios")
    logger.info("=" * 50)
    
    try:
        num_players = 6
        max_nodes = 200
        max_actions = 4
        
        # Allocate arrays similar to what CFR training would need
        arrays = {}
        
        start_time = time.time()
        
        # Card and game state arrays
        arrays['decks'] = cp.zeros((batch_size, 52), dtype=cp.int32)
        arrays['hands'] = cp.zeros((batch_size, num_players, 2), dtype=cp.int32)
        arrays['community'] = cp.zeros((batch_size, 5), dtype=cp.int32)
        arrays['pots'] = cp.zeros(batch_size, dtype=cp.float32)
        arrays['bets'] = cp.zeros((batch_size, num_players), dtype=cp.float32)
        
        # Equity calculation arrays
        arrays['equity_results'] = cp.zeros((batch_size, num_players), dtype=cp.float32)
        arrays['win_counts'] = cp.zeros((batch_size, num_players), dtype=cp.int32)
        
        # CFR arrays
        arrays['regrets'] = cp.zeros((batch_size, max_nodes, max_actions), dtype=cp.float32)
        arrays['strategies'] = cp.zeros((batch_size, max_nodes, max_actions), dtype=cp.float32)
        arrays['utilities'] = cp.zeros((batch_size, num_players), dtype=cp.float32)
        
        # Large simulation arrays
        arrays['simulations'] = cp.zeros((batch_size, 10000), dtype=cp.float32)
        
        # Force allocation
        cp.cuda.Stream.null.synchronize()
        
        allocation_time = time.time() - start_time
        
        # Check memory usage
        mempool = cp.get_default_memory_pool()
        allocated_bytes = mempool.used_bytes()
        
        logger.info(f"✅ Allocation successful!")
        logger.info(f"   Time: {allocation_time:.3f} seconds")
        logger.info(f"   Memory used: {allocated_bytes / 1024**3:.2f}GB")
        logger.info(f"   Bytes per scenario: {allocated_bytes / batch_size:.0f}")
        
        # Test some operations
        logger.info("🧪 Testing GPU operations...")
        
        # Fill arrays with random data
        for name, array in arrays.items():
            if 'int' in str(array.dtype):
                array.fill(cp.random.randint(0, 100))
            else:
                array.fill(cp.random.random())
        
        # Test computation
        start_compute = time.time()
        result = cp.sum(arrays['equity_results'] * arrays['utilities'])
        cp.cuda.Stream.null.synchronize()
        compute_time = time.time() - start_compute
        
        logger.info(f"   Computation test: {compute_time:.6f}s")
        logger.info(f"   Result: {result}")
        
        # Cleanup
        for array in arrays.values():
            del array
        
        return True, allocated_bytes
        
    except Exception as e:
        logger.error(f"❌ Allocation failed: {e}")
        return False, 0

def find_maximum_batch_size(available_memory):
    """Find the maximum usable batch size through binary search."""
    
    logger.info("🔍 FINDING MAXIMUM BATCH SIZE")
    logger.info("=" * 40)
    
    # Start with conservative estimate
    bytes_per_scenario = 8000
    initial_estimate = int(available_memory * 0.8 / bytes_per_scenario)
    
    # Binary search for maximum batch size
    low = 1000
    high = min(initial_estimate, 200000)  # Cap at 200k
    max_working_size = 0
    
    logger.info(f"🔍 Binary search range: {low:,} to {high:,}")
    
    while low <= high:
        mid = (low + high) // 2
        
        # Round to nearest 1000 for cleaner testing
        test_size = (mid // 1000) * 1000
        if test_size == 0:
            test_size = 1000
        
        logger.info(f"🧪 Testing batch size: {test_size:,}")
        
        success, memory_used = test_memory_allocation(test_size)
        
        if success:
            max_working_size = test_size
            actual_bytes_per_scenario = memory_used / test_size
            logger.info(f"✅ Success! Actual bytes per scenario: {actual_bytes_per_scenario:.0f}")
            low = mid + 1
        else:
            logger.info(f"❌ Failed at {test_size:,}")
            high = mid - 1
        
        # Clean up GPU memory
        mempool = cp.get_default_memory_pool()
        mempool.free_all_blocks()
        
        time.sleep(0.5)  # Brief pause
    
    logger.info(f"🎯 MAXIMUM BATCH SIZE FOUND: {max_working_size:,}")
    return max_working_size

def run_memory_analysis():
    """Run comprehensive GPU memory analysis."""
    
    logger.info("🚀 GPU MEMORY ANALYSIS AND OPTIMIZATION")
    logger.info("=" * 60)
    
    if not GPU_AVAILABLE:
        logger.error("❌ GPU not available")
        return
    
    # 1. Analyze current memory
    free_memory, total_memory = analyze_gpu_memory()
    
    # 2. Calculate theoretical batch sizes
    calculate_optimal_batch_sizes(free_memory)
    
    # 3. Find actual maximum batch size
    max_batch_size = find_maximum_batch_size(free_memory)
    
    # 4. Final recommendations
    logger.info("🎯 FINAL RECOMMENDATIONS")
    logger.info("=" * 30)
    logger.info(f"   Maximum batch size: {max_batch_size:,}")
    logger.info(f"   Conservative batch size: {max_batch_size // 2:,}")
    logger.info(f"   Safe batch size: {max_batch_size // 4:,}")
    
    # 5. Performance projections
    scenarios_per_second_estimate = 1000  # Conservative estimate
    simulations_per_scenario = 10000
    
    total_sims_per_sec = max_batch_size * simulations_per_scenario / (max_batch_size / scenarios_per_second_estimate)
    
    logger.info(f"📊 PERFORMANCE PROJECTIONS:")
    logger.info(f"   Scenarios/sec: {scenarios_per_second_estimate:,}")
    logger.info(f"   Simulations/sec: {total_sims_per_sec:.0f}")
    logger.info(f"   GPU memory utilization: ~90%")
    
    # Save results
    results = {
        'gpu_total_memory_gb': total_memory / 1024**3,
        'gpu_free_memory_gb': free_memory / 1024**3,
        'max_batch_size': max_batch_size,
        'recommended_batch_size': max_batch_size // 2,
        'safe_batch_size': max_batch_size // 4,
        'estimated_scenarios_per_sec': scenarios_per_second_estimate,
        'estimated_simulations_per_sec': total_sims_per_sec
    }
    
    import json
    with open('gpu_memory_analysis.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"📄 Analysis saved to gpu_memory_analysis.json")

if __name__ == "__main__":
    run_memory_analysis()
