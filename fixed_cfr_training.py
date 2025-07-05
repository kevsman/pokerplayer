#!/usr/bin/env python3
"""
Fixed CFR Training Script for No-Limit Hold'em
This script initializes and runs the GPU-accelerated CFR trainer for a 6-player game.
"""
import logging
import cupy as cp
import numpy as np
import random
import time

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    from gpu_cfr_trainer import GPUCFRTrainer
    
    # CRITICAL: Use different random seeds for each run to explore different areas
    current_time_seed = int(time.time()) % 1000000  # Use current time as base
    random_seed = current_time_seed + random.randint(0, 999999)
    
    # Set different seeds for all random number generators
    np.random.seed(random_seed)
    random.seed(random_seed)
    cp.random.seed(random_seed)
    
    logger.info(f"🎲 Using random seed: {random_seed} for maximum diversity")
    
    # ENHANCED PARAMETERS for comprehensive strategy database building
    # Target: 1M+ strategies for professional-level play
    
    # DIVERSIFICATION STRATEGY: Randomize parameters for each run
    base_batch_size = 60000
    batch_size_multiplier = random.uniform(0.8, 1.5)  # 80% to 150% of base
    optimal_batch_size = int(base_batch_size * batch_size_multiplier)
    
    base_iterations = 5000
    iteration_multiplier = random.uniform(0.8, 1.2)  # 80% to 120% of base
    total_iterations = int(base_iterations * iteration_multiplier)
    
    # Randomize player count (4-9 players for different dynamics)
    num_players = random.choice([4, 5, 6, 7, 8, 9])
    
    # Randomize blind structure (create different stack-to-blind ratios)
    blind_multiplier = random.uniform(0.5, 2.0)
    small_blind = 0.02 * blind_multiplier
    big_blind = 0.04 * blind_multiplier
    
    logger.info("🚀 Starting DIVERSIFIED STRATEGY DATABASE BUILDING!")
    logger.info(f"🎯 This run focuses on: {num_players}-player games with {blind_multiplier:.1f}x blinds")
    logger.info(f"⚡ Using batch size of {optimal_batch_size:,} × {total_iterations:,} iterations")
    logger.info(f"📊 Expected NEW game states: ~{optimal_batch_size * total_iterations:,}")
    
    # Initialize trainer with randomized parameters
    trainer = GPUCFRTrainer(
        use_gpu=True, 
        num_players=num_players, 
        small_blind=small_blind, 
        big_blind=big_blind, 
        dtype=cp.float16
    )
    
    # Run with enhanced parameters for maximum strategy coverage
    trainer.train(iterations=total_iterations, batch_size=optimal_batch_size)
    
    logger.info("✅ DIVERSIFIED STRATEGY DATABASE expansion complete!")
    logger.info(f"🎯 Explored {num_players}-player poker dynamics with {blind_multiplier:.1f}x blind structure")
    logger.info("📈 Run this script multiple times to explore different game configurations!")
    logger.info("💡 Each run will use different: player counts, blind sizes, batch sizes, and random seeds")
