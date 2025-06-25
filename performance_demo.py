"""
Performance Demo: CPU vs GPU-Enhanced Poker Bot
This script demonstrates the performance improvements possible with optimized simulation counts
and GPU acceleration (when available).
"""
import time
import logging
import numpy as np
from typing import List, Dict, Any
import matplotlib.pyplot as plt
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def benchmark_equity_calculations():
    """Benchmark equity calculation performance."""
    logger.info("=== EQUITY CALCULATION BENCHMARK ===")
    
    # Standard imports
    from equity_calculator import EquityCalculator
    from hand_evaluator import HandEvaluator
    
    # Try GPU imports
    try:
        from gpu_accelerated_equity import GPUEquityCalculator
        gpu_available = True
    except ImportError:
        gpu_available = False
        logger.warning("GPU acceleration not available")
    
    # Test parameters
    player_hands = [['Ah', 'Kh']]
    community_cards = ['Qh', 'Jh', '10s']
    simulation_counts = [50, 100, 200, 500, 1000, 2000]
    
    results = {
        'simulation_counts': simulation_counts,
        'cpu_times': [],
        'gpu_times': [],
        'speedups': []
    }
    
    # Test CPU performance
    logger.info("Testing CPU performance...")
    cpu_calculator = EquityCalculator()
    
    for sim_count in simulation_counts:
        start_time = time.time()
        
        # Run multiple calculations for stable timing
        for _ in range(10):
            win_prob, _, _ = cpu_calculator.calculate_equity_monte_carlo(
                player_hands, community_cards, None,
                num_simulations=sim_count, num_opponents=2
            )
        
        cpu_time = (time.time() - start_time) / 10  # Average time per calculation
        results['cpu_times'].append(cpu_time)
        logger.info(f"CPU - {sim_count} simulations: {cpu_time:.4f}s per calculation")
    
    # Test GPU performance if available
    if gpu_available:
        logger.info("Testing GPU performance...")
        try:
            gpu_calculator = GPUEquityCalculator(use_gpu=True)
            
            for i, sim_count in enumerate(simulation_counts):
                start_time = time.time()
                
                # Run multiple calculations for stable timing
                for _ in range(10):
                    try:
                        equities, _, _ = gpu_calculator.calculate_equity_batch(
                            player_hands, community_cards, num_simulations=sim_count
                        )
                    except Exception as e:
                        logger.warning(f"GPU calculation failed: {e}")
                        # Use CPU fallback time
                        gpu_time = results['cpu_times'][i]
                        break
                else:
                    gpu_time = (time.time() - start_time) / 10  # Average time per calculation
                
                results['gpu_times'].append(gpu_time)
                speedup = results['cpu_times'][i] / gpu_time if gpu_time > 0 else 1.0
                results['speedups'].append(speedup)
                logger.info(f"GPU - {sim_count} simulations: {gpu_time:.4f}s per calculation (speedup: {speedup:.2f}x)")
        
        except Exception as e:
            logger.error(f"GPU testing failed: {e}")
            gpu_available = False
    
    if not gpu_available:
        results['gpu_times'] = results['cpu_times']
        results['speedups'] = [1.0] * len(simulation_counts)
    
    return results

def benchmark_cfr_training():
    """Benchmark CFR training performance."""
    logger.info("\n=== CFR TRAINING BENCHMARK ===")
    
    # Try different training approaches
    try:
        from train_cfr import CFRTrainer
        standard_available = True
    except ImportError:
        standard_available = False
        logger.warning("Standard CFR trainer not available")
    
    try:
        from gpu_cfr_trainer import GPUCFRTrainer
        gpu_trainer_available = True
    except ImportError:
        gpu_trainer_available = False
        logger.warning("GPU CFR trainer not available")
    
    results = {
        'iterations': [50, 100, 200],
        'standard_times': [],
        'gpu_times': [],
        'speedups': []
    }
    
    # Test standard CFR training
    if standard_available:
        logger.info("Testing standard CFR training...")
        try:
            trainer = CFRTrainer(num_players=6, use_gpu=False)
            
            for iterations in results['iterations']:
                start_time = time.time()
                trainer.train(iterations)
                train_time = time.time() - start_time
                results['standard_times'].append(train_time)
                logger.info(f"Standard CFR - {iterations} iterations: {train_time:.2f}s")
        
        except Exception as e:
            logger.error(f"Standard CFR training failed: {e}")
            results['standard_times'] = [float('inf')] * len(results['iterations'])
    else:
        results['standard_times'] = [float('inf')] * len(results['iterations'])
    
    # Test GPU-enhanced CFR training
    if gpu_trainer_available:
        logger.info("Testing GPU-enhanced CFR training...")
        try:
            gpu_trainer = GPUCFRTrainer(num_players=6, use_gpu=True)
            
            for i, iterations in enumerate(results['iterations']):
                start_time = time.time()
                # Use batch training if available
                if hasattr(gpu_trainer, 'train_batch'):
                    gpu_trainer.train_batch(iterations)
                else:
                    # Fallback to standard training
                    train_time = results['standard_times'][i]
                
                if 'train_time' not in locals():
                    train_time = time.time() - start_time
                
                results['gpu_times'].append(train_time)
                
                if results['standard_times'][i] != float('inf'):
                    speedup = results['standard_times'][i] / train_time
                else:
                    speedup = 1.0
                
                results['speedups'].append(speedup)
                logger.info(f"GPU CFR - {iterations} iterations: {train_time:.2f}s (speedup: {speedup:.2f}x)")
        
        except Exception as e:
            logger.error(f"GPU CFR training failed: {e}")
            results['gpu_times'] = results['standard_times']
            results['speedups'] = [1.0] * len(results['iterations'])
    else:
        results['gpu_times'] = results['standard_times']
        results['speedups'] = [1.0] * len(results['iterations'])
    
    return results

def create_performance_plots(equity_results: Dict, cfr_results: Dict):
    """Create performance comparison plots."""
    logger.info("Creating performance plots...")
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    
    # Equity calculation times
    ax1.plot(equity_results['simulation_counts'], equity_results['cpu_times'], 'b-o', label='CPU')
    ax1.plot(equity_results['simulation_counts'], equity_results['gpu_times'], 'r-o', label='GPU/Optimized')
    ax1.set_xlabel('Number of Simulations')
    ax1.set_ylabel('Time per Calculation (seconds)')
    ax1.set_title('Equity Calculation Performance')
    ax1.legend()
    ax1.grid(True)
    
    # Equity calculation speedup
    ax2.plot(equity_results['simulation_counts'], equity_results['speedups'], 'g-o')
    ax2.set_xlabel('Number of Simulations')
    ax2.set_ylabel('Speedup Factor')
    ax2.set_title('Equity Calculation Speedup')
    ax2.grid(True)
    ax2.axhline(y=1, color='r', linestyle='--', alpha=0.5, label='No speedup')
    ax2.legend()
    
    # CFR training times
    ax3.bar([f"{i}\nStd" for i in cfr_results['iterations']], cfr_results['standard_times'], 
            alpha=0.7, label='Standard CFR', color='blue')
    ax3.bar([f"{i}\nGPU" for i in cfr_results['iterations']], cfr_results['gpu_times'], 
            alpha=0.7, label='GPU/Optimized CFR', color='red')
    ax3.set_ylabel('Training Time (seconds)')
    ax3.set_title('CFR Training Performance')
    ax3.legend()
    ax3.grid(True, axis='y')
    
    # CFR training speedup
    ax4.bar(range(len(cfr_results['iterations'])), cfr_results['speedups'], 
            alpha=0.7, color='green')
    ax4.set_xlabel('Training Iterations')
    ax4.set_ylabel('Speedup Factor')
    ax4.set_title('CFR Training Speedup')
    ax4.set_xticks(range(len(cfr_results['iterations'])))
    ax4.set_xticklabels(cfr_results['iterations'])
    ax4.grid(True, axis='y')
    ax4.axhline(y=1, color='r', linestyle='--', alpha=0.5, label='No speedup')
    ax4.legend()
    
    plt.tight_layout()
    plt.savefig('poker_bot_performance_comparison.png', dpi=150, bbox_inches='tight')
    logger.info("Performance plots saved as 'poker_bot_performance_comparison.png'")
    
    # Show plots if running interactively
    try:
        plt.show()
    except Exception:
        pass  # Headless environment

def generate_performance_report(equity_results: Dict, cfr_results: Dict):
    """Generate a comprehensive performance report."""
    logger.info("\n=== PERFORMANCE REPORT ===")
    
    # Equity calculation summary
    max_equity_speedup = max(equity_results['speedups'])
    avg_equity_speedup = np.mean(equity_results['speedups'])
    
    logger.info(f"EQUITY CALCULATION PERFORMANCE:")
    logger.info(f"  Maximum speedup: {max_equity_speedup:.2f}x")
    logger.info(f"  Average speedup: {avg_equity_speedup:.2f}x")
    logger.info(f"  Best performance at {equity_results['simulation_counts'][equity_results['speedups'].index(max_equity_speedup)]} simulations")
    
    # CFR training summary
    max_cfr_speedup = max(cfr_results['speedups'])
    avg_cfr_speedup = np.mean(cfr_results['speedups'])
    
    logger.info(f"\nCFR TRAINING PERFORMANCE:")
    logger.info(f"  Maximum speedup: {max_cfr_speedup:.2f}x")
    logger.info(f"  Average speedup: {avg_cfr_speedup:.2f}x")
    
    # Recommendations
    logger.info(f"\nRECOMMENDations:")
    
    if max_equity_speedup > 1.5:
        logger.info(f"  ✅ GPU/Optimized equity calculation provides significant speedup")
        recommended_sims = equity_results['simulation_counts'][equity_results['speedups'].index(max_equity_speedup)]
        logger.info(f"  ✅ Recommended simulation count: {recommended_sims}")
    else:
        logger.info(f"  ⚠️  Limited benefit from GPU acceleration - CPU optimization recommended")
        logger.info(f"  ⚠️  Consider using 200-500 simulations for good balance of speed/accuracy")
    
    if max_cfr_speedup > 1.2:
        logger.info(f"  ✅ Enhanced CFR training provides measurable improvement")
    else:
        logger.info(f"  ⚠️  CFR training improvements limited - focus on algorithm optimization")
    
    # Save report to file
    report = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'equity_results': equity_results,
        'cfr_results': cfr_results,
        'summary': {
            'max_equity_speedup': max_equity_speedup,
            'avg_equity_speedup': avg_equity_speedup,
            'max_cfr_speedup': max_cfr_speedup,
            'avg_cfr_speedup': avg_cfr_speedup
        }
    }
    
    with open('performance_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"\nDetailed report saved to 'performance_report.json'")

def main():
    """Main performance demonstration."""
    logger.info("🚀 Poker Bot Performance Demo Starting...")
    logger.info("=" * 60)
    
    # Run benchmarks
    equity_results = benchmark_equity_calculations()
    cfr_results = benchmark_cfr_training()
    
    # Create visualizations
    try:
        create_performance_plots(equity_results, cfr_results)
    except ImportError:
        logger.warning("Matplotlib not available - skipping plots")
    except Exception as e:
        logger.error(f"Failed to create plots: {e}")
    
    # Generate report
    generate_performance_report(equity_results, cfr_results)
    
    logger.info("=" * 60)
    logger.info("🎉 Performance demo completed!")
    logger.info("Check 'performance_report.json' and 'poker_bot_performance_comparison.png' for results")

if __name__ == "__main__":
    main()
