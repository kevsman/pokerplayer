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
    
    # Start the vectorized training process.
    logger.info("🚀 Starting STABLE Vectorized NLHE CFR training for 6 players with GPU acceleration...")
    logger.info("🎯 Target: 10,000 iterations with a batch size of 1,000 for stability and strategy coverage")
    trainer.train(iterations=10000, batch_size=1000) # Focus on stability over speed
    
    logger.info("✅ Vectorized training complete. Strategies have been saved to 'strategy_table.json'.")
