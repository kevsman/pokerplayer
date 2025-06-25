"""
Quick Performance Demo for Poker Bot GPU Acceleration
Focuses on practical improvements without complex CFR training.
"""
import time
import logging
import statistics

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_simulation_improvements():
    """Test the impact of different simulation counts on performance and accuracy."""
    logger.info("🎯 Testing Simulation Count Optimizations...")
    
    from equity_calculator import EquityCalculator
    
    calculator = EquityCalculator()
    player_hands = [['Ah', 'Kh']]
    community_cards = ['Qh', 'Jh', '10s']
    
    # Test different simulation counts
    sim_counts = [50, 100, 200, 500, 1000]
    results = {}
    
    for sim_count in sim_counts:
        times = []
        equities = []
        
        # Run multiple tests for stable results
        for _ in range(5):
            start_time = time.time()
            win_prob, _, _ = calculator.calculate_equity_monte_carlo(
                player_hands, community_cards, None,
                num_simulations=sim_count, num_opponents=2
            )
            elapsed = time.time() - start_time
            
            times.append(elapsed)
            equities.append(win_prob)
        
        avg_time = statistics.mean(times)
        avg_equity = statistics.mean(equities)
        equity_std = statistics.stdev(equities) if len(equities) > 1 else 0
        
        results[sim_count] = {
            'avg_time': avg_time,
            'avg_equity': avg_equity,
            'equity_std': equity_std,
            'sims_per_sec': sim_count / avg_time
        }
        
        logger.info(f"{sim_count:4d} sims: {avg_time:.3f}s, equity={avg_equity:.3f}±{equity_std:.3f}, {sim_count/avg_time:.0f} sims/sec")
    
    # Find optimal simulation count (best speed/accuracy tradeoff)
    efficiency_scores = {}
    for sim_count, data in results.items():
        # Score based on speed and low variance
        speed_score = data['sims_per_sec'] / max(r['sims_per_sec'] for r in results.values())
        accuracy_score = 1.0 / (1.0 + data['equity_std'] * 10)  # Lower std deviation is better
        efficiency_scores[sim_count] = speed_score * accuracy_score
    
    optimal_sim_count = max(efficiency_scores, key=efficiency_scores.get)
    logger.info(f"🏆 Optimal simulation count: {optimal_sim_count} (efficiency score: {efficiency_scores[optimal_sim_count]:.3f})")
    
    return results, optimal_sim_count

def test_enhanced_cfr_solver():
    """Test the enhanced CFR solver with optimized simulation counts."""
    logger.info("\n🧠 Testing Enhanced CFR Solver...")
    
    try:
        from cfr_solver_enhanced import CFRSolver
        enhanced_available = True
    except ImportError:
        logger.warning("Enhanced CFR solver not available")
        enhanced_available = False
    
    # Test standard CFR solver
    from cfr_solver import CFRSolver as StandardCFRSolver
    from hand_evaluator import HandEvaluator
    from equity_calculator import EquityCalculator  
    from hand_abstraction import HandAbstraction
    
    hand_evaluator = HandEvaluator()
    equity_calculator = EquityCalculator()
    abstraction = HandAbstraction(hand_evaluator, equity_calculator)
    
    # Test parameters
    player_cards = ['Ah', 'Kh']
    community_cards = ['Qh', 'Jh', '10s']
    pot_size = 100
    actions = ['fold', 'call', 'raise']
    
    results = {}
    
    # Test standard solver
    logger.info("Testing standard CFR solver...")
    standard_solver = StandardCFRSolver(abstraction, hand_evaluator, equity_calculator)
    
    start_time = time.time()
    strategy = standard_solver.solve(player_cards, community_cards, pot_size, actions, 'flop', iterations=100)
    standard_time = time.time() - start_time
    
    results['standard'] = {
        'time': standard_time,
        'strategy': strategy
    }
    logger.info(f"Standard solver: {standard_time:.3f}s, strategy={strategy}")
    
    # Test enhanced solver if available
    if enhanced_available:
        logger.info("Testing enhanced CFR solver...")
        enhanced_solver = CFRSolver(abstraction, hand_evaluator, equity_calculator, use_gpu=True)
        
        start_time = time.time()
        strategy = enhanced_solver.solve(player_cards, community_cards, pot_size, actions, 'flop', iterations=100)
        enhanced_time = time.time() - start_time
        
        results['enhanced'] = {
            'time': enhanced_time,
            'strategy': strategy
        }
        
        speedup = standard_time / enhanced_time if enhanced_time > 0 else 1.0
        logger.info(f"Enhanced solver: {enhanced_time:.3f}s, strategy={strategy}")
        logger.info(f"🚀 CFR Solver Speedup: {speedup:.2f}x")
    
    return results

def test_batch_processing():
    """Test batch processing capabilities for multiple scenarios."""
    logger.info("\n📦 Testing Batch Processing...")
    
    try:
        from gpu_accelerated_equity import GPUEquityCalculator
        gpu_available = True
    except ImportError:
        logger.warning("GPU equity calculator not available")
        gpu_available = False
    
    from equity_calculator import EquityCalculator
    
    # Test scenarios
    test_hands = [
        ['Ah', 'Kh'],
        ['Qs', 'Js'],
        ['10h', '9h'],
        ['As', 'Ad'],
        ['7c', '7d']
    ]
    community_cards = ['Qh', 'Jh', '10s']
    
    # Test standard (individual) processing
    logger.info("Testing individual equity calculations...")
    cpu_calculator = EquityCalculator()
    
    start_time = time.time()
    individual_equities = []
    for hand in test_hands:
        win_prob, _, _ = cpu_calculator.calculate_equity_monte_carlo(
            [hand], community_cards, None, num_simulations=500, num_opponents=2
        )
        individual_equities.append(win_prob)
    individual_time = time.time() - start_time
    
    logger.info(f"Individual processing: {individual_time:.3f}s")
    logger.info(f"Equities: {[f'{eq:.3f}' for eq in individual_equities]}")
    
    # Test batch processing if available
    if gpu_available:
        logger.info("Testing batch equity calculations...")
        try:
            gpu_calculator = GPUEquityCalculator(use_gpu=True)
            
            start_time = time.time()
            batch_equities, mean_eq, std_eq = gpu_calculator.calculate_equity_batch(
                test_hands, community_cards, num_simulations=500
            )
            batch_time = time.time() - start_time
            
            speedup = individual_time / batch_time if batch_time > 0 else 1.0
            logger.info(f"Batch processing: {batch_time:.3f}s")
            logger.info(f"Equities: {[f'{eq:.3f}' for eq in batch_equities]}")
            logger.info(f"🚀 Batch Processing Speedup: {speedup:.2f}x")
            
            return {
                'individual_time': individual_time,
                'batch_time': batch_time,
                'speedup': speedup,
                'individual_equities': individual_equities,
                'batch_equities': batch_equities
            }
        
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
    
    return {
        'individual_time': individual_time,
        'batch_time': individual_time,
        'speedup': 1.0,
        'individual_equities': individual_equities,
        'batch_equities': individual_equities
    }

def generate_recommendations(sim_results, cfr_results, batch_results, optimal_sim_count):
    """Generate performance optimization recommendations."""
    logger.info("\n📋 PERFORMANCE OPTIMIZATION RECOMMENDATIONS")
    logger.info("=" * 60)
    
    # Simulation count recommendations
    logger.info(f"1. SIMULATION COUNTS:")
    logger.info(f"   ✅ Optimal count: {optimal_sim_count} simulations")
    logger.info(f"   ✅ Provides good balance of speed and accuracy")
    
    best_efficiency = max(sim_results[optimal_sim_count]['sims_per_sec'] for optimal_sim_count in sim_results)
    logger.info(f"   ✅ Performance: {best_efficiency:.0f} simulations/second")
    
    # CFR solver recommendations
    logger.info(f"\n2. CFR SOLVER OPTIMIZATION:")
    if 'enhanced' in cfr_results:
        cfr_speedup = cfr_results['standard']['time'] / cfr_results['enhanced']['time']
        if cfr_speedup > 1.1:
            logger.info(f"   ✅ Enhanced CFR solver provides {cfr_speedup:.2f}x speedup")
            logger.info(f"   ✅ Recommended: Use enhanced CFR solver for training")
        else:
            logger.info(f"   ⚠️  Enhanced CFR solver provides minimal speedup ({cfr_speedup:.2f}x)")
    else:
        logger.info(f"   ⚠️  Enhanced CFR solver not available")
    
    # Batch processing recommendations
    logger.info(f"\n3. BATCH PROCESSING:")
    if batch_results['speedup'] > 1.2:
        logger.info(f"   ✅ Batch processing provides {batch_results['speedup']:.2f}x speedup")
        logger.info(f"   ✅ Recommended: Use batch calculations for multiple scenarios")
    else:
        logger.info(f"   ⚠️  Batch processing provides minimal benefit ({batch_results['speedup']:.2f}x)")
    
    # Overall recommendations
    logger.info(f"\n4. IMPLEMENTATION STRATEGY:")
    
    if optimal_sim_count >= 500:
        logger.info(f"   ✅ System can handle high simulation counts efficiently")
        logger.info(f"   ✅ Recommended CFR iterations: 1000-2000 for training")
        logger.info(f"   ✅ Recommended Monte Carlo sims: {optimal_sim_count}")
    else:
        logger.info(f"   ⚠️  System performance limited - use conservative settings")
        logger.info(f"   ⚠️  Recommended CFR iterations: 200-500 for training")
        logger.info(f"   ⚠️  Recommended Monte Carlo sims: {optimal_sim_count}")
    
    if batch_results['speedup'] > 1.5:
        logger.info(f"   ✅ GPU/batch acceleration is effective on this system")
        logger.info(f"   ✅ Consider implementing GPU acceleration for production")
    else:
        logger.info(f"   ⚠️  Focus on CPU optimization and algorithmic improvements")
    
    logger.info("=" * 60)

def main():
    """Main performance testing function."""
    logger.info("🚀 Poker Bot Performance Analysis")
    logger.info("=" * 60)
    
    # Test simulation count optimization
    sim_results, optimal_sim_count = test_simulation_improvements()
    
    # Test enhanced CFR solver
    cfr_results = test_enhanced_cfr_solver()
    
    # Test batch processing
    batch_results = test_batch_processing()
    
    # Generate recommendations
    generate_recommendations(sim_results, cfr_results, batch_results, optimal_sim_count)
    
    logger.info(f"\n🎉 Performance analysis completed!")
    logger.info(f"Key findings:")
    logger.info(f"  • Optimal simulation count: {optimal_sim_count}")
    logger.info(f"  • Best throughput: {sim_results[optimal_sim_count]['sims_per_sec']:.0f} sims/sec")
    if 'enhanced' in cfr_results:
        cfr_speedup = cfr_results['standard']['time'] / cfr_results['enhanced']['time']
        logger.info(f"  • CFR solver improvement: {cfr_speedup:.2f}x")
    logger.info(f"  • Batch processing improvement: {batch_results['speedup']:.2f}x")

if __name__ == "__main__":
    main()
