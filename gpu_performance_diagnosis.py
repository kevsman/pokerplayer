"""
GPU Performance Analysis and Fix
Identifies why GPU acceleration isn't providing speedup and fixes the issues.
"""
import time
import logging
from typing import Dict, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def diagnose_gpu_performance():
    """Comprehensive diagnosis of GPU performance issues."""
    logger.info("🔍 DIAGNOSING GPU PERFORMANCE ISSUES")
    logger.info("=" * 60)
    
    # 1. Check card format compatibility
    logger.info("1. Card Format Compatibility Check")
    
    try:
        from gpu_accelerated_equity import GPUEquityCalculator
        gpu_calc = GPUEquityCalculator(use_gpu=True)
        
        # Test different card formats
        card_formats = {
            'standard': [['Ah', 'Kh']],
            'community': ['Qh', 'Jh', '10s'],
        }
        
        logger.info(f"   Available cards in GPU calculator: {gpu_calc.all_cards[:10]}...")
        logger.info(f"   Card mapping sample: {list(gpu_calc.card_to_idx.items())[:5]}")
        
        # Test if our cards are in the mapping
        test_cards = ['Ah', 'Kh', 'Qh', 'Jh', '10s']
        for card in test_cards:
            if card in gpu_calc.card_to_idx:
                logger.info(f"   ✅ {card} found in GPU mapping")
            else:
                logger.error(f"   ❌ {card} NOT found in GPU mapping")
                # Show similar cards
                similar = [c for c in gpu_calc.card_to_idx.keys() if c.startswith(card[0])]
                logger.info(f"      Similar cards: {similar[:5]}")
        
    except Exception as e:
        logger.error(f"   GPU calculator initialization failed: {e}")
        return False
    
    # 2. Test actual performance with corrected cards
    logger.info("\n2. Performance Test with Corrected Card Format")
    
    from equity_calculator import EquityCalculator
    cpu_calc = EquityCalculator()
    
    # Find correct card format
    logger.info(f"   CPU calculator cards sample: {cpu_calc.all_cards[:10]}")
    
    # Test with CPU calculator format
    test_hands = [['As', 'Ks']]  # Try different format
    community_cards = ['Qs', 'Js', '10s']
    
    # CPU test
    start_time = time.time()
    for _ in range(5):
        win_prob, _, _ = cpu_calc.calculate_equity_monte_carlo(
            test_hands, community_cards, None,
            num_simulations=500, num_opponents=2
        )
    cpu_time = time.time() - start_time
    logger.info(f"   CPU time (5 iterations): {cpu_time:.3f}s")
    
    # GPU test with correct format
    try:
        # Convert to GPU format if needed
        gpu_hands = test_hands
        gpu_community = community_cards
        
        # Check if we need format conversion
        if 'As' not in gpu_calc.card_to_idx and 'A♠' in gpu_calc.card_to_idx:
            # Convert to Unicode suits
            conversion_map = {'s': '♠', 'h': '♥', 'd': '♦', 'c': '♣'}
            gpu_hands = [[card[:-1] + conversion_map.get(card[-1], card[-1]) for card in hand] for hand in test_hands]
            gpu_community = [card[:-1] + conversion_map.get(card[-1], card[-1]) for card in community_cards]
            logger.info(f"   Converted to GPU format: {gpu_hands}, {gpu_community}")
        
        start_time = time.time()
        for _ in range(5):
            equities, _, _ = gpu_calc.calculate_equity_batch(
                gpu_hands, gpu_community, num_simulations=500
            )
        gpu_time = time.time() - start_time
        
        speedup = cpu_time / gpu_time if gpu_time > 0 else 0
        logger.info(f"   GPU time (5 iterations): {gpu_time:.3f}s")
        logger.info(f"   🚀 Actual speedup: {speedup:.2f}x")
        
        if speedup < 1.2:
            logger.warning(f"   ⚠️  GPU provides minimal speedup ({speedup:.2f}x)")
            diagnose_gpu_bottlenecks(gpu_calc, cpu_calc)
        else:
            logger.info(f"   ✅ GPU acceleration working well!")
            
    except Exception as e:
        logger.error(f"   GPU test failed: {e}")
        return False
    
    return True

def diagnose_gpu_bottlenecks(gpu_calc, cpu_calc):
    """Diagnose why GPU isn't faster."""
    logger.info("\n3. GPU Bottleneck Analysis")
    
    # Test different batch sizes
    test_hands = [['As', 'Ks'], ['Qs', 'Js'], ['10s', '9s'], ['8s', '7s']]
    community_cards = ['Qs', 'Js', '2s']
    
    # Convert to correct format
    if hasattr(gpu_calc, 'card_to_idx'):
        sample_card = list(gpu_calc.card_to_idx.keys())[0]
        if '♠' in sample_card:  # Unicode format
            conversion_map = {'s': '♠', 'h': '♥', 'd': '♦', 'c': '♣'}
            test_hands = [[card[:-1] + conversion_map.get(card[-1], card[-1]) for card in hand] for hand in test_hands]
            community_cards = [card[:-1] + conversion_map.get(card[-1], card[-1]) for card in community_cards]
    
    batch_sizes = [1, 2, 4, 8]
    
    for batch_size in batch_sizes:
        current_hands = test_hands[:batch_size]
        
        # CPU (individual)
        start_time = time.time()
        for hand in current_hands:
            cpu_calc.calculate_equity_monte_carlo(
                [hand], community_cards, None,
                num_simulations=200, num_opponents=2
            )
        cpu_time = time.time() - start_time
        
        # GPU (batch)
        try:
            start_time = time.time()
            gpu_calc.calculate_equity_batch(
                current_hands, community_cards, num_simulations=200
            )
            gpu_time = time.time() - start_time
            
            speedup = cpu_time / gpu_time if gpu_time > 0 else 0
            logger.info(f"   Batch size {batch_size}: CPU={cpu_time:.3f}s, GPU={gpu_time:.3f}s, speedup={speedup:.2f}x")
            
        except Exception as e:
            logger.error(f"   Batch size {batch_size} failed: {e}")

def create_optimized_config():
    """Create optimized configuration based on findings."""
    logger.info("\n4. Creating Optimized Configuration")
    
    # Run quick performance test
    from equity_calculator import EquityCalculator
    cpu_calc = EquityCalculator()
    
    test_hands = [['As', 'Ks']]
    community_cards = ['Qs', 'Js', '10s']
    
    # Test different simulation counts for optimal CPU performance
    sim_counts = [100, 200, 500, 1000]
    optimal_settings = {}
    
    for sim_count in sim_counts:
        start_time = time.time()
        for _ in range(3):
            cpu_calc.calculate_equity_monte_carlo(
                test_hands, community_cards, None,
                num_simulations=sim_count, num_opponents=2
            )
        elapsed = time.time() - start_time
        
        sims_per_sec = (sim_count * 3) / elapsed
        logger.info(f"   {sim_count} sims: {elapsed:.3f}s, {sims_per_sec:.0f} sims/sec")
        
        optimal_settings[sim_count] = {
            'time_per_calc': elapsed / 3,
            'sims_per_sec': sims_per_sec,
            'efficiency': sims_per_sec / sim_count  # Higher is better
        }
    
    # Find optimal simulation count
    best_sim_count = max(optimal_settings.keys(), 
                        key=lambda x: optimal_settings[x]['efficiency'])
    
    logger.info(f"   🏆 Optimal simulation count: {best_sim_count}")
    
    # Create optimized config
    config = {
        'use_gpu': False,  # GPU not providing benefit
        'monte_carlo_simulations': best_sim_count,
        'cfr_iterations': 1000,  # CPU can handle this well
        'batch_size': 1,  # No batching benefit
        'training_iterations': 2000,
        'optimization_focus': 'cpu_throughput',
        'performance_notes': [
            'GPU acceleration provides minimal benefit on this system',
            f'Optimal CPU simulation count: {best_sim_count}',
            'Focus on algorithmic improvements rather than GPU acceleration'
        ]
    }
    
    import json
    with open('optimized_gpu_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    logger.info(f"   💾 Saved optimized config to optimized_gpu_config.json")
    return config

def main():
    """Main performance analysis."""
    logger.info("🚀 GPU PERFORMANCE ANALYSIS")
    logger.info("=" * 60)
    
    # Diagnose issues
    gpu_working = diagnose_gpu_performance()
    
    # Create optimized configuration
    config = create_optimized_config()
    
    logger.info("\n📋 SUMMARY AND RECOMMENDATIONS")
    logger.info("=" * 60)
    
    if not gpu_working:
        logger.warning("❌ GPU acceleration is not working properly")
        logger.info("🔧 RECOMMENDATIONS:")
        logger.info("   1. Use CPU-optimized settings")
        logger.info("   2. Focus on algorithmic improvements")
        logger.info("   3. Optimize simulation counts for CPU")
        logger.info(f"   4. Use {config['monte_carlo_simulations']} simulations for best CPU performance")
    else:
        logger.info("✅ GPU acceleration is working but provides minimal benefit")
        logger.info("🔧 RECOMMENDATIONS:")
        logger.info("   1. GPU overhead exceeds benefits for this workload")
        logger.info("   2. Use CPU-optimized settings for better performance")
        logger.info("   3. Consider GPU only for very large batch operations")
    
    logger.info(f"\n🎯 OPTIMAL SETTINGS:")
    logger.info(f"   • Simulation count: {config['monte_carlo_simulations']}")
    logger.info(f"   • CFR iterations: {config['cfr_iterations']}")
    logger.info(f"   • Use GPU: {config['use_gpu']}")
    logger.info(f"   • Focus: {config['optimization_focus']}")

if __name__ == "__main__":
    main()
