#!/usr/bin/env python3
"""
Fixed CFR Training Script
Addresses critical issues found in the training pipeline.
"""
import logging
import time
import random
import numpy as np
from train_cfr import CFRTrainer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_fixed_training():
    """Run training with critical fixes applied."""
    
    logger.info("🔧 FIXED CFR TRAINING - ADDRESSING CRITICAL ISSUES")
    logger.info("=" * 60)
    logger.info("🎯 FIXES APPLIED:")
    logger.info("   • Added missing save_strategy method")
    logger.info("   • Fixed CFR solver logic")
    logger.info("   • Consistent card formats")
    logger.info("   • Improved hand strength modeling")
    logger.info("   • Better logging and validation")
    logger.info("=" * 60)
    
    # Initialize trainer
    trainer = CFRTrainer(num_players=6, big_blind=0.04, small_blind=0.02, use_gpu=False)
    
    # Override to use standard card format consistently
    trainer.use_standard_cards = True
    
    # Run training with validation
    iterations = 5000  # Start with smaller number to validate fixes
    
    logger.info(f"🚀 Starting fixed training with {iterations} iterations...")
    start_time = time.time()
    
    try:
        strategies_count = trainer.train(iterations)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        logger.info("=" * 60)
        logger.info("✅ FIXED TRAINING COMPLETE!")
        logger.info(f"   Time: {total_time:.1f}s")
        logger.info(f"   Strategies: {strategies_count}")
        logger.info(f"   Rate: {iterations/total_time:.1f} iter/sec")
        logger.info("=" * 60)
        
        # Validate saved strategies
        validate_strategies(trainer)
        
        return strategies_count
        
    except Exception as e:
        logger.error(f"❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        return 0

def validate_strategies(trainer):
    """Validate that strategies were saved correctly."""
    logger.info("🔍 VALIDATING SAVED STRATEGIES...")
    
    strategy_count = len(trainer.strategy_lookup.strategy_table)
    logger.info(f"📊 Total strategies in memory: {strategy_count}")
    
    if strategy_count > 0:
        # Check a few sample strategies
        sample_keys = list(trainer.strategy_lookup.strategy_table.keys())[:5]
        
        for i, key in enumerate(sample_keys):
            strategy = trainer.strategy_lookup.strategy_table[key]
            logger.info(f"✅ Strategy {i+1}: {key}")
            logger.info(f"   Actions: {strategy}")
            
            # Validate probabilities sum to ~1.0
            total_prob = sum(strategy.values())
            if abs(total_prob - 1.0) < 0.01:
                logger.info(f"   ✅ Valid probabilities (sum={total_prob:.3f})")
            else:
                logger.warning(f"   ⚠️ Invalid probabilities (sum={total_prob:.3f})")
    
    # Test strategy lookup with common scenarios
    test_lookups = [
        ("0", "0", "pot1.0", ['fold', 'call', 'raise']),
        ("0", "10", "pot2.0", ['fold', 'call', 'raise']),
        ("0", "100", "pot0.5", ['fold', 'call', 'raise']),
    ]
    
    logger.info("🧪 Testing strategy lookups...")
    for street, hand, board, actions in test_lookups:
        strategy = trainer.strategy_lookup.get_strategy(street, hand, board, actions)
        if strategy:
            logger.info(f"✅ Found strategy for {street}, {hand}, {board}")
        else:
            logger.warning(f"❌ No strategy for {street}, {hand}, {board}")

if __name__ == "__main__":
    run_fixed_training()
