"""
Optimal Training Configuration for 50,000 Iterations
Based on performance analysis showing CPU is faster than GPU for this workload.
"""
import time
import logging
from train_cfr import CFRTrainer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def train_optimal_configuration():
    """Train with optimal CPU configuration for maximum performance."""
    
    logger.info("🎯 OPTIMAL POKER BOT TRAINING")
    logger.info("=" * 60)
    logger.info("Configuration:")
    logger.info("  • 50,000 CFR iterations")
    logger.info("  • 500 Monte Carlo simulations per calculation")
    logger.info("  • CPU-optimized (GPU disabled)")
    logger.info("  • Expected training time: ~45-60 minutes")
    logger.info("=" * 60)
    
    # Create trainer with optimal CPU settings
    trainer = CFRTrainer(num_players=6, use_gpu=False)  # GPU disabled for better performance
    
    # Override simulation counts in equity calculator for optimal performance
    if hasattr(trainer.cpu_equity_calculator, 'default_simulations'):
        trainer.cpu_equity_calculator.default_simulations = 500
    
    start_time = time.time()
    
    try:
        # Run the optimized training
        logger.info("🚀 Starting optimized CFR training...")
        strategies_count = trainer.train(iterations=50000)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        logger.info("=" * 60)
        logger.info("✅ TRAINING COMPLETE!")
        logger.info(f"  • Total time: {total_time/60:.1f} minutes")
        logger.info(f"  • Strategies learned: {strategies_count}")
        logger.info(f"  • Average time per iteration: {total_time/50000:.4f}s")
        logger.info(f"  • Performance: {50000*500/total_time:.0f} simulations/second")
        logger.info("=" * 60)
        
        return {
            'total_time': total_time,
            'strategies_count': strategies_count,
            'iterations_per_second': 50000 / total_time,
            'simulations_per_second': 50000 * 500 / total_time
        }
        
    except KeyboardInterrupt:
        logger.info("Training interrupted by user")
        return None
    except Exception as e:
        logger.error(f"Training failed: {e}")
        return None

if __name__ == "__main__":
    # Run the optimal training configuration
    results = train_optimal_configuration()
    
    if results:
        print(f"\n🏆 FINAL RESULTS:")
        print(f"Training completed in {results['total_time']/60:.1f} minutes")
        print(f"Performance: {results['simulations_per_second']:.0f} simulations/second")
        print(f"Strategies learned: {results['strategies_count']}")
