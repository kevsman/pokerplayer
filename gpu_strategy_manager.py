import cupy as cp
import numpy as np
import logging
import json
import os

logger = logging.getLogger(__name__)

class GPUStrategyManager:
    def __init__(self, num_actions=3, initial_capacity=1_000_000, dtype=cp.float32):
        self.num_actions = num_actions
        self.capacity = initial_capacity
        self.dtype = dtype # Store dtype
        
        self.node_map = {}
        self.next_node_index = 0
        
        self.regret_sum = cp.zeros((self.capacity, self.num_actions), dtype=self.dtype)
        self.strategy_sum = cp.zeros((self.capacity, self.num_actions), dtype=self.dtype)
        
        logger.info(f"GPUStrategyManager initialized with capacity for {self.capacity} nodes and dtype {self.dtype}.")

    def _resize_if_needed(self):
        if self.next_node_index >= self.capacity:
            new_capacity = self.capacity * 2
            logger.info(f"Resizing strategy arrays from {self.capacity} to {new_capacity}")
            
            new_regret_sum = cp.zeros((new_capacity, self.num_actions), dtype=self.dtype)
            new_regret_sum[:self.capacity] = self.regret_sum
            self.regret_sum = new_regret_sum
            
            new_strategy_sum = cp.zeros((new_capacity, self.num_actions), dtype=self.dtype)
            new_strategy_sum[:self.capacity] = self.strategy_sum
            self.strategy_sum = new_strategy_sum
            
            self.capacity = new_capacity

    def get_node_indices(self, info_state_hashes: list) -> cp.ndarray:
        indices = []
        for h in info_state_hashes:
            if h not in self.node_map:
                self._resize_if_needed()
                index = self.next_node_index
                self.node_map[h] = index
                self.next_node_index += 1
                indices.append(index)
            else:
                indices.append(self.node_map[h])
        return cp.array(indices, dtype=cp.int32)

    def get_strategies(self, node_indices: cp.ndarray) -> cp.ndarray:
        regrets = self.regret_sum[node_indices]
        strategies = cp.maximum(0, regrets)
        normalizing_sum = cp.sum(strategies, axis=1, keepdims=True)
        default_strategy = cp.full((1, self.num_actions), 1.0 / self.num_actions, dtype=self.dtype)
        strategies = cp.where(normalizing_sum > 0, strategies / normalizing_sum, default_strategy)
        return strategies

    def update_regrets_and_strategies(self, node_indices: cp.ndarray, regrets: cp.ndarray, strategies: cp.ndarray, reach_probs: cp.ndarray):
        reach_probs_b = reach_probs[:, None]
        # Ensure dtypes match for in-place operations
        self.regret_sum.scatter_add(node_indices, regrets.astype(self.dtype))
        self.strategy_sum.scatter_add(node_indices, (reach_probs_b * strategies).astype(self.dtype))

    def get_average_strategies(self):
        strategy_sum_cpu = cp.asnumpy(self.strategy_sum[:self.next_node_index])
        normalizing_sum = np.sum(strategy_sum_cpu, axis=1, keepdims=True)
        
        # Determine numpy dtype from cupy dtype
        numpy_dtype = np.float16 if self.dtype == cp.float16 else np.float32

        avg_strategies = np.where(
            normalizing_sum > 0,
            strategy_sum_cpu / normalizing_sum,
            np.full((1, self.num_actions), 1.0 / self.num_actions, dtype=numpy_dtype)
        )
        return avg_strategies

    def save_strategy_table(self, filename="strategy_table.json"):
        logger.info(f"Saving {self.next_node_index} strategies to {filename}...")
        avg_strategies = self.get_average_strategies()
        index_to_hash = {v: k for k, v in self.node_map.items()}
        
        strategy_dict = {}
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    strategy_dict = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                strategy_dict = {}

        for i in range(self.next_node_index):
            info_hash = index_to_hash.get(i, f"unknown_hash_{i}")
            strategy = {f"action_{j}": float(prob) for j, prob in enumerate(avg_strategies[i])}
            strategy_dict[str(info_hash)] = strategy
            
        try:
            with open(filename, 'w') as f:
                json.dump(strategy_dict, f)
            logger.info(f"Successfully saved strategy table with {len(strategy_dict)} total strategies.")
        except Exception as e:
            logger.error(f"Error saving strategy table: {e}")
