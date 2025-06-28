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
    
    # Initialize the trainer for a 6-player NLHE game with specified blinds.
    # Ensure use_gpu is True to leverage GPU acceleration.
    trainer = GPUCFRTrainer(use_gpu=True, num_players=6, small_blind=0.02, big_blind=0.04)
    
    # Start the training process. For a robust strategy, a high number of iterations is recommended.
    logger.info("🚀 Starting NLHE CFR training for 6 players...")
    trainer.train_like_fixed_cfr(iterations=2) # Using 2 for debugging
    logger.info("✅ Training complete. Strategies have been saved.")
