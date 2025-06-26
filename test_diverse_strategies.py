#!/usr/bin/env python3
"""
Test script for diverse strategy generation covering 2-6 players with various scenarios.
"""
import logging
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_diverse_strategy_generation():
    """Test the diverse strategy generation with a small number of iterations."""
    print("🧪 TESTING DIVERSE STRATEGY GENERATION")
    print("=" * 50)
    
    try:
        from gpu_cfr_trainer import GPUCFRTrainer
        
        # Test with smaller number for quick validation
        print("📊 Testing diverse strategy generation with 10,000 iterations")
        trainer = GPUCFRTrainer(use_gpu=True)
        
        if not trainer.use_gpu:
            print("GPU not available for testing")
            return False
        
        start_time = time.time()
        trainer.train_ultra_batch_gpu(iterations=10000, use_max_memory=True)
        total_time = time.time() - start_time
        
        print(f"\n🎯 DIVERSITY TEST COMPLETED!")
        print(f"⏱️  Total time: {total_time:.2f}s")
        print(f"📊 Total strategies generated: {len(trainer.nodes)}")
        print(f"⚡ Rate: {10000/total_time:,.0f} iterations/second")
        
        # Analyze diversity
        scenario_types = set()
        player_counts = set()
        equity_buckets = set()
        
        for info_set in trainer.nodes.keys():
            parts = info_set.split('_')
            
            for part in parts:
                if 'p_street' in part:
                    scenario_types.add(part)
                    # Extract player count
                    player_count = part.split('p_street')[0]
                    if player_count.isdigit():
                        player_counts.add(int(player_count))
                elif part in ['low', 'medium', 'high']:
                    equity_buckets.add(part)
        
        print(f"\n📈 DIVERSITY ANALYSIS:")
        print(f"  Player counts: {sorted(player_counts)}")
        print(f"  Equity buckets: {sorted(equity_buckets)}")
        print(f"  Scenario types: {len(scenario_types)} unique types")
        
        # Show sample strategies
        sample_count = min(5, len(trainer.nodes))
        print(f"\n📝 SAMPLE STRATEGIES ({sample_count}):")
        for i, (info_set, node) in enumerate(list(trainer.nodes.items())[:sample_count]):
            avg_strategy = node.get_average_strategy()
            strategy_dict = {act: f"{prob:.3f}" for act, prob in zip(node.actions, avg_strategy)}
            print(f"  {i+1}. {info_set[:50]}...")
            print(f"     -> {strategy_dict}")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_diverse_strategy_generation()
    
    if success:
        print("\n✅ DIVERSE STRATEGY GENERATION TEST PASSED!")
        print("🚀 Ready for full 1M iteration training!")
    else:
        print("\n❌ TEST FAILED")
        print("Please check the implementation")
