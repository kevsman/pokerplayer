"""
Example: GPU Performance Monitoring
"""
import time
from gpu_accelerated_equity import GPUEquityCalculator
from equity_calculator import EquityCalculator
import json

def compare_performance():
    """Compare GPU vs CPU performance in real-time."""
    
    # Load config
    with open('gpu_config.json', 'r') as f:
        config = json.load(f)
    
    test_hands = [['Ah', 'Kh'], ['Qs', 'Js'], ['10h', '9h']]
    community_cards = ['Qh', 'Jh', '10s']
    
    print("Performance Comparison:")
    
    # CPU test
    cpu_calc = EquityCalculator()
    start = time.time()
    for hand in test_hands:
        cpu_calc.calculate_equity_monte_carlo(
            [hand], community_cards, None,
            num_simulations=config['monte_carlo_simulations'], 
            num_opponents=2
        )
    cpu_time = time.time() - start
    
    # GPU test (if available)
    if config['use_gpu']:
        gpu_calc = GPUEquityCalculator(use_gpu=True)
        start = time.time()
        gpu_calc.calculate_equity_batch(
            test_hands, community_cards, 
            num_simulations=config['monte_carlo_simulations']
        )
        gpu_time = time.time() - start
        speedup = cpu_time / gpu_time
        
        print(f"CPU Time: {cpu_time:.3f}s")
        print(f"GPU Time: {gpu_time:.3f}s")
        print(f"Speedup: {speedup:.2f}x")
    else:
        print(f"CPU Time: {cpu_time:.3f}s")
        print("GPU: Not available")

if __name__ == "__main__":
    compare_performance()
