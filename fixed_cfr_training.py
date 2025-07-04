#!/usr/bin/env python3
"""
Fixed CFR Training Script for No-Limit Hold'em
This script initializes and runs the GPU-accelerated CFR trainer for a 6-player game.
"""
import logging
import cupy as cp

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    from gpu_cfr_trainer import GPUCFRTrainer
    
    # Initialize the new GPU-native trainer with float16 for mixed-precision training
    trainer = GPUCFRTrainer(use_gpu=True, num_players=6, small_blind=0.02, big_blind=0.04, dtype=cp.float16)
    
    # Dramatically increase batch size to fully utilize 8GB GPU memory
    # Since we're only using 0.4% with 5K batch, we can go much higher
    optimal_batch_size = 40000  # 8x larger batch size to utilize full GPU memory
    
    # Start the vectorized training process with MAXIMUM GPU utilization
    logger.info("🚀 Starting MAXIMUM GPU MEMORY UTILIZATION CFR Training!")
    logger.info(f"🎯 Using MASSIVE batch size of {optimal_batch_size:,} to fully utilize 8GB GPU memory")
    logger.info("⚡ Targeting maximum GPU memory usage and strategy generation!")
    
    # Run with maximum GPU utilization parameters
    trainer.train(iterations=2000, batch_size=optimal_batch_size) # Fewer iterations, massive batches
    
    logger.info("✅ ULTRA-HIGH-PERFORMANCE training complete. Massive strategy database saved!")
