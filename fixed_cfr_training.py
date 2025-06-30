#!/usr/bin/env python3
"""
Fixed CFR Training Script for No-Limit Hold'em
This script initializes and runs the GPU-accelerated CFR trainer for a 6-player game.
"""
import logging

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    from gpu_cfr_trainer import GPUCFRTrainer
    
    # Initialize the new GPU-native trainer
    trainer = GPUCFRTrainer(use_gpu=True, num_players=6, small_blind=0.02, big_blind=0.04)
    
    # Start the vectorized training process.
    logger.info("🚀 Starting Vectorized NLHE CFR training for 6 players with GPU acceleration...")
    logger.info("🎯 Target: 100,000 iterations with a batch size of 100,000 for a high-quality, comprehensive strategy")
    trainer.train(iterations=100000, batch_size=100000) # Call the new vectorized training method
    
    logger.info("✅ Vectorized training complete. Strategies have been saved to 'strategy_table.json'.")
