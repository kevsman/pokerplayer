"""
Strategy lookup module for PokerBotV2.
Loads and retrieves pre-computed strategies from a strategy file using a direct hash lookup.
"""
import json
import os
import logging

logger = logging.getLogger(__name__)

class StrategyLookup:
    def __init__(self, strategy_file='strategy_table.json'):
        self.strategy_file = strategy_file
        logger.info(f"Initializing StrategyLookup with file: {strategy_file}")
        self.strategy_table = self._load_strategy_table()
        
        if self.strategy_table:
            logger.info(f"✅ Loaded {len(self.strategy_table)} strategies from file.")
        else:
            logger.warning(f"⚠️ Strategy file {self.strategy_file} is empty or could not be loaded.")

    def _load_strategy_table(self):
        """Loads the strategy table from the JSON file with corruption recovery."""
        if not os.path.exists(self.strategy_file):
            logger.error(f"Strategy file not found: {self.strategy_file}")
            return {}
        
        # Try to load main file
        for attempt_file in [self.strategy_file, self.strategy_file + ".backup"]:
            if not os.path.exists(attempt_file):
                continue
                
            try:
                logger.info(f"Attempting to load strategies from: {attempt_file}")
                with open(attempt_file, 'r') as f:
                    # Keys are stored as strings in JSON, so we convert them back to integers for lookup.
                    string_keys_table = json.load(f)
                    
                    # Validate the data structure
                    if not isinstance(string_keys_table, dict):
                        raise ValueError("Strategy file does not contain a valid dictionary")
                    
                    # Use a dictionary comprehension for efficient conversion with error handling
                    converted_table = {}
                    invalid_entries = 0
                    
                    for k, v in string_keys_table.items():
                        try:
                            hash_key = int(k)
                            if isinstance(v, dict) and all(isinstance(val, (int, float)) for val in v.values()):
                                converted_table[hash_key] = v
                            else:
                                invalid_entries += 1
                        except (ValueError, TypeError):
                            invalid_entries += 1
                    
                    if invalid_entries > 0:
                        logger.warning(f"Skipped {invalid_entries} invalid strategy entries")
                    
                    logger.info(f"Successfully loaded {len(converted_table)} valid strategies from {attempt_file}")
                    return converted_table
                    
            except (json.JSONDecodeError, IOError, ValueError) as e:
                logger.error(f"Error loading strategy file {attempt_file}: {e}")
                if attempt_file == self.strategy_file:
                    logger.info("Trying backup file...")
                    continue
        
        logger.error("All strategy file loading attempts failed")
        return {}

    def get_strategy_by_hash(self, info_hash: int):
        """
        Retrieves a strategy directly using the information state hash.
        
        Args:
            info_hash (int): The hash representing the current game state.
            
        Returns:
            dict: The strategy dictionary if found, otherwise None.
        """
        return self.strategy_table.get(info_hash)
    
    def get_similar_strategies(self, target_hash: int, max_candidates: int = 50):
        """
        Find strategies with similar hash values for fuzzy matching.
        
        Args:
            target_hash (int): The target hash we're looking for
            max_candidates (int): Maximum number of candidates to return
            
        Returns:
            list: List of (hash, strategy, similarity_score) tuples, sorted by similarity
        """
        if not self.strategy_table:
            return []
        
        candidates = []
        target_bits = bin(target_hash)[2:].zfill(64)  # Convert to 64-bit binary string
        
        # Sample a subset of strategies for performance (check every nth strategy)
        sample_size = min(10000, len(self.strategy_table))
        strategy_items = list(self.strategy_table.items())
        step = max(1, len(strategy_items) // sample_size)
        
        for i in range(0, len(strategy_items), step):
            hash_key, strategy = strategy_items[i]
            
            # Calculate bit similarity (Hamming distance)
            candidate_bits = bin(hash_key)[2:].zfill(64)
            similarity = sum(1 for a, b in zip(target_bits, candidate_bits) if a == b)
            
            candidates.append((hash_key, strategy, similarity))
            
            if len(candidates) >= max_candidates * 2:  # Get extra for better sorting
                break
        
        # Sort by similarity (higher is better) and return top candidates
        candidates.sort(key=lambda x: x[2], reverse=True)
        return candidates[:max_candidates]
    
    def get_strategy_with_fuzzy_fallback(self, info_hash: int, state_components: dict = None):
        """
        Get strategy with fuzzy matching fallback when exact match fails.
        
        Args:
            info_hash (int): The exact hash to look for first
            state_components (dict): Components used to build the hash for component-wise matching
            
        Returns:
            tuple: (strategy_dict, match_type) where match_type is 'exact', 'fuzzy', or None
        """
        # Try exact match first
        exact_strategy = self.get_strategy_by_hash(info_hash)
        if exact_strategy:
            return exact_strategy, 'exact'
        
        # Try fuzzy matching with similar hashes
        similar_strategies = self.get_similar_strategies(info_hash, max_candidates=20)
        
        if similar_strategies:
            # Use the most similar strategy
            best_hash, best_strategy, similarity_score = similar_strategies[0]
            
            # Only use fuzzy match if similarity is reasonably high (> 50% bit match)
            if similarity_score > 32:  # More than 50% of 64 bits match
                logger.info(f"🔄 Using fuzzy match: hash {best_hash} (similarity: {similarity_score}/64 bits)")
                return best_strategy, 'fuzzy'
        
        # Try component-wise fuzzy matching if we have state components
        if state_components:
            component_strategy = self._get_strategy_by_components(state_components)
            if component_strategy:
                return component_strategy, 'component'
        
        return None, None
    
    def _get_strategy_by_components(self, state_components: dict):
        """
        Find strategies with similar state components (street, position, pot size ranges).
        
        Args:
            state_components (dict): Dictionary with 'street', 'turn_index', 'pot_range', etc.
            
        Returns:
            dict: Strategy dictionary if found, otherwise None
        """
        if not self.strategy_table or not state_components:
            return None
        
        target_street = state_components.get('street', 0)
        target_position = state_components.get('turn_index', 0)
        target_pot = state_components.get('effective_pot', 0)
        target_players = state_components.get('num_active', 6)
        
        # Look for strategies from similar game states
        candidates = []
        
        for hash_key, strategy in list(self.strategy_table.items())[:5000]:  # Sample for performance
            # Reverse engineer components from hash (approximate)
            # This is a simplified reverse engineering - in practice you'd want to store components
            try:
                # Extract street from hash (first component)
                estimated_street = (hash_key // 10000000000) % 10
                estimated_position = (hash_key // 1000000000) % 10
                
                # Score based on component similarity
                score = 0
                if estimated_street == target_street:
                    score += 10  # Street match is very important
                elif abs(estimated_street - target_street) <= 1:
                    score += 5   # Adjacent streets get partial credit
                
                if estimated_position == target_position:
                    score += 5   # Position match is important
                elif abs(estimated_position - target_position) <= 1:
                    score += 2   # Adjacent positions get partial credit
                
                if score >= 10:  # Require at least exact street match
                    candidates.append((hash_key, strategy, score))
                    
            except:
                continue  # Skip if hash parsing fails
        
        if candidates:
            # Sort by score and return best match
            candidates.sort(key=lambda x: x[2], reverse=True)
            best_hash, best_strategy, score = candidates[0]
            logger.info(f"🔄 Using component-wise match: hash {best_hash} (score: {score})")
            return best_strategy
        
        return None
