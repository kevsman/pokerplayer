#!/usr/bin/env python3
"""
Fixed CFR Training Script
This script now implements a proper Counter-Factual Regret Minimization (CFR) trainer.
It replaces the previous heuristic-based strategy generation with a learning-based approach.
The trainer learns by simulating games and minimizing regret, which is the core of a poker solver.
"""
import logging
import numpy as np
from collections import defaultdict
from strategy_lookup import StrategyLookup
from hand_evaluator import HandEvaluator
from equity_calculator import EquityCalculator
from hand_abstraction import HandAbstraction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CFRNode:
    """A node in the CFR game tree."""
    def __init__(self, num_actions):
        self.num_actions = num_actions
        self.regret_sum = np.zeros(num_actions)
        self.strategy_sum = np.zeros(num_actions)
        self.strategy = np.repeat(1/num_actions, num_actions)

    def get_strategy(self):
        """Get the current strategy from the regret sums."""
        self.strategy = np.maximum(0, self.regret_sum)
        normalizing_sum = np.sum(self.strategy)
        if normalizing_sum > 0:
            self.strategy /= normalizing_sum
        else:
            self.strategy = np.repeat(1/self.num_actions, self.num_actions)
        return self.strategy

    def get_average_strategy(self):
        """Get the average strategy over all iterations."""
        normalizing_sum = np.sum(self.strategy_sum)
        if normalizing_sum > 0:
            return self.strategy_sum / normalizing_sum
        return np.repeat(1/self.num_actions, self.num_actions)

if __name__ == '__main__':
    from gpu_cfr_trainer import GPUCFRTrainer
    
    # This is a simplified training run. For a real bot, you would need many more iterations.
    trainer = GPUCFRTrainer(use_gpu=False) # Run on CPU
    logger.info("🚀 Starting FixedCFR-style training...")
    trainer.train_like_fixed_cfr(iterations=10000)
    logger.info("✅ Training complete.")
