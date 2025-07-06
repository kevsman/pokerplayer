#!/usr/bin/env python3
"""
Low-Stakes Cash Game CFR Training Script for No-Limit Hold'em (Poker Bot v3)
This script initializes and runs the GPU-accelerated CFR trainer optimized for 
low-stakes cash games (2-6 players).
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
    
    # --- OPTIMIZED PARAMETERS for Low-Stakes Cash Games (2-6 players) ---
    
    # DIVERSIFICATION STRATEGY: Randomize parameters for each run
    base_batch_size = 150000
    batch_size_multiplier = random.uniform(0.8, 1.5)
    optimal_batch_size = int(base_batch_size * batch_size_multiplier)
    
    base_iterations = 12000
    iteration_multiplier = random.uniform(0.8, 1.3)
    total_iterations = int(base_iterations * iteration_multiplier)
    
    # Focus on 2-6 player dynamics for low-stakes cash games
    num_players = random.choice([2, 3, 4, 5, 6])
    
    # Use blind structures common in low-stakes online cash games
    blind_structures = [(0.01, 0.02), (0.02, 0.05), (0.05, 0.10)]
    small_blind, big_blind = random.choice(blind_structures)
    
    logger.info("🚀 Starting LOW-STAKES CASH GAME STRATEGY DATABASE BUILDING (v3)!")
    logger.info(f"🎯 This run focuses on: {num_players}-player games with blinds ${small_blind}/${big_blind}")
    logger.info(f"⚡ Using batch size of {optimal_batch_size:,} × {total_iterations:,} iterations")
    logger.info(f"📊 Expected NEW game states: ~{optimal_batch_size * total_iterations:,}")
    
    # Initialize trainer with low-stakes optimized parameters
    trainer = GPUCFRTrainer(
        use_gpu=True, 
        num_players=num_players, 
        small_blind=small_blind, 
        big_blind=big_blind, 
        dtype=cp.float16
    )
    
    # Run with enhanced parameters for maximum strategy coverage
    trainer.train(iterations=total_iterations, batch_size=optimal_batch_size)
    
    logger.info("✅ LOW-STAKES STRATEGY DATABASE expansion complete!")
    logger.info(f"🎯 Explored {num_players}-player poker dynamics with ${small_blind}/${big_blind} blinds")
    logger.info("📈 Run this script multiple times to build a comprehensive low-stakes strategy!")
    logger.info("💡 Each run will use different: player counts, blind sizes, batch sizes, and random seeds")
