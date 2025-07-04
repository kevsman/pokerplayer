import cupy as cp
import numpy as np
import logging
import json
import os

logger = logging.getLogger(__name__)

class GPUStrategyManager:
    def __init__(self, num_actions=6, initial_capacity=1_000_000, dtype=cp.float32):
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

        # --- CFR+ Enhancement ---
        # After adding new regrets, clamp them to be non-negative.
        # This is the core of the CFR+ algorithm.
        # We apply this to the updated regrets in-place.
        updated_regrets = self.regret_sum[node_indices]
        self.regret_sum[node_indices] = cp.maximum(updated_regrets, 0)

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
        
        # Use atomic write with temporary file to prevent corruption
        temp_filename = filename + ".tmp"
        backup_filename = filename + ".backup"
        
        try:
            # Create backup of existing file
            if os.path.exists(filename):
                import shutil
                shutil.copy2(filename, backup_filename)
                logger.info(f"Created backup: {backup_filename}")
            
            avg_strategies = self.get_average_strategies()
            index_to_hash = {v: k for k, v in self.node_map.items()}
            
            # Load existing strategies if any
            strategy_dict = {}
            if os.path.exists(filename):
                try:
                    with open(filename, 'r') as f:
                        strategy_dict = json.load(f)
                        logger.info(f"Loaded {len(strategy_dict)} existing strategies")
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    logger.warning(f"Could not load existing strategies: {e}")
                    strategy_dict = {}

            # Add new strategies with reduced precision to save space
            new_strategies_count = 0
            for i in range(self.next_node_index):
                info_hash = index_to_hash.get(i, f"unknown_hash_{i}")
                hash_key = str(info_hash)
                
                if hash_key not in strategy_dict:  # Only add new strategies
                    # Round to 4 decimal places to reduce file size and prevent precision issues
                    strategy = {f"action_{j}": round(float(prob), 4) for j, prob in enumerate(avg_strategies[i])}
                    strategy_dict[hash_key] = strategy
                    new_strategies_count += 1
            
            logger.info(f"Added {new_strategies_count} new strategies")
            
            # Write to temporary file first (atomic operation)
            with open(temp_filename, 'w') as f:
                json.dump(strategy_dict, f, separators=(',', ':'))  # Compact format
            
            # Only replace original if temp file was written successfully
            import shutil
            shutil.move(temp_filename, filename)
            
            logger.info(f"Successfully saved strategy table with {len(strategy_dict)} total strategies.")
            
            # Clean up backup after successful save
            if os.path.exists(backup_filename):
                os.remove(backup_filename)
                
        except Exception as e:
            logger.error(f"Error saving strategy table: {e}")
            
            # Restore from backup if something went wrong
            if os.path.exists(backup_filename):
                import shutil
                shutil.move(backup_filename, filename)
                logger.info("Restored from backup due to save error")
            
            # Clean up temp file
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
