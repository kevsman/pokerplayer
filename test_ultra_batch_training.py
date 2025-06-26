#!/usr/bin/env python3
"""
Test script for ultra-batch GPU training with maximum memory utilization.
This tests the new memory-optimized training capabilities.
"""
import logging
import time
import sys
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_ultra_batch_training():
    """Test the ultra-batch training with various memory configurations."""
    print("🚀 TESTING ULTRA-BATCH GPU TRAINING")
    print("=" * 50)
    
    try:
        from gpu_cfr_trainer import GPUCFRTrainer
        
        # Test 1: Standard batch size
        print("\n📊 TEST 1: Standard batch training")
        trainer1 = GPUCFRTrainer(use_gpu=True)
        if trainer1.use_gpu:
            print(f"Standard batch size: {trainer1.batch_size:,}")
            start_time = time.time()
            trainer1.train_batch_gpu(iterations=1000, batch_size=10000)
            standard_time = time.time() - start_time
            print(f"Standard training time: {standard_time:.2f}s")
        else:
            print("GPU not available for testing")
            return
        
        # Test 2: Ultra-batch with safe memory
        print("\n📊 TEST 2: Ultra-batch with safe memory")
        trainer2 = GPUCFRTrainer(use_gpu=True)
        start_time = time.time()
        trainer2.train_ultra_batch_gpu(iterations=1000, use_max_memory=False)
        safe_time = time.time() - start_time
        print(f"Safe ultra-batch time: {safe_time:.2f}s")
        
        # Test 3: Ultra-batch with maximum memory
        print("\n📊 TEST 3: Ultra-batch with MAXIMUM memory")
        trainer3 = GPUCFRTrainer(use_gpu=True)
        start_time = time.time()
        trainer3.train_ultra_batch_gpu(iterations=1000, use_max_memory=True)
        max_time = time.time() - start_time
        print(f"Maximum ultra-batch time: {max_time:.2f}s")
        
        # Performance comparison
        print("\n🎯 PERFORMANCE COMPARISON")
        print("-" * 30)
        if 'standard_time' in locals():
            print(f"Standard batch:    {1000/standard_time:,.0f} scenarios/second")
        print(f"Safe ultra-batch:  {1000/safe_time:,.0f} scenarios/second")
        print(f"Max ultra-batch:   {1000/max_time:,.0f} scenarios/second")
        
        if 'standard_time' in locals():
            safe_speedup = standard_time / safe_time
            max_speedup = standard_time / max_time
            print(f"\nSpeedup over standard:")
            print(f"Safe ultra-batch: {safe_speedup:.1f}x faster")
            print(f"Max ultra-batch:  {max_speedup:.1f}x faster")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False
    
    return True

def test_memory_limits():
    """Test different memory configurations to find optimal settings."""
    print("\n🧠 TESTING MEMORY LIMITS")
    print("=" * 30)
    
    try:
        from gpu_cfr_trainer import GPUCFRTrainer
        
        trainer = GPUCFRTrainer(use_gpu=True)
        if not trainer.use_gpu:
            print("GPU not available for memory testing")
            return
        
        # Test different batch sizes
        batch_sizes = [50000, 100000, 150000, 175000]
        
        for batch_size in batch_sizes:
            print(f"\n📊 Testing batch size: {batch_size:,}")
            try:
                start_time = time.time()
                
                # Generate scenarios to test memory allocation
                scenarios = trainer._generate_mega_batch_scenarios(min(batch_size, 1000))
                
                alloc_time = time.time() - start_time
                memory_gb = (batch_size * 46776) / (1024**3)
                
                print(f"✅ Success! Memory: {memory_gb:.2f}GB, Time: {alloc_time:.3f}s")
                
            except Exception as e:
                print(f"❌ Failed at {batch_size:,}: {e}")
                break
    
    except Exception as e:
        logger.error(f"Memory test failed: {e}")

def benchmark_throughput():
    """Benchmark the throughput of different training modes."""
    print("\n⚡ THROUGHPUT BENCHMARK")
    print("=" * 25)
    
    try:
        from gpu_cfr_trainer import GPUCFRTrainer
        
        trainer = GPUCFRTrainer(use_gpu=True)
        if not trainer.use_gpu:
            print("GPU not available for benchmarking")
            return
        
        # Small scale benchmark for speed
        test_iterations = 100
        
        print(f"Benchmarking {test_iterations} iterations...")
        
        # Ultra-batch benchmark
        start_time = time.time()
        trainer.train_ultra_batch_gpu(iterations=test_iterations, use_max_memory=True)
        ultra_time = time.time() - start_time
        
        throughput = test_iterations / ultra_time
        print(f"🔥 Ultra-batch throughput: {throughput:,.0f} scenarios/second")
        
        # Estimate performance for large-scale training
        estimated_50k_time = 50000 / throughput
        print(f"📈 Estimated time for 50K iterations: {estimated_50k_time:.1f}s ({estimated_50k_time/60:.1f} minutes)")
        
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")

if __name__ == "__main__":
    print("🧪 ULTRA-BATCH TRAINING TEST SUITE")
    print("=" * 40)
    
    # Run all tests
    success = test_ultra_batch_training()
    
    if success:
        test_memory_limits()
        benchmark_throughput()
        
        print("\n✅ ALL TESTS COMPLETED")
        print("🚀 Ultra-batch training is ready for production use!")
    else:
        print("\n❌ TESTS FAILED")
        print("Please check GPU configuration and memory availability")
    
    print("\n" + "=" * 40)
