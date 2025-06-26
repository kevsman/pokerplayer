#!/usr/bin/env python3
"""
Quick test of the strategy saving fix.
"""
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_strategy_saving():
    """Test the updated strategy saving functionality."""
    print("🧪 TESTING STRATEGY SAVING FIX")
    print("=" * 40)
    
    from gpu_cfr_trainer import GPUCFRTrainer
    
    # Run a small test
    trainer = GPUCFRTrainer(use_gpu=True)
    if trainer.use_gpu:
        print("Running small ultra-batch training...")
        trainer.train_ultra_batch_gpu(iterations=100, use_max_memory=False)
        print("Training completed!")
        
        # Check how many strategies were saved
        with open('strategy_table.json', 'r') as f:
            strategies = json.load(f)
        
        print(f"✅ Strategies saved: {len(strategies)}")
        print("📊 Sample strategy keys:")
        for i, key in enumerate(list(strategies.keys())[:5]):
            print(f"  {i+1}. {key}")
        
        if len(strategies) > 1:
            print("🎯 SUCCESS: Multiple strategies are being saved!")
        else:
            print("❌ ISSUE: Still only saving 1 strategy")
            
    else:
        print("GPU not available for testing")

if __name__ == "__main__":
    test_strategy_saving()
