"""
Example: Basic GPU-Accelerated Poker Bot Usage
"""
from gpu_integrated_trainer import IntegratedTrainer
from cfr_solver import CFRSolver
import json

# Load optimal settings
with open('gpu_config.json', 'r') as f:
    config = json.load(f)

def main():
    print("Starting GPU-Accelerated Poker Bot Training...")
    
    # Initialize trainer with GPU acceleration
    trainer = IntegratedTrainer(use_gpu=config['use_gpu'])
    
    # Train strategies with optimal settings
    training_stats = trainer.train_strategies(
        num_iterations=config['training_iterations']
    )
    
    print(f"Training completed!")
    print(f"GPU Used: {training_stats['gpu_accelerated']}")
    print(f"Training Time: {training_stats['total_time']:.2f}s")
    print(f"Iterations: {training_stats['total_iterations']}")

if __name__ == "__main__":
    main()
