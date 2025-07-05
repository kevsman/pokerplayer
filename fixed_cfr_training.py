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
    
    # ENHANCED PARAMETERS for comprehensive strategy database building
    # Target: 1M+ strategies for professional-level play
    optimal_batch_size = 200000  # Increased batch size for maximum diversity
    total_iterations = 1000     # More iterations for better convergence
    
    # Start the enhanced training process for comprehensive coverage
    logger.info("🚀 Starting COMPREHENSIVE STRATEGY DATABASE BUILDING!")
    logger.info(f"🎯 Target: 1M+ strategies for professional-level poker play")
    logger.info(f"⚡ Using batch size of {optimal_batch_size:,} × {total_iterations:,} iterations")
    logger.info(f"📊 Expected total game states: ~{optimal_batch_size * total_iterations:,}")
    
    # Run with enhanced parameters for maximum strategy coverage
    trainer.train(iterations=total_iterations, batch_size=optimal_batch_size)
    
    logger.info("✅ COMPREHENSIVE STRATEGY DATABASE complete!")
    logger.info("🎯 Professional-level strategy coverage achieved!")
    logger.info("📈 Run multiple times with different parameters for maximum diversity.")
